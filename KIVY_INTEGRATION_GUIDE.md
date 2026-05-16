# SafeReady for Kivy (Python) - Integration Guide

Use SafeReady in your Python Kivy applications!

## 🚀 Quick Start

### Installation

```bash
# Install Kivy
pip install kivy

# Optional: Install WebView for full features
pip install kivy-garden
garden install webview
```

### Basic Usage

```python
from kivy_safeready import SafeReadyApp

# Run standalone app
SafeReadyApp().run()
```

That's it! You now have a working SafeReady app in Python!

---

## 📦 Integration Methods

### Method 1: Standalone App

```python
from kivy_safeready import SafeReadyApp

app = SafeReadyApp()
app.run()
```

### Method 2: As a Widget

```python
from kivy.app import App
from kivy_safeready import SafeReadyWidget

class MyApp(App):
    def build(self):
        return SafeReadyWidget()

MyApp().run()
```

### Method 3: Embedded in Your App

```python
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy_safeready import SafeReadyWidget

class MyApp(App):
    def build(self):
        layout = BoxLayout(orientation='vertical')

        # Your other widgets
        layout.add_widget(MyTopBar())

        # Add SafeReady
        self.safeready = SafeReadyWidget()
        layout.add_widget(self.safeready)

        return layout

MyApp().run()
```

---

## 🎨 Customization API

### Change Language

```python
# Switch to Ukrainian
widget.set_language('uk')

# Switch to English
widget.set_language('en')
```

### Change Theme

```python
# Available themes: 'modern', 'bold', 'calm', 'vibrant'
widget.set_theme('bold')      # Red theme
widget.set_theme('calm')      # Teal theme
widget.set_theme('vibrant')   # Purple theme
```

### Set Custom Tasks

```python
tasks = [
    {'id': '1', 'text': 'Check smoke alarm', 'done': False},
    {'id': '2', 'text': 'Test flashlight', 'done': True},
    {'id': '3', 'text': 'Update emergency contacts', 'done': False}
]

widget.set_tasks(tasks)
```

### Get Current Data

```python
# Get all current data
data = widget.get_data()

print(data['tasks'])       # Current tasks
print(data['kitItems'])    # Kit items
print(data['contacts'])    # Emergency contacts
print(data['plans'])       # Evacuation plans
print(data['theme'])       # Current theme
print(data['language'])    # Current language
```

---

## 📝 Complete Examples

### Example 1: Custom Data

```python
from kivy.app import App
from kivy_safeready import SafeReadyWidget

class CustomApp(App):
    def build(self):
        widget = SafeReadyWidget()

        # Set custom tasks
        widget.set_tasks([
            {'id': '1', 'text': 'My custom task', 'done': False},
            {'id': '2', 'text': 'Another task', 'done': True}
        ])

        # Set language
        widget.set_language('uk')  # Ukrainian

        # Set theme
        widget.set_theme('calm')   # Teal theme

        return widget

if __name__ == '__main__':
    CustomApp().run()
```

### Example 2: With Control Panel

```python
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy_safeready import SafeReadyWidget

class ControlledApp(App):
    def build(self):
        root = BoxLayout(orientation='vertical')

        # Control panel
        controls = BoxLayout(size_hint=(1, 0.1))

        # Language buttons
        controls.add_widget(Button(
            text='English',
            on_press=lambda x: self.safeready.set_language('en')
        ))
        controls.add_widget(Button(
            text='Українська',
            on_press=lambda x: self.safeready.set_language('uk')
        ))

        # Theme buttons
        controls.add_widget(Button(
            text='Modern',
            on_press=lambda x: self.safeready.set_theme('modern')
        ))
        controls.add_widget(Button(
            text='Bold',
            on_press=lambda x: self.safeready.set_theme('bold')
        ))

        root.add_widget(controls)

        # SafeReady widget
        self.safeready = SafeReadyWidget()
        root.add_widget(self.safeready)

        return root

if __name__ == '__main__':
    ControlledApp().run()
```

