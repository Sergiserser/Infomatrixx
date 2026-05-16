"""
StepPrep

Prototype for detecting dangerous events from microphone + camera input.

Install dependencies:
    pip install opencv-python numpy sounddevice mediapipe Pillow

Run:
    python "rescue app.py"

Important safety note:
    The app starts in DEMO mode. It will show alarms and save evidence, but it
    will not call emergency services unless you explicitly enable it through
    environment variables. This is deliberate: false emergency calls can harm
    real people and may be illegal.

Optional real-call mode through Twilio or another SIP/phone gateway:
    set EMERGENCY_REAL_ACTION=1
    set EMERGENCY_NUMBER=0977477926
    set TWILIO_ACCOUNT_SID=...
    set TWILIO_AUTH_TOKEN=...
    set TWILIO_FROM_NUMBER=...

Keyboard in the desktop window:
    q  quit
    c  confirm/call now when alarm is active
    x  cancel current alarm
    1  monitoring tab
    2  shelter feed tab
    3  emergency supplies tab
    4  settings/language tab
    a  add local shelter from NEW_SHELTER_* environment variables
    l  Google login/registration
    g  refresh Google Maps shelter search
    m  open shelter map/search
    t  toggle Ukrainian/English language
"""

# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownParameterType=false, reportUnknownLambdaType=false

from __future__ import annotations

import base64
import hashlib
import html
import json
import math
import mimetypes
import os
import queue
import re
import time
import threading
import subprocess
import zipfile
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Optional, Sequence, Callable
try:
    import mediapipe as mp  # type: ignore[import]
except ImportError:
    mp: Any = None

try:
    import winsound
except ImportError:
    winsound: Any = None

import numpy as np
import cv2
import sounddevice as sd

import urllib.request
import urllib.parse
from localization import SUPPORTED_LANGUAGES, Translator, get_translator
import webbrowser
import secrets

tk: Any = None
try:
    import tkinter as tk
except ImportError:
    tk = None

Image: Any = None
ImageDraw: Any = None
ImageFont: Any = None
ImageTk: Any = None
try:
    from PIL import Image, ImageDraw, ImageFont, ImageTk
except ImportError:
    Image = None
    ImageDraw = None
    ImageFont = None
    ImageTk = None


APP_DIR = Path(__file__).resolve().parent
EVIDENCE_DIR = APP_DIR / "emergency_evidence"


_FONT_CACHE: dict[int, Any] = {}


def _has_unicode_text(text: str) -> bool:
    return any(ord(character) > 127 for character in str(text))


def _load_ui_font(size: int) -> Any:
    if ImageFont is None:
        return None
    size = max(10, int(size))
    cached = _FONT_CACHE.get(size)
    if cached is not None:
        return cached

    candidates = [
        os.getenv("RESCUE_UI_FONT", ""),
        r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\segoeui.ttf",
        r"C:\Windows\Fonts\calibri.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for candidate in candidates:
        if not candidate:
            continue
        try:
            font = ImageFont.truetype(candidate, size)
            _FONT_CACHE[size] = font
            return font
        except Exception:
            continue

    try:
        font = ImageFont.load_default()
        _FONT_CACHE[size] = font
        return font
    except Exception:
        return None


def put_text(
    frame: np.ndarray,
    text: object,
    org: tuple[int, int],
    font_face: int,
    font_scale: float,
    color: tuple[int, int, int],
    thickness: int = 1,
    line_type: int = cv2.LINE_AA,
) -> None:
    rendered_text = str(text)
    if not _has_unicode_text(rendered_text) or Image is None or ImageDraw is None:
        cv2.putText(frame, rendered_text, org, font_face, font_scale, color, thickness, line_type)
        return

    font_size = max(12, int(font_scale * 34))
    font = _load_ui_font(font_size)
    if font is None:
        cv2.putText(
            frame,
            rendered_text.encode("ascii", "replace").decode("ascii"),
            org,
            font_face,
            font_scale,
            color,
            thickness,
            line_type,
        )
        return

    image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(image)
    x, baseline_y = org
    y = max(0, baseline_y - font_size)
    rgb_color = (int(color[2]), int(color[1]), int(color[0]))
    stroke_width = max(0, thickness - 1)
    draw.text((x, y), rendered_text, font=font, fill=rgb_color, stroke_width=stroke_width)
    frame[:] = cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2BGR)


# Runtime settings / Налаштування запуску
@dataclass(frozen=True)
class RescueConfig:
    app_language: str = os.getenv("APP_LANG", os.getenv("RESCUE_LANG", "uk"))

    # Camera and audio input / Камера та аудіовхід
    camera_index: int = int(os.getenv("CAMERA_INDEX", "0"))
    sample_rate: int = int(os.getenv("AUDIO_SAMPLE_RATE", "16000"))
    audio_block_size: int = int(os.getenv("AUDIO_BLOCK_SIZE", "1024"))

    # Alarm behavior / Поведінка тривоги
    risk_threshold: float = float(os.getenv("RISK_THRESHOLD", "70"))
    countdown_seconds: float = float(os.getenv("EMERGENCY_COUNTDOWN_SECONDS", "8"))
    emergency_number: str = os.getenv("EMERGENCY_NUMBER", "0977477926")
    real_action_enabled: bool = os.getenv("EMERGENCY_REAL_ACTION", "0") == "1"
    save_evidence: bool = os.getenv("SAVE_EMERGENCY_EVIDENCE", "1") == "1"
    min_seconds_between_alerts: float = float(os.getenv("ALERT_COOLDOWN_SECONDS", "20"))
    gesture_hold_seconds: float = float(os.getenv("GESTURE_HOLD_SECONDS", "1.1"))
    hand_landmarker_model: str = os.getenv(
        "HAND_LANDMARKER_MODEL",
        str(APP_DIR / "hand_landmarker.task"),
    )

    # External call provider / Зовнішній сервіс дзвінка
    twilio_account_sid: str = os.getenv("TWILIO_ACCOUNT_SID", "")
    twilio_auth_token: str = os.getenv("TWILIO_AUTH_TOKEN", "")
    twilio_from_number: str = os.getenv("TWILIO_FROM_NUMBER", "")
    local_action_command: str = os.getenv("EMERGENCY_ACTION_COMMAND", "")

    # Shelter tab / Вкладка укриття
    shelters_file: str = os.getenv("SHELTERS_FILE", str(APP_DIR / "shelters.json"))
    user_lat: str = os.getenv("USER_LAT", "")
    user_lon: str = os.getenv("USER_LON", "")
    open_shelter_map_on_alarm: bool = os.getenv("OPEN_SHELTER_MAP_ON_ALARM", "0") == "1"
    google_maps_api_key: str = os.getenv("GOOGLE_MAPS_API_KEY", "")
    google_maps_query: str = os.getenv("GOOGLE_MAPS_SHELTER_QUERY", "")
    google_maps_radius_m: float = float(os.getenv("GOOGLE_MAPS_RADIUS_M", "1000"))
    google_maps_language: str = os.getenv("GOOGLE_MAPS_LANGUAGE", "")
    overpass_api_url: str = os.getenv("OVERPASS_API_URL", "https://overpass-api.de/api/interpreter")
    auto_location_url: str = os.getenv("AUTO_LOCATION_URL", "https://ipapi.co/json/")
    passive_shelter_refresh_seconds: float = float(os.getenv("PASSIVE_SHELTER_REFRESH_SECONDS", "90"))

    # Local HTTP server for camera view / Локальний HTTP-сервер для перегляду камери
    server_enabled: bool = os.getenv("RESCUE_SERVER_ENABLED", "0") == "1"
    server_port: int = int(os.getenv("RESCUE_SERVER_PORT", "8080"))
    api_host: str = os.getenv("RESCUE_API_HOST", "127.0.0.1")
    api_port: int = int(os.getenv("RESCUE_API_PORT", os.getenv("RESCUE_SERVER_PORT", "8080")))
    api_frontend_dir: str = os.getenv("RESCUE_FRONTEND_DIR", str(APP_DIR / "figma design" / "dist"))

    # App mode: 'api' exposes REST endpoints for the Figma/React UI; 'full' keeps the legacy Tk UI.
    mode: str = os.getenv("RESCUE_MODE", "api")
    # Moving object / weapon detection
    object_detection_enabled: bool = os.getenv("OBJECT_DETECTION_ENABLED", "1") == "1"
    object_min_area: float = float(os.getenv("OBJECT_MIN_AREA", "30"))
    object_max_area: float = float(os.getenv("OBJECT_MAX_AREA", "2000"))
    object_aspect_ratio: float = float(os.getenv("OBJECT_ASPECT_RATIO", "2.8"))
    object_speed_threshold: float = float(os.getenv("OBJECT_SPEED_THRESHOLD", "60"))

    # Hit-only detection: when enabled, only body_hit video events increase risk
    hit_only_detection: bool = os.getenv("RESCUE_HIT_ONLY", "0") == "1"

    # Gesture detection: require two hands for gestures when True
    gesture_require_two_hands: bool = os.getenv("RESCUE_GESTURE_TWO_HANDS", "0") == "1"

    # Google account registration / Реєстрація Google-акаунта
    google_oauth_client_id: str = os.getenv("GOOGLE_OAUTH_CLIENT_ID", "")
    google_oauth_client_secret: str = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", "")
    google_user_profile_file: str = os.getenv(
        "GOOGLE_USER_PROFILE_FILE",
        str(APP_DIR / "google_user_profile.json"),
    )
    google_oauth_timeout_seconds: float = float(os.getenv("GOOGLE_OAUTH_TIMEOUT_SECONDS", "120"))
    supplies_file: str = os.getenv("SUPPLIES_FILE", str(APP_DIR / "supplies.json"))
    _design_theme_source: str = os.getenv("DESIGN_THEME_FILE", str(APP_DIR / "figma_theme.json"))
    design_theme_file: str = str(Path(_design_theme_source) / "figma_theme.json") if Path(_design_theme_source).is_dir() else _design_theme_source


class UIDesignTheme:
    """Loads desktop UI colors/fonts from a Figma token-style JSON file."""

    DEFAULT: dict[str, Any] = {
        "font_family": "Segoe UI",
        "colors": {
            "app_bg": "#0d1219",
            "panel_bg": "#0f1720",
            "status_bg": "#111923",
            "input_bg": "#15202b",
            "button_bg": "#263545",
            "button_selected": "#0587f2",
            "button_hover": "#36506a",
            "button_selected_hover": "#0aa4ff",
            "primary": "#06b6d4",
            "border": "#1f2937",
            "danger": "#dc2626",
            "danger_hover": "#ef4444",
            "success": "#16a34a",
            "success_hover": "#22c55e",
            "warning": "#f59e0b",
            "video_bg": "#000000",
            "text": "#d9e8f4",
            "text_strong": "#eef6ff",
            "text_label": "#e7f4ff",
            "text_muted": "#c7d7e5",
            "button_text": "#ffffff",
            "caret": "#ffffff",
        },
        "font_sizes": {
            "body": 12,
            "button": 12,
            "label": 12,
            "heading": 13,
        },
    }

    COLOR_ALIASES = {
        "background": "app_bg",
        "bg": "app_bg",
        "app_background": "app_bg",
        "surface": "panel_bg",
        "panel": "panel_bg",
        "surface_bg": "panel_bg",
        "status": "status_bg",
        "input": "input_bg",
        "accent": "primary",
        "brand": "primary",
        "selected": "button_selected",
        "text_primary": "text",
        "primary_text": "text",
        "text_secondary": "text_muted",
        "secondary_text": "text_muted",
        "on_primary": "button_text",
    }

    def __init__(self, data: Optional[dict[str, Any]] = None, source: str = "") -> None:
        self.source = source
        self.load_error = ""
        self.data = json.loads(json.dumps(self.DEFAULT))
        self._deep_update(self.data, self._normalise(data or {}))

    @classmethod
    def from_file(cls, path: str) -> "UIDesignTheme":
        theme_path = Path(path)
        if theme_path.is_dir():
            candidate = cls._find_theme_file_in_directory(theme_path)
            if candidate is None:
                theme = cls(source=str(theme_path))
                theme.load_error = f"No theme JSON or ZIP found in directory: {theme_path}"
                return theme
            theme_path = candidate

        if not theme_path.exists():
            fallback = APP_DIR / "figma_theme.json"
            if fallback.exists():
                theme_path = fallback
            else:
                return cls(source=str(theme_path))

        if theme_path.suffix.lower() == ".zip":
            return cls.from_zip(theme_path)
        try:
            data = json.loads(theme_path.read_text(encoding="utf-8-sig"))
            if not isinstance(data, dict):
                raise ValueError("theme JSON root must be an object")
            return cls(data, source=str(theme_path))
        except Exception as error:
            theme = cls(source=str(theme_path))
            theme.load_error = str(error)
            return theme

    @classmethod
    def _find_theme_file_in_directory(cls, directory: Path) -> Optional[Path]:
        candidates = [
            directory / "figma_theme.json",
            directory / "theme.json",
            directory / "design_theme.json",
        ]
        for candidate in candidates:
            if candidate.exists() and candidate.is_file():
                return candidate

        for pattern in ("*.json", "*.zip"):
            for entry in sorted(directory.glob(pattern)):
                if entry.is_file():
                    return entry
        return None

    @classmethod
    def from_zip(cls, path: Path) -> "UIDesignTheme":
        try:
            with zipfile.ZipFile(path) as archive:
                source_parts: list[str] = []
                for entry in archive.namelist():
                    if entry.endswith(("StepPrepDesktop.tsx", "SafeReadyComponents.tsx", "theme.css")):
                        with archive.open(entry) as handle:
                            source_parts.append(handle.read().decode("utf-8", "ignore"))
            data = cls._theme_from_export_text("\n".join(source_parts))
            data["source"] = str(path)
            return cls(data, source=str(path))
        except Exception as error:
            theme = cls(source=str(path))
            theme.load_error = str(error)
            return theme

    @classmethod
    def _theme_from_export_text(cls, text: str) -> dict[str, Any]:
        hex_colors = {match.lower() for match in re.findall(r"#[0-9a-fA-F]{6}", text)}

        def pick(*candidates: str, fallback: str) -> str:
            for candidate in candidates:
                if candidate.lower() in hex_colors:
                    return candidate
            return fallback

        return {
            "font_family": "Segoe UI",
            "colors": {
                "app_bg": pick("#0a0e17", "#ffffff", fallback=cls.DEFAULT["colors"]["app_bg"]),
                "panel_bg": pick("#111827", "#ffffff", fallback=cls.DEFAULT["colors"]["panel_bg"]),
                "status_bg": pick("#0a0e17", "#111923", fallback=cls.DEFAULT["colors"]["status_bg"]),
                "input_bg": pick("#000000", "#f3f3f5", fallback=cls.DEFAULT["colors"]["input_bg"]),
                "button_bg": pick("#1f2937", "#030213", fallback=cls.DEFAULT["colors"]["button_bg"]),
                "button_selected": pick("#dc2626", "#030213", fallback=cls.DEFAULT["colors"]["button_selected"]),
                "button_hover": pick("#374151", "#e9ebef", fallback=cls.DEFAULT["colors"]["button_hover"]),
                "button_selected_hover": pick("#ef4444", "#dc2626", fallback=cls.DEFAULT["colors"]["button_selected_hover"]),
                "primary": pick("#06b6d4", fallback=cls.DEFAULT["colors"]["primary"]),
                "border": pick("#1f2937", "#e5e7eb", fallback=cls.DEFAULT["colors"]["border"]),
                "danger": pick("#dc2626", "#ef4444", fallback=cls.DEFAULT["colors"]["danger"]),
                "danger_hover": pick("#ef4444", "#dc2626", fallback=cls.DEFAULT["colors"]["danger_hover"]),
                "success": pick("#16a34a", "#10b981", fallback=cls.DEFAULT["colors"]["success"]),
                "success_hover": pick("#22c55e", "#16a34a", fallback=cls.DEFAULT["colors"]["success_hover"]),
                "warning": pick("#f59e0b", fallback=cls.DEFAULT["colors"]["warning"]),
                "video_bg": "#000000",
                "text": pick("#f9fafb", "#111827", fallback=cls.DEFAULT["colors"]["text"]),
                "text_strong": "#ffffff",
                "text_label": pick("#d1d5db", "#e5e7eb", fallback=cls.DEFAULT["colors"]["text_label"]),
                "text_muted": pick("#9ca3af", "#6b7280", fallback=cls.DEFAULT["colors"]["text_muted"]),
                "button_text": "#ffffff",
                "caret": "#ffffff",
            },
            "font_sizes": {
                "body": 12,
                "button": 12,
                "label": 12,
                "heading": 14,
            },
        }

    def color(self, key: str) -> str:
        colors = self.data.get("colors", {})
        defaults = self.DEFAULT["colors"]
        value = colors.get(key, defaults.get(key, "#ffffff")) if isinstance(colors, dict) else defaults.get(key, "#ffffff")
        return str(value)

    def font(self, role: str = "body", bold: bool = False) -> tuple[Any, ...]:
        family = str(self.data.get("font_family", self.DEFAULT["font_family"]))
        sizes = self.data.get("font_sizes", {})
        default_sizes = self.DEFAULT["font_sizes"]
        raw_size = sizes.get(role, default_sizes.get(role, default_sizes["body"])) if isinstance(sizes, dict) else default_sizes["body"]
        size = self._coerce_int(raw_size, int(default_sizes["body"]))
        if bold:
            return (family, size, "bold")
        return (family, size)

    @classmethod
    def _normalise(cls, data: dict[str, Any]) -> dict[str, Any]:
        normalised = dict(data)
        if "fontFamily" in normalised and "font_family" not in normalised:
            normalised["font_family"] = cls._token_value(normalised["fontFamily"])
        if "fontSizes" in normalised and "font_sizes" not in normalised:
            normalised["font_sizes"] = normalised["fontSizes"]

        colors = normalised.get("colors") or normalised.get("color") or normalised.get("palette")
        if isinstance(colors, dict):
            flat_colors = cls._flatten_tokens(colors)
            normalised["colors"] = {
                cls.COLOR_ALIASES.get(key, key): value
                for key, value in flat_colors.items()
                if isinstance(value, str) and value
            }

        for group_name in ("font_sizes", "spacing", "radii"):
            group = normalised.get(group_name)
            if isinstance(group, dict):
                normalised[group_name] = {
                    key: cls._token_value(value)
                    for key, value in cls._flatten_tokens(group).items()
                }
        return normalised

    @classmethod
    def _flatten_tokens(cls, data: dict[str, Any], prefix: str = "") -> dict[str, Any]:
        flat: dict[str, Any] = {}
        for raw_key, raw_value in data.items():
            key = cls._normalise_key(str(raw_key))
            full_key = f"{prefix}_{key}" if prefix else key
            value = cls._token_value(raw_value)
            if isinstance(value, dict):
                flat.update(cls._flatten_tokens(value, full_key))
            else:
                flat[full_key] = value
                if not prefix:
                    flat[key] = value
        return flat

    @staticmethod
    def _normalise_key(key: str) -> str:
        result = []
        previous_was_separator = False
        for character in key.strip():
            if character.isalnum():
                if character.isupper() and result and not previous_was_separator:
                    result.append("_")
                result.append(character.lower())
                previous_was_separator = False
            else:
                if result and not previous_was_separator:
                    result.append("_")
                previous_was_separator = True
        return "".join(result).strip("_")

    @classmethod
    def _token_value(cls, value: Any) -> Any:
        if isinstance(value, dict) and "value" in value:
            return cls._token_value(value.get("value"))
        return value

    @classmethod
    def _deep_update(cls, base: dict[str, Any], updates: dict[str, Any]) -> None:
        for key, value in updates.items():
            clean_value = cls._token_value(value)
            if isinstance(base.get(key), dict) and isinstance(clean_value, dict):
                cls._deep_update(base[key], clean_value)
            elif clean_value not in (None, ""):
                base[key] = clean_value

    @staticmethod
    def _coerce_int(value: Any, fallback: int) -> int:
        if isinstance(value, (int, float)):
            return max(8, int(value))
        if isinstance(value, str):
            numeric = "".join(character for character in value if character.isdigit() or character == ".")
            try:
                return max(8, int(float(numeric)))
            except ValueError:
                return fallback
        return fallback


# One detected audio warning / Одне знайдене аудіопопередження
@dataclass
class AudioEvent:
    timestamp: float
    rms_db: float
    peak: float
    crest_factor: float
    high_band_ratio: float
    event_type: str


# One detected video warning / Одне знайдене відеопопередження
@dataclass
class VideoEvent:
    timestamp: float
    motion_score: float
    flash_score: float
    event_type: str
    body_motion_score: float = 0.0
    body_direction: str = ""
    hit_score: float = 0.0
    hit_detected: bool = False
    hit_point: Optional[tuple[int, int]] = None


# One detected help gesture / Один знайдений жест допомоги
@dataclass
class GestureEvent:
    timestamp: float
    gesture: str
    held_seconds: float
    # optional center of the detected hand (pixels)
    center: Optional[tuple[int, int]] = None
    motion_score: float = 0.0


# Shelter data loaded from JSON / Дані укриття з JSON
@dataclass
class Shelter:
    name: str
    address: str
    lat: Optional[float] = None
    lon: Optional[float] = None
    note: str = ""
    phone: str = ""
    google_maps_uri: str = ""
    source: str = "local"


