# SafeReady Props Reference

Complete reference for all available props in the SafeReady component.

## Component Props

```tsx
interface SafeReadyProps {
  // Display Settings
  initialTheme?: Theme;
  initialScreen?: Screen;
  showThemeSwitcher?: boolean;
  showAlert?: boolean;

  // Text Customization
  customTexts?: Partial<TextCustomization>;

  // Data Customization
  initialTasks?: Task[];
  initialKitItems?: KitItem[];
  initialContacts?: Contact[];
  initialPlans?: EvacPlan[];

  // Event Handlers
  onThemeChange?: (theme: Theme) => void;
  onScreenChange?: (screen: Screen) => void;
  onTasksChange?: (tasks: Task[]) => void;
  onKitItemsChange?: (items: KitItem[]) => void;
  onContactsChange?: (contacts: Contact[]) => void;
  onPlansChange?: (plans: EvacPlan[]) => void;
}
```

## Display Settings

### `initialTheme`
- **Type:** `'modern' | 'bold' | 'calm' | 'vibrant'`
- **Default:** `'modern'`
- **Description:** Starting theme when app loads

```tsx
<SafeReady initialTheme="bold" />
```

### `initialScreen`
- **Type:** `'home' | 'kit' | 'sos' | 'plan'`
- **Default:** `'home'`
- **Description:** Starting screen when app loads

```tsx
<SafeReady initialScreen="sos" />
```

### `showThemeSwitcher`
- **Type:** `boolean`
- **Default:** `true`
- **Description:** Show/hide theme switcher buttons in top-left

```tsx
<SafeReady showThemeSwitcher={false} />
```

### `showAlert`
- **Type:** `boolean`
- **Default:** `true`
- **Description:** Show/hide the alert banner on home screen

```tsx
<SafeReady showAlert={false} />
```

## Text Customization

### `customTexts`
- **Type:** `Partial<TextCustomization>`
- **Default:** `{}` (uses default texts)
- **Description:** Customize any of 60+ text strings

```tsx
<SafeReady
  customTexts={{
    appName: 'My App',
    navHome: 'Dashboard',
    sosButtonText: 'HELP',
    // ... 57 more options
  }}
/>
```

**See:** `TEXT_CUSTOMIZATION_EXAMPLE.md` for all 60+ available text options

## Data Customization

### `initialTasks`
- **Type:** `Task[]`
- **Default:** Default example tasks
- **Description:** Custom task list for home screen

```tsx
const myTasks: Task[] = [
  { id: '1', text: 'Check batteries', done: false }
];

<SafeReady initialTasks={myTasks} />
```

### `initialKitItems`
- **Type:** `KitItem[]`
- **Default:** Default example kit items
- **Description:** Custom emergency kit items

```tsx
const myKit: KitItem[] = [
  {
    id: '1',
    icon: 'droplet',
    name: 'Water',
    qty: '5 gallons',
    status: 'ok',
    category: 'water-food'
  }
];

<SafeReady initialKitItems={myKit} />
```

### `initialContacts`
- **Type:** `Contact[]`
- **Default:** Default example contacts
- **Description:** Custom emergency contacts

```tsx
const myContacts: Contact[] = [
  {
    id: '1',
    name: 'John Doe',
    role: 'Primary',
    initials: 'JD',
    phone: '555-0100',
    isPrimary: true
  }
];

<SafeReady initialContacts={myContacts} />
```

### `initialPlans`
- **Type:** `EvacPlan[]`
- **Default:** Default example plans
- **Description:** Custom evacuation plans

```tsx
const myPlans: EvacPlan[] = [
  {
    id: '1',
    icon: 'map',
    title: 'Main Exit',
    sub: 'Front door to park',
    type: 'route'
  }
];

<SafeReady initialPlans={myPlans} />
```

**See:** `DATA_CUSTOMIZATION_EXAMPLE.md` for complete data type documentation

## Event Handlers

### `onThemeChange`
- **Type:** `(theme: Theme) => void`
- **Description:** Called when user changes theme