### Example 3: Save/Load Data

```python
from kivy.app import App
from kivy_safeready import SafeReadyWidget
import json

class PersistentApp(App):
    def build(self):
        self.widget = SafeReadyWidget()

        # Load saved data
        try:
            with open('safeready_data.json', 'r') as f:
                data = json.load(f)
                self.widget.set_tasks(data.get('tasks', []))
                self.widget.set_language(data.get('language', 'en'))
                self.widget.set_theme(data.get('theme', 'modern'))
        except FileNotFoundError:
            pass

        return self.widget

    def on_stop(self):
        # Save data on exit
        data = self.widget.get_data()
        with open('safeready_data.json', 'w') as f:
            json.dump(data, f)

if __name__ == '__main__':
    PersistentApp().run()
```

---

## 🔧 API Reference

### SafeReadyWidget

Main widget class for embedding SafeReady.

#### Methods

**`set_language(language: str) -> dict`**
- **Parameters:** `language` - 'en' or 'uk'
- **Returns:** `{'success': True, 'language': 'en'}`
- **Description:** Change UI language

**`set_theme(theme: str) -> dict`**
- **Parameters:** `theme` - 'modern', 'bold', 'calm', or 'vibrant'
- **Returns:** `{'success': True, 'theme': 'modern'}`
- **Description:** Change color theme

**`get_data() -> dict`**
- **Returns:** Dictionary with all current data
- **Description:** Retrieve current app state

```python
{
    'tasks': [...],
    'kitItems': [...],
    'contacts': [...],
    'plans': [...],
    'theme': 'modern',
    'language': 'en'
}
```

**`set_tasks(tasks: list) -> dict`**
- **Parameters:** `tasks` - List of task dictionaries
- **Returns:** `{'success': True}`
- **Description:** Update tasks list

**Task Format:**
```python
{
    'id': '1',
    'text': 'Task description',
    'done': False  # or True
}
```

---

## 🌐 WebView vs Native Mode

SafeReady works in two modes:

### WebView Mode (Recommended)
- ✅ Full features
- ✅ All themes and translations
- ✅ Best UI experience
- ✅ Requires: `kivy-garden webview`

### Native Mode (Fallback)
- ⚠️ Basic functionality
- ⚠️ Limited UI
- ✅ No dependencies
- ✅ Works everywhere

**Install WebView for best experience:**
```bash
pip install kivy-garden
garden install webview
```

---

## 📱 Platform Support

| Platform | Status | Notes |
|----------|--------|-------|
| **Linux** | ✅ Full support | WebView works great |
| **Windows** | ✅ Full support | Requires WebView |
| **macOS** | ✅ Full support | Requires WebView |
| **Android** | ✅ Supported | Use Buildozer |
| **iOS** | ⚠️ Limited | Kivy iOS support |

---

## 🔨 Building for Mobile

### Android (using Buildozer)

**buildozer.spec:**
```ini
[app]
title = SafeReady
package.name = safeready
package.domain = org.safeready

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json

requirements = python3,kivy,kivy-garden.webview

[buildozer]
android.permissions = INTERNET,ACCESS_FINE_LOCATION
android.api = 31
```

**Build:**
```bash
buildozer -v android debug
```

### iOS (using Kivy-iOS)

```bash
toolchain build python3 kivy
toolchain create SafeReady ~/safeready
```

---

## 🎯 Use Cases

### 1. Emergency Management App

```python
from kivy.app import App
from kivy_safeready import SafeReadyWidget

class EmergencyApp(App):
    def build(self):
        widget = SafeReadyWidget()
        widget.set_theme('bold')  # Red urgency theme
        widget.set_language('uk')  # Ukrainian

        # Set location-specific data
        widget.set_tasks([
            {'id': '1', 'text': 'Check radiation detector', 'done': False},
            {'id': '2', 'text': 'Test gas masks', 'done': False}
        ])

        return widget

EmergencyApp().run()
```

