/**
 * StepPrep Usage Examples
 * Real working examples showing how to import and use StepPrep components
 */

import {
  StepPrepDesktop,
  StepPrep,
  translations,
  type Language,
  type EmergencyContact,
  type DetectionEvent,
  type Theme
} from './src/app/components';

// ============================================================================
// EXAMPLE 1: Basic Desktop Component
// ============================================================================

export function Example1_BasicDesktop() {
  return <StepPrepDesktop />;
}

// ============================================================================
// EXAMPLE 2: Basic Mobile Component with Props
// ============================================================================

export function Example2_BasicMobile() {
  return (
    <StepPrep
      initialTheme="modern"
      initialScreen="home"
      showThemeSwitcher={true}
    />
  );
}

// ============================================================================
// EXAMPLE 3: Custom Contact Manager
// ============================================================================

import { useState } from 'react';
import { toast } from 'sonner';
import { MessageSquare, Phone, Trash2 } from 'lucide-react';

export function Example3_ContactManager() {
  const [contacts, setContacts] = useState<EmergencyContact[]>([
    { id: '1', name: 'Emergency Services', phone: '112' },
    { id: '2', name: 'Family Contact', phone: '+40 123 456 789' },
  ]);

  const [language, setLanguage] = useState<Language>('en');
  const t = translations[language];

  const callContact = (contact: EmergencyContact) => {
    toast.info(`Calling ${contact.phone}...`);
  };

  const messageContact = (contact: EmergencyContact) => {
    const message = language === 'en'
      ? 'EMERGENCY: I need help!'
      : 'ТРИВОГА: Мені потрібна допомога!';
    toast.success(`Message sent to ${contact.name}: ${message}`);
  };

  const deleteContact = (id: string) => {
    setContacts(contacts.filter(c => c.id !== id));
    toast.info('Contact deleted');
  };

  return (
    <div className="p-6 bg-gray-900 text-white min-h-screen">
      <div className="max-w-2xl mx-auto">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-2xl font-bold">{t.emergencyContacts}</h1>
          <button
            onClick={() => setLanguage(language === 'en' ? 'uk' : 'en')}
            className="px-4 py-2 bg-blue-600 rounded"
          >
            {language === 'en' ? 'EN' : 'UK'}
          </button>
        </div>

        <div className="space-y-3">
          {contacts.map((contact) => (
            <div
              key={contact.id}
              className="bg-gray-800 border border-gray-700 rounded-lg p-4"
            >
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-bold">{contact.name}</div>
                  <div className="text-sm text-gray-400">{contact.phone}</div>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => callContact(contact)}
                    className="p-2 bg-green-600 rounded hover:bg-green-500"
                    title={t.callContact}
                  >
                    <Phone className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => messageContact(contact)}
                    className="p-2 bg-blue-600 rounded hover:bg-blue-500"
                    title={t.messageContact}
                  >
                    <MessageSquare className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => deleteContact(contact.id)}
                    className="p-2 bg-red-600 rounded hover:bg-red-500"
                    title={t.deleteContact}
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// EXAMPLE 4: Event Monitor
// ============================================================================

export function Example4_EventMonitor() {
  const [events, setEvents] = useState<DetectionEvent[]>([]);
  const [language, setLanguage] = useState<Language>('en');
  const t = translations[language];

  const addTestEvent = (type: 'motion' | 'sound' | 'gesture', severity: 'low' | 'medium' | 'high') => {
    const descriptions = {
      motion: { en: 'Motion detected', uk: 'Виявлено рух' },
      sound: { en: 'Loud sound detected', uk: 'Виявлено гучний звук' },
      gesture: { en: 'Help gesture detected', uk: 'Виявлено жест допомоги' },
    };

    const event: DetectionEvent = {
      id: Date.now().toString(),
      type,
      timestamp: new Date(),
      description: descriptions[type][language],
      severity,
    };

    setEvents([event, ...events]);
    toast.warning(`New ${severity} severity event detected!`);
  };

  return (
    <div className="p-6 bg-gray-900 text-white min-h-screen">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-2xl font-bold mb-6">{t.recentEvents}</h1>

        {/* Test Event Buttons */}
        <div className="mb-6 flex gap-2">
          <button
            onClick={() => addTestEvent('motion', 'high')}
            className="px-4 py-2 bg-red-600 rounded hover:bg-red-500"
          >
            Add Motion Event
          </button>
          <button
            onClick={() => addTestEvent('sound', 'medium')}
            className="px-4 py-2 bg-yellow-600 rounded hover:bg-yellow-500"
          >
            Add Sound Event
          </button>
          <button
            onClick={() => addTestEvent('gesture', 'low')}
            className="px-4 py-2 bg-blue-600 rounded hover:bg-blue-500"
          >
            Add Gesture Event
          </button>
        </div>

        {/* Events List */}
        <div className="space-y-2">
          {events.length === 0 ? (
            <div className="text-center py-12 text-gray-500">
              {t.noEvents}
            </div>
          ) : (
            events.map((event) => (
              <div
                key={event.id}
                className={`p-4 rounded border-l-4 ${
                  event.severity === 'high'
                    ? 'bg-red-950/30 border-red-600'
                    : event.severity === 'medium'
                    ? 'bg-yellow-950/30 border-yellow-600'
                    : 'bg-blue-950/30 border-blue-600'
                }`}
              >
                <div className="flex justify-between items-start">
                  <div>
                    <div className="font-bold uppercase tracking-wider text-sm">
                      {event.description}
                    </div>
                    <div className="text-xs text-gray-400 mt-1">
                      {event.timestamp.toLocaleString()}
                    </div>
                  </div>
                  <div className={`px-2 py-1 rounded text-xs font-bold ${
                    event.severity === 'high'
                      ? 'bg-red-600'
                      : event.severity === 'medium'
                      ? 'bg-yellow-600'
                      : 'bg-blue-600'
                  }`}>
                    {event.type.toUpperCase()}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// EXAMPLE 5: Mobile App with Theme Switcher
// ============================================================================

export function Example5_ThemeSwitcher() {
  const [theme, setTheme] = useState<Theme>('modern');

  const handleThemeChange = (newTheme: Theme) => {
    setTheme(newTheme);
    toast.success(`Theme changed to ${newTheme}`);
  };

  return (
    <StepPrep
      initialTheme={theme}
      initialScreen="home"
      showThemeSwitcher={true}
      onThemeChange={handleThemeChange}
    />
  );
}

// ============================================================================
// EXAMPLE 6: Combined Desktop and Mobile View
// ============================================================================

export function Example6_CombinedView() {
  const [view, setView] = useState<'desktop' | 'mobile'>('desktop');

  return (
    <div className="min-h-screen bg-gray-900">
      <div className="p-4 bg-gray-800 border-b border-gray-700">
        <div className="max-w-7xl mx-auto flex gap-2">
          <button
            onClick={() => setView('desktop')}
            className={`px-4 py-2 rounded ${
              view === 'desktop' ? 'bg-blue-600' : 'bg-gray-700'
            }`}
          >
            Desktop View
          </button>
          <button
            onClick={() => setView('mobile')}
            className={`px-4 py-2 rounded ${
              view === 'mobile' ? 'bg-blue-600' : 'bg-gray-700'
            }`}
          >
            Mobile View
          </button>
        </div>
      </div>

      {view === 'desktop' ? (
        <StepPrepDesktop />
      ) : (
        <div className="flex justify-center items-center min-h-screen p-4">
          <div className="w-full max-w-md">
            <StepPrep showThemeSwitcher={true} />
          </div>
        </div>
      )}
    </div>
  );
}

// ============================================================================
// EXAMPLE 7: Simple Import Test
// ============================================================================

// Just to verify all imports work correctly
export function Example7_ImportTest() {
  const t = translations['en'];

  console.log('Translations loaded:', t.monitoring);

  return (
    <div className="p-6">
      <h1>All imports working correctly!</h1>
      <p>Check console for translation test.</p>
    </div>
  );
}
