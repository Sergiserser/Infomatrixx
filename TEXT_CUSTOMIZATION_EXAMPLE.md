# SafeReady Text Customization Guide

All buttons, labels, and messages in SafeReady can be customized using the `customTexts` prop.

## Quick Example

```tsx
import { SafeReady } from './SafeReady-Complete';
import { Toaster } from 'sonner';

function App() {
  return (
    <>
      <SafeReady
        customTexts={{
          appName: 'EmergencyHub',
          navHome: 'Dashboard',
          sosButtonText: 'HELP',
          homeAlertTitle: 'Severe Weather Alert',
        }}
      />
      <Toaster position="top-center" richColors />
    </>
  );
}
```

## All Available Text Customizations

### App Header
```tsx
{
  appName: 'SafeReady',                      // Main app title
  appLocation: 'Bucharest · Last updated: today',  // Location subtitle
}
```

### Navigation
```tsx
{
  navHome: 'Home',
  navKit: 'Kit',
  navSOS: 'SOS',
  navPlan: 'Plan',
  navSettings: 'Settings',
}
```

### Home Screen
```tsx
{
  // Alert Banner
  homeAlertTitle: 'Severe storm warning',
  homeAlertSubtitle: 'Active until 11 PM · Tap to see details',
  
  // Readiness Section
  homeReadinessTitle: 'Your readiness',
  homeReadinessEdit: 'Edit',
  
  // Cards
  homeCardSupplyKit: 'Supply kit',
  homeCardEvacPlan: 'Evac plan',
  homeCardContacts: 'Contacts',
  homeCardChecklist: 'Checklist',
  
  // Tasks
  homeTasksTitle: "Today's tasks",
  homeTasksSeeAll: 'See all',
}
```

### Kit Screen
```tsx
{
  kitOverallReadiness: 'Overall readiness',
  kitWaterFoodTitle: 'Water & food',
  kitMedicalTitle: 'Medical',
  kitToolsTitle: 'Tools',
  kitAddButton: 'Add',
  
  // Status badges
  kitStatusOK: 'OK',
  kitStatusExpired: 'Expired',
  kitStatusMissing: 'Missing',
  kitStatusLow: 'Low',
}
```

### SOS Screen
```tsx
{
  sosButtonText: 'SOS',
  sosButtonSubtitle: 'Tap to send location + alert to all contacts',
  sosContactsTitle: 'Emergency contacts',
  sosManageButton: 'Manage',
  sosNationalTitle: 'National emergency',
  sosNationalSubtitle: 'Call 112 · Fire: 081 · Police: 112',
}
```

### Plan Screen
```tsx
{
  planDisasterTitle: 'Plan for each disaster',
  planEditAll: 'Edit all',
}
```

### Toast Messages
```tsx
{
  toastTaskComplete: 'Task completed!',
  toastTaskIncomplete: 'Task marked incomplete',
  toastSOSAlert: '🚨 SOS Alert Sent! Location shared with all emergency contacts.',
  toastCalling: 'Calling',
  toastEditReadiness: 'Edit readiness settings',
  toastViewAllTasks: 'Viewing all tasks',
  toastAddItem: 'Add new',
  toastManageContacts: 'Manage emergency contacts',
  toastEditPlans: 'Edit evacuation plans',
  toastViewDetails: 'Viewing details:',
  toastAlertDetails: 'Severe storm warning details: High winds expected until 11 PM',
  toastNationalEmergency: 'Calling 112 - National Emergency Services',
  toastSettingsComingSoon: 'Settings screen coming soon',
}
```

## Real-World Examples

### Example 1: Multi-Language Support (Spanish)

```tsx
<SafeReady
  customTexts={{
    appName: 'Preparado',
    navHome: 'Inicio',
    navKit: 'Equipo',
    navSOS: 'SOS',
    navPlan: 'Plan',
    navSettings: 'Ajustes',
    
    homeReadinessTitle: 'Tu preparación',
    homeReadinessEdit: 'Editar',
    homeTasksTitle: 'Tareas de hoy',
    homeTasksSeeAll: 'Ver todo',
    
    sosButtonText: 'SOS',
    sosButtonSubtitle: 'Toca para enviar ubicación + alerta',
    sosContactsTitle: 'Contactos de emergencia',
    sosManageButton: 'Administrar',
    
    kitAddButton: 'Agregar',
    kitStatusOK: 'OK',
    kitStatusExpired: 'Expirado',
    kitStatusMissing: 'Faltante',
  }}
/>
```

### Example 2: Professional Emergency Management

```tsx
<SafeReady
  customTexts={{
    appName: 'Crisis Command',
    appLocation: 'Operations Center · Active',
    
    navHome: 'Command',
    navKit: 'Resources',
    navSOS: 'Alert',
    navPlan: 'Protocols',
    
    homeReadinessTitle: 'Operational Status',
    homeReadinessEdit: 'Configure',
    homeTasksTitle: 'Priority Actions',
    
    sosButtonText: 'ALERT',
    sosButtonSubtitle: 'Activate emergency protocol',
    sosContactsTitle: 'Emergency Response Team',
    
    toastSOSAlert: '⚠️ Emergency Protocol Activated - All teams notified',
  }}
/>
```

### Example 3: Family-Friendly Version

```tsx
<SafeReady
  customTexts={{
    appName: 'Family Safety',
    appLocation: 'Home Sweet Home',
    
    homeAlertTitle: '⚠️ Weather Watch',
    homeCardSupplyKit: '🎒 Emergency Bag',
    homeCardEvacPlan: '🚗 Exit Routes',
    homeCardContacts: '📞 Family & Friends',
    
    sosButtonText: 'HELP!',
    sosButtonSubtitle: 'Press to alert everyone',
    
    kitAddButton: '+ Add Item',
    toastTaskComplete: '✅ Great job!',
  }}
/>
```

### Example 4: Minimal/Short Labels

```tsx
<SafeReady
  customTexts={{
    homeReadinessEdit: '✏️',
    homeTasksSeeAll: '→',
    kitAddButton: '+',
    sosManageButton: '⚙️',
    planEditAll: '✏️',
  }}
/>
```

## TypeScript Support

The `customTexts` prop is fully typed with TypeScript autocomplete:

```tsx
import type { TextCustomization } from './SafeReady-Complete';

const myCustomTexts: Partial<TextCustomization> = {
  appName: 'My App',
  navHome: 'Dashboard',
  // TypeScript will autocomplete all available options!
};

<SafeReady customTexts={myCustomTexts} />
```

## Tips

1. **You only need to customize what you want to change** - All other text will use defaults
2. **Keep button labels short** - Especially for navigation and action buttons
3. **Maintain consistency** - Use similar tone across all customizations
4. **Test on mobile** - Some labels may be too long for small screens
5. **Consider accessibility** - Button labels should be clear and descriptive

## Dynamic Text (Advanced)

You can change text dynamically based on state:

```tsx
function App() {
  const [language, setLanguage] = useState<'en' | 'es'>('en');
  
  const texts = {
    en: {
      appName: 'SafeReady',
      navHome: 'Home',
      sosButtonText: 'SOS',
    },
    es: {
      appName: 'Preparado',
      navHome: 'Inicio',
      sosButtonText: 'SOS',
    },
  };
  
  return (
    <>
      <button onClick={() => setLanguage(language === 'en' ? 'es' : 'en')}>
        Toggle Language
      </button>
      <SafeReady customTexts={texts[language]} />
    </>
  );
}
```