```tsx
<SafeReady
  onThemeChange={(theme) => {
    console.log('New theme:', theme);
    localStorage.setItem('theme', theme);
  }}
/>
```

### `onScreenChange`
- **Type:** `(screen: Screen) => void`
- **Description:** Called when user navigates to different screen

```tsx
<SafeReady
  onScreenChange={(screen) => {
    console.log('Navigated to:', screen);
    analytics.track('screen_view', { screen });
  }}
/>
```

### `onTasksChange`
- **Type:** `(tasks: Task[]) => void`
- **Description:** Called when tasks are modified (toggled)

```tsx
<SafeReady
  onTasksChange={(tasks) => {
    console.log('Tasks updated:', tasks);
    localStorage.setItem('tasks', JSON.stringify(tasks));
  }}
/>
```

### `onKitItemsChange`
- **Type:** `(items: KitItem[]) => void`
- **Description:** Called when kit items are modified

```tsx
<SafeReady
  onKitItemsChange={(items) => {
    saveToDatabase('kit', items);
  }}
/>
```

### `onContactsChange`
- **Type:** `(contacts: Contact[]) => void`
- **Description:** Called when contacts are modified

```tsx
<SafeReady
  onContactsChange={(contacts) => {
    saveToDatabase('contacts', contacts);
  }}
/>
```

### `onPlansChange`
- **Type:** `(plans: EvacPlan[]) => void`
- **Description:** Called when plans are modified

```tsx
<SafeReady
  onPlansChange={(plans) => {
    saveToDatabase('plans', plans);
  }}
/>
```

## Type Definitions

### Theme
```tsx
type Theme = 'modern' | 'bold' | 'calm' | 'vibrant';
```

### Screen
```tsx
type Screen = 'home' | 'kit' | 'sos' | 'plan';
```

### Task
```tsx
interface Task {
  id: string;
  text: string;
  done: boolean;
}
```

### KitItem
```tsx
interface KitItem {
  id: string;
  icon: 'droplet' | 'package' | 'pill' | 'zap';
  name: string;
  qty: string;
  status: 'ok' | 'expired' | 'missing' | 'low';
  category: 'water-food' | 'medical' | 'tools';
}
```

### Contact
```tsx
interface Contact {
  id: string;
  name: string;
  role: string;
  initials: string;
  phone: string;
  isPrimary?: boolean;
}
```

### EvacPlan
```tsx
interface EvacPlan {
  id: string;
  icon: 'map' | 'flame' | 'waves' | 'zap';
  title: string;
  sub: string;
  type?: 'route' | 'disaster';
  disasterType?: string;
}
```

## Default Data Exports

Use these as starting points for your own data:

```tsx
import {
  defaultTasks,
  defaultKitItems,
  defaultContacts,
  defaultPlans
} from './SafeReady-Complete';

// Extend defaults
const myTasks = [
  ...defaultTasks,
  { id: '5', text: 'New task', done: false }
];

// Modify defaults
const myItems = defaultKitItems.map(item => ({
  ...item,
  qty: 'Updated'
}));
```

## Complete Example

```tsx
import { SafeReady, type Task } from './SafeReady-Complete';
import { Toaster } from 'sonner';
import { useState } from 'react';

function App() {
  const [tasks, setTasks] = useState<Task[]>([
    { id: '1', text: 'My task', done: false }
  ]);

  return (
    <>
      <SafeReady
        // Display
        initialTheme="modern"
        initialScreen="home"
        showThemeSwitcher={true}
        showAlert={true}

        // Text
        customTexts={{
          appName: 'My Emergency App'
        }}

        // Data
        initialTasks={tasks}

        // Handlers
        onTasksChange={setTasks}
        onThemeChange={(theme) => console.log(theme)}
      />
      <Toaster position="top-center" richColors />
    </>
  );
}
```

## See Also

- **TEXT_CUSTOMIZATION_EXAMPLE.md** - All 60+ text customization options
- **DATA_CUSTOMIZATION_EXAMPLE.md** - Complete data customization guide
- **COMPLETE_CUSTOMIZATION_EXAMPLE.tsx** - Full working example
- **SAFEREADY_FILES.md** - File locations and quick start
