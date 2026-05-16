# StepPrep Exports Reference

Complete reference of all exports available from StepPrep components.

## Component Exports

### From `./src/app/components` (index)

```typescript
// Components
export { StepPrepDesktop } from './StepPrepDesktop';
export { StepPrep } from './SafeReady';
export { SafeReadyPresentation } from './SafeReadyPresentation';

// Translations object
export { translations } from './StepPrepDesktop';

// Desktop Types
export type {
  Language,
  TabType,
  Translation,
  Shelter,
  GoBagItem,
  EmergencyContact,
  DetectionEvent
} from './StepPrepDesktop';

// Mobile Types
export type {
  StepPrepProps,
  Theme,
  Screen,
  Task,
  KitItem,
  Contact,
  EvacPlan
} from './SafeReady';
```

## Type Definitions

### Desktop Types

```typescript
type Language = 'en' | 'uk';

type TabType = 'monitoring' | 'shelter' | 'gobag' | 'settings';

interface Translation {
  monitoring: string;
  shelter: string;
  goBag: string;
  settings: string;
  riskScore: string;
  alarmStatus: string;
  active: string;
  inactive: string;
  demoMode: string;
  emergencyContact: string;
  detectionSystems: string;
  camera: string;
  microphone: string;
  gesture: string;
  motion: string;
  sound: string;
  emergency: string;
  recentEvents: string;
  noEvents: string;
  findShelters: string;
  searchingShelters: string;
  nearbyShelters: string;
  openInMaps: string;
  noSheltersFound: string;
  distance: string;
  emergencySupplies: string;
  addItem: string;
  saveList: string;
  itemName: string;
  language: string;
  emergencyContacts: string;
  contactName: string;
  phoneNumber: string;
  location: string;
  demoModeLabel: string;
  enableDemo: string;
  testAlarm: string;
  currentLocation: string;
  last24Hours: string;
  addContact: string;
  editContact: string;
  deleteContact: string;
  callContact: string;
  messageContact: string;
  addNewContact: string;
  saveContact: string;
  cancel: string;
}

interface Shelter {
  id: string;
  name: string;
  distance: string;
  address: string;
  lat: number;
  lon: number;
}

interface GoBagItem {
  id: string;
  name: string;
  checked: boolean;
}

interface EmergencyContact {
  id: string;
  name: string;
  phone: string;
}

interface DetectionEvent {
  id: string;
  type: 'motion' | 'sound' | 'gesture';
  timestamp: Date;
  description: string;
  severity: 'low' | 'medium' | 'high';
}
```

### Mobile Types

```typescript
type Theme = 'modern' | 'bold' | 'calm' | 'vibrant';

type Screen = 'home' | 'kit' | 'sos' | 'plan' | 'settings';

interface StepPrepProps {
  initialTheme?: Theme;
  initialScreen?: Screen;
  showThemeSwitcher?: boolean;
  onThemeChange?: (theme: Theme) => void;
  onScreenChange?: (screen: Screen) => void;
}

interface Task {
  id: string;
  text: string;
  done: boolean;
}

interface KitItem {
  id: string;
  icon: string;
  name: string;
  qty: string;
  status: 'ok' | 'expired' | 'missing';
  category: string;
}

interface Contact {
  id: string;
  name: string;
  role: string;
  initials: string;
  phone: string;
  isPrimary?: boolean;
}

interface EvacPlan {
  id: string;
  icon: string;
  title: string;
  sub: string;
  type: 'route' | 'disaster';
  disasterType?: 'fire' | 'flood' | 'earthquake';
}
```

## Constants

### Translations Object

```typescript
const translations: Record<Language, Translation> = {
  en: { /* English translations */ },
  uk: { /* Ukrainian translations */ }
};
```

## Import Patterns

### Pattern 1: Named Imports (Recommended)

```typescript
import {
  StepPrepDesktop,
  StepPrep,
  translations,
  type Language,
  type EmergencyContact
} from './src/app/components';
```

### Pattern 2: Direct Component Import

```typescript
import { StepPrepDesktop } from './src/app/components/StepPrepDesktop';
```

### Pattern 3: Type-Only Import

```typescript
import type {
  Language,
  EmergencyContact,
  DetectionEvent
} from './src/app/components';
```

### Pattern 4: Mixed Import

```typescript
import { StepPrepDesktop } from './src/app/components';
import type { Language } from './src/app/components';
```

### Pattern 5: Import All Types

```typescript
import type * as StepPrepTypes from './src/app/components';

// Usage
const contact: StepPrepTypes.EmergencyContact = {
  id: '1',
  name: 'Test',
  phone: '112'
};
```

## Tree Structure

```
src/app/components/
├── index.ts                    # Main export file
├── StepPrepDesktop.tsx        # Desktop component + types
├── SafeReady.tsx              # Mobile component + types
└── SafeReadyPresentation.tsx  # Presentation component
```

## Quick Reference

| Import | Type | Source File |
|--------|------|-------------|
| `StepPrepDesktop` | Component | StepPrepDesktop.tsx |
| `StepPrep` | Component | SafeReady.tsx |
| `SafeReadyPresentation` | Component | SafeReadyPresentation.tsx |
| `translations` | Constant | StepPrepDesktop.tsx |
| `Language` | Type | StepPrepDesktop.tsx |
| `TabType` | Type | StepPrepDesktop.tsx |
| `Translation` | Interface | StepPrepDesktop.tsx |
| `Shelter` | Interface | StepPrepDesktop.tsx |
| `GoBagItem` | Interface | StepPrepDesktop.tsx |
| `EmergencyContact` | Interface | StepPrepDesktop.tsx |
| `DetectionEvent` | Interface | StepPrepDesktop.tsx |
| `Theme` | Type | SafeReady.tsx |
| `Screen` | Type | SafeReady.tsx |
| `StepPrepProps` | Interface | SafeReady.tsx |
| `Task` | Interface | SafeReady.tsx |
| `KitItem` | Interface | SafeReady.tsx |
| `Contact` | Interface | SafeReady.tsx |
| `EvacPlan` | Interface | SafeReady.tsx |

## Usage Notes

1. **Always use type imports for types**: Use `import type { ... }` for better tree-shaking
2. **Import from index**: Import from `./components` instead of individual files
3. **Translations**: Import translations separately when needed
4. **Component props**: All components work standalone without required props
5. **TypeScript**: All exports are fully typed
