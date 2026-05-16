/**
 * Test file to verify all imports work correctly
 * This file should compile without errors if all exports are properly configured
 */

// Import all components
import {
  StepPrepDesktop,
  StepPrep,
  SafeReadyPresentation,
  translations
} from './app/components';

// Import all desktop types
import type {
  Language,
  TabType,
  Translation,
  Shelter,
  GoBagItem,
  EmergencyContact,
  DetectionEvent
} from './app/components';

// Import all mobile types
import type {
  StepPrepProps,
  Theme,
  Screen,
  Task,
  KitItem,
  Contact,
  EvacPlan
} from './app/components';

// Test type usage
const testLanguage: Language = 'en';
const testTab: TabType = 'monitoring';
const testTheme: Theme = 'modern';
const testScreen: Screen = 'home';

const testContact: EmergencyContact = {
  id: '1',
  name: 'Test Contact',
  phone: '112'
};

const testEvent: DetectionEvent = {
  id: '1',
  type: 'motion',
  timestamp: new Date(),
  description: 'Test event',
  severity: 'high'
};

const testShelter: Shelter = {
  id: '1',
  name: 'Test Shelter',
  distance: '1.0 km',
  address: 'Test Address',
  lat: 44.4268,
  lon: 26.1025
};

const testGoBagItem: GoBagItem = {
  id: '1',
  name: 'Water',
  checked: true
};

const testTask: Task = {
  id: '1',
  text: 'Test task',
  done: false
};

const testKitItem: KitItem = {
  id: '1',
  icon: 'droplet',
  name: 'Water',
  qty: '12 L',
  status: 'ok',
  category: 'water-food'
};

const testContactMobile: Contact = {
  id: '1',
  name: 'John Doe',
  role: 'Primary',
  initials: 'JD',
  phone: '+1234567890'
};

const testEvacPlan: EvacPlan = {
  id: '1',
  icon: 'map',
  title: 'Route A',
  sub: 'Main exit',
  type: 'route'
};

const testProps: StepPrepProps = {
  initialTheme: 'modern',
  initialScreen: 'home',
  showThemeSwitcher: true
};

// Test translations
const t: Translation = translations['en'];
const tUk: Translation = translations['uk'];

console.log('All imports and type definitions are working correctly!');
console.log('Test language:', testLanguage);
console.log('Test theme:', testTheme);
console.log('Test contact:', testContact);
console.log('Test translation:', t.monitoring);

export {
  // Re-export for verification
  StepPrepDesktop,
  StepPrep,
  SafeReadyPresentation,
  translations,
  // Test values
  testContact,
  testEvent,
  testShelter,
  testGoBagItem,
  testTask,
  testKitItem,
  testContactMobile,
  testEvacPlan,
  testProps,
  t,
  tUk
};
