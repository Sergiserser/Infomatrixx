# SafeReady Data Customization Guide

All data in SafeReady can be fully customized - tasks, kit items, contacts, and evacuation plans.

## Quick Example

```tsx
import { SafeReady, type Task, type KitItem, type Contact, type EvacPlan } from './SafeReady-Complete';
import { Toaster } from 'sonner';

const myTasks: Task[] = [
  { id: '1', text: 'Update emergency contacts', done: false },
  { id: '2', text: 'Check fire extinguisher', done: true },
];

const myKitItems: KitItem[] = [
  { id: '1', icon: 'droplet', name: 'Water bottles', qty: '24 bottles', status: 'ok', category: 'water-food' },
  { id: '2', icon: 'pill', name: 'First aid kit', qty: 'Complete', status: 'ok', category: 'medical' },
];

const myContacts: Contact[] = [
  { id: '1', name: 'John Smith', role: 'Emergency contact', initials: 'JS', phone: '911', isPrimary: true },
];

const myPlans: EvacPlan[] = [
  { id: '1', icon: 'map', title: 'Exit Route', sub: 'Main street to shelter', type: 'route' },
];

function App() {
  return (
    <>
      <SafeReady
        initialTasks={myTasks}
        initialKitItems={myKitItems}
        initialContacts={myContacts}
        initialPlans={myPlans}
      />
      <Toaster position="top-center" richColors />
    </>
  );
}
```

## Data Types Reference

### Task Interface

```tsx
interface Task {
  id: string;           // Unique identifier
  text: string;         // Task description
  done: boolean;        // Completion status
}
```

**Example:**
```tsx
const tasks: Task[] = [
  { id: '1', text: 'Test smoke detector', done: false },
  { id: '2', text: 'Check batteries', done: true },
  { id: '3', text: 'Review escape routes', done: false },
  { id: '4', text: 'Update insurance documents', done: false },
];
```

### KitItem Interface

```tsx
interface KitItem {
  id: string;                           // Unique identifier
  icon: string;                         // Icon name: 'droplet' | 'package' | 'pill' | 'zap'
  name: string;                         // Item name
  qty: string;                          // Quantity/description
  status: 'ok' | 'expired' | 'missing' | 'low';  // Item status
  category: 'water-food' | 'medical' | 'tools';  // Category
}
```

**Example:**
```tsx
const kitItems: KitItem[] = [
  {
    id: '1',
    icon: 'droplet',
    name: 'Drinking water',
    qty: '5 gallons · expires Dec 2026',
    status: 'ok',
    category: 'water-food'
  },
  {
    id: '2',
    icon: 'package',
    name: 'Canned food',
    qty: '20 cans · expires Jan 2027',
    status: 'ok',
    category: 'water-food'
  },
  {
    id: '3',
    icon: 'pill',
    name: 'Pain medication',
    qty: 'Bottle of 100',
    status: 'low',
    category: 'medical'
  },
  {
    id: '4',
    icon: 'pill',
    name: 'Bandages',
    qty: 'Not purchased',
    status: 'missing',
    category: 'medical'
  },
  {
    id: '5',
    icon: 'zap',
    name: 'LED flashlight',
    qty: '2 units with batteries',
    status: 'ok',
    category: 'tools'
  },
  {
    id: '6',
    icon: 'zap',
    name: 'Hand crank radio',
    qty: '1 unit',
    status: 'ok',
    category: 'tools'
  },
];
```

**Available Icons:**
- `'droplet'` - Water/liquids
- `'package'` - Food/boxes/general items
- `'pill'` - Medicine/medical supplies
- `'zap'` - Tools/electronics/batteries

**Status Options:**
- `'ok'` - Green badge, item is ready
- `'expired'` - Yellow/orange badge, item needs replacement
- `'low'` - Yellow/orange badge, running low
- `'missing'` - Red badge, item not available

### Contact Interface

```tsx
interface Contact {
  id: string;         // Unique identifier
  name: string;       // Contact name
  role: string;       // Contact role/description
  initials: string;   // 2-letter initials for avatar
  phone: string;      // Phone number
  isPrimary?: boolean; // Optional: marks as primary contact (green color)
}
```

