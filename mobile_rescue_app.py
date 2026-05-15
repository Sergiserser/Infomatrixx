"""
KivyMD mobile extension for Emergency Rescue Assistant.

Run on desktop for UI testing:
    python mobile_rescue_app.py

Build Android APK/AAB from Linux or WSL:
    buildozer android debug

Environment/settings supported:
    APP_LANG=uk
    APP_LANG=en
    EMERGENCY_NUMBER=0977477926
    GOOGLE_MAPS_API_KEY=...
    GOOGLE_MAPS_SHELTER_QUERY="optional custom query"
    GOOGLE_MAPS_RADIUS_M=1000
    USER_LAT=50.4501
    USER_LON=30.5234
"""

from __future__ import annotations

import json
import math
import os
import threading
import time
import urllib.parse
import urllib.request
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from kivy.clock import Clock, mainthread
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.uix.scrollview import ScrollView
from kivy.utils import platform
from kivymd.app import MDApp
from kivymd.uix.button import MDFlatButton, MDRaisedButton
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel

from localization import get_translator


APP_DIR = Path(__file__).resolve().parent
SHELTERS_FILE = APP_DIR / "shelters.json"
GOOGLE_PROFILE_FILE = APP_DIR / "google_user_profile.json"


@dataclass(frozen=True)
class MobileConfig:
    app_language: str = os.getenv("APP_LANG", os.getenv("RESCUE_LANG", "uk"))
    emergency_number: str = os.getenv("EMERGENCY_NUMBER", "0977477926")
    google_maps_api_key: str = os.getenv("GOOGLE_MAPS_API_KEY", "")
    google_maps_query: str = os.getenv("GOOGLE_MAPS_SHELTER_QUERY", "")
    google_maps_radius_m: float = float(os.getenv("GOOGLE_MAPS_RADIUS_M", "1000"))
    google_maps_language: str = os.getenv("GOOGLE_MAPS_LANGUAGE", "")
    user_lat: str = os.getenv("USER_LAT", "")
    user_lon: str = os.getenv("USER_LON", "")


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
        ("Їжа", "батончики, консерви, горіхи, дитяче харчування"),
        ("Аптечка", "особисті ліки, бинт, антисептик"),
        ("Світло", "ліхтарик, батарейки, павербанк"),
        ("Тепло", "теплий одяг, плед/термоковдра"),
        ("Зв'язок", "телефон, зарядка, паперові контакти"),
        ("Готівка", "невеликі купюри та банківська картка"),
        ("Гігієна", "серветки, антисептик, індивідуальні засоби"),
    ],
    "en": [
        ("Documents", "passport/ID, copies, important contacts"),
        ("Water", "at least 1-2 l per person"),
        ("Food", "bars, canned food, nuts"),
        ("First aid", "personal medicine, bandage, antiseptic"),
        ("Light", "flashlight, batteries, power bank"),
        ("Warmth", "warm clothes, blanket/thermal blanket"),
        ("Connection", "phone, charger, paper contacts"),
        ("Cash", "small bills and a bank card"),
        ("Hygiene", "wipes, sanitizer, personal care items"),
    ],
}


def parse_optional_float(value: str) -> Optional[float]:
    try:
        value = value.strip()
        return float(value) if value else None
    except ValueError:
        return None


