# SafeReady - Quick Start Guide

Get started with SafeReady in 3 steps!

## Step 1: Copy the File

Copy **`SafeReady-Complete.tsx`** to your project.

This single file contains everything:
- ✅ All 4 themes
- ✅ All 4 screens  
- ✅ Text customization (60+ options)
- ✅ Data customization
- ✅ Full TypeScript types

## Step 2: Install Dependencies

```bash
pnpm install lucide-react sonner
```

## Step 3: Use It!

```tsx
import { SafeReady } from './SafeReady-Complete';
import { Toaster } from 'sonner';

function App() {
  return (
    <>
      <SafeReady />
      <Toaster position="top-center" richColors />
    </>
  );
}
```

**That's it!** You now have a fully working disaster preparedness app with:
- ✅ 4 screens (Home, Kit, SOS, Plan, Settings)
- ✅ 4 themes (Modern, Bold, Calm, Vibrant)
- ✅ 2 languages (English & Ukrainian)
- ✅ Full interactivity

---

## Use Settings Screen

Users can customize the app directly:

1. Tap **Settings** in the bottom navigation
2. Choose theme color variation
3. Switch between English 🇬🇧 and Ukrainian 🇺🇦
4. Changes apply instantly!

---

## Customize It (Optional)

### Change Text

```tsx
<SafeReady
  customTexts={{
    appName: 'My App',
    sosButtonText: 'HELP',
  }}
/>
```

### Change Language

```tsx
<SafeReady initialLanguage="uk" />  // Ukrainian
```

### Change Data

```tsx
import { type Task } from './SafeReady-Complete';

const myTasks: Task[] = [
  { id: '1', text: 'My custom task', done: false }
];

<SafeReady initialTasks={myTasks} />
```

### Track Changes

```tsx
<SafeReady
  onTasksChange={(tasks) => {
    localStorage.setItem('tasks', JSON.stringify(tasks));
  }}
/>
```

---

## What Can You Customize?

| Category | Options | Documentation |
|----------|---------|---------------|
| **Text** | 60+ options | [TEXT_CUSTOMIZATION_EXAMPLE.md](TEXT_CUSTOMIZATION_EXAMPLE.md) |
| **Tasks** | Full control | [DATA_CUSTOMIZATION_EXAMPLE.md](DATA_CUSTOMIZATION_EXAMPLE.md) |
| **Kit Items** | Full control | [DATA_CUSTOMIZATION_EXAMPLE.md](DATA_CUSTOMIZATION_EXAMPLE.md) |
| **Contacts** | Full control | [DATA_CUSTOMIZATION_EXAMPLE.md](DATA_CUSTOMIZATION_EXAMPLE.md) |
| **Plans** | Full control | [DATA_CUSTOMIZATION_EXAMPLE.md](DATA_CUSTOMIZATION_EXAMPLE.md) |
| **Theme** | 4 built-in themes | [SAFEREADY_README.md](SAFEREADY_README.md) |
| **Language** | English & Ukrainian | [LOCALIZATION_GUIDE.md](LOCALIZATION_GUIDE.md) |
| **Settings** | Built-in screen | [SETTINGS_DEMO.tsx](SETTINGS_DEMO.tsx) |
| **All Props** | Complete reference | [PROPS_REFERENCE.md](PROPS_REFERENCE.md) |

---

## Examples

### Example 1: Ukrainian Version (Built-in)

```tsx
<SafeReady
  initialLanguage="uk"  // Ukrainian language
  initialTheme="calm"
/>
```

### Example 2: Spanish Version (Custom)

```tsx
<SafeReady
  customTexts={{
    appName: 'Preparado',
    navHome: 'Inicio',
    navKit: 'Equipo',
    sosButtonText: 'SOS',
  }}
/>
```

### Example 3: Custom Emergency Kit

```tsx
import { type KitItem } from './SafeReady-Complete';

const officeKit: KitItem[] = [
  {
    id: '1',
    icon: 'droplet',
    name: 'Water cooler',
    qty: '5 gallon jug',
    status: 'ok',
    category: 'water-food'
  },
  {
    id: '2',
    icon: 'pill',
    name: 'First aid station',
    qty: 'Wall-mounted',
    status: 'ok',
    category: 'medical'
  },
];

<SafeReady initialKitItems={officeKit} />
```

### Example 4: With Auto-Save

```tsx
function App() {
  const [tasks, setTasks] = useState(() => {
    const saved = localStorage.getItem('tasks');
    return saved ? JSON.parse(saved) : [];
  });

  return (
    <SafeReady
      initialTasks={tasks}
      onTasksChange={(newTasks) => {
        setTasks(newTasks);
        localStorage.setItem('tasks', JSON.stringify(newTasks));
      }}
    />
  );
}
```

---

## Full Documentation

| Document | Description |
|----------|-------------|
| **[SAFEREADY_README.md](SAFEREADY_README.md)** | Complete overview and features |
| **[SAFEREADY_FILES.md](SAFEREADY_FILES.md)** | File locations and quick reference |
| **[PROPS_REFERENCE.md](PROPS_REFERENCE.md)** | All props and their types |
| **[TEXT_CUSTOMIZATION_EXAMPLE.md](TEXT_CUSTOMIZATION_EXAMPLE.md)** | All 60+ text options with examples |
| **[DATA_CUSTOMIZATION_EXAMPLE.md](DATA_CUSTOMIZATION_EXAMPLE.md)** | Complete data customization guide |
| **[COMPLETE_CUSTOMIZATION_EXAMPLE.tsx](COMPLETE_CUSTOMIZATION_EXAMPLE.tsx)** | Full working example |

---

## Need Help?

1. **See all text options:** Open `TEXT_CUSTOMIZATION_EXAMPLE.md`
2. **See all data options:** Open `DATA_CUSTOMIZATION_EXAMPLE.md`
3. **See all props:** Open `PROPS_REFERENCE.md`
4. **See full example:** Open `COMPLETE_CUSTOMIZATION_EXAMPLE.tsx`

---

## TypeScript Support

All types are exported for your convenience:

```tsx
import {
  SafeReady,
  type Task,
  type KitItem,
  type Contact,
  type EvacPlan,
  type Theme,
  type Screen,
  type TextCustomization,
  defaultTasks,
  defaultKitItems,
  defaultContacts,
  defaultPlans,
  themes,
} from './SafeReady-Complete';
```

---

## Common Use Cases

### Office Building
- Custom contacts (security, building manager)
- Office-specific kit items
- Multiple floor evacuation plans

### Family Home
- Family member contacts
- Child-specific tasks
- Neighborhood meeting points

### School/Institution
- Multiple emergency protocols
- Large contact lists
- Detailed evacuation procedures

### Multi-Language App
- Switch between languages dynamically
- Save language preference
- Translate all UI text

---

## License

This is a demo application for educational purposes.
