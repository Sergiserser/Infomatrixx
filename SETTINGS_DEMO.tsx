/**
 * Settings Screen Demo
 *
 * This example shows how to use the Settings screen
 * to change themes and languages
 */

import { SafeReady } from './SafeReady-Complete';
import { Toaster } from 'sonner';

// Example 1: Basic usage - Settings screen is included automatically
export function BasicSettingsDemo() {
  return (
    <>
      <SafeReady
        // Settings screen is already included!
        // Users can access it via the bottom navigation
      />
      <Toaster position="top-center" richColors />
    </>
  );
}

// Example 2: Start with Settings screen open
export function StartWithSettingsDemo() {
  return (
    <>
      <SafeReady
        initialScreen="settings"  // Open settings by default
      />
      <Toaster position="top-center" richColors />
    </>
  );
}

// Example 3: Track theme and language changes
export function TrackedSettingsDemo() {
  return (
    <>
      <SafeReady
        onThemeChange={(theme) => {
          console.log('Theme changed to:', theme);
          localStorage.setItem('preferred-theme', theme);
        }}
        onLanguageChange={(language) => {
          console.log('Language changed to:', language);
          localStorage.setItem('preferred-language', language);
        }}
      />
      <Toaster position="top-center" richColors />
    </>
  );
}

// Example 4: Load saved preferences
export function SavedPreferencesDemo() {
  const savedTheme = (localStorage.getItem('preferred-theme') as any) || 'modern';
  const savedLanguage = (localStorage.getItem('preferred-language') as any) || 'en';

  return (
    <>
      <SafeReady
        initialTheme={savedTheme}
        initialLanguage={savedLanguage}
        onThemeChange={(theme) => localStorage.setItem('preferred-theme', theme)}
        onLanguageChange={(language) => localStorage.setItem('preferred-language', language)}
      />
      <Toaster position="top-center" richColors />
    </>
  );
}

// Example 5: Hide theme switcher, use Settings screen instead
export function SettingsOnlyDemo() {
  return (
    <>
      <SafeReady
        showThemeSwitcher={false}  // Hide top-left theme buttons
        // Users can still change theme via Settings screen!
      />
      <Toaster position="top-center" richColors />
    </>
  );
}

// Example 6: Start with Ukrainian language
export function UkrainianDemo() {
  return (
    <>
      <SafeReady
        initialLanguage="uk"
        initialTheme="calm"
      />
      <Toaster position="top-center" richColors />
    </>
  );
}

export default BasicSettingsDemo;