**Example:**
```tsx
const contacts: Contact[] = [
  {
    id: '1',
    name: 'Sarah Johnson',
    role: 'Wife · Primary contact',
    initials: 'SJ',
    phone: '+1 555-0101',
    isPrimary: true
  },
  {
    id: '2',
    name: 'Mike Davis',
    role: 'Neighbor',
    initials: 'MD',
    phone: '+1 555-0102'
  },
  {
    id: '3',
    name: 'City Hospital',
    role: 'Emergency Room',
    initials: 'CH',
    phone: '+1 555-9999'
  },
  {
    id: '4',
    name: 'Fire Department',
    role: 'Local Station #5',
    initials: 'FD',
    phone: '911'
  },
];
```

### EvacPlan Interface

```tsx
interface EvacPlan {
  id: string;             // Unique identifier
  icon: string;           // Icon name: 'map' | 'flame' | 'waves' | 'zap'
  title: string;          // Plan title
  sub: string;            // Subtitle/description
  type?: 'route' | 'disaster';  // Plan type (optional)
  disasterType?: string;  // Disaster type (optional)
}
```

**Example:**
```tsx
const plans: EvacPlan[] = [
  // Routes
  {
    id: '1',
    icon: 'map',
    title: 'Primary Exit Route',
    sub: 'Main Street → Community Center (0.5 mi)',
    type: 'route'
  },
  {
    id: '2',
    icon: 'map',
    title: 'Backup Route',
    sub: 'Oak Avenue → School Gymnasium (0.8 mi)',
    type: 'route'
  },
  {
    id: '3',
    icon: 'map',
    title: 'Meeting Point',
    sub: 'Central Park - North Entrance',
    type: 'route'
  },
  
  // Disaster Plans
  {
    id: '4',
    icon: 'flame',
    title: 'Fire',
    sub: '2 exits mapped · Extinguisher locations marked',
    type: 'disaster',
    disasterType: 'fire'
  },
  {
    id: '5',
    icon: 'waves',
    title: 'Flood',
    sub: 'High ground route · Sandbags ready',
    type: 'disaster',
    disasterType: 'flood'
  },
  {
    id: '6',
    icon: 'zap',
    title: 'Power Outage',
    sub: 'Generator protocol · Emergency lighting tested',
    type: 'disaster',
    disasterType: 'power'
  },
];
```

**Available Icons:**
- `'map'` - Routes/locations
- `'flame'` - Fire
- `'waves'` - Flood/water
- `'zap'` - Earthquake/power/electrical

## Real-World Examples

### Example 1: Office Emergency Kit

```tsx
import { SafeReady, defaultTasks, defaultContacts } from './SafeReady-Complete';

const officeKitItems: KitItem[] = [
  { id: '1', icon: 'droplet', name: 'Water cooler', qty: '5 gallon jug', status: 'ok', category: 'water-food' },
  { id: '2', icon: 'package', name: 'Granola bars', qty: '50 count box', status: 'ok', category: 'water-food' },
  { id: '3', icon: 'pill', name: 'First aid station', qty: 'Wall-mounted kit', status: 'ok', category: 'medical' },
  { id: '4', icon: 'pill', name: 'AED device', qty: 'Lobby entrance', status: 'ok', category: 'medical' },
  { id: '5', icon: 'zap', name: 'Emergency lights', qty: '12 units', status: 'ok', category: 'tools' },
  { id: '6', icon: 'zap', name: 'Fire extinguishers', qty: 'All floors', status: 'ok', category: 'tools' },
];

const officeContacts: Contact[] = [
  { id: '1', name: 'Security Desk', role: 'Building Security', initials: 'SD', phone: 'ext 5000', isPrimary: true },
  { id: '2', name: 'Fire Department', role: 'Emergency Services', initials: 'FD', phone: '911' },
  { id: '3', name: 'Building Manager', role: 'John Smith', initials: 'JS', phone: '+1 555-0100' },
];

<SafeReady
  initialTasks={defaultTasks} // Use defaults
  initialKitItems={officeKitItems}
  initialContacts={officeContacts}
  customTexts={{
    appName: 'Office Safety',
    appLocation: 'Floor 12 · East Wing',
  }}
/>
```

### Example 2: Family Home Setup

