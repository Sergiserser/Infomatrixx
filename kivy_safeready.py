"""
SafeReady for Kivy (Python)

This module provides SafeReady integration for Kivy applications.
It uses an embedded WebView to display the React app.

Installation:
    pip install kivy
    pip install kivy-garden
    garden install webview

Usage:
    from kivy_safeready import SafeReadyApp
    SafeReadyApp().run()
"""

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.core.window import Window
import json

# HTML content for SafeReady standalone
SAFEREADY_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SafeReady</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f3f4f6; }
        .container { max-width: 400px; margin: 0 auto; height: 100vh; background: white; }
        .header { padding: 16px; background: #1a1a1a; color: white; }
        .header h1 { font-size: 20px; }
        .header p { font-size: 12px; opacity: 0.8; }
        .content { padding: 16px; overflow-y: auto; height: calc(100vh - 140px); }
        .nav { display: flex; border-top: 1px solid #e5e7eb; }
        .nav button { flex: 1; padding: 12px; border: none; background: white; cursor: pointer; font-size: 11px; }
        .nav button.active { font-weight: 600; color: #1a1a1a; }
        .card { background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px; margin-bottom: 12px; }
        .btn { padding: 12px 24px; border-radius: 8px; border: none; cursor: pointer; font-weight: 500; }
        .btn-danger { background: #ef4444; color: white; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header" id="header">
            <h1 id="appName">SafeReady</h1>
            <p id="appLocation">Emergency Preparedness</p>
        </div>
        <div class="content" id="content"></div>
        <div class="nav">
            <button onclick="showScreen('home')" data-screen="home" class="active">🏠<br>Home</button>
            <button onclick="showScreen('kit')" data-screen="kit">📦<br>Kit</button>
            <button onclick="showScreen('sos')" data-screen="sos">📞<br>SOS</button>
            <button onclick="showScreen('plan')" data-screen="plan">🗺️<br>Plan</button>
            <button onclick="showScreen('settings')" data-screen="settings">⚙️<br>Settings</button>
        </div>
    </div>
    <script>
        window.safeReadyAPI = {
            setLanguage: (lang) => { currentLanguage = lang; applyTranslations(); renderCurrentScreen(); return {success: true}; },
            setTheme: (theme) => { currentTheme = themes[theme] || themes.modern; applyTheme(); return {success: true}; },
            getData: () => ({ tasks, kitItems, contacts, plans, theme: Object.keys(themes).find(k => themes[k] === currentTheme), language: currentLanguage }),
            setTasks: (newTasks) => { tasks = newTasks; renderCurrentScreen(); return {success: true}; }
        };

        let currentLanguage = 'en', currentScreen = 'home';
        let tasks = [
            {id: '1', text: 'Check water supply', done: true},
            {id: '2', text: 'Test emergency radio', done: false},
            {id: '3', text: 'Rotate food stock', done: false}
        ];
        let kitItems = [
            {id: '1', name: 'Bottled water', qty: '12 L', status: 'ok'},
            {id: '2', name: 'First aid kit', qty: 'Complete', status: 'ok'},
            {id: '3', name: 'Prescription meds', qty: 'Not added', status: 'missing'}
        ];
        let contacts = [
            {id: '1', name: 'Emergency Services', role: '911', phone: '911'}
        ];
        let plans = [
            {id: '1', title: 'Primary Exit Route', sub: 'Main street to shelter'}
        ];

        const themes = {
            modern: {primary: '#1a1a1a', bg: '#ffffff'},
            bold: {primary: '#dc2626', bg: '#fef2f2'},
            calm: {primary: '#0891b2', bg: '#f0fdfa'},
            vibrant: {primary: '#8b5cf6', bg: '#faf5ff'}
        };
        let currentTheme = themes.modern;

        const translations = {
            en: {appName: 'SafeReady', homeTitle: 'Tasks', kitTitle: 'Supply Kit', sosTitle: 'Emergency SOS', planTitle: 'Plans', settingsTitle: 'Settings'},
            uk: {appName: 'БезпекаГотова', homeTitle: 'Завдання', kitTitle: 'Набір', sosTitle: 'SOS', planTitle: 'Плани', settingsTitle: 'Налаштування'}
        };

        function applyTranslations() {
            const t = translations[currentLanguage];
            document.getElementById('appName').textContent = t.appName;
        }

        function applyTheme() {
            document.getElementById('header').style.background = currentTheme.primary;
        }

        function showScreen(screen) {
            currentScreen = screen;
            document.querySelectorAll('.nav button').forEach(btn => {
                btn.classList.toggle('active', btn.dataset.screen === screen);
            });
            renderCurrentScreen();
        }

        function renderCurrentScreen() {
            const content = document.getElementById('content');
            const t = translations[currentLanguage];
            switch(currentScreen) {
                case 'home':
                    content.innerHTML = '<h2>' + t.homeTitle + '</h2>' + tasks.map(task =>
                        '<div class="card"><input type="checkbox" ' + (task.done ? 'checked' : '') +
                        ' onchange="toggleTask(\'' + task.id + '\')">' + task.text + '</div>'
                    ).join('');
                    break;
                case 'kit':
                    content.innerHTML = '<h2>' + t.kitTitle + '</h2>' + kitItems.map(item =>
                        '<div class="card"><strong>' + item.name + '</strong><br>' + item.qty + ' - ' + item.status + '</div>'
                    ).join('');
                    break;
                case 'sos':
                    content.innerHTML = '<h2>' + t.sosTitle + '</h2><div style="text-align:center; margin: 32px 0;"><button class="btn btn-danger" onclick="sendSOS()" style="width: 100px; height: 100px; border-radius: 50px; font-size: 20px;">🚨<br>SOS</button></div>' +
                        contacts.map(c => '<div class="card" onclick="callContact(\'' + c.id + '\')">' + c.name + '<br>' + c.phone + '</div>').join('');
                    break;
                case 'plan':
                    content.innerHTML = '<h2>' + t.planTitle + '</h2>' + plans.map(p =>
                        '<div class="card"><strong>' + p.title + '</strong><br>' + p.sub + '</div>'
                    ).join('');
                    break;
                case 'settings':
                    content.innerHTML = '<h2>' + t.settingsTitle + '</h2>' +
                        '<div class="card" onclick="changeLanguage(\'en\')">🇬🇧 English ' + (currentLanguage === 'en' ? '✓' : '') + '</div>' +
                        '<div class="card" onclick="changeLanguage(\'uk\')">🇺🇦 Українська ' + (currentLanguage === 'uk' ? '✓' : '') + '</div>';
                    break;
            }
        }

        function toggleTask(id) {
            const task = tasks.find(t => t.id === id);
            if (task) { task.done = !task.done; renderCurrentScreen(); }
        }

        function sendSOS() {
            alert('🚨 SOS Alert Sent!');
        }

        function callContact(id) {
            const contact = contacts.find(c => c.id === id);
            if (contact) alert('Calling ' + contact.name);
        }

        function changeLanguage(lang) {
            currentLanguage = lang;
            applyTranslations();
            renderCurrentScreen();
        }

        applyTranslations();
        renderCurrentScreen();
    </script>
</body>
</html>"""


class SafeReadyWidget(BoxLayout):
    """SafeReady widget that can be embedded in Kivy apps"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'

        # Try to use WebView if available
        try:
            from kivy.garden.webview import WebView
            self.webview = WebView()
            self.webview.load_html(SAFEREADY_HTML)
            self.add_widget(self.webview)
        except ImportError:
            # Fallback: Show native Kivy UI
            self._create_native_ui()

    def _create_native_ui(self):
        """Create native Kivy UI as fallback"""
        # Header
        header = BoxLayout(size_hint=(1, 0.15), orientation='vertical')
        header.add_widget(Label(text='SafeReady', font_size='24sp', bold=True))
        header.add_widget(Label(text='Emergency Preparedness', font_size='12sp'))
        self.add_widget(header)

        # Content area
        self.content = BoxLayout(orientation='vertical', size_hint=(1, 0.7))
        self.content.add_widget(Label(text='SafeReady - Native Kivy Mode'))
        self.content.add_widget(Label(text='Install kivy-garden webview for full features'))
        self.add_widget(self.content)

        # Navigation
        nav = BoxLayout(size_hint=(1, 0.15))
        for screen in ['Home', 'Kit', 'SOS', 'Plan', 'Settings']:
            btn = Button(text=screen, on_press=lambda x, s=screen: self._show_screen(s))
            nav.add_widget(btn)
        self.add_widget(nav)

    def _show_screen(self, screen):
        """Show a screen in native mode"""
        self.content.clear_widgets()
        self.content.add_widget(Label(text=f'{screen} Screen'))

    def set_language(self, language):
        """Set language: 'en' or 'uk'"""
        if hasattr(self, 'webview'):
            self.webview.evaluate_javascript(f"window.safeReadyAPI.setLanguage('{language}')")
        return {'success': True, 'language': language}

    def set_theme(self, theme):
        """Set theme: 'modern', 'bold', 'calm', or 'vibrant'"""
        if hasattr(self, 'webview'):
            self.webview.evaluate_javascript(f"window.safeReadyAPI.setTheme('{theme}')")
        return {'success': True, 'theme': theme}

    def get_data(self):
        """Get current data from SafeReady"""
        if hasattr(self, 'webview'):
            result = self.webview.evaluate_javascript("JSON.stringify(window.safeReadyAPI.getData())")
            return json.loads(result)
        return {}

    def set_tasks(self, tasks):
        """Set tasks data

        Args:
            tasks: List of dicts with 'id', 'text', 'done' keys
        """
        if hasattr(self, 'webview'):
            tasks_json = json.dumps(tasks)
            self.webview.evaluate_javascript(f"window.safeReadyAPI.setTasks({tasks_json})")
        return {'success': True}


class SafeReadyApp(App):
    """Standalone SafeReady Kivy application"""

    def build(self):
        Window.size = (400, 700)
        self.title = 'SafeReady - Emergency Preparedness'
        return SafeReadyWidget()


# Example usage functions
def example_basic():
    """Example 1: Basic usage"""
    app = SafeReadyApp()
    app.run()


def example_custom_data():
    """Example 2: Custom data"""
    from kivy.app import App

    class CustomSafeReadyApp(App):
        def build(self):
            widget = SafeReadyWidget()

            # Set custom tasks
            widget.set_tasks([
                {'id': '1', 'text': 'My custom task', 'done': False},
                {'id': '2', 'text': 'Another task', 'done': True}
            ])

            # Set Ukrainian language
            widget.set_language('uk')

            # Set bold theme
            widget.set_theme('bold')

            return widget

    CustomSafeReadyApp().run()


def example_integrated():
    """Example 3: Integrated in larger app"""
    from kivy.app import App
    from kivy.uix.boxlayout import BoxLayout
    from kivy.uix.button import Button

    class MyApp(App):
        def build(self):
            root = BoxLayout(orientation='vertical')

            # Add some controls
            controls = BoxLayout(size_hint=(1, 0.1))
            controls.add_widget(Button(
                text='English',
                on_press=lambda x: self.safeready.set_language('en')
            ))
            controls.add_widget(Button(
                text='Українська',
                on_press=lambda x: self.safeready.set_language('uk')
            ))

            root.add_widget(controls)

            # Add SafeReady
            self.safeready = SafeReadyWidget()
            root.add_widget(self.safeready)

            return root

    MyApp().run()


if __name__ == '__main__':
    # Run the basic app
    example_basic()

    # To run other examples, uncomment:
    # example_custom_data()
    # example_integrated()