class ShelterManager:
    def __init__(self, config: MobileConfig, i18n) -> None:
        self.config = config
        self.i18n = i18n
        self.user_lat = parse_optional_float(config.user_lat)
        self.user_lon = parse_optional_float(config.user_lon)
        self.local_shelters = self._load_local_shelters()
        self.google_shelters: list[Shelter] = []
        self.status = self.i18n.t("google_not_searched")
        self.last_url = ""

    @property
    def all_shelters(self) -> list[Shelter]:
        return self.google_shelters + self.local_shelters

    def set_user_location(self, lat: float, lon: float) -> None:
        self.user_lat = lat
        self.user_lon = lon

    def google_maps_query(self) -> str:
        return (self.config.google_maps_query or self.i18n.t("google_maps_shelter_query")).strip()

    def google_maps_language(self) -> str:
        return (self.config.google_maps_language or self.i18n.language).strip()

    def search_radius_m(self) -> float:
        return max(100.0, min(float(self.config.google_maps_radius_m), 1500.0))

    def max_search_distance_km(self) -> float:
        return self.search_radius_m() / 1000.0

    def query_near_user(self) -> str:
        query = self.google_maps_query()
        if self.user_lat is not None and self.user_lon is not None:
            return f"{query} {self.i18n.t('google_maps_near')} {self.user_lat},{self.user_lon}"
        return query

    def _load_local_shelters(self) -> list[Shelter]:
        if not SHELTERS_FILE.exists():
            return []

        try:
            data = json.loads(SHELTERS_FILE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
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

    def ranked_shelters(self, limit: int = 12) -> list[tuple[Shelter, Optional[float]]]:
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
        return ranked[:limit]

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
        if not name or (not address and (lat is None or lon is None)):
            return self.i18n.t("shelter_add_missing")

        try:
            if SHELTERS_FILE.exists():
                data = json.loads(SHELTERS_FILE.read_text(encoding="utf-8"))
                if not isinstance(data, dict):
                    data = {}
            else:
                data = {}
            shelters_data = data.setdefault("shelters", [])
            if not isinstance(shelters_data, list):
                shelters_data = []
                data["shelters"] = shelters_data
            shelters_data.append(
                {
                    "name": name,
                    "address": address,
                    "lat": lat,
                    "lon": lon,
                    "note": note.strip(),
                    "phone": phone.strip(),
                    "source": "manual",
                }
            )
            SHELTERS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            self.local_shelters = self._load_local_shelters()
            self.status = self.i18n.t("shelter_added", name=name)
            return self.status
        except Exception as error:
            self.status = self.i18n.t("shelter_add_failed", error=error)
            return self.status

    def add_shelter_from_env(self) -> str:
        # Mobile test UI also uses env vars for quick manual input / Мобільний тестовий UI також бере дані з env
        return self.add_shelter(
            name=os.getenv("NEW_SHELTER_NAME", ""),
            address=os.getenv("NEW_SHELTER_ADDRESS", ""),
            lat=parse_optional_float(os.getenv("NEW_SHELTER_LAT", "")),
            lon=parse_optional_float(os.getenv("NEW_SHELTER_LON", "")),
            note=os.getenv("NEW_SHELTER_NOTE", ""),
            phone=os.getenv("NEW_SHELTER_PHONE", ""),
        )

    def search_google_places(self) -> str:
        if not self.config.google_maps_api_key:
            self.status = self.i18n.t("google_set_api")
            return self.status

        if self.user_lat is None or self.user_lon is None:
            self.status = self.i18n.t("google_waiting_location")
            return self.status

        url = "https://places.googleapis.com/v1/places:searchText"
        payload = {
            "textQuery": self.google_maps_query(),
            "languageCode": self.google_maps_language(),
            "maxResultCount": 12,
            "locationRestriction": {
                "circle": {
                    "center": {"latitude": self.user_lat, "longitude": self.user_lon},
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
            with urllib.request.urlopen(request, timeout=12) as response:
                data = json.loads(response.read().decode("utf-8"))
        except Exception as error:
            self.status = self.i18n.t("google_search_failed", error=error)
            return self.status

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
                    note=self.i18n.t("google_candidate_note"),
                    phone=str(place.get("nationalPhoneNumber", "")),
                    google_maps_uri=str(place.get("googleMapsUri", "")),
                    source="google_maps",
                )
            )

        self.google_shelters = found
        self.status = self.i18n.t("google_found", count=len(found))
        return self.status

    def map_url_for(self, shelter: Optional[Shelter] = None) -> str:
        if shelter is None:
            ranked = self.ranked_shelters(limit=1)
            shelter = ranked[0][0] if ranked else None

        if shelter is not None and shelter.lat is not None and shelter.lon is not None:
            destination = f"{shelter.lat},{shelter.lon}"
            if self.user_lat is not None and self.user_lon is not None:
                origin = f"{self.user_lat},{self.user_lon}"
                return (
                    "https://www.google.com/maps/dir/?api=1&travelmode=walking"
                    f"&origin={urllib.parse.quote(origin)}&destination={urllib.parse.quote(destination)}"
                )
            return "https://www.google.com/maps/search/?api=1&query=" + urllib.parse.quote(destination)

        if shelter is not None and shelter.google_maps_uri:
            return shelter.google_maps_uri

        return "https://www.google.com/maps/search/?api=1&query=" + urllib.parse.quote(self.query_near_user())

    def open_map(self, shelter: Optional[Shelter] = None) -> None:
        url = self.map_url_for(shelter)
        self.last_url = url
        open_external_url(url)

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


def open_external_url(url: str) -> None:
    if platform == "android":
        try:
            from jnius import autoclass

            intent = autoclass("android.content.Intent")
            uri = autoclass("android.net.Uri")
            activity = autoclass("org.kivy.android.PythonActivity").mActivity
            activity.startActivity(intent(intent.ACTION_VIEW, uri.parse(url)))
            return
        except Exception:
            pass

    webbrowser.open(url, new=2, autoraise=True)


def dial_number(number: str) -> None:
    # ACTION_DIAL opens dialer; the user confirms the call / ACTION_DIAL відкриває дзвонилку, користувач підтверджує дзвінок
    tel_url = "tel:" + urllib.parse.quote(number)
    if platform == "android":
        try:
            from jnius import autoclass

            intent = autoclass("android.content.Intent")
            uri = autoclass("android.net.Uri")
            activity = autoclass("org.kivy.android.PythonActivity").mActivity
            activity.startActivity(intent(intent.ACTION_DIAL, uri.parse(tel_url)))
            return
        except Exception:
            pass

    open_external_url(tel_url)


def request_android_permissions() -> None:
    if platform != "android":
        return

    try:
        from android.permissions import Permission, request_permissions

        def permission(name: str) -> str:
            return getattr(Permission, name, f"android.permission.{name}")

        request_permissions(
            [
                permission("INTERNET"),
                permission("ACCESS_FINE_LOCATION"),
                permission("ACCESS_COARSE_LOCATION"),
                permission("CAMERA"),
                permission("RECORD_AUDIO"),
                permission("VIBRATE"),
            ]
        )
    except Exception:
        return


def load_google_account_label(i18n) -> str:
    if not GOOGLE_PROFILE_FILE.exists():
        return i18n.t("not_registered")

    try:
        data = json.loads(GOOGLE_PROFILE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return i18n.t("not_registered")

    return str(data.get("email") or data.get("name") or i18n.t("registered"))


def register_google_profile(i18n) -> str:
    # Full OAuth stays in desktop app; mobile stores the same local profile / Повний OAuth лишається в desktop, mobile зберігає той самий профіль
    email = os.getenv("GOOGLE_ACCOUNT_EMAIL", "").strip()
    if email:
        GOOGLE_PROFILE_FILE.write_text(
            json.dumps(
                {
                    "email": email,
                    "name": os.getenv("GOOGLE_ACCOUNT_NAME", ""),
                    "source": "mobile_environment",
                    "registered_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        return i18n.t("google_profile_saved_env", email=email)

    open_external_url("https://accounts.google.com/")
    return i18n.t("google_account_opened")


class ShelterFeedCard(MDCard):
    def __init__(
        self,
        shelter: Shelter,
        distance_km: Optional[float],
        index: int,
        on_open_map,
        i18n,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.shelter = shelter
        self.orientation = "vertical"
        self.padding = dp(14)
        self.spacing = dp(8)
        self.size_hint_y = None
        self.height = dp(214)
        self.radius = [dp(10), dp(10), dp(10), dp(10)]
        self.elevation = 2

        badge = i18n.t("nearest") if index == 0 else f"#{index + 1}"
        distance = f"{distance_km:.2f} km" if distance_km is not None else i18n.t("distance_unknown")

        self.add_widget(
            MDLabel(
                text=f"{badge}  {shelter.name}",
                bold=index == 0,
                font_style="Subtitle1",
                size_hint_y=None,
                height=dp(28),
            )
        )
        self.add_widget(
            MDLabel(
                text=f"{distance} | {shelter.source}",
                theme_text_color="Secondary",
                size_hint_y=None,
                height=dp(24),
            )
        )
        self.add_widget(
            MDLabel(
                text=shelter.address or i18n.t("address_not_provided"),
                theme_text_color="Primary",
                size_hint_y=None,
                height=dp(42),
            )
        )
        self.add_widget(
            MDLabel(
                text=shelter.phone or shelter.note or i18n.t("metro_note"),
                theme_text_color="Secondary",
                size_hint_y=None,
                height=dp(34),
            )
        )
        self.add_widget(
            MDFlatButton(
                text=i18n.t("mobile_open_map"),
                size_hint=(1, None),
                height=dp(42),
                on_release=lambda *_: on_open_map(shelter),
            )
        )


class MonitorScreen(Screen):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        root = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(14))
        self.status_label = MDLabel(
            text="",
            halign="center",
            font_style="H5",
            size_hint_y=None,
            height=dp(48),
        )
        self.account_label = MDLabel(
            text="",
            halign="center",
            theme_text_color="Secondary",
            size_hint_y=None,
            height=dp(32),
        )

        root.add_widget(self.status_label)
        root.add_widget(self.account_label)
        self.sos_button = MDRaisedButton(
            text="",
            md_bg_color=(0.82, 0.1, 0.1, 1),
            size_hint=(1, None),
            height=dp(56),
            on_release=lambda *_: MDApp.get_running_app().trigger_alarm(
                MDApp.get_running_app().i18n.t("mobile_manual_sos")
            ),
        )
        root.add_widget(self.sos_button)
        self.dial_button = MDRaisedButton(
            text="",
            size_hint=(1, None),
            height=dp(50),
            on_release=lambda *_: MDApp.get_running_app().dial_emergency(),
        )
        root.add_widget(self.dial_button)
        self.feed_button = MDFlatButton(
            text="",
            size_hint=(1, None),
            height=dp(48),
            on_release=lambda *_: MDApp.get_running_app().go("shelters"),
        )
        root.add_widget(self.feed_button)
        self.supplies_button = MDFlatButton(
            text="",
            size_hint=(1, None),
            height=dp(48),
            on_release=lambda *_: MDApp.get_running_app().go("supplies"),
        )
        root.add_widget(self.supplies_button)
        self.settings_button = MDFlatButton(
            text="",
            size_hint=(1, None),
            height=dp(48),
            on_release=lambda *_: MDApp.get_running_app().go("settings"),
        )
        root.add_widget(self.settings_button)
        self.hooks_label = MDLabel(text="", theme_text_color="Secondary")
        root.add_widget(self.hooks_label)
        self.add_widget(root)

    def refresh(self) -> None:
        app = MDApp.get_running_app()
        self.status_label.text = app.i18n.t("mobile_alarm_active") if app.alarm_active else app.i18n.t("mobile_ready")
        self.account_label.text = f"{app.i18n.t('google_account')}: {app.account_label}"
        self.sos_button.text = app.i18n.t("mobile_sos")
        self.dial_button.text = app.i18n.t("mobile_dial")
        self.feed_button.text = app.i18n.t("mobile_open_feed")
        self.supplies_button.text = app.i18n.t("supplies_header")
        self.settings_button.text = app.i18n.t("mobile_register_google")
        self.hooks_label.text = app.i18n.t("mobile_hooks_note")


class ShelterFeedScreen(Screen):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        root = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(10))
        self.header = MDLabel(
            text="",
            font_style="H5",
            size_hint_y=None,
            height=dp(42),
        )
        self.status = MDLabel(
            text="",
            theme_text_color="Secondary",
            size_hint_y=None,
            height=dp(32),
        )
        buttons = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
        self.search_button = MDRaisedButton(text="", on_release=lambda *_: MDApp.get_running_app().search_google())
        self.map_button = MDFlatButton(text="", on_release=lambda *_: MDApp.get_running_app().open_nearest_map())
        self.back_button = MDFlatButton(text="", on_release=lambda *_: MDApp.get_running_app().go("monitor"))
        buttons.add_widget(self.search_button)
        buttons.add_widget(self.map_button)
        buttons.add_widget(self.back_button)

        self.scroll = ScrollView()
        self.feed = BoxLayout(orientation="vertical", spacing=dp(10), size_hint_y=None)
        self.feed.bind(minimum_height=self.feed.setter("height"))
        self.scroll.add_widget(self.feed)

        root.add_widget(self.header)
        root.add_widget(self.status)
        root.add_widget(buttons)
        root.add_widget(self.scroll)
        self.add_widget(root)

    def refresh(self) -> None:
        app = MDApp.get_running_app()
        self.header.text = app.i18n.t("mobile_shelter_feed")
        self.status.text = app.shelters.status
        self.search_button.text = app.i18n.t("mobile_search")
        self.map_button.text = app.i18n.t("mobile_map")
        self.back_button.text = app.i18n.t("mobile_back")
        self.feed.clear_widgets()

        ranked = app.shelters.ranked_shelters()
        if not ranked:
            self.feed.add_widget(
                MDLabel(
                    text=app.i18n.t("mobile_empty_feed"),
                    halign="center",
                    theme_text_color="Secondary",
                    size_hint_y=None,
                    height=dp(140),
                )
            )
            return

        for index, (shelter, distance_km) in enumerate(ranked):
            card = ShelterFeedCard(shelter, distance_km, index, app.open_shelter_map, app.i18n)
            self.feed.add_widget(card)


class SuppliesScreen(Screen):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        root = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(10))
        self.header = MDLabel(text="", font_style="H5", size_hint_y=None, height=dp(42))
        self.back_button = MDFlatButton(
            text="",
            size_hint=(1, None),
            height=dp(46),
            on_release=lambda *_: MDApp.get_running_app().go("monitor"),
        )
        self.scroll = ScrollView()
        self.list_box = BoxLayout(orientation="vertical", spacing=dp(10), size_hint_y=None)
        self.list_box.bind(minimum_height=self.list_box.setter("height"))
        self.scroll.add_widget(self.list_box)

        root.add_widget(self.header)
        root.add_widget(self.back_button)
        root.add_widget(self.scroll)
        self.add_widget(root)

    def refresh(self) -> None:
        app = MDApp.get_running_app()
        self.header.text = app.i18n.t("supplies_header")
        self.back_button.text = app.i18n.t("mobile_back")
        self.list_box.clear_widgets()
        for title, detail in EMERGENCY_SUPPLIES.get(app.i18n.language, EMERGENCY_SUPPLIES["uk"]):
            card = MDCard(
                orientation="vertical",
                padding=dp(14),
                spacing=dp(6),
                size_hint_y=None,
                height=dp(86),
                radius=[dp(8), dp(8), dp(8), dp(8)],
                elevation=1,
            )
            card.add_widget(MDLabel(text=title, bold=True, size_hint_y=None, height=dp(26)))
            card.add_widget(
                MDLabel(
                    text=detail,
                    theme_text_color="Secondary",
                    size_hint_y=None,
                    height=dp(32),
                )
            )
            self.list_box.add_widget(card)


class SettingsScreen(Screen):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        root = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(12))
        self.account = MDLabel(text="", font_style="H6", size_hint_y=None, height=dp(38))
        self.number = MDLabel(text="", theme_text_color="Secondary", size_hint_y=None, height=dp(30))
        self.location = MDLabel(text="", theme_text_color="Secondary", size_hint_y=None, height=dp(60))
        self.maps = MDLabel(text="", theme_text_color="Secondary", size_hint_y=None, height=dp(70))

        root.add_widget(self.account)
        root.add_widget(self.number)
        root.add_widget(self.location)
        root.add_widget(self.maps)
        self.gps_button = MDRaisedButton(text="", size_hint=(1, None), height=dp(48), on_release=lambda *_: MDApp.get_running_app().start_gps())
        self.oauth_button = MDFlatButton(text="", size_hint=(1, None), height=dp(48), on_release=lambda *_: MDApp.get_running_app().register_google())
        self.add_shelter_button = MDFlatButton(text="", size_hint=(1, None), height=dp(48), on_release=lambda *_: MDApp.get_running_app().add_shelter_from_env())
        self.language_button = MDFlatButton(text="", size_hint=(1, None), height=dp(48), on_release=lambda *_: MDApp.get_running_app().toggle_language())
        self.back_button = MDFlatButton(text="", size_hint=(1, None), height=dp(48), on_release=lambda *_: MDApp.get_running_app().go("monitor"))
        root.add_widget(self.gps_button)
        root.add_widget(self.oauth_button)
        root.add_widget(self.add_shelter_button)
        root.add_widget(self.language_button)
        root.add_widget(self.back_button)
        self.add_widget(root)

    def refresh(self) -> None:
        app = MDApp.get_running_app()
        lat = app.shelters.user_lat
        lon = app.shelters.user_lon
        location = (
            f"{lat:.6f}, {lon:.6f}"
            if lat is not None and lon is not None
            else app.i18n.t("mobile_waiting_location")
        )
        api_key = app.i18n.t("api_configured") if app.rescue_config.google_maps_api_key else app.i18n.t("api_not_configured")
        self.account.text = f"{app.i18n.t('google_account')}: {app.account_label}"
        self.number.text = app.i18n.t("mobile_emergency_contact", number=app.rescue_config.emergency_number)
        self.location.text = app.i18n.t("mobile_location", location=location)
        self.maps.text = app.i18n.t("mobile_maps", query=app.shelters.google_maps_query(), api_key=api_key)
        self.gps_button.text = app.i18n.t("mobile_start_gps")
        self.oauth_button.text = app.i18n.t("mobile_register_google")
        self.add_shelter_button.text = app.i18n.t("shelter_add_ready")
        self.language_button.text = f"{app.i18n.t('mobile_toggle_language')}: {app.i18n.language_name()}"
        self.back_button.text = app.i18n.t("mobile_back")


class RescueMobileApp(MDApp):
    alarm_active = False

    def build(self):
        self.theme_cls.primary_palette = "Red"
        self.theme_cls.theme_style = "Light"
        self.rescue_config = MobileConfig()
        self.i18n = get_translator(self.rescue_config.app_language)
        self.shelters = ShelterManager(self.rescue_config, self.i18n)
        self.account_label = load_google_account_label(self.i18n)
        request_android_permissions()

        self.root_manager = ScreenManager()
        self.root_manager.add_widget(MonitorScreen(name="monitor"))
        self.root_manager.add_widget(ShelterFeedScreen(name="shelters"))
        self.root_manager.add_widget(SuppliesScreen(name="supplies"))
        self.root_manager.add_widget(SettingsScreen(name="settings"))
        Clock.schedule_once(lambda *_: self.refresh_all(), 0)
        return self.root_manager

    def go(self, screen_name: str) -> None:
        self.root_manager.current = screen_name
        self.refresh_all()

    def refresh_all(self) -> None:
        for screen in self.root_manager.screens:
            if hasattr(screen, "refresh"):
                screen.refresh()

    def trigger_alarm(self, reason: str) -> None:
        self.alarm_active = True
        self.shelters.status = self.i18n.t("mobile_alarm_status", reason=reason)
        self.go("shelters")
        self.search_google()

    def dial_emergency(self) -> None:
        dial_number(self.rescue_config.emergency_number)

    def open_nearest_map(self) -> None:
        self.shelters.open_map()

    def open_shelter_map(self, shelter: Shelter) -> None:
        self.shelters.open_map(shelter)

    def add_shelter_from_env(self) -> None:
        self.shelters.add_shelter_from_env()
        self.go("shelters")

    def register_google(self) -> None:
        self.shelters.status = register_google_profile(self.i18n)
        self.account_label = load_google_account_label(self.i18n)
        self.refresh_all()

    def search_google(self) -> None:
        self.shelters.status = self.i18n.t("google_searching")
        self.refresh_all()

        def worker() -> None:
            self.shelters.search_google_places()
            self._refresh_from_thread()

        threading.Thread(target=worker, daemon=True).start()

    @mainthread
    def _refresh_from_thread(self) -> None:
        self.refresh_all()

    def start_gps(self) -> None:
        if platform != "android":
            self.shelters.status = self.i18n.t("gps_desktop")
            self.refresh_all()
            return

        try:
            from plyer import gps

            gps.configure(on_location=self._on_location, on_status=self._on_gps_status)
            gps.start(minTime=1000, minDistance=1)
            self.shelters.status = self.i18n.t("gps_starting")
        except Exception as error:
            self.shelters.status = f"GPS: {error}"
        self.refresh_all()

    def _on_location(self, **kwargs) -> None:
        lat = kwargs.get("lat")
        lon = kwargs.get("lon")
        if lat is not None and lon is not None:
            self.shelters.set_user_location(float(lat), float(lon))
            self.shelters.status = self.i18n.t("gps_updated")
            self._refresh_from_thread()

    def _on_gps_status(self, stype, status) -> None:
        self.shelters.status = f"GPS: {status}"
        self._refresh_from_thread()

    def toggle_language(self) -> None:
        self.i18n.toggle()
        self.shelters.i18n = self.i18n
        self.account_label = load_google_account_label(self.i18n)
        self.refresh_all()


if __name__ == "__main__":
    RescueMobileApp().run()
