# StepPrep Import System

All StepPrep components and types are now fully exportable and importable for use in your code.

## Quick Start

```typescript
// Import the desktop component
import { StepPrepDesktop } from './src/app/components';

// Use it
export default function App() {
  return <StepPrepDesktop />;
}
```

## Documentation Files

📚 **[IMPORT_GUIDE.md](./IMPORT_GUIDE.md)** - Complete guide with examples and best practices

📝 **[EXPORTS_REFERENCE.md](./EXPORTS_REFERENCE.md)** - Full reference of all available exports

💡 **[USAGE_EXAMPLES.tsx](./USAGE_EXAMPLES.tsx)** - Working code examples you can copy

✅ **[src/test-imports.ts](./src/test-imports.ts)** - Import test file to verify everything works

## Available Components

### 🖥️ StepPrepDesktop
Professional emergency monitoring system for desktop
- Real-time camera monitoring
- Detection systems (camera, mic, gesture)
- Shelter finder
- Emergency supplies checklist
- Contact management with call/message
- English/Ukrainian support

### 📱 StepPrep (Mobile)
Mobile emergency response app
- Task management
- Kit tracking
- SOS alerts
- Multiple themes
- Emergency contacts

### 📊 SafeReadyPresentation
Presentation/slideshow component

## Main Export File

All exports are centralized in: **`src/app/components/index.ts`**

```typescript
import { StepPrepDesktop, StepPrep, translations } from './src/app/components';
import type { Language, EmergencyContact } from './src/app/components';
```

## What's Exported

### Components
- `StepPrepDesktop` - Desktop monitoring system
- `StepPrep` - Mobile app
- `SafeReadyPresentation` - Presentation component
- `translations` - Translation object (EN/UK)

### Desktop Types
- `Language`, `TabType`, `Translation`
- `Shelter`, `GoBagItem`, `EmergencyContact`, `DetectionEvent`

### Mobile Types
- `Theme`, `Screen`, `StepPrepProps`
- `Task`, `KitItem`, `Contact`, `EvacPlan`

## New Features

✅ Message function for emergency contacts
✅ Full TypeScript support
✅ Centralized exports
✅ Complete documentation
✅ Working examples

## Testing

Verify imports work:
```bash
# TypeScript will check if imports are valid
npm run build
# or
tsc --noEmit
```

## Files Structure

```
src/app/components/
├── index.ts                    ← Main export file
├── StepPrepDesktop.tsx         ← Desktop component
├── SafeReady.tsx               ← Mobile component
└── SafeReadyPresentation.tsx   ← Presentation
```

## Need Help?

1. Check **IMPORT_GUIDE.md** for detailed examples
2. Look at **USAGE_EXAMPLES.tsx** for working code
3. See **EXPORTS_REFERENCE.md** for complete API reference

---

**Ready to use!** All components are properly exported and ready to import in your code.
