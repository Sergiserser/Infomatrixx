# SafeReady Localization Guide

SafeReady now supports multiple languages! Currently available: **English** and **Ukrainian (Українська)**.

## Features

✅ **Settings Screen** - Choose language and theme
✅ **Complete Ukrainian Translation** - All UI text translated
✅ **Automatic Language Switching** - Changes apply instantly
✅ **Language State Management** - Track language changes

## Quick Start

### Basic Usage with Language

```tsx
import { SafeReady } from './SafeReady-Complete';
import { Toaster } from 'sonner';

<SafeReady
  initialLanguage="uk"  // Start with Ukrainian
/>
<Toaster position="top-center" richColors />
```

### Track Language Changes

```tsx
<SafeReady
  initialLanguage="en"
  onLanguageChange={(language) => {
    console.log('Language changed to:', language);
    localStorage.setItem('language', language);
  }}
/>
```

### Load Saved Language

```tsx
function App() {
  const savedLanguage = localStorage.getItem('language') as 'en' | 'uk' || 'en';
  
  return (
    <SafeReady
      initialLanguage={savedLanguage}
      onLanguageChange={(lang) => localStorage.setItem('language', lang)}
    />
  );
}
```

## Using the Settings Screen

Users can change language in the app:

1. Tap **"Settings"** in the bottom navigation
2. Select **"Language"** section
3. Choose **English 🇬🇧** or **Українська 🇺🇦**
4. Changes apply immediately!

## Available Languages

| Language | Code | Flag | Status |
|----------|------|------|--------|
| English | `en` | 🇬🇧 | ✅ Complete |
| Ukrainian | `uk` | 🇺🇦 | ✅ Complete |

## Ukrainian Translation Coverage

All text is translated including:

- ✅ Navigation labels
- ✅ Screen titles
- ✅ Button labels
- ✅ Alert messages
- ✅ Status badges
- ✅ Toast notifications
- ✅ Settings screen
- ✅ All hints and descriptions

## Using Built-in Translations

```tsx
import { translations } from './SafeReady-Complete';

// Access translations
const englishTexts = translations.en;
const ukrainianTexts = translations.uk;

console.log(ukrainianTexts.appName); // "БезпекаГотова"
console.log(ukrainianTexts.navHome); // "Головна"
```

## Custom Texts Override Translations

If you provide `customTexts`, they override the language translations:

```tsx
<SafeReady
  initialLanguage="uk"  // Ukrainian selected
  customTexts={{
    appName: 'My Custom App',  // This overrides Ukrainian "БезпекаГотова"
  }}
/>
```

## Example: Language Switcher

```tsx
import { useState } from 'react';
import { SafeReady, type Language } from './SafeReady-Complete';

function App() {
  const [language, setLanguage] = useState<Language>('en');

  return (
    <>
      <div style={{ position: 'fixed', top: 10, right: 10, zIndex: 100 }}>
        <select 
          value={language} 
          onChange={(e) => setLanguage(e.target.value as Language)}
        >
          <option value="en">English</option>
          <option value="uk">Українська</option>
        </select>
      </div>

      <SafeReady
        initialLanguage={language}
        onLanguageChange={setLanguage}
      />
    </>
  );
}
```

## Settings Screen Features

The Settings screen allows users to customize:

### 1. Appearance (Theme)
- Modern Minimal
- Bold Urgent
- Calm Professional
- Vibrant Friendly

### 2. Language
- English 🇬🇧
- Українська 🇺🇦

Both sections show:
- Visual preview (color for themes, flag for languages)
- Current selection with checkmark
- Instant application of changes

## Translation Examples

### English vs Ukrainian

| English | Ukrainian |
|---------|-----------|
| Home | Головна |
| Kit | Набір |
| Emergency contacts | Екстрені контакти |
| Task completed! | Завдання виконано! |
| Add | Додати |
| Settings | Налаштування |
| Your readiness | Ваша готовність |

### Full Example Comparison

**English:**
```
SafeReady
Bucharest · Last updated: today
Severe storm warning
Active until 11 PM · Tap to see details
```

**Ukrainian:**
```
БезпекаГотова
Бухарест · Оновлено: сьогодні
Попередження про сильний шторм
Активне до 23:00 · Натисніть для деталей
```

## TypeScript Support

```tsx
import { type Language } from './SafeReady-Complete';

const language: Language = 'uk'; // Type-safe!

// Event handler type
const handleChange = (lang: Language) => {
  console.log('New language:', lang);
};
```

## Props Reference

### SafeReadyProps

```tsx
interface SafeReadyProps {
  initialLanguage?: Language;           // 'en' | 'uk', default: 'en'
  onLanguageChange?: (language: Language) => void;
  // ... other props
}
```

### Language Type

```tsx
type Language = 'en' | 'uk';
```

## Adding More Languages

To add a new language (e.g., French):

1. Create translation object:
```tsx
const frenchTexts: TextCustomization = {
  appName: 'SécuritéPrêt',
  navHome: 'Accueil',
  // ... all other translations
};
```

2. Add to translations export:
```tsx
export const translations = {
  en: defaultTexts,
  uk: ukrainianTexts,
  fr: frenchTexts,  // Add new language
};
```

3. Update Language type:
```tsx
export type Language = 'en' | 'uk' | 'fr';
```

4. Add to Settings screen language options

## Best Practices

1. **Save user preference** - Store language choice in localStorage
2. **Detect system language** - Use `navigator.language` for initial language
3. **Test both languages** - Ensure UI works in all supported languages
4. **Consider text length** - Ukrainian text may be longer than English
5. **Use proper Unicode** - Ensure Ukrainian characters display correctly

## Complete Example with Persistence

```tsx
import { useEffect, useState } from 'react';
import { SafeReady, type Language } from './SafeReady-Complete';
import { Toaster } from 'sonner';

function App() {
  // Load saved language or detect system language
  const [language, setLanguage] = useState<Language>(() => {
    const saved = localStorage.getItem('language') as Language;
    if (saved) return saved;
    
    // Detect Ukrainian
    if (navigator.language.startsWith('uk')) return 'uk';
    
    return 'en';
  });

  // Save language when changed
  useEffect(() => {
    localStorage.setItem('language', language);
  }, [language]);

  return (
    <>
      <SafeReady
        initialLanguage={language}
        onLanguageChange={setLanguage}
      />
      <Toaster position="top-center" richColors />
    </>
  );
}
```

## Troubleshooting

**Q: Language doesn't change when I select it**
- Make sure you're using `SafeReady-Complete.tsx` (not the older modular version)
- Check that you don't have `customTexts` overriding all text

**Q: Some text is still in English when Ukrainian is selected**
- This may be data content (tasks, contacts, etc.) - only UI text is translated
- Update your data content separately if needed

**Q: Can I use custom text AND translations?**
- Yes! Custom texts override translations for specific keys only

## See Also

- **PROPS_REFERENCE.md** - All available props
- **TEXT_CUSTOMIZATION_EXAMPLE.md** - Text customization guide
- **SAFEREADY_README.md** - Complete feature overview