```tsx
const familyTasks: Task[] = [
  { id: '1', text: 'Test smoke detectors', done: true },
  { id: '2', text: 'Check fire extinguisher expiry', done: false },
  { id: '3', text: 'Practice escape plan with kids', done: false },
  { id: '4', text: 'Update emergency contact list', done: true },
  { id: '5', text: 'Refill prescription medications', done: false },
];

const familyContacts: Contact[] = [
  { id: '1', name: 'Mom (Lisa)', role: 'Primary contact', initials: 'LM', phone: '+1 555-0001', isPrimary: true },
  { id: '2', name: 'Dad (Tom)', role: 'Secondary contact', initials: 'TM', phone: '+1 555-0002' },
  { id: '3', name: 'Grandma', role: 'Emergency backup', initials: 'GM', phone: '+1 555-0003' },
  { id: '4', name: 'Neighbor - Smith Family', role: 'Next door', initials: 'SF', phone: '+1 555-0004' },
  { id: '5', name: 'Pediatrician', role: 'Dr. Johnson', initials: 'DJ', phone: '+1 555-1234' },
];

<SafeReady
  initialTasks={familyTasks}
  initialContacts={familyContacts}
  customTexts={{
    appName: 'Family Safety Plan',
    appLocation: '123 Main Street',
  }}
/>
```

### Example 3: Minimal Setup

```tsx
const minimalTasks: Task[] = [
  { id: '1', text: 'Check kit', done: false },
];

const minimalContacts: Contact[] = [
  { id: '1', name: 'Emergency', role: '911', initials: '911', phone: '911', isPrimary: true },
];

<SafeReady
  initialTasks={minimalTasks}
  initialContacts={minimalContacts}
  initialKitItems={[]}  // Empty kit
  initialPlans={[]}     // No plans yet
/>
```

## Dynamic Data with State Management

Track changes to your data with callbacks:

```tsx
function App() {
  const [tasks, setTasks] = useState<Task[]>(myInitialTasks);
  const [kitItems, setKitItems] = useState<KitItem[]>(myInitialKitItems);

  // Auto-save to localStorage
  const handleTasksChange = (updatedTasks: Task[]) => {
    setTasks(updatedTasks);
    localStorage.setItem('safeready-tasks', JSON.stringify(updatedTasks));
  };

  const handleKitItemsChange = (updatedItems: KitItem[]) => {
    setKitItems(updatedItems);
    localStorage.setItem('safeready-kit', JSON.stringify(updatedItems));
  };

  return (
    <SafeReady
      initialTasks={tasks}
      initialKitItems={kitItems}
      onTasksChange={handleTasksChange}
      onKitItemsChange={handleKitItemsChange}
    />
  );
}
```

## Using Default Data as Template

Import and modify the defaults:

```tsx
import { SafeReady, defaultTasks, defaultKitItems, defaultContacts, defaultPlans } from './SafeReady-Complete';

// Add to defaults
const myTasks = [
  ...defaultTasks,
  { id: '5', text: 'My custom task', done: false },
];

// Modify defaults
const myKitItems = defaultKitItems.map(item => ({
  ...item,
  qty: 'Updated quantity',
}));

<SafeReady
  initialTasks={myTasks}
  initialKitItems={myKitItems}
/>
```

## Available Callbacks

```tsx
interface SafeReadyProps {
  onTasksChange?: (tasks: Task[]) => void;
  onKitItemsChange?: (items: KitItem[]) => void;
  onContactsChange?: (contacts: Contact[]) => void;
  onPlansChange?: (plans: EvacPlan[]) => void;
  onThemeChange?: (theme: Theme) => void;
  onScreenChange?: (screen: Screen) => void;
}
```

## Hide Alert Banner

```tsx
<SafeReady
  showAlert={false}  // Hide the weather alert banner
/>
```

## Tips

1. **Keep IDs unique** - Each item needs a unique `id` field
2. **Use descriptive text** - Make tasks and items clear and actionable
3. **Realistic quantities** - Include expiry dates and counts for kit items
4. **Contact roles** - Add context to help identify contacts quickly
5. **Plan details** - Include distances, landmarks, or specific instructions
6. **Test with empty arrays** - Make sure your UI handles `[]` gracefully

## Complete Example

See `COMPLETE_CUSTOMIZATION_EXAMPLE.tsx` for a full working example with all data types customized.