### 2. Family Safety Tracker

```python
class FamilySafetyApp(App):
    def build(self):
        widget = SafeReadyWidget()
        widget.set_theme('calm')  # Calm theme for families

        # Family-specific tasks
        widget.set_tasks([
            {'id': '1', 'text': 'Practice evacuation with kids', 'done': False},
            {'id': '2', 'text': 'Update school contact info', 'done': True}
        ])

        return widget
```

### 3. Multi-Language Support

```python
class MultiLingualApp(App):
    def build(self):
        root = BoxLayout(orientation='vertical')

        # Language selector
        lang_selector = BoxLayout(size_hint=(1, 0.1))
        lang_selector.add_widget(Button(
            text='🇬🇧 EN',
            on_press=lambda x: self.switch_language('en')
        ))
        lang_selector.add_widget(Button(
            text='🇺🇦 UK',
            on_press=lambda x: self.switch_language('uk')
        ))

        root.add_widget(lang_selector)

        self.safeready = SafeReadyWidget()
        root.add_widget(self.safeready)

        return root

    def switch_language(self, lang):
        self.safeready.set_language(lang)
```

---

## 🐛 Troubleshooting

### WebView Not Working

```bash
# Reinstall webview
garden uninstall webview
garden install webview

# Or use native mode (fallback)
# The widget will automatically switch to native Kivy UI
```

### Import Errors

```python
# Make sure kivy_safeready.py is in your project directory
import sys
sys.path.append('/path/to/safeready')
from kivy_safeready import SafeReadyWidget
```

### JavaScript Not Executing

```python
# Give WebView time to load
from kivy.clock import Clock

def setup_safeready(dt):
    widget.set_language('uk')
    widget.set_theme('bold')

Clock.schedule_once(setup_safeready, 1)  # Wait 1 second
```

---

## 📚 Additional Resources

- **Kivy Documentation:** https://kivy.org/doc/stable/
- **Garden WebView:** https://github.com/kivy-garden/webview
- **Buildozer:** https://buildozer.readthedocs.io/

---

## 🎉 Complete Working Example

Save as `my_safeready_app.py`:

```python
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy_safeready import SafeReadyWidget

class MySafeReadyApp(App):
    def build(self):
        # Main layout
        root = BoxLayout(orientation='vertical')

        # Title bar
        title = Label(
            text='My Emergency App',
            size_hint=(1, 0.05),
            bold=True
        )
        root.add_widget(title)

        # Control buttons
        controls = BoxLayout(size_hint=(1, 0.08))

        controls.add_widget(Button(
            text='🇬🇧 English',
            on_press=lambda x: self.safeready.set_language('en')
        ))

        controls.add_widget(Button(
            text='🇺🇦 Українська',
            on_press=lambda x: self.safeready.set_language('uk')
        ))

        controls.add_widget(Button(
            text='Bold Theme',
            on_press=lambda x: self.safeready.set_theme('bold')
        ))

        controls.add_widget(Button(
            text='Calm Theme',
            on_press=lambda x: self.safeready.set_theme('calm')
        ))

        root.add_widget(controls)

        # SafeReady widget
        self.safeready = SafeReadyWidget()
        root.add_widget(self.safeready)

        # Set initial state
        self.safeready.set_language('en')
        self.safeready.set_theme('modern')

        return root

if __name__ == '__main__':
    MySafeReadyApp().run()
```

**Run it:**
```bash
python my_safeready_app.py
```

---

## 💡 Tips

1. **Always check WebView installation** for best experience
2. **Use Clock.schedule_once** for JavaScript calls after widget loads
3. **Save user preferences** using `get_data()` and JSON
4. **Test on mobile** early if building mobile apps
5. **Use native mode** as fallback for reliability

---

**Enjoy using SafeReady in your Kivy applications!** 🎉🐍
