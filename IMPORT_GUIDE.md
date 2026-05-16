# StepPrep Components Import Guide

This guide shows how to import and use StepPrep components in your code.

## Basic Imports

### Import Desktop Component

```typescript
// Simple import
import { StepPrepDesktop } from './components';

// Or direct import
import { StepPrepDesktop } from './components/StepPrepDesktop';
```

### Import Mobile Component

```typescript
import { StepPrep } from './components';

// With props type
import { StepPrep, StepPrepProps } from './components';
```

### Import Presentation Component

```typescript
import { SafeReadyPresentation } from './components';
```

## Import Types

### Desktop Types

```typescript
import type {
  Language,
  TabType,
  Translation,
  Shelter,
  GoBagItem,
  EmergencyContact,
  DetectionEvent
} from './components';
```

### Mobile Types

```typescript
import type {
  Theme,
  Screen,
  Task,
  KitItem,
  Contact,
  EvacPlan,
  StepPrepProps
} from './components';
```

## Import Translations

```typescript
import { translations } from './components/StepPrepDesktop';

// Use translations
const t = translations['en']; // English
const tUk = translations['uk']; // Ukrainian
```

## Usage Examples

### Example 1: Using Desktop Component

```typescript
import { StepPrepDesktop } from './components';

export default function App() {
  return <StepPrepDesktop />;
}
```

### Example 2: Using Mobile Component with Props

```typescript
import { StepPrep, type StepPrepProps } from './components';

export default function App() {
  const handleThemeChange = (theme: Theme) => {
    console.log('Theme changed to:', theme);
  };

  return (
    <StepPrep
      initialTheme="modern"
      initialScreen="home"
      showThemeSwitcher={true}
      onThemeChange={handleThemeChange}
    />
  );
}
```

### Example 3: Using Types

```typescript
import type { EmergencyContact, Language } from './components';
import { translations } from './components/StepPrepDesktop';

function ContactList() {
  const [contacts, setContacts] = useState<EmergencyContact[]>([
    { id: '1', name: 'Emergency', phone: '112' }
  ]);

  const [language, setLanguage] = useState<Language>('en');
  const t = translations[language];

  return (
    <div>
      <h2>{t.emergencyContacts}</h2>
      {contacts.map(contact => (
        <div key={contact.id}>
          {contact.name}: {contact.phone}
        </div>
      ))}
    </div>
  );
}
```

### Example 4: Custom Emergency System

```typescript
import { StepPrepDesktop, type DetectionEvent } from './components';
import { useState } from 'react';

function CustomEmergencySystem() {
  const [events, setEvents] = useState<DetectionEvent[]>([]);

  const addEvent = () => {
    const newEvent: DetectionEvent = {
      id: Date.now().toString(),
      type: 'motion',
      timestamp: new Date(),
      description: 'Motion detected in zone A',
      severity: 'high'
    };
    setEvents([newEvent, ...events]);
  };

  return (
    <div>
      <StepPrepDesktop />
      <button onClick={addEvent}>Add Test Event</button>
    </div>
  );
}
```

## Available Components

### StepPrepDesktop
Professional desktop emergency monitoring system with:
- Real-time camera monitoring
- Multi-sensor detection (camera, microphone, gesture)
- Shelter location finder
- Emergency supplies checklist
- Contact management with call/message functions
- Full English/Ukrainian localization

### StepPrep (Mobile)
Mobile-optimized emergency response app with:
- Task management
- Kit tracking
- SOS alerts
- Emergency contacts
- Multiple themes (modern, bold, calm, vibrant)

### SafeReadyPresentation
Professional presentation/slideshow component showcasing the StepPrep system features

## All Available Types

### Desktop Types
- `Language`: 'en' | 'uk'
- `TabType`: 'monitoring' | 'shelter' | 'gobag' | 'settings'
- `Translation`: Interface containing all UI text translations
- `Shelter`: Emergency shelter location data
- `GoBagItem`: Emergency supply item
- `EmergencyContact`: Contact with name and phone
- `DetectionEvent`: Security detection event with severity levels

### Mobile Types
- `Theme`: 'modern' | 'bold' | 'calm' | 'vibrant'
- `Screen`: 'home' | 'kit' | 'sos' | 'plan' | 'settings'
- `Task`: Preparedness checklist item
- `KitItem`: Emergency kit supply item
- `Contact`: Emergency contact with role
- `EvacPlan`: Evacuation plan/route
- `StepPrepProps`: Component props interface

## Full Import Statement

```typescript
// Import everything at once
import {
  // Components
  StepPrepDesktop,
  StepPrep,
  SafeReadyPresentation,
  
  // Desktop Types
  type Language,
  type TabType,
  type Translation,
  type Shelter,
  type GoBagItem,
  type EmergencyContact,
  type DetectionEvent,
  
  // Mobile Types
  type StepPrepProps,
  type Theme,
  type Screen,
  type Task,
  type KitItem,
  type Contact,
  type EvacPlan
} from './components';

// Import translations separately
import { translations } from './components/StepPrepDesktop';
```

## Notes

- All components are fully typed with TypeScript
- Desktop component includes demo mode by default for safe testing
- Both components support full localization (English/Ukrainian)
- All types are exported for custom implementations
- Components can be used standalone or integrated into larger systems