EMERGENCY_SUPPLIES = {
    "uk": [
        ("Документи", "паспорт/ID, копії документів, важливі контакти"),
        ("Вода", "мінімум 1-2 л на людину"),
        ("Їжа", "батончики, консерви, горіхи, дитяче харчування за потреби"),
        ("Аптечка", "особисті ліки, бинт, антисептик, знеболювальне"),
        ("Світло", "ліхтарик, батарейки, павербанк, зарядний кабель"),
        ("Тепло", "теплий одяг, плед/термоковдра, дощовик"),
        ("Зв'язок", "телефон, зарядка, паперові номери близьких"),
        ("Готівка", "невеликі купюри та банківська картка"),
        ("Гігієна", "серветки, антисептик, маска, індивідуальні засоби"),
    ],
    "en": [
        ("Documents", "passport/ID, document copies, important contacts"),
        ("Water", "at least 1-2 l per person"),
        ("Food", "bars, canned food, nuts, baby food if needed"),
        ("First aid", "personal medicine, bandage, antiseptic, painkiller"),
        ("Light", "flashlight, batteries, power bank, charging cable"),
        ("Warmth", "warm clothes, blanket/thermal blanket, raincoat"),
        ("Connection", "phone, charger, paper contact numbers"),
        ("Cash", "small bills and a bank card"),
        ("Hygiene", "wipes, sanitizer, mask, personal care items"),
    ],
}


def parse_supplies_text(text: str) -> list[tuple[str, str]]:
    items: list[tuple[str, str]] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if ":" in line:
            title, detail = line.split(":", 1)
        elif " - " in line:
            title, detail = line.split(" - ", 1)
        else:
            title, detail = line, ""
        title = title.strip(" -\t")
        detail = detail.strip()
        if title:
            items.append((title, detail))
    return items


def format_supplies_text(items: Sequence[tuple[str, str]]) -> str:
    lines = []
    for title, detail in items:
        lines.append(f"{title}: {detail}" if detail else title)
    return "\n".join(lines)


class SuppliesManager:
    """Keeps the go-bag checklist editable while preserving localized defaults."""

    def __init__(self, config: RescueConfig, i18n: Translator) -> None:
        self.config = config
        self.i18n = i18n
        self.items_by_language: dict[str, list[tuple[str, str]]] = {
            language: list(items)
            for language, items in EMERGENCY_SUPPLIES.items()
        }
        self.status_message = ""
        self.load()

    def load(self) -> None:
        path = Path(self.config.supplies_file)
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return
            for language in SUPPORTED_LANGUAGES:
                raw_items = data.get(language)
                parsed_items: list[tuple[str, str]] = []
                if not isinstance(raw_items, list):
                    continue
                for item in raw_items:
                    if isinstance(item, dict):
                        title = str(item.get("title", "")).strip()
                        detail = str(item.get("detail", "")).strip()
                    elif isinstance(item, (list, tuple)) and item:
                        title = str(item[0]).strip()
                        detail = str(item[1]).strip() if len(item) > 1 else ""
                    else:
                        continue
                    if title:
                        parsed_items.append((title, detail))
                if parsed_items:
                    self.items_by_language[language] = parsed_items
        except Exception as error:
            self.status_message = self.i18n.t("supplies_load_failed", error=error)

    def current_items(self) -> list[tuple[str, str]]:
        return list(self.items_by_language.get(self.i18n.language, EMERGENCY_SUPPLIES["uk"]))

    def current_text(self) -> str:
        return format_supplies_text(self.current_items())

    def update_current_text(self, text: str) -> None:
        self.items_by_language[self.i18n.language] = parse_supplies_text(text)

    def reset_current(self) -> str:
        self.items_by_language[self.i18n.language] = list(EMERGENCY_SUPPLIES.get(self.i18n.language, EMERGENCY_SUPPLIES["uk"]))
        self.status_message = self.i18n.t("supplies_reset_done")
        return self.status_message

    def save(self) -> str:
        path = Path(self.config.supplies_file)
        data = {
            language: [
                {"title": title, "detail": detail}
                for title, detail in self.items_by_language.get(language, [])
            ]
            for language in SUPPORTED_LANGUAGES
        }
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            self.status_message = self.i18n.t("supplies_saved", path=path)
        except Exception as error:
            self.status_message = self.i18n.t("supplies_save_failed", error=error)
        return self.status_message


class AudioAnalyzer:
    """Detect abrupt dangerous sounds with lightweight signal features."""

    def __init__(self, config: RescueConfig, i18n: Translator) -> None:
        self.config = config
        self.i18n = i18n
        self.events: "queue.Queue[AudioEvent]" = queue.Queue()
        self.enabled = sd is not None
        self.stream: Optional[Any] = None
        self._previous_rms_db = -90.0
        self._last_impulse_at = 0.0
        self._loud_blocks = 0

    def start(self) -> None:
        if not self.enabled:
            print(self.i18n.t("audio_disabled_install"))
            return

        try:
            self.stream = sd.InputStream(
                samplerate=self.config.sample_rate,
                blocksize=self.config.audio_block_size,
                channels=1,
                dtype="float32",
                callback=self._on_audio_block,
            )
            if self.stream is not None:
                self.stream.start()
        except Exception as error:
            self.enabled = False
            self.stream = None
            print(self.i18n.t("audio_disabled_microphone", error=error))

    def stop(self) -> None:
        if self.stream is not None:
            self.stream.stop()
            self.stream.close()
            self.stream = None

    def _on_audio_block(
        self,
        indata: Any,
        frames: Any,
        time_info: Any,
        status: Any,
    ) -> None:
        if status:
            print(f"Audio status: {status}")

        # Convert microphone block to one numeric stream / Перетворюємо блок мікрофона в один числовий потік
        samples = np.asarray(indata[:, 0], dtype=np.float32)
        if samples.size == 0:
            return

        # Loudness and impulse features / Ознаки гучності та різкого імпульсу
        now = time.time()
        rms = float(np.sqrt(np.mean(samples * samples)) + 1e-9)
        peak = float(np.max(np.abs(samples)))
        rms_db = 20.0 * math.log10(rms)
        crest_factor = peak / rms
        rise_db = rms_db - self._previous_rms_db
        self._previous_rms_db = (self._previous_rms_db * 0.75) + (rms_db * 0.25)

        spectrum = np.asarray(np.fft.rfft(samples * np.hanning(samples.size)))
        power = np.square(np.abs(spectrum))
        freqs = np.fft.rfftfreq(samples.size, 1.0 / self.config.sample_rate)
        total_power = float(np.sum(power) + 1e-9)
        high_power = float(np.sum(power[freqs > 2500.0]))
        high_band_ratio = high_power / total_power

        # Scream-like sounds often keep high-frequency energy / Звуки типу крику часто тримають високі частоти
        if rms_db > -28 and high_band_ratio > 0.35:
            self._loud_blocks += 1
        else:
            self._loud_blocks = max(0, self._loud_blocks - 1)

        cooldown_passed = now - self._last_impulse_at > 0.45
        is_impulse = (
            cooldown_passed
            and peak > 0.55
            and rms_db > -24
            and crest_factor > 6.0
            and rise_db > 7.0
            and high_band_ratio > 0.22
        )
        is_scream_like = self._loud_blocks >= 10 and -34 < rms_db < -8 and high_band_ratio > 0.38

        if is_impulse:
            self._last_impulse_at = now
            self.events.put(
                AudioEvent(now, rms_db, peak, crest_factor, high_band_ratio, "gunshot_like")
            )
        elif is_scream_like:
            self.events.put(
                AudioEvent(now, rms_db, peak, crest_factor, high_band_ratio, "scream_like")
            )
            self._loud_blocks = 0


