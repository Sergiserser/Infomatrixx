# SafeReady - Disaster Preparedness App

A fully functional, highly customizable disaster preparedness app with 4 design variations and interactive features.

## Features

- **4 Theme Variations**: Modern Minimal, Bold Urgent, Calm Professional, and Vibrant Friendly
- **4 Main Screens**:
  - **Home Dashboard**: Shows alerts, readiness status, and daily tasks
  - **Supply Kit Tracker**: Manage water, food, medical supplies, and tools
  - **Emergency SOS**: Quick access to emergency contacts and SOS button
  - **Evacuation Plan**: View routes and disaster-specific plans
- **Fully Interactive**: All buttons are functional with toast notifications
- **Fully Customizable**: 
  - 60+ text customization options (all buttons, labels, messages)
  - Complete data customization (tasks, kit items, contacts, plans)
  - Event callbacks for state management
- **Responsive Design**: Mobile-first design with phone frame presentation
- **TypeScript**: Full type safety and autocomplete support

## Quick Start

The main app is already configured in `src/app/App.tsx`:

```tsx
import { SafeReady } from './components/SafeReady';
import { Toaster } from 'sonner';

export default function App() {
  return (
    <>
      <SafeReady showThemeSwitcher={true} />
      <Toaster position="top-center" richColors />
    </>
  );
}
```

## Importing into Your App

### Option 1: Use the Complete Component

```tsx
import { SafeReady } from './components/SafeReady';
import { Toaster } from 'sonner';

function MyApp() {
  return (
    <>
      <SafeReady 
        initialTheme="modern"
        initialScreen="home"
        showThemeSwitcher={true}
        onThemeChange={(theme) => console.log('Theme changed:', theme)}
        onScreenChange={(screen) => console.log('Screen changed:', screen)}
      />
      <Toaster position="top-center" richColors />
    </>
  );
}
```

### Option 2: Use Individual Screen Components

```tsx
import { 
  HomeScreen, 
  KitScreen, 
  SOSScreen, 
  PlanScreen,
  themes,
  type Task,
  type KitItem,
  type Contact,
  type EvacPlan 
} from './components/SafeReadyComponents';

function MyCustomApp() {
  const [tasks, setTasks] = useState<Task[]>([...]);
  const currentTheme = themes.modern;

  return (
    <HomeScreen
      theme={currentTheme}
      tasks={tasks}
      showAlert={true}
      onToggleTask={(id) => {/* your handler */}}
      onEditReadiness={() => {/* your handler */}}
      onSeeAllTasks={() => {/* your handler */}}
      onAlertClick={() => {/* your handler */}}
      onDismissAlert={() => {/* your handler */}}
    />
  );
}
```

## Component Props

### SafeReady Component

```tsx
interface SafeReadyProps {
  initialTheme?: Theme; // 'modern' | 'bold' | 'calm' | 'vibrant'
  initialScreen?: Screen; // 'home' | 'kit' | 'sos' | 'plan'
  showThemeSwitcher?: boolean;
  onThemeChange?: (theme: Theme) => void;
  onScreenChange?: (screen: Screen) => void;
}
```

### Available Types

```tsx
type Theme = 'modern' | 'bold' | 'calm' | 'vibrant';
type Screen = 'home' | 'kit' | 'sos' | 'plan';

interface Task {
  id: string;
  text: string;
  done: boolean;
}

interface KitItem {
  id: string;
  icon: string; // 'droplet' | 'package' | 'pill' | 'zap'
  name: string;
  qty: string;
  status: 'ok' | 'expired' | 'missing' | 'low';
  category: 'water-food' | 'medical' | 'tools';
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
  icon: string; // 'map' | 'flame' | 'waves' | 'zap'
  title: string;
  sub: string;
  type?: 'route' | 'disaster';
  disasterType?: string;
}
```

## Theme Colors

Each theme includes the following color tokens:

```tsx
{
  name: string;
  primary: string;    // Main brand color
  secondary: string;  // Secondary brand color
  accent: string;     // Accent/link color
  danger: string;     // Error/emergency color
  success: string;    // Success/complete color
  warning: string;    // Warning/attention color
  bg: string;         // Background color
  bgSecondary: string; // Secondary background
  border: string;     // Border color
  text: string;       // Primary text color
  textSecondary: string; // Secondary text color
}
```

## Interactive Features

All buttons and interactive elements are fully functional:

- ✅ **Task checkboxes**: Toggle task completion
- ✅ **Theme switcher**: Change between 4 design variations
- ✅ **Navigation tabs**: Switch between screens
- ✅ **Alert banner**: Dismiss alerts
- ✅ **SOS button**: Trigger emergency alert
- ✅ **Call buttons**: Initiate calls to contacts
- ✅ **Add buttons**: Add new items to kit categories
- ✅ **Edit buttons**: Edit readiness, contacts, and plans
- ✅ **View details**: Tap on evacuation plans for details

## File Structure

```
/workspaces/default/code/
├── SafeReady-Complete.tsx                    # ⭐ Complete standalone file (USE THIS)
├── COMPLETE_CUSTOMIZATION_EXAMPLE.tsx        # Full working example
├── SAFEREADY_README.md                       # This file
├── SAFEREADY_FILES.md                        # File locations guide
├── TEXT_CUSTOMIZATION_EXAMPLE.md             # All text options (60+)
├── DATA_CUSTOMIZATION_EXAMPLE.md             # Data customization guide
├── PROPS_REFERENCE.md                        # Complete props reference
└── src/app/
    ├── App.tsx                               # Current app (uses SafeReady)
    └── components/
        ├── SafeReady.tsx                     # Modular version (older)
        └── SafeReadyComponents.tsx           # Individual screens (older)
```

**Recommended:** Use `SafeReady-Complete.tsx` - it has all features including text and data customization.

## Dependencies

- `react` - UI framework
- `lucide-react` - Icons
- `sonner` - Toast notifications
- `tailwindcss` - Styling

## Customization

### Text Customization (60+ Options)

Customize any text in the app:

```tsx
<SafeReady
  customTexts={{
    appName: 'My Emergency App',
    navHome: 'Dashboard',
    sosButtonText: 'HELP!',
    kitAddButton: '+ Add Item',
    homeAlertTitle: 'Weather Warning',
    // ... 55+ more options
  }}
/>
```

**See:** `TEXT_CUSTOMIZATION_EXAMPLE.md` for complete list

### Data Customization

Provide your own tasks, kit items, contacts, and plans:

```tsx
import { type Task, type KitItem } from './SafeReady-Complete';

const myTasks: Task[] = [
  { id: '1', text: 'Check smoke alarm', done: false }
];

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

<SafeReady
  initialTasks={myTasks}
  initialKitItems={myKit}
/>
```

**See:** `DATA_CUSTOMIZATION_EXAMPLE.md` for complete guide

### Event Handlers

Track and save changes:

```tsx
<SafeReady
  onTasksChange={(tasks) => {
    // Auto-save to localStorage
    localStorage.setItem('tasks', JSON.stringify(tasks));
  }}
  onThemeChange={(theme) => {
    // Track analytics
    analytics.track('theme_change', { theme });
  }}
/>
```

**See:** `PROPS_REFERENCE.md` for all available props and handlers

### Multi-Language Support

```tsx
const translations = {
  en: { appName: 'SafeReady', navHome: 'Home' },
  es: { appName: 'Preparado', navHome: 'Inicio' },
};

<SafeReady customTexts={translations[language]} />
```

**See:** `COMPLETE_CUSTOMIZATION_EXAMPLE.tsx` for full example

## License

This is a demo application for educational purposes.