class VideoAnalyzer:
    """Detect flashes, full-body movement, hit collisions, and moving small weapons."""

    def __init__(self, config: RescueConfig, i18n: Translator) -> None:
        self.config = config
        self.i18n = i18n
        self._previous_gray: Optional[np.ndarray] = None
        self._previous_brightness: Optional[float] = None
        self._last_video_event_at = 0.0
        self._last_hit_event_at = 0.0
        self._last_body_center: Optional[tuple[int, int]] = None
        self._last_body_center_at = 0.0
        self._last_body_speed = 0.0
        self._body_motion_score = 0.0
        self._body_direction = "unknown"
        self._body_box: Optional[tuple[int, int, int, int]] = None
        self._body_source = "none"
        self._frame_index = 0
        self._last_person_box: Optional[tuple[int, int, int, int]] = None
        self._last_person_at = 0.0
        self._hit_score = 0.0
        self._hit_point: Optional[tuple[int, int]] = None
        self._hit_until = 0.0
        self._hog = self._create_hog_detector()
        self._last_object_centroids: list[tuple[float, float]] = []
        self._last_object_at: float = 0.0

    def analyze(self, frame: np.ndarray) -> tuple[Optional[VideoEvent], dict[str, Any]]:
        self._frame_index += 1
        now = time.time()

        # Work on a small grayscale frame for speed / Працюємо з малим сірим кадром для швидкості
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray_small = cv2.resize(gray, (320, 180), interpolation=cv2.INTER_AREA)
        brightness = float(np.mean(gray_small))

        motion_score = 0.0
        flash_score = 0.0
        body_motion_score = self._body_motion_score
        body_direction = self._body_direction
        hit_score = 0.0
        hit_detected = False

        person_box = self._detect_full_body_person(frame, now)
        weapon_detected = False
        weapon_kind = None
        weapon_score = 0.0

        if self._previous_gray is not None:
            # Difference from previous frame gives motion / Різниця з попереднім кадром показує рух
            diff = cv2.absdiff(gray_small, self._previous_gray)
            motion_score = float(np.mean(diff) / 255.0)
            body_motion_score, body_direction, hit_score, hit_detected = self._analyze_body(
                frame,
                diff,
                now,
                person_box,
            )
            # small moving-object (knife/gun) heuristic
            weapon_detected = False
            weapon_kind = None
            weapon_score = 0.0
            if self.config.object_detection_enabled:
                weapon_detected, weapon_kind, weapon_score = self._detect_moving_weapon(diff, now)
        else:
            if person_box is not None:
                self._body_box = person_box
                self._body_source = "person"
            self._draw_body_motion(frame)

        if self._previous_brightness is not None:
            # Fast brightness jump can mean flash / Швидкий стрибок яскравості може означати спалах
            brightness_delta = brightness - self._previous_brightness
            flash_score = max(0.0, min(1.0, brightness_delta / 70.0))

        self._previous_gray = gray_small
        self._previous_brightness = brightness

        event = None
        cooldown_passed = now - self._last_video_event_at > 0.7
        hit_cooldown_passed = now - self._last_hit_event_at > 1.0
        if cooldown_passed and flash_score > 0.38:
            event = VideoEvent(
                now,
                motion_score,
                flash_score,
                "flash_like",
                body_motion_score,
                self._direction_label(body_direction),
                hit_score,
                hit_detected,
            )
            self._last_video_event_at = now
        elif hit_detected and hit_cooldown_passed:
            event = VideoEvent(
                now,
                motion_score,
                flash_score,
                "body_hit",
                body_motion_score,
                self._direction_label(body_direction),
                hit_score,
                True,
            )
            self._last_hit_event_at = now
            self._last_video_event_at = now
        elif cooldown_passed and body_motion_score > 0.72:
            event = VideoEvent(
                now,
                motion_score,
                flash_score,
                "sudden_motion",
                body_motion_score,
                self._direction_label(body_direction),
                hit_score,
                hit_detected,
            )
            self._last_video_event_at = now

        metrics = {
            "motion": motion_score,
            "flash": flash_score,
            "brightness": brightness,
            "body_motion": body_motion_score,
            "body_direction": self._direction_label(body_direction),
            "body_collision": hit_score,
            "body_hit": hit_detected,
            "body_detected": self._body_box is not None,
            "disaster_estimate": self._estimate_disaster_proximity(frame, motion_score, flash_score, brightness),
        }
        if self.config.object_detection_enabled:
            metrics["weapon_detected"] = weapon_detected
            metrics["weapon_kind"] = weapon_kind or ""
            metrics["weapon_score"] = weapon_score

        return (
            event,
            metrics,
        )

    def _estimate_disaster_proximity(
        self,
        frame: np.ndarray,
        motion_score: float,
        flash_score: float,
        brightness: float,
    ) -> str:
        if frame.size == 0:
            return self.i18n.t("safe_area")

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        hue = hsv[:, :, 0]
        sat = hsv[:, :, 1].astype(float) / 255.0
        val = hsv[:, :, 2].astype(float) / 255.0

        red_mask = (
            ((hue < 10) | (hue > 160))
            & (sat > 0.4)
            & (val > 0.25)
        )
        orange_mask = (
            (hue >= 10)
            & (hue < 28)
            & (sat > 0.4)
            & (val > 0.35)
        )
        blue_mask = (
            (hue >= 90)
            & (hue <= 140)
            & (sat > 0.2)
            & (val > 0.3)
        )

        total = float(frame.shape[0] * frame.shape[1])
        red_area = float(np.count_nonzero(red_mask | orange_mask)) / max(1.0, total)
        blue_area = float(np.count_nonzero(blue_mask)) / max(1.0, total)

        tornado_score = max(0.0, (motion_score - 0.15) * 1.6 + max(0.0, 1.0 - brightness / 130.0) * 0.9)
        flood_score = max(0.0, blue_area * 7.5 + motion_score * 0.4)
        fire_score = max(0.0, red_area * 12.0 + flash_score * 0.7)

        tornado_level = self._severity_label(tornado_score)
        flood_level = self._severity_label(flood_score)
        fire_level = self._severity_label(fire_score)

        if tornado_level == "none" and flood_level == "none" and fire_level == "none":
            return self.i18n.t("safe_area")

        return (
            f"{self.i18n.t('disaster_tornado')}: {self.i18n.t('hazard_' + tornado_level)}, "
            f"{self.i18n.t('disaster_flood')}: {self.i18n.t('hazard_' + flood_level)}, "
            f"{self.i18n.t('disaster_fire')}: {self.i18n.t('hazard_' + fire_level)}"
        )

    @staticmethod
    def _severity_label(score: float) -> str:
        if score > 0.68:
            return "near"
        if score > 0.32:
            return "medium"
        if score > 0.12:
            return "far"
        return "none"

    def _analyze_body(
        self,
        frame: np.ndarray,
        diff_small: np.ndarray,
        now: float,
        person_box: Optional[tuple[int, int, int, int]],
    ) -> tuple[float, str, float, bool]:
        motion_box = self._motion_body_candidate(frame, diff_small, person_box)
        body_box = self._select_body_box(frame, person_box, motion_box, now)
        if body_box is None:
            self._body_motion_score *= 0.82
            self._hit_score *= 0.78
            if self._body_motion_score < 0.05:
                self._body_direction = "still"
                self._body_box = None
                self._body_source = "none"
            self._draw_body_motion(frame)
            return self._body_motion_score, self._body_direction, self._hit_score, False

        center = self._box_center(body_box)
        direction = self._body_direction
        body_speed = 0.0
        if self._last_body_center is not None and self._last_body_center_at > 0:
            dt = max(0.001, now - self._last_body_center_at)
            dx = center[0] - self._last_body_center[0]
            dy = center[1] - self._last_body_center[1]
            body_speed = math.sqrt(dx * dx + dy * dy) / dt
            instant_score = min(1.0, body_speed / 950.0)
            self._body_motion_score = (self._body_motion_score * 0.64) + (instant_score * 0.36)
            direction = self._classify_direction(dx, dy, body_speed)
        else:
            self._body_motion_score *= 0.75
            direction = "unknown"

        hit_score, hit_point = self._detect_hit_only_collision(diff_small, frame.shape[:2], body_box, body_speed)
        hit_detected = hit_score >= 0.62
        self._hit_score = (self._hit_score * 0.5) + (hit_score * 0.5)
        if hit_detected:
            self._hit_point = hit_point
            self._hit_until = now + 0.9

        self._last_body_center = center
        self._last_body_center_at = now
        self._last_body_speed = body_speed
        self._body_direction = direction
        self._body_box = body_box
        self._draw_body_motion(frame)
        return self._body_motion_score, self._body_direction, self._hit_score, hit_detected

    def _detect_full_body_person(
        self,
        frame: np.ndarray,
        now: float,
    ) -> Optional[tuple[int, int, int, int]]:
        if self._last_person_box is not None and self._frame_index % 8 != 0:
            if now - self._last_person_at < 1.4:
                return self._last_person_box

        if self._hog is None:
            return self._last_person_box if now - self._last_person_at < 1.0 else None

        try:
            frame_h, frame_w = frame.shape[:2]
            target_w = 480
            scale = target_w / frame_w
            small = cv2.resize(frame, (target_w, int(frame_h * scale)), interpolation=cv2.INTER_AREA)
            boxes, weights = self._hog.detectMultiScale(
                small,
                winStride=(8, 8),
                padding=(8, 8),
                scale=1.05,
            )
        except Exception:
            return self._last_person_box if now - self._last_person_at < 1.0 else None

        best_box = None
        best_score = 0.0
        for index, rect in enumerate(boxes):
            x, y, w, h = [int(value) for value in rect]
            x1 = int(x / scale)
            y1 = int(y / scale)
            x2 = int((x + w) / scale)
            y2 = int((y + h) / scale)
            box = self._clip_box((x1, y1, x2, y2), frame.shape[:2])
            if not self._looks_like_full_body(box, frame.shape[:2]):
                continue
            confidence = 1.0
            try:
                confidence = float(weights[index])
            except Exception:
                pass
            area = self._box_area(box)
            score = area * max(0.25, confidence)
            if score > best_score:
                best_box = self._expand_box(box, frame.shape[:2], 0.08)
                best_score = score

        if best_box is not None:
            self._last_person_box = best_box
            self._last_person_at = now
            return best_box

        return self._last_person_box if now - self._last_person_at < 1.0 else None

    def _motion_body_candidate(
        self,
        frame: np.ndarray,
        diff_small: np.ndarray,
        person_box: Optional[tuple[int, int, int, int]],
    ) -> Optional[tuple[int, int, int, int]]:
        blurred = cv2.GaussianBlur(diff_small, (7, 7), 0)
        _, mask = cv2.threshold(blurred, 22, 255, cv2.THRESH_BINARY)
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
        mask = cv2.dilate(mask, kernel, iterations=2)
        contours = self._find_contours(mask)

        frame_shape = frame.shape[:2]
        focus_box = person_box or self._body_box
        if focus_box is not None:
            focus_box = self._expand_box(focus_box, frame_shape, 0.18)

        candidates = []
        min_area = max(170.0, mask.shape[0] * mask.shape[1] * 0.006)
        for contour in contours:
            area = float(cv2.contourArea(contour))
            if area < min_area:
                continue
            box = self._small_rect_to_frame_box(cv2.boundingRect(contour), diff_small.shape, frame_shape)
            if focus_box is not None:
                if self._overlap_ratio(box, focus_box) > 0.02 or self._point_in_box(self._box_center(box), focus_box):
                    candidates.append(box)
                continue
            if self._looks_like_full_body(box, frame_shape):
                candidates.append(box)

        if not candidates:
            return None

        union_box = candidates[0]
        for box in candidates[1:]:
            union_box = self._union_box(union_box, box)
        union_box = self._expand_box(union_box, frame_shape, 0.12)
        if focus_box is None and not self._looks_like_full_body(union_box, frame_shape):
            return None
        return union_box

    def _detect_moving_weapon(self, diff_small: np.ndarray, now: float) -> tuple[bool, Optional[str], float]:
        # Simple heuristic: look for small fast-moving elongated contours in the small diff frame.
        try:
            blurred = cv2.GaussianBlur(diff_small, (5, 5), 0)
            _, mask = cv2.threshold(blurred, 18, 255, cv2.THRESH_BINARY)
            kernel = np.ones((3, 3), np.uint8)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
            contours = self._find_contours(mask)
        except Exception:
            return False, None, 0.0

        detected = False
        kind = None
        best_score = 0.0
        dt = max(1e-3, now - self._last_object_at) if self._last_object_at > 0 else 0.0
        current_centroids: list[tuple[float, float]] = []

        for contour in contours:
            area = float(cv2.contourArea(contour))
            if area < self.config.object_min_area or area > self.config.object_max_area:
                continue
            x, y, w, h = cv2.boundingRect(contour)
            ar = float(max(w, h)) / max(1.0, min(w, h))
            M = cv2.moments(contour)
            if M.get("m00", 0) == 0:
                cx = x + w / 2.0
                cy = y + h / 2.0
            else:
                cx = M["m10"] / M["m00"]
                cy = M["m01"] / M["m00"]
            current_centroids.append((cx, cy))

            # estimate speed from previous centroids (nearest)
            speed = 0.0
            if dt > 0 and self._last_object_centroids:
                min_dist = min(math.hypot(cx - lx, cy - ly) for (lx, ly) in self._last_object_centroids)
                speed = min_dist / dt

            score = (ar / max(1.0, self.config.object_aspect_ratio)) * min(1.0, area / max(1.0, self.config.object_max_area))
            score = score * (1.0 + min(3.0, speed / max(1.0, self.config.object_speed_threshold)))

            if speed >= self.config.object_speed_threshold and score > best_score:
                best_score = score
                detected = True
                kind = "knife" if ar >= self.config.object_aspect_ratio else "gun"

        # update history
        self._last_object_centroids = current_centroids
        self._last_object_at = now
        return detected, kind, float(best_score)

    def _select_body_box(
        self,
        frame: np.ndarray,
        person_box: Optional[tuple[int, int, int, int]],
        motion_box: Optional[tuple[int, int, int, int]],
        now: float,
    ) -> Optional[tuple[int, int, int, int]]:
        frame_shape = frame.shape[:2]
        if person_box is not None:
            self._body_source = "person"
            return person_box

        if self._body_box is not None and now - self._last_body_center_at < 1.7:
            self._body_source = "tracked"
            if motion_box is not None and self._overlap_ratio(motion_box, self._expand_box(self._body_box, frame_shape, 0.22)) > 0.02:
                if self._looks_like_full_body(motion_box, frame_shape):
                    return self._smooth_box(self._body_box, motion_box, 0.35)
                return self._body_box
            return self._body_box

        if motion_box is not None and self._looks_like_full_body(motion_box, frame_shape):
            self._body_source = "motion"
            return motion_box

        self._body_source = "none"
        return None

    def _detect_hit_only_collision(
        self,
        diff_small: np.ndarray,
        frame_shape: tuple[int, int],
        body_box: tuple[int, int, int, int],
        body_speed: float,
    ) -> tuple[float, Optional[tuple[int, int]]]:
        # Collision is counted only when a localized fast motion hits the body box / Зіткнення рахуємо лише як локальний удар по тілу
        body_area = max(1.0, float(self._box_area(body_box)))

        blurred = cv2.GaussianBlur(diff_small, (5, 5), 0)
        _, mask = cv2.threshold(blurred, 36, 255, cv2.THRESH_BINARY)
        contours = self._find_contours(mask)

        best_score = 0.0
        best_point = None
        expanded_body = self._expand_box(body_box, frame_shape, 0.08)
        for contour in contours:
            area_small = float(cv2.contourArea(contour))
            if area_small < 28:
                continue
            small_rect = cv2.boundingRect(contour)
            hit_box = self._small_rect_to_frame_box(small_rect, diff_small.shape, frame_shape)
            if self._is_head_or_face_hit(hit_box, body_box):
                continue

            overlap = self._overlap_ratio(hit_box, expanded_body)
            if overlap < 0.18 and not self._point_in_box(self._box_center(hit_box), expanded_body):
                continue

            hit_area = float(self._box_area(hit_box))
            area_ratio = hit_area / body_area
            if area_ratio < 0.008 or area_ratio > 0.28:
                continue

            sx, sy, sw, sh = small_rect
            local_patch = diff_small[sy : sy + sh, sx : sx + sw]
            local_intensity = float(np.mean(local_patch) / 255.0) if local_patch.size else 0.0
            if local_intensity < 0.16:
                continue

            localized_score = min(1.0, area_ratio / 0.12)
            intensity_score = min(1.0, local_intensity / 0.42)
            jerk_score = min(1.0, max(0.0, body_speed - self._last_body_speed) / 620.0)
            score = min(1.0, localized_score * 0.38 + intensity_score * 0.5 + jerk_score * 0.16)
            if score > best_score:
                best_score = score
                best_point = self._box_center(hit_box)

        if best_score < 0.58:
            return 0.0, None
        return best_score, best_point

    @staticmethod
    def _is_head_or_face_hit(
        hit_box: tuple[int, int, int, int],
        body_box: tuple[int, int, int, int],
    ) -> bool:
        body_x1, body_y1, body_x2, body_y2 = body_box
        body_width = max(1, body_x2 - body_x1)
        body_height = max(1, body_y2 - body_y1)
        hit_center_x, hit_center_y = VideoAnalyzer._box_center(hit_box)
        relative_y = (hit_center_y - body_y1) / body_height
        relative_x = (hit_center_x - body_x1) / body_width
        return relative_y < 0.34 and 0.12 <= relative_x <= 0.88

    @staticmethod
    def _create_hog_detector() -> Optional[Any]:
        try:
            hog = cv2.HOGDescriptor()
            hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())  # type: ignore[attr-defined]
            return hog
        except Exception:
            return None

    @staticmethod
    def _find_contours(mask: np.ndarray) -> list[Any]:
        found_contours = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contours = found_contours[0] if len(found_contours) == 2 else found_contours[1]
        return list(contours)

    @staticmethod
    def _small_rect_to_frame_box(
        rect: Sequence[int],
        small_shape: tuple[int, int],
        frame_shape: tuple[int, int],
    ) -> tuple[int, int, int, int]:
        x, y, w, h = rect
        frame_h, frame_w = frame_shape
        small_h, small_w = small_shape[:2]
        scale_x = frame_w / small_w
        scale_y = frame_h / small_h
        return (
            int(x * scale_x),
            int(y * scale_y),
            int((x + w) * scale_x),
            int((y + h) * scale_y),
        )

    @staticmethod
    def _classify_direction(dx: int, dy: int, pixels_per_second: float) -> str:
        if pixels_per_second < 90:
            return "still"

        horizontal = "right" if dx > 0 else "left"
        vertical = "down" if dy > 0 else "up"
        abs_dx = abs(dx)
        abs_dy = abs(dy)
        if abs_dx > abs_dy * 1.35:
            return horizontal
        if abs_dy > abs_dx * 1.35:
            return vertical
        return f"{vertical}_{horizontal}"

    def _direction_label(self, direction: str) -> str:
        return {
            "left": self.i18n.t("direction_left"),
            "right": self.i18n.t("direction_right"),
            "up": self.i18n.t("direction_up"),
            "down": self.i18n.t("direction_down"),
            "up_left": self.i18n.t("direction_up_left"),
            "up_right": self.i18n.t("direction_up_right"),
            "down_left": self.i18n.t("direction_down_left"),
            "down_right": self.i18n.t("direction_down_right"),
            "still": self.i18n.t("direction_still"),
        }.get(direction, self.i18n.t("direction_unknown"))

    def _draw_body_motion(self, frame: np.ndarray) -> None:
        if self._body_box is None:
            return

        x1, y1, x2, y2 = self._body_box
        center = self._box_center(self._body_box)
        hit_active = time.time() < self._hit_until
        color = (0, 220, 255)
        if hit_active:
            color = (0, 0, 255)
        elif self._body_motion_score > 0.65:
            color = (0, 95, 255)
        elif self._body_motion_score > 0.35:
            color = (0, 165, 255)

        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 3)
        arrow_end = self._arrow_endpoint(center, self._body_direction, 78)
        cv2.arrowedLine(frame, center, arrow_end, color, 4, tipLength=0.24)

        hit_text = self.i18n.t("hit_yes") if hit_active else self.i18n.t("hit_no")
        label = self.i18n.t(
            "body_motion_overlay",
            direction=self._direction_label(self._body_direction),
            score=self._body_motion_score,
            hit=hit_text,
        )
        label_width = min(frame.shape[1] - x1 - 4, 18 + len(label) * 13)
        cv2.rectangle(frame, (x1, max(0, y1 - 32)), (x1 + label_width, y1), color, -1)
        put_text(
            frame,
            label,
            (x1 + 8, max(20, y1 - 9)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.54,
            (0, 0, 0),
            2,
            cv2.LINE_AA,
        )

        if hit_active and self._hit_point is not None:
            hx, hy = self._hit_point
            cv2.circle(frame, (hx, hy), 18, (0, 0, 255), 3)
            cv2.line(frame, (hx - 22, hy - 22), (hx + 22, hy + 22), (0, 0, 255), 4)
            cv2.line(frame, (hx - 22, hy + 22), (hx + 22, hy - 22), (0, 0, 255), 4)
            put_text(
                frame,
                self.i18n.t("body_hit_overlay"),
                (max(8, hx - 62), max(28, hy - 28)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.68,
                (0, 0, 255),
                2,
                cv2.LINE_AA,
            )

    @staticmethod
    def _looks_like_full_body(box: tuple[int, int, int, int], frame_shape: tuple[int, int]) -> bool:
        frame_h, frame_w = frame_shape
        x1, y1, x2, y2 = box
        width = max(1, x2 - x1)
        height = max(1, y2 - y1)
        area_ratio = (width * height) / max(1.0, float(frame_w * frame_h))
        aspect = height / width
        return (
            height >= frame_h * 0.26
            and width >= frame_w * 0.07
            and area_ratio >= 0.025
            and 0.85 <= aspect <= 4.8
        )

    @staticmethod
    def _box_center(box: tuple[int, int, int, int]) -> tuple[int, int]:
        x1, y1, x2, y2 = box
        return ((x1 + x2) // 2, (y1 + y2) // 2)

    @staticmethod
    def _box_area(box: tuple[int, int, int, int]) -> int:
        x1, y1, x2, y2 = box
        return max(0, x2 - x1) * max(0, y2 - y1)

    @staticmethod
    def _clip_box(box: tuple[int, int, int, int], frame_shape: tuple[int, int]) -> tuple[int, int, int, int]:
        frame_h, frame_w = frame_shape
        x1, y1, x2, y2 = box
        return (
            max(0, min(frame_w - 1, x1)),
            max(0, min(frame_h - 1, y1)),
            max(0, min(frame_w - 1, x2)),
            max(0, min(frame_h - 1, y2)),
        )

    def _expand_box(
        self,
        box: tuple[int, int, int, int],
        frame_shape: tuple[int, int],
        ratio: float,
    ) -> tuple[int, int, int, int]:
        x1, y1, x2, y2 = box
        pad_x = int((x2 - x1) * ratio)
        pad_y = int((y2 - y1) * ratio)
        return self._clip_box((x1 - pad_x, y1 - pad_y, x2 + pad_x, y2 + pad_y), frame_shape)

    @staticmethod
    def _union_box(
        first: tuple[int, int, int, int],
        second: tuple[int, int, int, int],
    ) -> tuple[int, int, int, int]:
        return (
            min(first[0], second[0]),
            min(first[1], second[1]),
            max(first[2], second[2]),
            max(first[3], second[3]),
        )

    @staticmethod
    def _smooth_box(
        previous: tuple[int, int, int, int],
        current: tuple[int, int, int, int],
        alpha: float,
    ) -> tuple[int, int, int, int]:
        return (
            int(previous[0] * (1.0 - alpha) + current[0] * alpha),
            int(previous[1] * (1.0 - alpha) + current[1] * alpha),
            int(previous[2] * (1.0 - alpha) + current[2] * alpha),
            int(previous[3] * (1.0 - alpha) + current[3] * alpha),
        )

    @staticmethod
    def _overlap_ratio(first: tuple[int, int, int, int], second: tuple[int, int, int, int]) -> float:
        x1 = max(first[0], second[0])
        y1 = max(first[1], second[1])
        x2 = min(first[2], second[2])
        y2 = min(first[3], second[3])
        inter_area = max(0, x2 - x1) * max(0, y2 - y1)
        if inter_area <= 0:
            return 0.0
        return inter_area / max(1.0, float(min(VideoAnalyzer._box_area(first), VideoAnalyzer._box_area(second))))

    @staticmethod
    def _point_in_box(point: tuple[int, int], box: tuple[int, int, int, int]) -> bool:
        x, y = point
        x1, y1, x2, y2 = box
        return x1 <= x <= x2 and y1 <= y <= y2

    @staticmethod
    def _arrow_endpoint(center: tuple[int, int], direction: str, length: int) -> tuple[int, int]:
        vectors = {
            "left": (-1, 0),
            "right": (1, 0),
            "up": (0, -1),
            "down": (0, 1),
            "up_left": (-1, -1),
            "up_right": (1, -1),
            "down_left": (-1, 1),
            "down_right": (1, 1),
        }
        vx, vy = vectors.get(direction, (0, 0))
        if vx and vy:
            length = int(length * 0.72)
        return (center[0] + vx * length, center[1] + vy * length)


class GestureAnalyzer:
    """Detect simple help gestures and direct hand motion with MediaPipe Tasks hand_landmarker.task."""

    THUMB_TIP = 4
    THUMB_IP = 3
    THUMB_MCP = 2
    INDEX_TIP = 8
    INDEX_PIP = 6
    MIDDLE_TIP = 12
    MIDDLE_PIP = 10
    RING_TIP = 16
    RING_PIP = 14
    PINKY_TIP = 20
    PINKY_PIP = 18
    HAND_CONNECTIONS = (
        (0, 1),
        (1, 2),
        (2, 3),
        (3, 4),
        (0, 5),
        (5, 6),
        (6, 7),
        (7, 8),
        (5, 9),
        (9, 10),
        (10, 11),
        (11, 12),
        (9, 13),
        (13, 14),
        (14, 15),
        (15, 16),
        (13, 17),
        (17, 18),
        (18, 19),
        (19, 20),
        (0, 17),
    )

    def __init__(self, config: RescueConfig, i18n: Translator) -> None:
        self.config = config
        self.i18n = i18n
        self.enabled = mp is not None
        self.current_label = i18n.t("gestures_disabled")
        self._candidate = ""
        self._candidate_since = 0.0
        self._last_event_at = 0.0
        self._detector: Optional[Any] = None
        self._last_timestamp_ms = 0
        self._last_hand_center: Optional[tuple[int, int]] = None
        self._last_hand_center_at = 0.0
        self._hand_motion_score = 0.0
        self._hand_trail: list[tuple[int, int]] = []
        self.last_gesture: str = ""
        self.last_gesture_at: float = 0.0
        self.last_gesture_center: Optional[tuple[int, int]] = None
        self.last_gesture_motion_score: float = 0.0

        if not self.enabled:
            print(self.i18n.t("gesture_disabled_install"))
            return

        model_path = Path(self.config.hand_landmarker_model)
        if not model_path.exists():
            self.enabled = False
            print(self.i18n.t("gesture_model_missing", path=model_path))
            return

        try:
            from mediapipe.tasks import python as mp_tasks_python
            from mediapipe.tasks.python import vision as mp_tasks_vision

            base_options = mp_tasks_python.BaseOptions(model_asset_path=str(model_path))
            # Use a minimal set of options; some mediapipe versions have
            # different parameter names for confidence thresholds.
            options = mp_tasks_vision.HandLandmarkerOptions(
                base_options=base_options,
                running_mode=mp_tasks_vision.RunningMode.VIDEO,
                num_hands=2 if self.config.gesture_require_two_hands else 1,
            )
            self._detector = mp_tasks_vision.HandLandmarker.create_from_options(options)
        except Exception as error:
            self.enabled = False
            self._detector = None
            print(self.i18n.t("gesture_tasks_failed", path=model_path, error=error))
            print(self.i18n.t("gesture_reinstall_hint"))

    def close(self) -> None:
        if self._detector is not None:
            self._detector.close()

    def analyze(self, frame: np.ndarray) -> Optional[GestureEvent]:
        if self._detector is None:
            return None

        # MediaPipe reads RGB frames / MediaPipe читає кадри у форматі RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image: Any = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        timestamp_ms = max(int(time.time() * 1000), self._last_timestamp_ms + 1)
        self._last_timestamp_ms = timestamp_ms
        result: Any = self._detector.detect_for_video(mp_image, timestamp_ms)

        if not result.hand_landmarks:
            # If two-hands required and model returned one, treat as no gesture
            if self.config.gesture_require_two_hands and getattr(result, 'hand_landmarks', []) and len(result.hand_landmarks) < 2:
                self._candidate = ""
                self._candidate_since = 0.0
                self.current_label = self.i18n.t("no_hand")
                self._last_hand_center = None
                self._last_hand_center_at = 0.0
                self._hand_motion_score *= 0.85
                if len(self._hand_trail) > 1:
                    self._hand_trail = self._hand_trail[-1:]
                return None
            self._candidate = ""
            self._candidate_since = 0.0
            self.current_label = self.i18n.t("no_hand")
            self._last_hand_center = None
            self._last_hand_center_at = 0.0
            self._hand_motion_score *= 0.85
            if len(self._hand_trail) > 1:
                self._hand_trail = self._hand_trail[-1:]
            return None

        # If two-hands are present prefer the one with higher visibility or the first
        landmarks_list = result.hand_landmarks
        hand_landmarks = landmarks_list[0]
        if self.config.gesture_require_two_hands and len(landmarks_list) >= 2:
            # combine or choose primary; for simplicity choose the most recent (second) hand
            hand_landmarks = landmarks_list[0]
        self._draw_landmarks(frame, hand_landmarks)
        self._draw_hand_motion(frame, hand_landmarks)

        gesture = self._classify(hand_landmarks)
        now = time.time()
        if gesture != self._candidate:
            self._candidate = gesture
            self._candidate_since = now if gesture else 0.0

        held_seconds = now - self._candidate_since if gesture else 0.0
        if gesture:
            self.current_label = self.i18n.t(
                "gesture_detected",
                gesture=self._gesture_display_name(gesture),
                seconds=held_seconds,
            )
        else:
            self.current_label = self.i18n.t("hand_visible")

        # Only emit fist rescue gestures; don't emit other gestures
        min_hold = min(0.2, self.config.gesture_hold_seconds)
        gesture_ready = (
            gesture == "fist_help"
            and held_seconds >= min_hold
            and now - self._last_event_at > 1.0
        )
        if not gesture_ready:
            return None

        self._last_event_at = now
        # record last gesture info for fusion checks
        self.last_gesture = gesture
        self.last_gesture_at = now
        self.last_gesture_center = self._last_hand_center
        self.last_gesture_motion_score = self._hand_motion_score
        return GestureEvent(now, gesture, held_seconds, center=self._last_hand_center, motion_score=self._hand_motion_score)

    def _classify(self, landmarks: Any) -> str:
        # Closed fingers plus thumb up means a help signal here / Закриті пальці та великий палець вгору тут є сигналом допомоги
        closed_fingers = [
            self._finger_closed(landmarks, self.INDEX_TIP, self.INDEX_PIP),
            self._finger_closed(landmarks, self.MIDDLE_TIP, self.MIDDLE_PIP),
            self._finger_closed(landmarks, self.RING_TIP, self.RING_PIP),
            self._finger_closed(landmarks, self.PINKY_TIP, self.PINKY_PIP),
        ]
        closed_count = sum(1 for value in closed_fingers if value)
        thumb_up = (
            landmarks[self.THUMB_TIP].y < landmarks[self.THUMB_IP].y - 0.04
            and landmarks[self.THUMB_TIP].y < landmarks[self.THUMB_MCP].y - 0.03
        )

        if thumb_up and closed_count >= 3:
            return "thumbs_up_help"
        if closed_count >= 4:
            return "fist_help"
        if self._hand_motion_score > 0.72 and closed_count <= 1:
            return "direct_move_help"
        return ""

    def _gesture_display_name(self, gesture: str) -> str:
        return {
            "thumbs_up_help": self.i18n.t("thumbs_up_help_label"),
            "fist_help": self.i18n.t("fist_help_label"),
            "direct_move_help": self.i18n.t("direct_move_help_label"),
        }.get(gesture, gesture.replace("_", " "))

    @staticmethod
    def _finger_closed(landmarks: Any, tip_index: int, pip_index: int) -> bool:
        return landmarks[tip_index].y > landmarks[pip_index].y + 0.015

    def _draw_landmarks(self, frame: np.ndarray, landmarks: Any) -> None:
        height, width = frame.shape[:2]
        points = []
        for landmark in landmarks:
            x = int(max(0, min(width - 1, landmark.x * width)))
            y = int(max(0, min(height - 1, landmark.y * height)))
            points.append((x, y))

        for start, end in self.HAND_CONNECTIONS:
            if start < len(points) and end < len(points):
                cv2.line(frame, points[start], points[end], (80, 220, 255), 2)

        for point in points:
            cv2.circle(frame, point, 4, (0, 255, 120), -1)

    def _draw_hand_motion(self, frame: np.ndarray, landmarks: Any) -> None:
        height, width = frame.shape[:2]
        xs = [landmark.x for landmark in landmarks]
        ys = [landmark.y for landmark in landmarks]
        if not xs or not ys:
            return

        padding = 22
        x1 = int(max(0, min(xs) * width - padding))
        y1 = int(max(0, min(ys) * height - padding))
        x2 = int(min(width - 1, max(xs) * width + padding))
        y2 = int(min(height - 1, max(ys) * height + padding))
        center = ((x1 + x2) // 2, (y1 + y2) // 2)

        now = time.time()
        if self._last_hand_center is not None and self._last_hand_center_at > 0:
            dt = max(0.001, now - self._last_hand_center_at)
            dx = center[0] - self._last_hand_center[0]
            dy = center[1] - self._last_hand_center[1]
            pixels_per_second = math.sqrt(dx * dx + dy * dy) / dt
            normalized_motion = min(1.0, pixels_per_second / 900.0)
            self._hand_motion_score = (self._hand_motion_score * 0.68) + (normalized_motion * 0.32)
        else:
            self._hand_motion_score *= 0.8

        self._last_hand_center = center
        self._last_hand_center_at = now
        self._hand_trail.append(center)
        self._hand_trail = self._hand_trail[-18:]

        motion_color = (0, 255, 0)
        if self._hand_motion_score > 0.65:
            motion_color = (0, 0, 255)
        elif self._hand_motion_score > 0.32:
            motion_color = (0, 180, 255)

        cv2.rectangle(frame, (x1, y1), (x2, y2), motion_color, 3)
        cv2.circle(frame, center, 7, motion_color, -1)

        for index in range(1, len(self._hand_trail)):
            thickness = max(1, int(index / 5))
            cv2.line(
                frame,
                self._hand_trail[index - 1],
                self._hand_trail[index],
                (255, 220, 80),
                thickness,
            )

        label = self.i18n.t("hand_motion_label", score=self._hand_motion_score)
        cv2.rectangle(frame, (x1, max(0, y1 - 30)), (x1 + 10 + len(label) * 14, y1), motion_color, -1)
        put_text(
            frame,
            label,
            (x1 + 8, max(18, y1 - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (0, 0, 0),
            2,
            cv2.LINE_AA,
        )


class RiskFusion:
    """Combine audio and video signals into one decaying emergency risk score."""

    def __init__(self, config: RescueConfig, i18n: Translator) -> None:
        self.config = config
        self.threshold = config.risk_threshold
        self.i18n = i18n
        self.risk = 0.0
        self._last_update = time.time()
        self._recent_audio_impulses: list[float] = []
        self.last_reason = self.i18n.t("monitoring")

    def update_idle(self) -> float:
        # Risk slowly fades when nothing dangerous repeats / Ризик повільно спадає, якщо небезпека не повторюється
        now = time.time()
        elapsed = now - self._last_update
        self._last_update = now
        self.risk *= math.exp(-elapsed / 7.0)
        if self.risk < 1.0:
            self.risk = 0.0
        return self.risk

    def add_audio(self, event: AudioEvent) -> float:
        self.update_idle()
        if self.config.hit_only_detection:
            return self.risk

        if event.event_type == "gunshot_like":
            # Several sharp sounds close together increase confidence / Кілька різких звуків поруч підвищують впевненість
            self._recent_audio_impulses = [
                ts for ts in self._recent_audio_impulses if event.timestamp - ts < 8.0
            ]
            self._recent_audio_impulses.append(event.timestamp)
            impulse_bonus = 18.0 if len(self._recent_audio_impulses) >= 2 else 0.0
            self.risk += 45.0 + impulse_bonus
            self.last_reason = self.i18n.t(
                "sharp_impulse_reason",
                rms_db=event.rms_db,
                peak=event.peak,
            )
        elif event.event_type == "scream_like":
            self.risk += 23.0
            self.last_reason = self.i18n.t(
                "sustained_sound_reason",
                rms_db=event.rms_db,
            )

        self.risk = min(100.0, self.risk)
        return self.risk

    def add_video(self, event: VideoEvent) -> float:
        self.update_idle()
        if event.event_type == "body_hit":
            self.risk += 62.0
            self.last_reason = self.i18n.t(
                "body_collision_reason",
                direction=event.body_direction or self.i18n.t("direction_unknown"),
                score=event.hit_score,
            )
            # If not hit-only, also consider other event types
            if not self.config.hit_only_detection:
                pass
        elif not self.config.hit_only_detection:
            if event.event_type == "flash_like":
                self.risk += 28.0
                self.last_reason = self.i18n.t("bright_flash_reason", score=event.flash_score)
            elif event.event_type == "sudden_motion":
                self.risk += 12.0
                if event.body_direction:
                    self.last_reason = self.i18n.t(
                        "body_direction_reason",
                        direction=event.body_direction,
                        score=event.body_motion_score,
                    )
                else:
                    self.last_reason = self.i18n.t("sudden_motion_reason", score=event.motion_score)

        self.risk = min(100.0, self.risk)
        return self.risk

    def add_gesture(self, event: GestureEvent) -> float:
        self.update_idle()
        self.risk += 85.0
        gesture_name = self._format_gesture_name(event.gesture)
        self.last_reason = self.i18n.t(
            "manual_gesture_reason",
            gesture=gesture_name,
            seconds=event.held_seconds,
        )
        self.risk = min(100.0, self.risk)
        return self.risk

    def _format_gesture_name(self, gesture: str) -> str:
        return {
            "thumbs_up_help": self.i18n.t("thumbs_up_help_label"),
            "fist_help": self.i18n.t("fist_help_label"),
            "direct_move_help": self.i18n.t("direct_move_help_label"),
        }.get(gesture, gesture.replace("_", " "))

    def reset(self, reason: Optional[str] = None) -> None:
        self.risk = 0.0
        self._recent_audio_impulses = []
        self.last_reason = reason or self.i18n.t("monitoring")
        self._last_update = time.time()

    @property
    def is_emergency(self) -> bool:
        return self.risk >= self.threshold


class EvidenceRecorder:
    def __init__(self, config: RescueConfig) -> None:
        self.config = config
        EVIDENCE_DIR.mkdir(exist_ok=True)

    def save(self, frame: np.ndarray, risk: float, reason: str) -> Path:
        # Save one frame and metadata for later review / Зберігаємо кадр і дані для подальшої перевірки
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        image_path = EVIDENCE_DIR / f"event_{timestamp}.jpg"
        meta_path = EVIDENCE_DIR / f"event_{timestamp}.json"

        cv2.imwrite(str(image_path), frame)
        meta = {
            "time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "risk": round(risk, 2),
            "reason": reason,
            "emergency_number": self.config.emergency_number,
            "real_action_enabled": self.config.real_action_enabled,
        }
        meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
        return image_path


def parse_optional_float(value: str) -> Optional[float]:
    try:
        value = value.strip()
        return float(value) if value else None
    except ValueError:
        return None


def open_url(url: str) -> bool:
    try:
        if webbrowser.open(url, new=2, autoraise=True):
            return True
    except Exception:
        pass

    try:
        os.startfile(url)  # type: ignore[attr-defined]
        return True
    except Exception:
        return False


KEY_ALIASES = {
    "quit": {"q", "й"},
    "cancel": {"x", "ч"},
    "confirm": {"c", "с"},
    "add_shelter": {"a", "ф"},
    "auto_shelters": {"o", "щ"},
    "google_search": {"g", "п"},
    "login": {"l", "д"},
    "map": {"m", "ь"},
    "toggle_language": {"t", "е"},
    "uk_language": {"u", "г"},
    "en_language": {"e", "у"},
}


def key_to_action(key_code: int) -> str:
    if key_code < 0:
        return ""
    if key_code == 27:
        return "quit"

    return key_text_to_action(_key_to_text(key_code))


def key_text_to_action(key_text: str) -> str:
    key_text = (key_text or "").lower()
    if key_text in {"1", "2", "3", "4"}:
        return f"tab_{key_text}"

    for action, aliases in KEY_ALIASES.items():
        if key_text in aliases:
            return action
    return ""


def tk_event_to_action(event: Any) -> str:
    for value in (getattr(event, "char", ""), getattr(event, "keysym", "")):
        action = key_text_to_action(str(value))
        if action:
            return action
    if getattr(event, "keysym", "") == "Escape":
        return "quit"
    return ""


def _key_to_text(key_code: int) -> str:
    candidates = [key_code]
    low_byte = key_code & 0xFF
    if low_byte != key_code:
        candidates.append(low_byte)

    for candidate in candidates:
        if 0 <= candidate <= 0x10FFFF:
            try:
                text = chr(candidate).lower()
            except ValueError:
                continue
            if text and text.isprintable():
                return text
    return ""


class GoogleAccountManager:
    """Register a Google profile so Maps can be opened in the same user flow."""

    def __init__(self, config: RescueConfig, i18n: Translator) -> None:
        self.config = config
        self.i18n = i18n
        self.path = Path(config.google_user_profile_file)
        self.profile = self._load_profile()
        self.status_message = self.status()
        self._login_running = False
        self._lock = threading.Lock()

    @property
    def email(self) -> str:
        return str(self.profile.get("email", "")).strip()

    def status(self) -> str:
        if self.email:
            return self.i18n.t("google_account_registered", email=self.email)
        return self.i18n.t("google_account_not_registered")

    def profile_label(self) -> str:
        return self.email or self.i18n.t("not_registered")

    def register_async(self) -> str:
        # OAuth may wait for browser callback / OAuth може чекати зворотний виклик з браузера
        with self._lock:
            if self._login_running:
                return self.i18n.t("google_login_running")
            self._login_running = True
            self.status_message = self.i18n.t("opening_google_signin", url="Google")

        def worker() -> None:
            try:
                self.status_message = self._register_blocking()
                print(self.status_message)
            finally:
                with self._lock:
                    self._login_running = False

        threading.Thread(target=worker, daemon=True).start()
        return self.status_message

    def _load_profile(self) -> dict[str, object]:
        if not self.path.exists():
            return {}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return data if isinstance(data, dict) else {}

    def _save_profile(self, profile: dict[str, object]) -> None:
        self.path.write_text(
            json.dumps(profile, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        self.profile = profile

    def _register_blocking(self) -> str:
        manual_email = os.getenv("GOOGLE_ACCOUNT_EMAIL", "").strip()
        if manual_email:
            self._save_profile(
                {
                    "email": manual_email,
                    "name": os.getenv("GOOGLE_ACCOUNT_NAME", ""),
                    "source": "environment",
                    "registered_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                }
            )
            return self.i18n.t("google_profile_saved_env", email=manual_email)

        if not self.config.google_oauth_client_id:
            return self.i18n.t("google_account_set_client")

        try:
            return self._run_oauth_flow()
        except Exception as error:
            return self.i18n.t("google_account_error", error=error)

    def _run_oauth_flow(self) -> str:
        result: dict[str, str] = {}
        expected_state = secrets.token_urlsafe(24)
        code_verifier = secrets.token_urlsafe(64)
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode("ascii")).digest()
        ).rstrip(b"=").decode("ascii")

        done_page = self.i18n.t("google_signin_done_page")
        failed_page = self.i18n.t("google_signin_failed_page")

        class OAuthCallbackHandler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
                query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                result["code"] = query.get("code", [""])[0]
                result["state"] = query.get("state", [""])[0]
                result["error"] = query.get("error", [""])[0]
                ok = bool(result.get("code")) and result.get("state") == expected_state
                body = done_page if ok else failed_page
                encoded = body.encode("utf-8")
                self.send_response(200 if ok else 400)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Length", str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)

            def log_message(self, format: str, *_args: object) -> None:  # noqa: A002, F841
                return

        try:
            server = ThreadingHTTPServer(("127.0.0.1", 0), OAuthCallbackHandler)
        except OSError as error:
            return self.i18n.t("google_account_callback_failed", error=error)

        redirect_uri = f"http://127.0.0.1:{server.server_address[1]}/oauth2callback"
        params = {
            "client_id": self.config.google_oauth_client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": expected_state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "access_type": "offline",
            "prompt": "select_account",
        }
        auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)
        self.status_message = self.i18n.t("opening_google_signin", url=auth_url)
        print(self.status_message)

        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()
        open_url(auth_url)

        deadline = time.time() + self.config.google_oauth_timeout_seconds
        try:
            while time.time() < deadline and not result:
                time.sleep(0.15)
        finally:
            server.shutdown()
            server.server_close()

        if not result:
            return self.i18n.t("google_account_timeout")
        if result.get("error"):
            return self.i18n.t("google_account_error", error=result["error"])
        if result.get("state") != expected_state or not result.get("code"):
            return self.i18n.t("google_account_timeout")

        token_data = self._exchange_code(result["code"], redirect_uri, code_verifier)
        access_token = str(token_data.get("access_token", ""))
        if not access_token:
            return self.i18n.t("google_token_error", error=token_data)

        profile = self._fetch_profile(access_token)
        email = str(profile.get("email", "")).strip()
        if not email:
            return self.i18n.t("google_profile_incomplete")

        self._save_profile(
            {
                "email": email,
                "name": profile.get("name", ""),
                "picture": profile.get("picture", ""),
                "source": "google_oauth",
                "registered_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            }
        )
        return self.i18n.t("google_account_registered", email=email)

    def _exchange_code(self, code: str, redirect_uri: str, code_verifier: str) -> dict[str, object]:
        payload = {
            "client_id": self.config.google_oauth_client_id,
            "code": code,
            "code_verifier": code_verifier,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        }
        if self.config.google_oauth_client_secret:
            payload["client_secret"] = self.config.google_oauth_client_secret

        request = urllib.request.Request(
            "https://oauth2.googleapis.com/token",
            data=urllib.parse.urlencode(payload).encode("utf-8"),
            method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as error:
            return {"error": str(error)}

    def _fetch_profile(self, access_token: str) -> dict[str, object]:
        request = urllib.request.Request("https://openidconnect.googleapis.com/v1/userinfo")
        request.add_header("Authorization", f"Bearer {access_token}")
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as error:
            return {"error": str(error)}


class ShelterManager:
    """Load shelters and find the nearest one when user coordinates are known."""

    def __init__(self, config: RescueConfig, i18n: Optional[Translator] = None) -> None:
        self.config = config
        self.i18n = i18n or get_translator(config.app_language)
        self.path = Path(config.shelters_file)
        self.user_lat = parse_optional_float(config.user_lat)
        self.user_lon = parse_optional_float(config.user_lon)
        self.shelters = self._load_shelters()
        self.google_shelters: list[Shelter] = []
        self.google_status = self.i18n.t("google_not_searched")
        self.last_opened_url = ""
        self._google_search_running = False
        self._last_refresh_at = 0.0
        self._refresh_lock = threading.Lock()
        self._query_override: Optional[str] = None

    def default_query(self) -> str:
        return (self.config.google_maps_query or self.i18n.t("google_maps_shelter_query")).strip()

    def query_text(self, query: Optional[str] = None) -> str:
        if query is not None:
            return (query.strip() or self.default_query())
        return (self._query_override or self.default_query()).strip()

    def language_code(self) -> str:
        return (self.config.google_maps_language or self.i18n.language).strip()

    def search_radius_m(self) -> float:
        return max(100.0, min(float(self.config.google_maps_radius_m), 1500.0))

    def max_search_distance_km(self) -> float:
        return self.search_radius_m() / 1000.0

    def set_user_location(self, lat: float, lon: float) -> None:
        self.user_lat = lat
        self.user_lon = lon

    def query_near_user(self, query_text: str) -> str:
        if self.user_lat is None or self.user_lon is None:
            return query_text
        return f"{query_text} {self.i18n.t('google_maps_near')} {self.user_lat},{self.user_lon}"

    def auto_search_shelters_async(self) -> str:
        with self._refresh_lock:
            if self._google_search_running:
                return self.i18n.t("google_search_running")
            self._google_search_running = True
            self.google_status = self.i18n.t("auto_shelter_searching")

        def worker() -> None:
            try:
                print(self.auto_search_shelters())
            finally:
                with self._refresh_lock:
                    self._google_search_running = False

        threading.Thread(target=worker, daemon=True).start()
        return self.google_status

    def auto_search_shelters(self) -> str:
        if self.user_lat is None or self.user_lon is None:
            self.google_status = self.i18n.t("auto_location_detecting")
            if not self.detect_location():
                return self.google_status
        return self.refresh_open_shelters()

    def detect_location(self) -> bool:
        urls = [
            self.config.auto_location_url,
            "https://ipwho.is/",
        ]
        for url in urls:
            try:
                request = urllib.request.Request(url, headers={"User-Agent": "StepPrep/1.0"})
                with urllib.request.urlopen(request, timeout=8) as response:
                    data = json.loads(response.read().decode("utf-8"))
                lat = parse_optional_float(str(data.get("latitude", data.get("lat", ""))))
                lon = parse_optional_float(str(data.get("longitude", data.get("lon", ""))))
                if lat is not None and lon is not None:
                    self.set_user_location(lat, lon)
                    self.google_status = self.i18n.t("auto_location_found")
                    return True
            except Exception:
                continue
        self.google_status = self.i18n.t("auto_location_failed")
        return False

    def refresh_open_shelters(self) -> str:
        if self.user_lat is None or self.user_lon is None:
            self.google_status = self.i18n.t("auto_location_failed")
            return self.google_status

        radius = self.search_radius_m()
        query = f"""
[out:json][timeout:12];
(
  node(around:{radius:.0f},{self.user_lat},{self.user_lon})["railway"="station"]["station"="subway"];
  way(around:{radius:.0f},{self.user_lat},{self.user_lon})["railway"="station"]["station"="subway"];
  relation(around:{radius:.0f},{self.user_lat},{self.user_lon})["railway"="station"]["station"="subway"];
  node(around:{radius:.0f},{self.user_lat},{self.user_lon})["public_transport"="station"]["subway"="yes"];
  way(around:{radius:.0f},{self.user_lat},{self.user_lon})["public_transport"="station"]["subway"="yes"];
  relation(around:{radius:.0f},{self.user_lat},{self.user_lon})["public_transport"="station"]["subway"="yes"];
  node(around:{radius:.0f},{self.user_lat},{self.user_lon})["railway"="subway_entrance"];
  way(around:{radius:.0f},{self.user_lat},{self.user_lon})["railway"="subway_entrance"];
  node(around:{radius:.0f},{self.user_lat},{self.user_lon})["amenity"="shelter"];
  way(around:{radius:.0f},{self.user_lat},{self.user_lon})["amenity"="shelter"];
  relation(around:{radius:.0f},{self.user_lat},{self.user_lon})["amenity"="shelter"];
  node(around:{radius:.0f},{self.user_lat},{self.user_lon})["emergency"="shelter"];
  way(around:{radius:.0f},{self.user_lat},{self.user_lon})["emergency"="shelter"];
  relation(around:{radius:.0f},{self.user_lat},{self.user_lon})["emergency"="shelter"];
);
out center tags 30;
"""
        try:
            request = urllib.request.Request(
                self.config.overpass_api_url,
                data=urllib.parse.urlencode({"data": query}).encode("utf-8"),
                method="POST",
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "User-Agent": "StepPrep/1.0",
                },
            )
            with urllib.request.urlopen(request, timeout=18) as response:
                data = json.loads(response.read().decode("utf-8"))
        except Exception as error:
            self.google_status = self.i18n.t("auto_shelter_failed", error=error)
            return self.google_status

        self.google_shelters = self._shelters_from_overpass(data)
        self._last_refresh_at = time.time()
        if not self.google_shelters:
            self.google_status = self.i18n.t("auto_shelter_no_candidates", radius=int(radius))
        else:
            self.google_status = self.i18n.t("auto_shelter_found", count=len(self.google_shelters), radius=int(radius))
        return self.google_status

    def _shelters_from_overpass(self, data: dict[str, Any]) -> list[Shelter]:
        found: list[Shelter] = []
        seen: set[tuple[str, str, str]] = set()
        for element in data.get("elements", []):
            if not isinstance(element, dict):
                continue
            tags = element.get("tags", {})
            if not isinstance(tags, dict):
                tags = {}
            center = element.get("center", {})
            if not isinstance(center, dict):
                center = {}
            lat = parse_optional_float(str(element.get("lat", center.get("lat", ""))))
            lon = parse_optional_float(str(element.get("lon", center.get("lon", ""))))
            if lat is None or lon is None:
                continue
            if self.user_lat is not None and self.user_lon is not None:
                if self._distance_km(self.user_lat, self.user_lon, lat, lon) > self.max_search_distance_km():
                    continue
            fallback_name = (
                self.i18n.t("metro_entrance_shelter")
                if tags.get("railway") == "subway_entrance"
                else self.i18n.t("metro_station_shelter")
            )
            name = self._localized_osm_tag(tags, "name") or self._localized_osm_tag(tags, "official_name") or fallback_name
            address = self._osm_address(tags)
            key = (name.casefold(), f"{lat:.5f}", f"{lon:.5f}")
            if key in seen:
                continue
            seen.add(key)
            found.append(
                Shelter(
                    name=name,
                    address=address,
                    lat=lat,
                    lon=lon,
                    note=self.i18n.t("osm_shelter_note"),
                    source="openstreetmap",
                )
            )
        return found

    def _localized_osm_tag(self, tags: dict[str, Any], key: str) -> str:
        language = self.i18n.language
        for candidate in (f"{key}:{language}", key, f"{key}:uk", f"{key}:en"):
            value = str(tags.get(candidate, "")).strip()
            if value:
                return value
        return ""

    def _osm_address(self, tags: dict[str, Any]) -> str:
        full_address = str(tags.get("addr:full", "")).strip()
        if full_address:
            return full_address
        street = str(tags.get("addr:street", "")).strip()
        house = str(tags.get("addr:housenumber", "")).strip()
        city = str(tags.get("addr:city", "")).strip()
        first_line = " ".join(part for part in (street, house) if part)
        parts = [part for part in (first_line, city) if part]
        return ", ".join(parts)

    def _load_shelters(self) -> list[Shelter]:
        if not self.path.exists():
            print(self.i18n.t("shelter_file_missing", path=self.path))
            return []

        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            print(self.i18n.t("shelter_file_read_failed", path=self.path, error=error))
            return []

        shelters = []
        for item in data.get("shelters", []):
            shelters.append(
                Shelter(
                    name=str(item.get("name", self.i18n.t("unnamed_shelter"))),
                    address=str(item.get("address", "")),
                    lat=parse_optional_float(str(item.get("lat", ""))),
                    lon=parse_optional_float(str(item.get("lon", ""))),
                    note=str(item.get("note", "")),
                    phone=str(item.get("phone", "")),
                    google_maps_uri=str(item.get("google_maps_uri", "")),
                    source=str(item.get("source", "local")),
                )
            )
        return shelters

    @property
    def all_shelters(self) -> list[Shelter]:
        return self.google_shelters + self.shelters

    def add_shelter(
        self,
        name: str,
        address: str,
        lat: Optional[float],
        lon: Optional[float],
        note: str,
        phone: str,
    ) -> str:
        name = name.strip()
        address = address.strip()
        note = note.strip()
        phone = phone.strip()
        if not name or (not address and (lat is None or lon is None)):
            return self.i18n.t("shelter_add_missing")

        try:
            if self.path.exists():
                data = json.loads(self.path.read_text(encoding="utf-8"))
                if not isinstance(data, dict):
                    data = {}
            else:
                data = {}
            shelters_data = data.setdefault("shelters", [])
            if not isinstance(shelters_data, list):
                shelters_data = []
                data["shelters"] = shelters_data

            entry = {
                "name": name,
                "address": address,
                "lat": lat,
                "lon": lon,
                "note": note,
                "phone": phone,
                "source": "manual",
            }
            shelters_data.append(entry)
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            self.shelters = self._load_shelters()
            return self.i18n.t("shelter_added", name=name)
        except Exception as error:
            return self.i18n.t("shelter_add_failed", error=error)

    def add_shelter_from_env(self) -> str:
        # Env vars keep manual shelter input simple / Env-змінні спрощують ручне додавання укриття
        return self.add_shelter(
            name=os.getenv("NEW_SHELTER_NAME", ""),
            address=os.getenv("NEW_SHELTER_ADDRESS", ""),
            lat=parse_optional_float(os.getenv("NEW_SHELTER_LAT", "")),
            lon=parse_optional_float(os.getenv("NEW_SHELTER_LON", "")),
            note=os.getenv("NEW_SHELTER_NOTE", ""),
            phone=os.getenv("NEW_SHELTER_PHONE", ""),
        )

    def refresh_google_shelters(self, query: Optional[str] = None) -> str:
        self._last_refresh_at = time.time()
        if query is not None:
            self._query_override = query.strip() or None
        query_text = self.query_text()

        # Google Places search needs API key and current coordinates / Пошук Google Places потребує ключ і координати
        if not self.config.google_maps_api_key:
            self.google_status = self.i18n.t("google_set_api_places")
            return self.google_status

        if self.user_lat is None or self.user_lon is None:
            self.google_status = self.i18n.t("google_set_location")
            return self.google_status

        url = "https://places.googleapis.com/v1/places:searchText"
        payload = {
            "textQuery": query_text,
            "languageCode": self.language_code(),
            "maxResultCount": 8,
            "locationRestriction": {
                "circle": {
                    "center": {
                        "latitude": self.user_lat,
                        "longitude": self.user_lon,
                    },
                    "radius": self.search_radius_m(),
                }
            },
        }
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={
                "Content-Type": "application/json",
                "X-Goog-Api-Key": self.config.google_maps_api_key,
                "X-Goog-FieldMask": (
                    "places.displayName,places.formattedAddress,places.location,"
                    "places.googleMapsUri,places.nationalPhoneNumber"
                ),
            },
        )

        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))
        except Exception as error:
            self.google_status = self.i18n.t("google_search_failed", error=error)
            return self.google_status

        found = []
        for place in data.get("places", []):
            location = place.get("location", {})
            display_name = place.get("displayName", {})
            found.append(
                Shelter(
                    name=str(display_name.get("text") or self.i18n.t("google_shelter_name")),
                    address=str(place.get("formattedAddress", "")),
                    lat=parse_optional_float(str(location.get("latitude", ""))),
                    lon=parse_optional_float(str(location.get("longitude", ""))),
                    note=self.i18n.t("google_candidate_note_desktop"),
                    phone=str(place.get("nationalPhoneNumber", "")),
                    google_maps_uri=str(place.get("googleMapsUri", "")),
                    source="google_maps",
                )
            )

        self.google_shelters = found
        self._last_refresh_at = time.time()
        self.google_status = self.i18n.t("google_found_shelters", count=len(found))
        return self.google_status

    def refresh_google_shelters_async(self, query: Optional[str] = None) -> str:
        with self._refresh_lock:
            if self._google_search_running:
                return self.i18n.t("google_search_running")
            self._google_search_running = True
            self.google_status = self.i18n.t("google_searching")
            if query is not None:
                self._query_override = query.strip() or None

        def worker() -> None:
            try:
                print(self.refresh_google_shelters(query=query))
            finally:
                with self._refresh_lock:
                    self._google_search_running = False

        threading.Thread(target=worker, daemon=True).start()
        return self.google_status

    def search_shelters(self, query: Optional[str] = None) -> str:
        if query is not None:
            self._query_override = query.strip() or None
        if not self.config.google_maps_api_key:
            url = self.map_url(query=query)
            self.last_opened_url = url
            opened = open_url(url)
            self.google_status = self.i18n.t("google_search_fallback")
            return self.i18n.t("shelter_map_opened") if opened else self.i18n.t("open_url", url=url)
        return self.refresh_google_shelters_async(query=query)

    def maybe_refresh_passively(self) -> None:
        if not self.config.google_maps_api_key:
            self.google_status = self.i18n.t("passive_fallback_ready")
            return

        if self.user_lat is None or self.user_lon is None:
            self.google_status = self.i18n.t("passive_waiting_location")
            return

        now = time.time()
        if now - self._last_refresh_at < self.config.passive_shelter_refresh_seconds:
            return

        self.refresh_google_shelters_async()

    def nearest(self) -> tuple[Optional[Shelter], Optional[float]]:
        # Exact nearest needs user and shelter coordinates / Точне найближче потребує координати користувача та укриттів
        if self.user_lat is None or self.user_lon is None:
            return None, None

        nearest_shelter = None
        nearest_distance = None
        for shelter in self.all_shelters:
            if shelter.lat is None or shelter.lon is None:
                continue

            distance = self._distance_km(self.user_lat, self.user_lon, shelter.lat, shelter.lon)
            if distance > self.max_search_distance_km():
                continue
            if nearest_distance is None or distance < nearest_distance:
                nearest_shelter = shelter
                nearest_distance = distance

        return nearest_shelter, nearest_distance

    def best_available(self) -> Optional[Shelter]:
        nearest_shelter, _ = self.nearest()
        if nearest_shelter is not None:
            return nearest_shelter
        return self.all_shelters[0] if self.all_shelters else self.fallback_search_shelter()

    def fallback_search_shelter(self) -> Shelter:
        if self.user_lat is not None and self.user_lon is not None:
            address = f"{self.i18n.t('google_maps_near')} {self.user_lat},{self.user_lon}"
        else:
            address = self.i18n.t("google_maps_no_location")

        return Shelter(
            name=self.i18n.t("google_maps_fallback_name"),
            address=address,
            note=self.i18n.t("google_maps_fallback_note"),
            source="google_maps_search",
        )

    def ranked_shelters(self, limit: int = 5) -> list[tuple[Shelter, Optional[float]]]:
        ranked = []
        for shelter in self.all_shelters:
            distance = None
            if (
                self.user_lat is not None
                and self.user_lon is not None
                and shelter.lat is not None
                and shelter.lon is not None
            ):
                distance = self._distance_km(self.user_lat, self.user_lon, shelter.lat, shelter.lon)
                if distance > self.max_search_distance_km():
                    continue
            ranked.append((shelter, distance))

        ranked.sort(key=lambda item: item[1] if item[1] is not None else 1_000_000.0)
        if not ranked:
            ranked.append((self.fallback_search_shelter(), None))
        return ranked[:limit]

    def map_url(self, query: Optional[str] = None) -> str:
        shelter = self.best_available()
        query_text = self.query_text(query)
        if shelter is not None and shelter.source == "google_maps_search":
            if self.user_lat is not None and self.user_lon is not None:
                query_text = self.query_near_user(query_text)
            return "https://www.google.com/maps/search/?api=1&query=" + urllib.parse.quote(query_text)

        if shelter is not None and shelter.google_maps_uri:
            return shelter.google_maps_uri

        if shelter is not None and shelter.lat is not None and shelter.lon is not None:
            destination = f"{shelter.lat},{shelter.lon}"
            if self.user_lat is not None and self.user_lon is not None:
                origin = f"{self.user_lat},{self.user_lon}"
                return (
                    "https://www.google.com/maps/dir/?api=1&travelmode=walking"
                    f"&origin={urllib.parse.quote(origin)}&destination={urllib.parse.quote(destination)}"
                )
            return f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(destination)}"

        if shelter is not None and shelter.address:
            return "https://www.google.com/maps/search/?api=1&query=" + urllib.parse.quote(
                shelter.address
            )

        if self.user_lat is not None and self.user_lon is not None:
            query = self.query_near_user(self.query_text())
            return "https://www.google.com/maps/search/?api=1&query=" + urllib.parse.quote(query)

        return "https://www.google.com/maps/search/?api=1&query=" + urllib.parse.quote(
            self.query_text()
        )

    def open_map(self) -> str:
        url = self.map_url()
        self.last_opened_url = url
        opened = open_url(url)
        return self.i18n.t("shelter_map_opened") if opened else self.i18n.t("open_url", url=url)

    @staticmethod
    def _distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        radius_km = 6371.0
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        a = (
            math.sin(delta_lat / 2) ** 2
            + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
        )
        return radius_km * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


class EmergencyAction:
    """Run the final emergency action after confirmation/countdown."""

    def __init__(self, config: RescueConfig, i18n: Translator) -> None:
        self.config = config
        self.i18n = i18n
        self._last_action_at = 0.0

    def run(self, reason: str) -> str:
        # Cooldown prevents repeated calls from one event / Пауза захищає від повторних дзвінків з однієї події
        now = time.time()
        if now - self._last_action_at < self.config.min_seconds_between_alerts:
            return self.i18n.t("action_cooldown")

        self._last_action_at = now
        if not self.config.real_action_enabled:
            # Demo mode never calls real emergency services / Demo-режим ніколи не дзвонить у реальні служби
            return self.i18n.t("demo_action", number=self.config.emergency_number, reason=reason)

        if self.config.local_action_command:
            return self._run_local_command(reason)

        return self._call_with_twilio(reason)

    def _run_local_command(self, reason: str) -> str:
        command = self.config.local_action_command
        safe_reason = reason.replace('"', "'")
        completed = subprocess.run(
            f'{command} "{self.config.emergency_number}" "{safe_reason}"',
            shell=True,
            capture_output=True,
            text=True,
        )
        exit_code = completed.returncode
        return self.i18n.t("local_action_finished", code=exit_code)

    def _call_with_twilio(self, reason: str) -> str:
        # Twilio needs account data before placing a call / Twilio потребує дані акаунта перед дзвінком
        missing = [
            name
            for name, value in {
                "TWILIO_ACCOUNT_SID": self.config.twilio_account_sid,
                "TWILIO_AUTH_TOKEN": self.config.twilio_auth_token,
                "TWILIO_FROM_NUMBER": self.config.twilio_from_number,
            }.items()
            if not value
        ]
        if missing:
            return self.i18n.t("twilio_missing", missing=", ".join(missing))

        message = self.i18n.t("twilio_message", reason=reason)
        message = html.escape(message, quote=True)
        twiml = f"<Response><Say>{message}</Say><Pause length=\"1\"/><Say>{message}</Say></Response>"
        payload = urllib.parse.urlencode(
            {
                "To": self.config.emergency_number,
                "From": self.config.twilio_from_number,
                "Twiml": twiml,
            }
        ).encode("utf-8")

        url = (
            "https://api.twilio.com/2010-04-01/Accounts/"
            f"{self.config.twilio_account_sid}/Calls.json"
        )
        request = urllib.request.Request(url, data=payload, method="POST")
        token = f"{self.config.twilio_account_sid}:{self.config.twilio_auth_token}"
        auth_header = base64.b64encode(token.encode("utf-8")).decode("ascii")
        request.add_header("Authorization", f"Basic {auth_header}")
        request.add_header("Content-Type", "application/x-www-form-urlencoded")

        try:
            with urllib.request.urlopen(request, timeout=12) as response:
                body = response.read().decode("utf-8", errors="replace")
                return self.i18n.t("twilio_sent", status=response.status, body=body[:180])
        except Exception as error:
            return self.i18n.t("twilio_failed", error=error)


class AlarmController:
    def __init__(self, config: RescueConfig, action: EmergencyAction, i18n: Translator) -> None:
        self.config = config
        self.action = action
        self.i18n = i18n
        self.active = False
        self.started_at = 0.0
        self.reason = ""
        self.status_message = self.i18n.t("monitoring")
        self._last_beep_at = 0.0
        self._already_triggered = False

    def start(self, reason: str) -> None:
        # Start countdown so the user can cancel false alarms / Запускаємо відлік, щоб можна було скасувати хибну тривогу
        if self.active:
            self.reason = reason
            return

        self.active = True
        self.started_at = time.time()
        self.reason = reason
        self.status_message = self.i18n.t("alarm_status")
        self._already_triggered = False
        self._beep()

    def cancel(self) -> None:
        self.active = False
        self.status_message = self.i18n.t("alarm_cancelled")
        self._already_triggered = False

    def confirm_now(self) -> None:
        if self.active:
            self._trigger()

    def tick(self) -> None:
        if not self.active:
            return

        self._beep()
        remaining = self.remaining_seconds
        if remaining <= 0 and not self._already_triggered:
            self._trigger()

    @property
    def remaining_seconds(self) -> float:
        if not self.active:
            return 0.0
        elapsed = time.time() - self.started_at
        return max(0.0, self.config.countdown_seconds - elapsed)

    def _trigger(self) -> None:
        self._already_triggered = True
        result = self.action.run(self.reason)
        print(result)
        self.status_message = result
        self.active = False

    def _beep(self) -> None:
        # Short periodic sound draws attention / Короткий періодичний звук привертає увагу
        now = time.time()
        if now - self._last_beep_at < 0.9:
            return

        self._last_beep_at = now
        if winsound is not None:
            threading.Thread(
                target=lambda: winsound.Beep(1400, 180),
                daemon=True,
            ).start()
        else:
            print("\a", end="", flush=True)


def draw_tabs(frame: np.ndarray, current_tab: str, i18n: Translator) -> None:
    # Simple OpenCV tabs / Прості вкладки OpenCV
    tabs = [
        ("monitor", i18n.t("monitor_tab")),
        ("shelter", i18n.t("shelter_feed_tab")),
        ("supplies", i18n.t("supplies_tab")),
        ("settings", i18n.t("settings_tab")),
    ]
    x = 18
    available_width = max(540, frame.shape[1] - 36 - (len(tabs) - 1) * 8)
    tab_width = min(190, max(128, available_width // len(tabs)))
    for tab_id, label in tabs:
        selected = tab_id == current_tab
        color = (0, 135, 245) if selected else (24, 31, 40)
        border = (0, 205, 255) if selected else (86, 100, 116)
        cv2.rectangle(frame, (x, 8), (x + tab_width, 42), color, -1)
        cv2.rectangle(frame, (x, 8), (x + tab_width, 42), border, 2)
        put_text(
            frame,
            label[:24],
            (x + 12, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.52,
            (255, 255, 255),
            2 if selected else 1,
            cv2.LINE_AA,
        )
        x += tab_width + 8


def draw_text_lines(
    frame: np.ndarray,
    lines: list[str],
    x: int,
    y: int,
    color: tuple[int, int, int] = (240, 240, 240),
    scale: float = 0.62,
    thickness: int = 1,
    line_height: int = 30,
) -> None:
    for index, line in enumerate(lines):
        put_text(
            frame,
            line[:118],
            (x, y + index * line_height),
            cv2.FONT_HERSHEY_SIMPLEX,
            scale,
            color,
            thickness,
            cv2.LINE_AA,
        )


def draw_shelter_feed_card(
    frame: np.ndarray,
    shelter: Shelter,
    distance_km: Optional[float],
    index: int,
    i18n: Translator,
    x: int,
    y: int,
    width: int,
    height: int,
) -> None:
    is_primary = index == 0
    fill = (28, 36, 46) if not is_primary else (28, 54, 68)
    border = (82, 120, 150) if not is_primary else (0, 190, 255)
    cv2.rectangle(frame, (x, y), (x + width, y + height), fill, -1)
    cv2.rectangle(frame, (x, y), (x + width, y + height), border, 2)

    badge = i18n.t("nearest") if is_primary else f"#{index + 1}"
    cv2.rectangle(frame, (x + 14, y + 12), (x + 134, y + 42), border, -1)
    put_text(
        frame,
        badge[:14],
        (x + 24, y + 34),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.52,
        (0, 0, 0) if is_primary else (255, 255, 255),
        2,
        cv2.LINE_AA,
    )

    distance_label = f"{distance_km:.2f} km" if distance_km is not None else i18n.t("distance_unknown")
    title = f"{shelter.name[:58]} ({shelter.source})"
    address = shelter.address or i18n.t("address_not_provided")
    note = shelter.note or i18n.t("open_route_note")
    phone = (
        f"{i18n.t('phone')}: {shelter.phone}"
        if shelter.phone
        else f"{i18n.t('phone')}: {i18n.t('phone_not_provided')}"
    )

    put_text(
        frame,
        title,
        (x + 154, y + 34),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.64,
        (245, 248, 252),
        2 if is_primary else 1,
        cv2.LINE_AA,
    )
    draw_text_lines(
        frame,
        [
            f"{i18n.t('distance')}: {distance_label}",
            f"{i18n.t('address')}: {address}",
            f"{phone} | {note}",
        ],
        x + 24,
        y + 70,
        color=(226, 232, 238),
        scale=0.52,
        line_height=24,
    )


def draw_overlay(
    frame: np.ndarray,
    risk: float,
    reason: str,
    metrics: dict[str, Any],
    alarm: AlarmController,
    config: RescueConfig,
    gesture_label: str,
    current_tab: str,
    i18n: Translator,
) -> np.ndarray:
    # Draw status text over the camera image / Малюємо статус поверх зображення з камери
    _height, width = frame.shape[:2]

    panel_height = 236 if alarm.active else 206
    cv2.rectangle(frame, (0, 0), (width, panel_height), (14, 18, 24), -1)
    cv2.rectangle(frame, (0, panel_height - 2), (width, panel_height), (0, 170, 255), -1)
    draw_tabs(frame, current_tab, i18n)

    risk_color = (0, 220, 0)
    if risk >= config.risk_threshold:
        risk_color = (0, 0, 255)
    elif risk >= config.risk_threshold * 0.6:
        risk_color = (0, 180, 255)

    put_text(
        frame,
        f"{i18n.t('app_title')} | {i18n.t('risk')}: {risk:05.1f}/100 | "
        f"{i18n.t('mode')}: {i18n.t('real') if config.real_action_enabled else i18n.t('demo')}",
        (18, 68),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.75,
        risk_color,
        2,
        cv2.LINE_AA,
    )
    draw_text_lines(
        frame,
        [
            f"{i18n.t('reason')}: {reason[:88]}",
            f"{i18n.t('motion')}: {metrics.get('motion', 0):.2f} | "
            f"{i18n.t('body_direction')}: {metrics.get('body_direction', i18n.t('direction_unknown'))} "
            f"{float(metrics.get('body_motion', 0.0)):.2f} | "
            f"{i18n.t('body_collision')}: {float(metrics.get('body_collision', 0.0)):.2f} "
            f"{i18n.t('hit_yes') if metrics.get('body_hit') else i18n.t('hit_no')}",
            f"{i18n.t('gesture')}: {gesture_label[:30]} | "
            f"{i18n.t('flash')}: {metrics.get('flash', 0):.2f} | {i18n.t('number')}: {config.emergency_number}",
            f"T {i18n.t('language')}: {i18n.language_name()} | 3 {i18n.t('supplies_short')} | "
            f"4 {i18n.t('settings_short')} | A {i18n.t('add_shelter_short')} | L {i18n.t('google_account')}",
        ],
        18,
        100,
        color=(220, 230, 240),
        scale=0.58,
        line_height=28,
    )

    if alarm.active:
        put_text(
            frame,
            i18n.t("alarm_action_line", seconds=alarm.remaining_seconds),
            (18, 224),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 0, 255),
            2,
            cv2.LINE_AA,
        )

    return frame


def draw_shelter_tab(
    frame: np.ndarray,
    risk: float,
    reason: str,
    alarm: AlarmController,
    config: RescueConfig,
    shelter_manager: ShelterManager,
    current_tab: str,
    i18n: Translator,
) -> np.ndarray:
    # Shelter view shares alarm state / Вкладка укриття пов'язана зі станом тривоги
    height, width = frame.shape[:2]
    cv2.rectangle(frame, (0, 0), (width, height), (16, 21, 28), -1)
    draw_tabs(frame, current_tab, i18n)

    alarm_state = i18n.t("active") if alarm.active else i18n.t("ready")
    lines = [
        f"{i18n.t('shelter_feed_header')} | {i18n.t('alarm')}: {alarm_state} | "
        f"{i18n.t('risk')}: {risk:05.1f}/100 | {i18n.t('call')}: {config.emergency_number}",
        f"{i18n.t('reason')}: {reason[:88]}",
        shelter_manager.google_status,
        i18n.t("keys_shelter"),
    ]
    if alarm.active:
        lines.insert(3, i18n.t("alarm_feed_opened"))

    draw_text_lines(frame, lines, 26, 68, line_height=28)

    ranked_shelters = shelter_manager.ranked_shelters(limit=4)
    card_x = 26
    card_y = 190
    card_width = max(500, width - 52)
    card_height = 118
    gap = 14
    max_cards = max(1, min(len(ranked_shelters), (height - card_y - 54) // (card_height + gap)))
    for index, (shelter, distance_km) in enumerate(ranked_shelters[:max_cards]):
        draw_shelter_feed_card(
            frame,
            shelter,
            distance_km,
            index,
            i18n,
            card_x,
            card_y + index * (card_height + gap),
            card_width,
            card_height,
        )

    if shelter_manager.last_opened_url:
        draw_text_lines(
            frame,
            [i18n.t("last_map_url", url=shelter_manager.last_opened_url)],
            26,
            height - 36,
            color=(180, 220, 255),
            scale=0.48,
            line_height=24,
        )

    return frame


def draw_supplies_tab(frame: np.ndarray, current_tab: str, i18n: Translator) -> np.ndarray:
    # Compact checklist for evacuation / Короткий список для швидкого збору речей
    height, width = frame.shape[:2]
    cv2.rectangle(frame, (0, 0), (width, height), (13, 18, 25), -1)
    draw_tabs(frame, current_tab, i18n)

    put_text(
        frame,
        i18n.t("supplies_header"),
        (26, 88),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.9,
        (0, 205, 255),
        2,
        cv2.LINE_AA,
    )
    put_text(
        frame,
        i18n.t("supplies_keys"),
        (26, 122),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.52,
        (220, 235, 245),
        1,
        cv2.LINE_AA,
    )

    items = EMERGENCY_SUPPLIES.get(i18n.language, EMERGENCY_SUPPLIES["uk"])
    columns = 1 if width < 1120 else 2
    card_width = width - 52 if columns == 1 else (width - 72) // 2
    card_height = 74
    start_y = 158
    for index, (title, detail) in enumerate(items):
        column = index % columns
        row = index // columns
        x = 26 + column * (card_width + 20)
        y = start_y + row * (card_height + 14)
        if y + card_height > height - 28:
            break
        fill = (24, 32, 42)
        border = (70, 112, 144)
        cv2.rectangle(frame, (x, y), (x + card_width, y + card_height), fill, -1)
        cv2.rectangle(frame, (x, y), (x + card_width, y + card_height), border, 2)
        cv2.rectangle(frame, (x + 12, y + 17), (x + 36, y + 41), (0, 180, 255), 2)
        put_text(
            frame,
            title[:30],
            (x + 52, y + 29),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (248, 252, 255),
            2,
            cv2.LINE_AA,
        )
        put_text(
            frame,
            detail[:70],
            (x + 52, y + 56),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.49,
            (214, 224, 234),
            1,
            cv2.LINE_AA,
        )

    return frame


def draw_settings_tab(
    frame: np.ndarray,
    config: RescueConfig,
    shelter_manager: ShelterManager,
    account_manager: GoogleAccountManager,
    current_tab: str,
    i18n: Translator,
) -> np.ndarray:
    height, width = frame.shape[:2]
    cv2.rectangle(frame, (0, 0), (width, height), (13, 18, 25), -1)
    draw_tabs(frame, current_tab, i18n)

    put_text(
        frame,
        i18n.t("settings_header"),
        (26, 88),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.92,
        (0, 205, 255),
        2,
        cv2.LINE_AA,
    )

    left_x = 26
    panel_y = 118
    panel_h = 205
    narrow = width < 1080
    panel_w = max(300, width - 52) if narrow else max(460, min(width // 2 - 42, 620))
    right_x = left_x if narrow else max(520, width // 2 + 10)
    right_y = panel_y + panel_h + 18 if narrow else panel_y

    cv2.rectangle(frame, (left_x, panel_y), (left_x + panel_w, panel_y + panel_h), (24, 32, 42), -1)
    cv2.rectangle(frame, (left_x, panel_y), (left_x + panel_w, panel_y + panel_h), (0, 140, 220), 2)
    put_text(
        frame,
        i18n.t("google_account"),
        (left_x + 18, panel_y + 36),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (245, 250, 255),
        2,
        cv2.LINE_AA,
    )
    draw_text_lines(
        frame,
        [
            f"{i18n.t('registered')}: {account_manager.profile_label()}",
            account_manager.status_message,
            i18n.t("maps_account_hint"),
            i18n.t("login_register"),
            f"M - {i18n.t('mobile_map')}",
        ],
        left_x + 18,
        panel_y + 72,
        color=(222, 234, 244),
        scale=0.52,
        line_height=28,
    )

    cv2.rectangle(frame, (right_x, right_y), (right_x + panel_w, right_y + panel_h), (24, 32, 42), -1)
    cv2.rectangle(frame, (right_x, right_y), (right_x + panel_w, right_y + panel_h), (0, 140, 220), 2)
    put_text(
        frame,
        i18n.t("manual_shelter_header"),
        (right_x + 18, right_y + 36),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (245, 250, 255),
        2,
        cv2.LINE_AA,
    )
    draw_text_lines(
        frame,
        [
            i18n.t("manual_shelter_hint"),
            "NEW_SHELTER_NAME / NEW_SHELTER_ADDRESS",
            "NEW_SHELTER_LAT / NEW_SHELTER_LON",
            "NEW_SHELTER_NOTE / NEW_SHELTER_PHONE",
            i18n.t("shelter_add_ready"),
        ],
        right_x + 18,
        right_y + 72,
        color=(222, 234, 244),
        scale=0.52,
        line_height=28,
    )

    rows = [
        f"{i18n.t('language')}: {i18n.language_name()} | T/U/E",
        f"{i18n.t('emergency_contact')}: {config.emergency_number}",
        f"Google Maps: {shelter_manager.google_status}",
        f"{i18n.t('location_status')}: USER_LAT={config.user_lat or i18n.t('not_set')} | "
        f"USER_LON={config.user_lon or i18n.t('not_set')}",
        i18n.t("settings_keys"),
    ]
    draw_text_lines(
        frame,
        rows,
        34,
        min(height - 150, right_y + panel_h + 48),
        color=(235, 242, 248),
        scale=0.62,
        line_height=34,
    )
    return frame


class TkRescueUI:
    """Desktop UI rendered with Tkinter instead of OpenCV windows."""

    def __init__(
        self,
        config: RescueConfig,
        i18n: Translator,
        camera: cv2.VideoCapture,
        audio: AudioAnalyzer,
        video: VideoAnalyzer,
        gestures: GestureAnalyzer,
        fusion: RiskFusion,
        alarm: AlarmController,
        recorder: EvidenceRecorder,
        shelter_manager: ShelterManager,
        supplies_manager: SuppliesManager,
        account_manager: GoogleAccountManager,
    ) -> None:
        if tk is None or Image is None or ImageTk is None:
            raise RuntimeError(i18n.t("desktop_ui_missing"))

        self.config = config
        self.i18n = i18n
        self.camera = camera
        self.audio = audio
        self.video = video
        self.gestures = gestures
        self.fusion = fusion
        self.alarm = alarm
        self.recorder = recorder
        self.shelter_manager = shelter_manager
        self.supplies_manager = supplies_manager
        self.account_manager = account_manager
        self.theme = UIDesignTheme.from_file(config.design_theme_file)
        if self.theme.load_error:
            print(f"Design theme load failed: {self.theme.load_error}")
        self.current_tab = "monitor"
        self.saved_current_alarm = False
        self.opened_map_for_current_alarm = False
        self.running = True
        self.message = ""
        self._photo = None
        self.latest_frame: Optional[np.ndarray] = None
        self.popup_windows: dict[str, Any] = {}
        self._popup_content_labels: dict[str, Any] = {}
        self._supplies_editor_updating = False
        self._visible_form: Optional[str] = None
        self._video_visible = True
        self._stats_visible = True

        self.root = tk.Tk()
        self.root.title(self.i18n.t("app_title"))
        self.root.configure(bg=self.theme.color("app_bg"))
        self.root.geometry("1180x860")
        self.root.minsize(980, 720)
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.bind("<Key>", self._on_key)
        self._build_layout()
        self.shelter_manager.maybe_refresh_passively()

    def run(self) -> None:
        self._tick()
        self.root.mainloop()

    def close(self) -> None:
        self.running = False
        try:
            self.root.quit()
            self.root.destroy()
        except Exception:
            pass

    def _build_layout(self) -> None:
        # Tkinter renders Ukrainian text reliably / Tkinter надійно показує український текст
        color = self.theme.color
        font = self.theme.font

        self.header_frame = tk.Frame(
            self.root,
            bg=color("panel_bg"),
            highlightbackground=color("border"),
            highlightthickness=2,
            padx=18,
            pady=12,
        )
        self.header_frame.pack(fill="x")
        self.header_frame.grid_columnconfigure(1, weight=1)

        self.header_mark = tk.Label(
            self.header_frame,
            text="STEP",
            bg=color("danger"),
            fg=color("button_text"),
            font=font("button", bold=True),
            padx=12,
            pady=8,
            highlightbackground=color("border"),
            highlightthickness=2,
        )
        self.header_mark.grid(row=0, column=0, rowspan=2, sticky="w", padx=(0, 12))
        self.header_title_label = tk.Label(
            self.header_frame,
            text=self.i18n.t("desktop_system_title"),
            bg=color("panel_bg"),
            fg=color("text_strong"),
            font=font("heading", bold=True),
            anchor="w",
        )
        self.header_title_label.grid(row=0, column=1, sticky="ew")
        self.header_subtitle_label = tk.Label(
            self.header_frame,
            text=self.i18n.t("desktop_platform_subtitle"),
            bg=color("panel_bg"),
            fg=color("text_muted"),
            font=font("label", bold=True),
            anchor="w",
        )
        self.header_subtitle_label.grid(row=1, column=1, sticky="ew")

        self.header_status_frame = tk.Frame(self.header_frame, bg=color("panel_bg"))
        self.header_status_frame.grid(row=0, column=2, rowspan=2, sticky="e")
        self.header_mode_label = tk.Label(
            self.header_status_frame,
            bg=color("button_bg"),
            fg=color("warning"),
            font=font("label", bold=True),
            padx=12,
            pady=7,
            highlightbackground=color("warning"),
            highlightthickness=2,
        )
        self.header_mode_label.pack(side="left", padx=4)
        self.header_contact_label = tk.Label(
            self.header_status_frame,
            bg=color("button_bg"),
            fg=color("danger_hover"),
            font=font("label", bold=True),
            padx=12,
            pady=7,
            highlightbackground=color("danger"),
            highlightthickness=2,
        )
        self.header_contact_label.pack(side="left", padx=4)
        self.header_language_button = tk.Button(
            self.header_status_frame,
            command=lambda: self._handle_action("toggle_language"),
            relief="flat",
            bd=0,
            bg=color("button_bg"),
            fg=color("button_text"),
            activebackground=color("button_hover"),
            activeforeground=color("button_text"),
            font=font("label", bold=True),
            padx=12,
            pady=7,
        )
        self.header_language_button.pack(side="left", padx=4)

        self.main_container = tk.Frame(self.root, bg=color("app_bg"))
        self.main_container.pack(fill="both", expand=True, padx=16, pady=14)

        self.nav_frame = tk.Frame(
            self.main_container,
            bg=color("panel_bg"),
            highlightbackground=color("border"),
            highlightthickness=2,
            padx=4,
            pady=4,
        )
        self.nav_frame.pack(fill="x", pady=(0, 12))

        # Quick access framed buttons that open separate windows
        self.quick_frames = tk.Frame(self.main_container, bg=color("app_bg"))
        self.quick_frames.pack(fill="x", pady=(0, 12))
        self.quick_access_frames: dict[str, Any] = {}
        self.quick_access_buttons: dict[str, Any] = {}
        quick_access_items = (
            ("shelter", "shelter_tab"),
            ("supplies", "supplies_tab"),
            ("settings", "settings_tab"),
        )
        for window_id, button_key in quick_access_items:
            button = tk.Button(
                self.quick_frames,
                text=self.i18n.t(button_key),
                command=lambda selected=window_id: self._toggle_popup(selected),
                bg=color("button_bg"),
                fg=color("button_text"),
                activebackground=color("button_hover"),
                activeforeground=color("button_text"),
                relief="flat",
                bd=0,
                font=font("button", bold=True),
                padx=14,
                pady=8,
                highlightbackground=color("border"),
                highlightthickness=2,
            )
            button.pack(side="left", padx=(0, 8))
            self.quick_access_buttons[window_id] = button

        self.tab_buttons: dict[str, Any] = {}
        for tab_id in ("monitor", "shelter", "supplies", "settings"):
            button = tk.Button(
                self.nav_frame,
                command=lambda selected=tab_id: self._set_tab(selected),
                bg=color("button_bg"),
                fg=color("button_text"),
                activebackground=color("button_hover"),
                activeforeground=color("button_text"),
                highlightbackground=color("border"),
                highlightthickness=2,
                relief="flat",
                bd=0,
                padx=14,
                pady=11,
                font=font("button", bold=True),
            )
            button.pack(side="left", fill="x", expand=True, padx=2)
            self.tab_buttons[tab_id] = button

        self.main_panel = tk.Frame(
            self.main_container,
            bg=color("panel_bg"),
            highlightbackground=color("border"),
            highlightthickness=2,
            padx=14,
            pady=14,
        )
        self.main_panel.pack(fill="both", expand=True)

        self.stats_frame = tk.Frame(self.main_panel, bg=color("panel_bg"))
        self.stats_frame.pack(fill="x", pady=(0, 10))
        self.stat_title_labels: dict[str, Any] = {}
        self.stat_value_labels: dict[str, Any] = {}
        self.stat_detail_labels: dict[str, Any] = {}
        stat_items = (
            ("risk", "risk"),
            ("alarm", "alarm"),
            ("camera", "camera"),
            ("systems", "detection_systems"),
        )
        for index, (stat_id, label_key) in enumerate(stat_items):
            card = tk.Frame(
                self.stats_frame,
                bg=color("app_bg"),
                highlightbackground=color("border"),
                highlightthickness=2,
                padx=14,
                pady=10,
            )
            card.grid(row=0, column=index, sticky="nsew", padx=(0, 10 if index < len(stat_items) - 1 else 0))
            self.stats_frame.grid_columnconfigure(index, weight=1, uniform="stats")
            title = tk.Label(
                card,
                text=self.i18n.t(label_key).upper(),
                bg=color("app_bg"),
                fg=color("text_muted"),
                font=font("label", bold=True),
                anchor="w",
            )
            title.pack(fill="x")
            value = tk.Label(
                card,
                bg=color("app_bg"),
                fg=color("text_strong"),
                font=(str(self.theme.data.get("font_family", "Segoe UI")), 20, "bold"),
                anchor="w",
            )
            value.pack(fill="x", pady=(6, 0))
            detail = tk.Label(
                card,
                bg=color("app_bg"),
                fg=color("text_muted"),
                font=font("label", bold=True),
                anchor="w",
            )
            detail.pack(fill="x", pady=(2, 0))
            self.stat_title_labels[stat_id] = title
            self.stat_value_labels[stat_id] = value
            self.stat_detail_labels[stat_id] = detail

        self.video_label = tk.Label(
            self.main_panel,
            bg=color("video_bg"),
            highlightbackground=color("border"),
            highlightthickness=2,
        )
        self.video_label.pack(fill="both", expand=True, pady=(0, 10))

        self.status_label = tk.Label(
            self.main_panel,
            bg=color("app_bg"),
            fg=color("text_strong"),
            justify="left",
            anchor="w",
            padx=12,
            pady=8,
            font=font("body"),
            highlightbackground=color("border"),
            highlightthickness=2,
        )
        self.status_label.pack(fill="x", pady=(0, 10))

        self.action_frame_top = tk.Frame(self.main_panel, bg=color("panel_bg"))
        self.action_frame_top.pack(fill="x", pady=(0, 4))
        self.action_frame_bottom = tk.Frame(self.main_panel, bg=color("panel_bg"))
        self.action_frame_bottom.pack(fill="x", pady=(0, 10))

        self.action_buttons: dict[str, Any] = {}
        top_actions = ("cancel", "confirm", "auto_shelters", "google_search", "map")
        bottom_actions = ("login", "toggle_language", "add_shelter", "quit")
        for index, action in enumerate(top_actions):
            button = tk.Button(
                self.action_frame_top,
                command=lambda selected=action: self._handle_action(selected),
                relief="flat",
                bd=0,
                bg=color("button_bg"),
                fg=color("button_text"),
                activebackground=color("button_hover"),
                activeforeground=color("button_text"),
                highlightbackground=color("border"),
                highlightthickness=2,
                width=20,
                height=2,
                font=font("button", bold=True),
            )
            button.grid(row=0, column=index, sticky="ew", padx=5, pady=4)
            self.action_frame_top.grid_columnconfigure(index, weight=1)
            self.action_buttons[action] = button

        for index, action in enumerate(bottom_actions):
            button = tk.Button(
                self.action_frame_bottom,
                command=lambda selected=action: self._handle_action(selected),
                relief="flat",
                bd=0,
                bg=color("button_bg"),
                fg=color("button_text"),
                activebackground=color("button_hover"),
                activeforeground=color("button_text"),
                highlightbackground=color("border"),
                highlightthickness=2,
                width=20,
                height=2,
                font=font("button", bold=True),
            )
            button.grid(row=0, column=index, sticky="ew", padx=5, pady=4)
            self.action_frame_bottom.grid_columnconfigure(index, weight=1)
            self.action_buttons[action] = button

        self.shelter_form_frame = tk.Frame(
            self.main_panel,
            bg=color("panel_bg"),
            highlightbackground=color("border"),
            highlightthickness=2,
            padx=10,
            pady=10,
        )
        self.shelter_form_frame.pack(fill="x", pady=(0, 10))
        self._visible_form = "shelter"
        self.shelter_form_title = tk.Label(
            self.shelter_form_frame,
            text=self.i18n.t("manual_shelter_header").upper(),
            bg=color("panel_bg"),
            fg=color("text_strong"),
            font=font("heading", bold=True),
            anchor="w",
        )
        self.shelter_form_title.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))

        self._last_search_query_default = self.shelter_manager.default_query()
        self.search_query_var = tk.StringVar(value=self._last_search_query_default)
        self.shelter_name_var = tk.StringVar()
        self.shelter_address_var = tk.StringVar()
        self.shelter_lat_var = tk.StringVar(value=self.config.user_lat or "")
        self.shelter_lon_var = tk.StringVar(value=self.config.user_lon or "")
        self.shelter_note_var = tk.StringVar()
        self.shelter_phone_var = tk.StringVar()

        form_labels = [
            ("search_query_label", self.search_query_var),
            ("shelter_name_label", self.shelter_name_var),
            ("address_label", self.shelter_address_var),
            ("latitude_label", self.shelter_lat_var),
            ("longitude_label", self.shelter_lon_var),
            ("phone_label", self.shelter_phone_var),
            ("note_label", self.shelter_note_var),
        ]
        self.shelter_form_labels: dict[str, Any] = {}
        for row, (label_key, variable) in enumerate(form_labels, start=1):
            label = tk.Label(
                self.shelter_form_frame,
                text=self.i18n.t(label_key),
                bg=color("panel_bg"),
                fg=color("text_label"),
                font=font("label", bold=True),
            )
            label.grid(row=row, column=0, sticky="w", padx=(0, 6), pady=4)
            self.shelter_form_labels[label_key] = label
            entry = tk.Entry(
                self.shelter_form_frame,
                textvariable=variable,
                font=font("body"),
                bg=color("input_bg"),
                fg=color("text_strong"),
                insertbackground=color("caret"),
                relief="flat",
                width=46,
            )
            entry.grid(row=row, column=1, sticky="ew", pady=4)
            self.shelter_form_frame.grid_columnconfigure(1, weight=1)

        self.shelter_buttons_frame = tk.Frame(self.shelter_form_frame, bg=color("panel_bg"))
        self.shelter_buttons_frame.grid(row=len(form_labels) + 1, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        self.shelter_buttons_frame.grid_columnconfigure(0, weight=1)
        self.shelter_buttons_frame.grid_columnconfigure(1, weight=1)

        self.search_query_button = tk.Button(
            self.shelter_buttons_frame,
            text=self.i18n.t("button_search"),
            command=lambda: self._handle_action("google_search"),
            relief="flat",
            bd=0,
            bg=color("primary"),
            fg=color("button_text"),
            activebackground=color("button_selected_hover"),
            activeforeground=color("button_text"),
            font=font("button", bold=True),
            height=2,
        )
        self.search_query_button.grid(row=0, column=0, sticky="ew", padx=5)

        self.add_shelter_button = tk.Button(
            self.shelter_buttons_frame,
            text=self.i18n.t("button_add_shelter"),
            command=lambda: self._handle_action("add_shelter"),
            relief="flat",
            bd=0,
            bg=color("primary"),
            fg=color("button_text"),
            activebackground=color("button_selected_hover"),
            activeforeground=color("button_text"),
            font=font("button", bold=True),
            height=2,
        )
        self.add_shelter_button.grid(row=0, column=1, sticky="ew", padx=5)

        self.supplies_editor_frame = tk.Frame(
            self.main_panel,
            bg=color("panel_bg"),
            highlightbackground=color("border"),
            highlightthickness=2,
            padx=10,
            pady=10,
        )
        self.supplies_editor_title = tk.Label(
            self.supplies_editor_frame,
            text=self.i18n.t("supplies_custom_header").upper(),
            bg=color("panel_bg"),
            fg=color("text_strong"),
            font=font("heading", bold=True),
            anchor="w",
        )
        self.supplies_editor_title.pack(fill="x", pady=(0, 6))
        self.supplies_editor_hint = tk.Label(
            self.supplies_editor_frame,
            text=self.i18n.t("supplies_editor_hint"),
            bg=color("panel_bg"),
            fg=color("text_muted"),
            font=font("body"),
            anchor="w",
        )
        self.supplies_editor_hint.pack(fill="x", pady=(0, 6))
        self.supplies_editor_text = tk.Text(
            self.supplies_editor_frame,
            height=6,
            wrap="word",
            font=font("body"),
            bg=color("input_bg"),
            fg=color("text_strong"),
            insertbackground=color("caret"),
            relief="flat",
            padx=8,
            pady=7,
        )
        self.supplies_editor_text.pack(fill="x")
        self.supplies_editor_text.bind("<KeyRelease>", self._on_supplies_editor_change)
        self.supplies_editor_text.bind("<FocusOut>", self._on_supplies_editor_change)
        self.supplies_buttons_frame = tk.Frame(self.supplies_editor_frame, bg=color("panel_bg"))
        self.supplies_buttons_frame.pack(fill="x", pady=(8, 0))
        self.supplies_buttons_frame.grid_columnconfigure(0, weight=1)
        self.supplies_buttons_frame.grid_columnconfigure(1, weight=1)
        self.supplies_save_button = tk.Button(
            self.supplies_buttons_frame,
            text=self.i18n.t("button_save_supplies"),
            command=self._save_supplies,
            relief="flat",
            bd=0,
            bg=color("primary"),
            fg=color("button_text"),
            activebackground=color("button_selected_hover"),
            activeforeground=color("button_text"),
            font=font("button", bold=True),
            height=2,
        )
        self.supplies_save_button.grid(row=0, column=0, sticky="ew", padx=5)
        self.supplies_reset_button = tk.Button(
            self.supplies_buttons_frame,
            text=self.i18n.t("button_reset_supplies"),
            command=self._reset_supplies,
            relief="flat",
            bd=0,
            bg=color("button_bg"),
            fg=color("button_text"),
            activebackground=color("button_hover"),
            activeforeground=color("button_text"),
            font=font("button", bold=True),
            height=2,
        )
        self.supplies_reset_button.grid(row=0, column=1, sticky="ew", padx=5)

        self.content_label = tk.Label(
            self.main_panel,
            bg=color("app_bg"),
            fg=color("text"),
            justify="left",
            anchor="nw",
            padx=12,
            pady=10,
            font=font("body"),
            wraplength=1050,
            highlightbackground=color("border"),
            highlightthickness=2,
        )
        self.content_label.pack(fill="x")
        self._refresh_supplies_editor_text()
        self._refresh_static_text()
        self._update_stat_cards(0.0)

    def _tick(self) -> None:
        if not self.running:
            return

        success, frame = self.camera.read()
        if not success:
            self.message = self.i18n.t("camera_read_failed")
            self.status_label.config(text=self.message)
            self.root.after(500, self._tick)
            return

        frame = cv2.flip(frame, 1)
        self.latest_frame = frame.copy()
        metrics: dict[str, Any] = {
            "motion": 0.0,
            "flash": 0.0,
            "brightness": 0.0,
            "body_motion": 0.0,
            "body_direction": self.i18n.t("direction_unknown"),
            "body_collision": 0.0,
            "body_hit": False,
            "body_detected": False,
        }
        self.shelter_manager.maybe_refresh_passively()

        video_event, metrics = self.video.analyze(frame)
        if video_event is not None:
            self.fusion.add_video(video_event)

        gesture_event = self.gestures.analyze(frame)
        if gesture_event is not None:
            self.fusion.add_gesture(gesture_event)

        while True:
            try:
                audio_event = self.audio.events.get_nowait()
            except queue.Empty:
                break
            self.fusion.add_audio(audio_event)

        risk = self.fusion.update_idle()
        if self.fusion.is_emergency and not self.alarm.active:
            self.alarm.start(self.fusion.last_reason)
            self.saved_current_alarm = False
            self.opened_map_for_current_alarm = False
            self.current_tab = "shelter"

        if self.alarm.active and self.config.save_evidence and not self.saved_current_alarm:
            saved_path = self.recorder.save(frame, risk, self.fusion.last_reason)
            self.message = self.i18n.t("evidence_saved", path=saved_path)
            print(self.message)
            self.saved_current_alarm = True

        if (
            self.alarm.active
            and self.config.open_shelter_map_on_alarm
            and not self.opened_map_for_current_alarm
        ):
            self.message = self.shelter_manager.open_map()
            print(self.message)
            self.opened_map_for_current_alarm = True

        if not self.alarm.active:
            self.saved_current_alarm = False
            self.opened_map_for_current_alarm = False

        self.alarm.tick()
        self._render_frame(frame)
        self._render_status(risk, self.fusion.last_reason, metrics)
        self.root.after(15, self._tick)

    def _render_frame(self, frame: np.ndarray) -> None:
        image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        image.thumbnail((1040, 585), self._resample_filter())
        self._photo = ImageTk.PhotoImage(image)
        self.video_label.config(image=self._photo)

    def get_snapshot_image(self) -> Optional[bytes]:
        if self.latest_frame is None:
            return None
        success, encoded = cv2.imencode(".jpg", self.latest_frame)
        if not success:
            return None
        return encoded.tobytes()

    def _render_status(self, risk: float, reason: str, metrics: dict[str, Any]) -> None:
        self._refresh_static_text()
        alarm_state = self.i18n.t("active") if self.alarm.active else self.i18n.t("ready")
        hit_state = self.i18n.t("hit_yes") if metrics.get("body_hit") else self.i18n.t("hit_no")
        lines = [
            f"{self.i18n.t('risk')}: {risk:05.1f}/100 | {self.i18n.t('alarm')}: {alarm_state} | "
            f"{self.i18n.t('mode')}: {self.i18n.t('real') if self.config.real_action_enabled else self.i18n.t('demo')}",
            f"{self.i18n.t('reason')}: {reason}",
            f"{self.i18n.t('motion')}: {float(metrics.get('motion', 0.0)):.2f} | "
            f"{self.i18n.t('body_direction')}: {metrics.get('body_direction', self.i18n.t('direction_unknown'))} "
            f"{float(metrics.get('body_motion', 0.0)):.2f} | "
            f"{self.i18n.t('body_collision')}: {float(metrics.get('body_collision', 0.0)):.2f} {hit_state} | "
            f"{self.i18n.t('flash')}: {float(metrics.get('flash', 0.0)):.2f}",
            f"{self.i18n.t('disaster_estimate')}: {metrics.get('disaster_estimate', self.i18n.t('safe_area'))}",
            f"{self.i18n.t('gesture')}: {self.gestures.current_label} | "
            f"{self.i18n.t('number')}: {self.config.emergency_number} | "
            f"{self.i18n.t('language')}: {self.i18n.language_name()}",
        ]
        if self.alarm.active:
            lines.append(self.i18n.t("alarm_action_line", seconds=self.alarm.remaining_seconds))
        if self.message:
            lines.append(self.message)
        self._update_stat_cards(risk)
        self.status_label.config(text="\n".join(lines))
        self.content_label.config(text=self._tab_content())
        # Update any open popup windows' contents
        for win_id in list(self.popup_windows.keys()):
            try:
                self._update_popup_content(win_id)
            except Exception:
                continue

    def _update_stat_cards(self, risk: float) -> None:
        if not hasattr(self, "stat_value_labels"):
            return
        color = self.theme.color
        risk_elevated = risk > 50
        alarm_active = bool(getattr(self.alarm, "active", False))
        remaining_seconds = float(getattr(self.alarm, "remaining_seconds", 0.0))
        stat_updates = {
            "risk": (
                f"{risk:.0f}%",
                self.i18n.t("risk_elevated") if risk_elevated else self.i18n.t("risk_normal"),
                color("danger_hover") if risk_elevated else color("success_hover"),
            ),
            "alarm": (
                self.i18n.t("active") if alarm_active else self.i18n.t("ready").upper(),
                f"{remaining_seconds:04.1f}s" if alarm_active else self.i18n.t("monitoring").upper(),
                color("danger_hover") if alarm_active else color("text_muted"),
            ),
            "camera": (
                self.i18n.t("camera_online"),
                self.i18n.t("live_camera_feed").upper(),
                color("success_hover"),
            ),
            "systems": (
                "CAM / MIC / GEST",
                self.i18n.t("detection_systems").upper(),
                color("primary"),
            ),
        }
        for stat_id, (value, detail, value_color) in stat_updates.items():
            value_label = self.stat_value_labels.get(stat_id)
            detail_label = self.stat_detail_labels.get(stat_id)
            if value_label is not None:
                value_label.config(text=value, fg=value_color)
            if detail_label is not None:
                detail_label.config(text=detail, fg=color("text_muted"))

    def _tab_content(self) -> str:
        if self.current_tab == "shelter":
            rows = [
                self.i18n.t("shelter_feed_header"),
                self.shelter_manager.google_status,
            ]
            for index, (shelter, distance_km) in enumerate(self.shelter_manager.ranked_shelters(limit=5), start=1):
                distance = f"{distance_km:.2f} km" if distance_km is not None else self.i18n.t("distance_unknown")
                rows.append(f"{index}. {shelter.name} | {distance} | {shelter.address or self.i18n.t('address_not_provided')}")
            return "\n".join(rows)

        if self.current_tab == "supplies":
            rows = [self.i18n.t("supplies_header")]
            items = self.supplies_manager.current_items()
            if items:
                rows.extend(
                    f"- {title}: {detail}" if detail else f"- {title}"
                    for title, detail in items
                )
            else:
                rows.append(self.i18n.t("supplies_empty"))
            if self.supplies_manager.status_message:
                rows.append(self.supplies_manager.status_message)
            return "\n".join(rows)

        if self.current_tab == "settings":
            return "\n".join(
                [
                    self.i18n.t("settings_header"),
                    f"{self.i18n.t('google_account')}: {self.account_manager.profile_label()}",
                    self.account_manager.status_message,
                    f"{self.i18n.t('emergency_contact')}: {self.config.emergency_number}",
                    f"{self.i18n.t('location_status')}: USER_LAT={self.shelter_manager.user_lat if self.shelter_manager.user_lat is not None else self.i18n.t('not_set')} | "
                    f"USER_LON={self.shelter_manager.user_lon if self.shelter_manager.user_lon is not None else self.i18n.t('not_set')}",
                    self.i18n.t("manual_shelter_hint"),
                    "NEW_SHELTER_NAME / NEW_SHELTER_ADDRESS / NEW_SHELTER_LAT / NEW_SHELTER_LON",
                ]
            )

        return "\n".join(
            [
                self.i18n.t("app_title"),
                self.i18n.t("desktop_keys_print"),
            ]
        )

    def _refresh_static_text(self) -> None:
        color = self.theme.color
        if hasattr(self, "header_title_label"):
            self.header_title_label.config(text=self.i18n.t("desktop_system_title"))
            self.header_subtitle_label.config(text=self.i18n.t("desktop_platform_subtitle").upper())
            mode_text = self.i18n.t("real") if self.config.real_action_enabled else self.i18n.t("demo_mode_enabled")
            self.header_mode_label.config(text=mode_text.upper())
            self.header_contact_label.config(
                text=f"{self.i18n.t('emergency_contact').upper()}: {self.config.emergency_number}"
            )
            self.header_language_button.config(text=self.i18n.language.upper())
        labels = {
            "monitor": self.i18n.t("monitor_tab"),
            "shelter": self.i18n.t("shelter_feed_tab"),
            "supplies": self.i18n.t("supplies_tab"),
            "settings": self.i18n.t("settings_tab"),
        }
        stat_labels = {
            "risk": self.i18n.t("risk"),
            "alarm": self.i18n.t("alarm"),
            "camera": self.i18n.t("camera"),
            "systems": self.i18n.t("detection_systems"),
        }
        for stat_id, label in stat_labels.items():
            stat_title = getattr(self, "stat_title_labels", {}).get(stat_id)
            if stat_title is not None:
                stat_title.config(text=label.upper())
        for tab_id, button in self.tab_buttons.items():
            selected = tab_id == self.current_tab
            button.config(
                text=labels[tab_id].upper(),
                bg=color("button_selected") if selected else color("button_bg"),
                fg=color("button_text") if selected else color("text_muted"),
                activebackground=color("button_selected_hover") if selected else color("button_hover"),
                activeforeground=color("button_text"),
            )

        quick_access_labels = {
            "shelter": ("shelter_tab", "shelter_tab"),
            "supplies": ("supplies_tab", "supplies_short"),
            "settings": ("settings_tab", "settings_short"),
        }
        for window_id, (frame_key, button_key) in quick_access_labels.items():
            frame = self.quick_access_frames.get(window_id)
            if frame is not None:
                frame.config(text=self.i18n.t(frame_key))
            button = self.quick_access_buttons.get(window_id)
            if button is not None:
                button.config(text=self.i18n.t(button_key).upper())

        action_labels = {
            "cancel": self.i18n.t("button_cancel"),
            "confirm": self.i18n.t("button_confirm"),
            "auto_shelters": self.i18n.t("button_auto_shelters"),
            "google_search": self.i18n.t("button_search"),
            "login": self.i18n.t("button_login"),
            "map": self.i18n.t("button_map"),
            "toggle_language": self.i18n.t("button_language"),
            "add_shelter": self.i18n.t("button_add_shelter"),
            "quit": self.i18n.t("button_quit"),
        }
        for action, button in self.action_buttons.items():
            action_bg = color("button_bg")
            action_hover = color("button_hover")
            if action in {"cancel", "confirm"}:
                action_bg = color("danger")
                action_hover = color("danger_hover")
            elif action in {"auto_shelters", "google_search", "map"}:
                action_bg = color("primary")
                action_hover = color("button_selected_hover")
            elif action == "add_shelter":
                action_bg = color("success")
                action_hover = color("success_hover")
            button.config(
                text=action_labels[action].upper(),
                bg=action_bg,
                fg=color("button_text"),
                activebackground=action_hover,
                activeforeground=color("button_text"),
            )
        self.shelter_form_title.config(text=self.i18n.t("manual_shelter_header").upper())
        for label_key, label in self.shelter_form_labels.items():
            label.config(text=self.i18n.t(label_key))
        self.search_query_button.config(
            text=self.i18n.t("button_search").upper(),
            bg=color("primary"),
            activebackground=color("button_selected_hover"),
        )
        self.add_shelter_button.config(
            text=self.i18n.t("button_add_shelter").upper(),
            bg=color("success"),
            activebackground=color("success_hover"),
        )
        self.supplies_editor_title.config(text=self.i18n.t("supplies_custom_header").upper())
        self.supplies_editor_hint.config(text=self.i18n.t("supplies_editor_hint"))
        self.supplies_save_button.config(
            text=self.i18n.t("button_save_supplies").upper(),
            bg=color("success"),
            activebackground=color("success_hover"),
        )
        self.supplies_reset_button.config(text=self.i18n.t("button_reset_supplies").upper())
        for window_id, window in self.popup_windows.items():
            try:
                window.title(self._popup_title(window_id))
            except Exception:
                continue
        self._refresh_visible_forms()
        self._refresh_camera_preview_visibility()
        self.root.title(self.i18n.t("app_title"))

    def _set_tab(self, tab_id: str) -> None:
        self.current_tab = tab_id
        if tab_id == "supplies":
            self._refresh_supplies_editor_text()
        self._refresh_static_text()

    def _refresh_visible_forms(self) -> None:
        if not hasattr(self, "content_label"):
            return
        target = None
        if self.current_tab == "shelter":
            target = "shelter"
        elif self.current_tab == "supplies":
            target = "supplies"
        if target == self._visible_form:
            return
        self.shelter_form_frame.pack_forget()
        self.supplies_editor_frame.pack_forget()
        if target == "shelter":
            self.shelter_form_frame.pack(fill="x", pady=(0, 10), before=self.content_label)
        elif target == "supplies":
            self.supplies_editor_frame.pack(fill="x", pady=(0, 10), before=self.content_label)
        self._visible_form = target

    def _refresh_camera_preview_visibility(self) -> None:
        if not hasattr(self, "video_label") or not hasattr(self, "status_label"):
            return
        should_show = self.current_tab == "monitor"
        if hasattr(self, "stats_frame") and should_show != self._stats_visible:
            if should_show:
                self.stats_frame.pack(fill="x", pady=(0, 10), before=self.status_label)
            else:
                self.stats_frame.pack_forget()
            self._stats_visible = should_show
        if should_show == self._video_visible:
            return
        if should_show:
            self.video_label.pack(fill="both", expand=True, pady=(0, 10), before=self.status_label)
        else:
            self.video_label.pack_forget()
        self._video_visible = should_show

    def _refresh_supplies_editor_text(self) -> None:
        self._supplies_editor_updating = True
        try:
            self.supplies_editor_text.delete("1.0", "end")
            self.supplies_editor_text.insert("1.0", self.supplies_manager.current_text())
        finally:
            self._supplies_editor_updating = False

    def _on_supplies_editor_change(self, _event: Any = None) -> None:
        if self._supplies_editor_updating:
            return
        self.supplies_manager.update_current_text(self.supplies_editor_text.get("1.0", "end-1c"))
        if self.current_tab == "supplies":
            self.content_label.config(text=self._tab_content())
        self._update_popup_content("supplies")

    def _save_supplies(self) -> None:
        self.supplies_manager.update_current_text(self.supplies_editor_text.get("1.0", "end-1c"))
        self.message = self.supplies_manager.save()
        self.current_tab = "supplies"
        self.content_label.config(text=self._tab_content())
        self._update_popup_content("supplies")
        print(self.message)

    def _reset_supplies(self) -> None:
        self.message = self.supplies_manager.reset_current()
        self._refresh_supplies_editor_text()
        self.current_tab = "supplies"
        self.content_label.config(text=self._tab_content())
        self._update_popup_content("supplies")
        print(self.message)

    def _on_key(self, event: Any) -> None:
        self._handle_action(tk_event_to_action(event))

    def _handle_action(self, action: str) -> None:
        if not action:
            return
        if action == "quit":
            self.close()
            return
        if action == "cancel":
            self.alarm.cancel()
            self.fusion.reset(self.i18n.t("alarm_cancelled"))
            return
        if action == "confirm":
            self.alarm.confirm_now()
            return
        if action.startswith("tab_"):
            self._set_tab(
                {
                    "tab_1": "monitor",
                    "tab_2": "shelter",
                    "tab_3": "supplies",
                    "tab_4": "settings",
                }.get(action, self.current_tab)
            )
            return
        if action == "add_shelter":
            self.message = self._add_shelter_from_form()
            self.current_tab = "shelter"
            print(self.message)
            return
        if action == "google_search":
            self.message = self.shelter_manager.search_shelters(self._google_maps_query_from_field())
            self.current_tab = "shelter"
            print(self.message)
            return
        if action == "auto_shelters":
            self.message = self.shelter_manager.auto_search_shelters_async()
            self.current_tab = "shelter"
            print(self.message)
            return
        if action == "login":
            self.message = self.account_manager.register_async()
            self.current_tab = "settings"
            print(self.message)
            return
        if action == "map":
            self.message = self.shelter_manager.open_map()
            print(self.message)
            return
        if action == "toggle_language":
            self.i18n.toggle()
            self._sync_i18n()
            self.message = self.i18n.t("language_toggled", language=self.i18n.language_name())
            print(self.message)
            return
        if action == "uk_language":
            self.i18n.set_language("uk")
            self._sync_i18n()
            self.message = self.i18n.t("language_toggled", language=self.i18n.language_name())
            print(self.message)
            return
        if action == "en_language":
            self.i18n.set_language("en")
            self._sync_i18n()
            self.message = self.i18n.t("language_toggled", language=self.i18n.language_name())
            print(self.message)
            return

    def _add_shelter_from_form(self) -> str:
        name = self.shelter_name_var.get().strip()
        address = self.shelter_address_var.get().strip()
        lat = parse_optional_float(self.shelter_lat_var.get())
        lon = parse_optional_float(self.shelter_lon_var.get())
        note = self.shelter_note_var.get().strip()
        phone = self.shelter_phone_var.get().strip()
        if not name:
            return self.i18n.t("shelter_add_missing")

        message = self.shelter_manager.add_shelter(
            name=name,
            address=address,
            lat=lat,
            lon=lon,
            note=note,
            phone=phone,
        )
        if "added" in message.lower() or "додано" in message.lower():
            self.shelter_name_var.set("")
            self.shelter_address_var.set("")
            self.shelter_lat_var.set("")
            self.shelter_lon_var.set("")
            self.shelter_note_var.set("")
            self.shelter_phone_var.set("")
        return message

    def _sync_i18n(self) -> None:
        for component in (
            self.audio,
            self.video,
            self.gestures,
            self.fusion,
            self.alarm,
            self.alarm.action,
            self.shelter_manager,
            self.supplies_manager,
            self.account_manager,
        ):
            if hasattr(component, "i18n"):
                component.i18n = self.i18n
        if self.fusion.risk <= 0.0 and not self.alarm.active:
            self.fusion.reset(self.i18n.t("monitoring"))
        if not self.alarm.active:
            self.alarm.status_message = self.i18n.t("monitoring")
        if not getattr(self.account_manager, "_login_running", False):
            self.account_manager.status_message = self.account_manager.status()
        self._refresh_search_query_for_language()
        if self.current_tab == "supplies":
            self._refresh_supplies_editor_text()
        self._refresh_static_text()

    def _google_maps_query_from_field(self) -> str:
        query = self.search_query_var.get().strip()
        return "" if query == self.shelter_manager.default_query() else query

    def _refresh_search_query_for_language(self) -> None:
        new_default = self.shelter_manager.default_query()
        current_query = self.search_query_var.get().strip()
        if not current_query or current_query == self._last_search_query_default:
            self.search_query_var.set(new_default)
        self._last_search_query_default = new_default

    def _toggle_popup(self, window_id: str) -> None:
        existing = self.popup_windows.get(window_id)
        if existing is not None:
            try:
                existing.destroy()
            except Exception:
                pass
            self.popup_windows.pop(window_id, None)
            self._popup_content_labels.pop(window_id, None)
            return
        self._create_popup_window(window_id)

    def _popup_title(self, window_id: str) -> str:
        title_keys = {
            "shelter": "shelter_tab",
            "supplies": "supplies_tab",
            "settings": "settings_tab",
        }
        return self.i18n.t(title_keys.get(window_id, "app_title"))

    def _create_popup_window(self, window_id: str) -> None:
        color = self.theme.color
        font = self.theme.font
        win = tk.Toplevel(self.root)
        win.title(self._popup_title(window_id))
        win.configure(bg=color("panel_bg"))
        win.protocol("WM_DELETE_WINDOW", lambda wid=window_id: self._toggle_popup(wid))
        content = tk.Label(
            win,
            bg=color("panel_bg"),
            fg=color("text"),
            justify="left",
            anchor="nw",
            padx=14,
            pady=14,
            font=font("body"),
            wraplength=900,
        )
        content.pack(fill="both", expand=True)
        self.popup_windows[window_id] = win
        self._popup_content_labels[window_id] = content
        # populate initial content
        self._update_popup_content(window_id)

    def _update_popup_content(self, window_id: str) -> None:
        label = self._popup_content_labels.get(window_id)
        if label is None:
            return
        if window_id == "shelter":
            text = self._tab_content() if self.current_tab == "shelter" else self.i18n.t("shelter_feed_header") + "\n" + self.shelter_manager.google_status
        elif window_id == "supplies":
            text = self.i18n.t("supplies_header") + "\n"
            items = self.supplies_manager.current_items()
            if items:
                text += "\n".join(f"- {title}: {detail}" if detail else f"- {title}" for title, detail in items)
            else:
                text += self.i18n.t("supplies_empty")
        elif window_id == "settings":
            text = self._tab_content() if self.current_tab == "settings" else self.i18n.t("settings_header") + "\n"
            text += f"\n{self.i18n.t('emergency_contact')}: {self.config.emergency_number}"
        else:
            text = self._tab_content()
        try:
            label.config(text=text)
        except Exception:
            pass

    @staticmethod
    def _resample_filter() -> Any:
        resampling = getattr(Image, "Resampling", None)
        if resampling is not None:
            return resampling.LANCZOS
        return getattr(Image, "LANCZOS", 1)


def open_camera(index: int) -> cv2.VideoCapture:
    # Open selected webcam / Відкриваємо вибрану вебкамеру
    camera = cv2.VideoCapture(index)
    if not camera.isOpened():
        raise RuntimeError(f"Could not open camera {index}.")

    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    return camera


def _shelter_to_api(shelter: Shelter, distance_km: Optional[float] = None) -> dict[str, object]:
    return {
        "id": f"{shelter.source}:{shelter.name}:{shelter.address}",
        "name": shelter.name,
        "address": shelter.address,
        "distanceKm": distance_km,
        "distance": f"{distance_km:.2f} km" if distance_km is not None else "",
        "lat": shelter.lat,
        "lon": shelter.lon,
        "note": shelter.note,
        "phone": shelter.phone,
        "googleMapsUri": shelter.google_maps_uri,
        "source": shelter.source,
    }


class RestRescueRuntime:
    """Runs monitoring without Tkinter and exposes state/actions for a web UI."""

    def __init__(
        self,
        config: RescueConfig,
        i18n: Translator,
        camera: Optional[cv2.VideoCapture],
        audio: AudioAnalyzer,
        video: VideoAnalyzer,
        gestures: GestureAnalyzer,
        fusion: RiskFusion,
        alarm: AlarmController,
        recorder: EvidenceRecorder,
        shelter_manager: ShelterManager,
        supplies_manager: SuppliesManager,
        account_manager: GoogleAccountManager,
        camera_error: str = "",
    ) -> None:
        self.config = config
        self.i18n = i18n
        self.camera = camera
        self.audio = audio
        self.video = video
        self.gestures = gestures
        self.fusion = fusion
        self.alarm = alarm
        self.recorder = recorder
        self.shelter_manager = shelter_manager
        self.supplies_manager = supplies_manager
        self.account_manager = account_manager
        self.camera_error = camera_error
        self.running = False
        self.message = camera_error
        self.saved_current_alarm = False
        self.opened_map_for_current_alarm = False
        self.latest_frame: Optional[np.ndarray] = None
        self.latest_jpeg: Optional[bytes] = None
        self.risk = 0.0
        self.metrics: dict[str, Any] = self._default_metrics()
        self.recent_events: list[dict[str, object]] = []
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if self.running:
            return
        self.running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self.running = False
        if self._thread is not None:
            self._thread.join(timeout=1.5)

    def snapshot(self) -> Optional[bytes]:
        with self._lock:
            return self.latest_jpeg

    def state(self) -> dict[str, object]:
        with self._lock:
            risk = self.risk
            metrics = dict(self.metrics)
            message = self.message
            events = list(self.recent_events)
            camera_online = self.camera is not None and not bool(self.camera_error)

        alarm_active = bool(self.alarm.active)
        supplies = [
            {
                "id": str(index + 1),
                "name": title,
                "detail": detail,
                "checked": False,
            }
            for index, (title, detail) in enumerate(self.supplies_manager.current_items())
        ]
        shelters = [
            _shelter_to_api(shelter, distance)
            for shelter, distance in self.shelter_manager.ranked_shelters(limit=8)
        ]
        return {
            "app": self.i18n.t("app_title"),
            "language": self.i18n.language,
            "languageName": self.i18n.language_name(),
            "mode": "real" if self.config.real_action_enabled else "demo",
            "demoMode": not self.config.real_action_enabled,
            "riskScore": round(risk, 1),
            "riskState": self.i18n.t("risk_elevated") if risk > 50 else self.i18n.t("risk_normal"),
            "alarmActive": alarm_active,
            "alarmRemainingSeconds": self.alarm.remaining_seconds,
            "alarmStatus": self.i18n.t("active") if alarm_active else self.i18n.t("ready"),
            "reason": self.fusion.last_reason,
            "message": message,
            "cameraOnline": camera_online,
            "cameraError": self.camera_error,
            "emergencyContact": self.config.emergency_number,
            "metrics": metrics,
            "events": events,
            "shelterStatus": self.shelter_manager.google_status,
            "shelters": shelters,
            "goBagItems": supplies,
            "googleAccount": self.account_manager.profile_label(),
            "location": {
                "lat": self.shelter_manager.user_lat,
                "lon": self.shelter_manager.user_lon,
            },
            "urls": {
                "snapshot": "/api/frame.jpg",
                "stream": "/api/stream",
            },
            "updatedAt": time.time(),
        }

    def perform_action(self, action: str, payload: Optional[dict[str, Any]] = None) -> dict[str, object]:
        payload = payload or {}
        action = (action or "").strip()
        message = ""

        if action == "cancel":
            self.alarm.cancel()
            self.fusion.reset(self.i18n.t("alarm_cancelled"))
            message = self.i18n.t("alarm_cancelled")
        elif action == "confirm":
            self.alarm.confirm_now()
            message = self.alarm.status_message
        elif action == "google_search":
            message = self.shelter_manager.search_shelters(str(payload.get("query", "")).strip() or None)
        elif action == "auto_shelters":
            message = self.shelter_manager.auto_search_shelters_async()
        elif action == "map":
            message = self.shelter_manager.open_map()
        elif action == "login":
            message = self.account_manager.register_async()
        elif action == "toggle_language":
            self.i18n.toggle()
            self._sync_i18n()
            message = self.i18n.t("language_toggled", language=self.i18n.language_name())
        elif action in {"uk_language", "en_language"}:
            self.i18n.set_language("uk" if action == "uk_language" else "en")
            self._sync_i18n()
            message = self.i18n.t("language_toggled", language=self.i18n.language_name())
        elif action == "set_language":
            self.i18n.set_language(str(payload.get("language", self.i18n.language)))
            self._sync_i18n()
            message = self.i18n.t("language_toggled", language=self.i18n.language_name())
        elif action == "set_location":
            lat = parse_optional_float(str(payload.get("lat", "")))
            lon = parse_optional_float(str(payload.get("lon", "")))
            if lat is not None and lon is not None:
                self.shelter_manager.set_user_location(lat, lon)
                message = self.i18n.t("auto_location_found")
            else:
                message = self.i18n.t("auto_location_failed")
        elif action == "add_shelter":
            message = self.shelter_manager.add_shelter(
                name=str(payload.get("name", "")),
                address=str(payload.get("address", "")),
                lat=parse_optional_float(str(payload.get("lat", ""))),
                lon=parse_optional_float(str(payload.get("lon", ""))),
                note=str(payload.get("note", "")),
                phone=str(payload.get("phone", "")),
            )
        elif action == "save_supplies":
            text = str(payload.get("text", ""))
            self.supplies_manager.update_current_text(text)
            message = self.supplies_manager.save()
        elif action == "reset_supplies":
            message = self.supplies_manager.reset_current()
        else:
            message = f"Unknown action: {action}"

        with self._lock:
            self.message = message
        return {"ok": not message.startswith("Unknown action"), "message": message, "state": self.state()}

    def _loop(self) -> None:
        while self.running:
            if self.camera is None:
                self._idle_without_camera()
                time.sleep(0.2)
                continue

            success, frame = self.camera.read()
            if not success:
                with self._lock:
                    self.message = self.i18n.t("camera_read_failed")
                    self.camera_error = self.message
                time.sleep(0.2)
                continue

            frame = cv2.flip(frame, 1)
            metrics = self._default_metrics()
            self.shelter_manager.maybe_refresh_passively()

            video_event, metrics = self.video.analyze(frame)
            if video_event is not None:
                self.fusion.add_video(video_event)
                self._record_event("motion", video_event.event_type, "medium")

            gesture_event = self.gestures.analyze(frame)
            if gesture_event is not None:
                self.fusion.add_gesture(gesture_event)
                self._record_event("gesture", gesture_event.gesture, "high")

            while True:
                try:
                    audio_event = self.audio.events.get_nowait()
                except queue.Empty:
                    break
                self.fusion.add_audio(audio_event)
                self._record_event("sound", audio_event.event_type, "high")

            risk = self.fusion.update_idle()
            if self.fusion.is_emergency and not self.alarm.active:
                self.alarm.start(self.fusion.last_reason)
                self.saved_current_alarm = False
                self.opened_map_for_current_alarm = False

            if self.alarm.active and self.config.save_evidence and not self.saved_current_alarm:
                saved_path = self.recorder.save(frame, risk, self.fusion.last_reason)
                self.message = self.i18n.t("evidence_saved", path=saved_path)
                self.saved_current_alarm = True

            if (
                self.alarm.active
                and self.config.open_shelter_map_on_alarm
                and not self.opened_map_for_current_alarm
            ):
                self.message = self.shelter_manager.open_map()
                self.opened_map_for_current_alarm = True

            if not self.alarm.active:
                self.saved_current_alarm = False
                self.opened_map_for_current_alarm = False

            self.alarm.tick()
            latest_jpeg = self._encode_jpeg(frame)
            with self._lock:
                self.latest_frame = frame.copy()
                self.latest_jpeg = latest_jpeg
                self.risk = risk
                self.metrics = metrics
                self.camera_error = ""
            time.sleep(0.015)

    def _idle_without_camera(self) -> None:
        while True:
            try:
                audio_event = self.audio.events.get_nowait()
            except queue.Empty:
                break
            self.fusion.add_audio(audio_event)
            self._record_event("sound", audio_event.event_type, "high")
        risk = self.fusion.update_idle()
        if self.fusion.is_emergency and not self.alarm.active:
            self.alarm.start(self.fusion.last_reason)
        self.alarm.tick()
        with self._lock:
            self.risk = risk
            self.metrics = self._default_metrics()

    def _record_event(self, event_type: str, description: str, severity: str) -> None:
        event = {
            "id": f"{time.time():.6f}",
            "type": event_type,
            "timestamp": time.time(),
            "description": description,
            "severity": severity,
        }
        with self._lock:
            self.recent_events.insert(0, event)
            self.recent_events = self.recent_events[:25]

    def _sync_i18n(self) -> None:
        for component in (
            self.audio,
            self.video,
            self.gestures,
            self.fusion,
            self.alarm,
            self.alarm.action,
            self.shelter_manager,
            self.supplies_manager,
            self.account_manager,
        ):
            if hasattr(component, "i18n"):
                component.i18n = self.i18n
        if self.fusion.risk <= 0.0 and not self.alarm.active:
            self.fusion.reset(self.i18n.t("monitoring"))
        if not self.alarm.active:
            self.alarm.status_message = self.i18n.t("monitoring")
        if not getattr(self.account_manager, "_login_running", False):
            self.account_manager.status_message = self.account_manager.status()

    @staticmethod
    def _default_metrics() -> dict[str, Any]:
        return {
            "motion": 0.0,
            "flash": 0.0,
            "brightness": 0.0,
            "body_motion": 0.0,
            "body_direction": "",
            "body_collision": 0.0,
            "body_hit": False,
            "body_detected": False,
        }

    @staticmethod
    def _encode_jpeg(frame: np.ndarray) -> Optional[bytes]:
        success, encoded = cv2.imencode(".jpg", frame)
        return encoded.tobytes() if success else None


def _make_camera_http_handler(get_frame: Callable[[], Optional[bytes]]) -> type[BaseHTTPRequestHandler]:
    class CameraHTTPHandler(BaseHTTPRequestHandler):
        server_version = "StepPrepCameraServer/1.0"

        def log_message(self, format: str, *args: object) -> None:
            return

        def _send_image(self, jpeg_bytes: bytes) -> None:
            self.send_response(200)
            self.send_header("Content-Type", "image/jpeg")
            self.send_header("Content-Length", str(len(jpeg_bytes)))
            self.end_headers()
            self.wfile.write(jpeg_bytes)

        def _send_html(self, content: str) -> None:
            body = content.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
            path = urllib.parse.urlparse(self.path).path
            if path in ("/", "/index.html"):
                self._send_html(
                    "<html><head><title>Camera Stream</title></head>"
                    "<body><h1>Camera Stream</h1>"
                    "<p><a href=\"/snapshot\">Snapshot</a> | "
                    "<a href=\"/stream\">Stream</a></p>"
                    "<img src=\"/stream\" style=\"max-width:100%;height:auto;\" />"
                    "</body></html>"
                )
                return

            if path == "/snapshot":
                image = get_frame()
                if image is None:
                    self.send_error(503, "Camera frame not available")
                    return
                self._send_image(image)
                return

            if path == "/stream":
                self.send_response(200)
                self.send_response(200)
                self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
                self.end_headers()
                boundary = b"--frame\r\n"
                try:
                    while True:
                        image = get_frame()
                        if image is None:
                            time.sleep(0.06)
                            continue
                        try:
                            header = (
                                b"Content-Type: image/jpeg\r\n"
                                + b"Content-Length: "
                                + str(len(image)).encode("ascii")
                                + b"\r\n\r\n"
                            )
                            self.wfile.write(boundary)
                            self.wfile.write(header)
                            self.wfile.write(image)
                            self.wfile.write(b"\r\n")
                            self.wfile.flush()
                            time.sleep(0.06)
                        except (BrokenPipeError, ConnectionResetError):
                            break
                except Exception:
                    # Ensure we don't crash the server loop on unexpected errors
                    pass
                return

            self.send_error(404, "Not found")

    return CameraHTTPHandler


def start_camera_server(get_frame: Callable[[], Optional[bytes]], port: int) -> ThreadingHTTPServer:
    handler_class = _make_camera_http_handler(get_frame)
    server = ThreadingHTTPServer(("127.0.0.1", port), handler_class)
    return server


def _make_rest_http_handler(runtime: RestRescueRuntime, frontend_dir: str) -> type[BaseHTTPRequestHandler]:
    frontend_root = Path(frontend_dir).resolve()

    class RestHTTPHandler(BaseHTTPRequestHandler):
        server_version = "StepPrepApiServer/1.0"

        def log_message(self, format: str, *args: object) -> None:
            return

        def _cors(self) -> None:
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")

        def _send_json(self, payload: object, status: int = 200) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self._cors()
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_bytes(self, data: bytes, content_type: str, status: int = 200) -> None:
            self.send_response(status)
            self._cors()
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _read_json(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length", "0") or "0")
            if length <= 0:
                return {}
            raw = self.rfile.read(length)
            if not raw:
                return {}
            data = json.loads(raw.decode("utf-8"))
            return data if isinstance(data, dict) else {}

        def do_OPTIONS(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
            self.send_response(204)
            self._cors()
            self.end_headers()

        def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path
            if path in ("/api/health", "/health"):
                self._send_json({"ok": True, "app": "StepPrep", "mode": "api"})
                return
            if path in ("/api/status", "/api/state"):
                self._send_json(runtime.state())
                return
            if path == "/api/shelters":
                self._send_json({"shelters": runtime.state()["shelters"], "status": runtime.shelter_manager.google_status})
                return
            if path == "/api/supplies":
                self._send_json({"items": runtime.state()["goBagItems"], "text": runtime.supplies_manager.current_text()})
                return
            if path == "/api/frame.jpg":
                image = runtime.snapshot()
                if image is None:
                    self._send_json({"ok": False, "message": runtime.i18n.t("camera_read_failed")}, status=503)
                    return
                self._send_bytes(image, "image/jpeg")
                return
            if path == "/api/stream":
                self._send_stream()
                return
            if path.startswith("/api/"):
                self._send_json({"ok": False, "message": "Not found"}, status=404)
                return
            self._serve_static(path)

        def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path
            try:
                payload = self._read_json()
            except Exception as error:
                self._send_json({"ok": False, "message": f"Invalid JSON: {error}"}, status=400)
                return

            if path == "/api/actions":
                self._send_json(runtime.perform_action(str(payload.get("action", "")), payload))
                return
            if path == "/api/language":
                self._send_json(runtime.perform_action("set_language", payload))
                return
            if path == "/api/location":
                self._send_json(runtime.perform_action("set_location", payload))
                return
            if path == "/api/shelters":
                self._send_json(runtime.perform_action("add_shelter", payload))
                return
            if path == "/api/supplies":
                self._send_json(runtime.perform_action("save_supplies", payload))
                return
            self._send_json({"ok": False, "message": "Not found"}, status=404)

        def do_PUT(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
            self.do_POST()

        def _send_stream(self) -> None:
            self.send_response(200)
            self._cors()
            self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
            self.end_headers()
            boundary = b"--frame\r\n"
            try:
                while True:
                    image = runtime.snapshot()
                    if image is None:
                        time.sleep(0.08)
                        continue
                    header = (
                        b"Content-Type: image/jpeg\r\n"
                        + b"Content-Length: "
                        + str(len(image)).encode("ascii")
                        + b"\r\n\r\n"
                    )
                    self.wfile.write(boundary)
                    self.wfile.write(header)
                    self.wfile.write(image)
                    self.wfile.write(b"\r\n")
                    self.wfile.flush()
                    time.sleep(0.08)
            except (BrokenPipeError, ConnectionResetError):
                return
            except Exception:
                return

        def _serve_static(self, request_path: str) -> None:
            if not frontend_root.exists():
                self._send_api_docs()
                return

            relative = urllib.parse.unquote(request_path.lstrip("/"))
            target = frontend_root / (relative or "index.html")
            if target.is_dir():
                target = target / "index.html"
            target = target.resolve()
            if frontend_root != target and frontend_root not in target.parents:
                self._send_json({"ok": False, "message": "Forbidden"}, status=403)
                return
            if not target.exists():
                target = frontend_root / "index.html"
            if not target.exists() or not target.is_file():
                self._send_api_docs()
                return

            content_type = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
            try:
                self._send_bytes(target.read_bytes(), content_type)
            except OSError as error:
                self._send_json({"ok": False, "message": str(error)}, status=500)

        def _send_api_docs(self) -> None:
            body = (
                "<!doctype html><html><head><meta charset=\"utf-8\"><title>StepPrep API</title></head>"
                "<body style=\"font-family:Segoe UI,Arial,sans-serif;background:#0a0e17;color:#fff;\">"
                "<h1>StepPrep REST API</h1>"
                "<p>Build the Figma React app in <code>figma design</code> to serve it here, or call the API directly.</p>"
                "<ul>"
                "<li><a href=\"/api/status\">GET /api/status</a></li>"
                "<li><a href=\"/api/shelters\">GET /api/shelters</a></li>"
                "<li><a href=\"/api/supplies\">GET /api/supplies</a></li>"
                "<li><a href=\"/api/frame.jpg\">GET /api/frame.jpg</a></li>"
                "<li><a href=\"/api/stream\">GET /api/stream</a></li>"
                "</ul>"
                "</body></html>"
            ).encode("utf-8")
            self._send_bytes(body, "text/html; charset=utf-8")

    return RestHTTPHandler


def start_rest_api_server(
    runtime: RestRescueRuntime,
    host: str,
    port: int,
    frontend_dir: str,
) -> ThreadingHTTPServer:
    handler_class = _make_rest_http_handler(runtime, frontend_dir)
    return ThreadingHTTPServer((host, port), handler_class)


def start_demo_mode(camera: cv2.VideoCapture, port: int) -> None:
    stop_event = threading.Event()
    frame_container: dict[str, Optional[bytes]] = {"frame": None}

    def capture_loop() -> None:
        while not stop_event.is_set():
            success, frame = camera.read()
            if not success:
                time.sleep(0.05)
                continue
            frame = cv2.flip(frame, 1)
            success_jpg, encoded = cv2.imencode('.jpg', frame)
            if success_jpg:
                frame_container["frame"] = encoded.tobytes()
            time.sleep(0.03)

    def get_frame() -> Optional[bytes]:
        return frame_container.get("frame")

    cap_thread = threading.Thread(target=capture_loop, daemon=True)
    cap_thread.start()
    server = start_camera_server(get_frame, port)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    print(f"Demo server running at http://127.0.0.1:{port}/")
    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("Stopping demo server...")
    finally:
        stop_event.set()
        server.shutdown()
        server.server_close()


def main() -> None:
    # Build all parts of the monitoring pipeline / Збираємо всі частини системи моніторингу
    config = RescueConfig()
    i18n = get_translator(config.app_language)
    print(i18n.t("app_title"))
    print(
        f"{i18n.t('mode')}: "
        f"{i18n.t('real') if config.real_action_enabled else i18n.t('demo')}"
    )
    print(f"{i18n.t('number')}: {config.emergency_number}")
    print(i18n.t("desktop_keys_print"))

    audio = AudioAnalyzer(config, i18n)
    video = VideoAnalyzer(config, i18n)
    gestures = GestureAnalyzer(config, i18n)
    fusion = RiskFusion(config, i18n)
    action = EmergencyAction(config, i18n)
    alarm = AlarmController(config, action, i18n)
    recorder = EvidenceRecorder(config)
    shelter_manager = ShelterManager(config, i18n)
    supplies_manager = SuppliesManager(config, i18n)
    account_manager = GoogleAccountManager(config, i18n)

    audio.start()

    camera: Optional[cv2.VideoCapture] = None
    camera_error = ""
    try:
        camera = open_camera(config.camera_index)
        print(i18n.t("camera_opened_debug", index=config.camera_index, opened=camera.isOpened()))
    except Exception as error:
        camera_error = i18n.t("camera_open_failed", index=config.camera_index)
        print(f"{camera_error}: {error}")
        if config.mode not in {"api", "rest"}:
            audio.stop()
            gestures.close()
            raise

    if config.mode == "demo":
        if camera is None:
            audio.stop()
            gestures.close()
            raise RuntimeError(camera_error)
        try:
            start_demo_mode(camera, config.server_port)
        finally:
            audio.stop()
            gestures.close()
            camera.release()
        return

    if config.mode in {"api", "rest"}:
        runtime = RestRescueRuntime(
            config,
            i18n,
            camera,
            audio,
            video,
            gestures,
            fusion,
            alarm,
            recorder,
            shelter_manager,
            supplies_manager,
            account_manager,
            camera_error=camera_error,
        )
        server: Optional[ThreadingHTTPServer] = None
        try:
            runtime.start()
            server = start_rest_api_server(runtime, config.api_host, config.api_port, config.api_frontend_dir)
            print(f"StepPrep REST API running at http://{config.api_host}:{config.api_port}/")
            print("API endpoints: /api/status, /api/actions, /api/shelters, /api/supplies, /api/frame.jpg")
            server.serve_forever()
        except KeyboardInterrupt:
            print("Stopping StepPrep REST API...")
        finally:
            if server is not None:
                server.shutdown()
                server.server_close()
            runtime.stop()
            audio.stop()
            gestures.close()
            if camera is not None:
                camera.release()
        return

    print(i18n.t("entering_main_loop"))

    server: Optional[ThreadingHTTPServer] = None
    server_thread: Optional[threading.Thread] = None
    try:
        if camera is None:
            raise RuntimeError(camera_error)
        ui = TkRescueUI(
            config,
            i18n,
            camera,
            audio,
            video,
            gestures,
            fusion,
            alarm,
            recorder,
            shelter_manager,
            supplies_manager,
            account_manager,
        )
        if config.server_enabled:
            try:
                server = start_camera_server(ui.get_snapshot_image, config.server_port)
                server_thread = threading.Thread(target=server.serve_forever, daemon=True)
                server_thread.start()
                print(f"Camera server started at http://127.0.0.1:{config.server_port}/")
            except Exception as error:
                print(f"Could not start camera server: {error}")
        ui.run()
    finally:
        if server is not None:
            server.shutdown()
            server.server_close()
        audio.stop()
        gestures.close()
        if camera is not None:
            camera.release()


if __name__ == "__main__":
    main()
