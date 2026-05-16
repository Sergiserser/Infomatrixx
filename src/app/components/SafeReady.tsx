import { useState } from 'react';
import { Home, Package, Phone, Map, Settings } from 'lucide-react';
import { toast } from 'sonner';
import {
  HomeScreen,
  KitScreen,
  SOSScreen,
  PlanScreen,
  SettingsScreen,
  themes,
  translations,
  type Theme,
  type Screen,
  type Language,
  type Task,
  type KitItem,
  type Contact,
  type EvacPlan,
} from './SafeReadyComponents';

const initialTasks: Task[] = [
  { id: '1', text: 'Check water supply', done: true },
  { id: '2', text: 'Test emergency radio', done: true },
  { id: '3', text: 'Rotate food stock', done: false },
  { id: '4', text: 'Share plan with family', done: false },
];

const initialKitItems: KitItem[] = [
  { id: '1', icon: 'droplet', name: 'Bottled water', qty: '12 L · expires Aug 2026', status: 'ok', category: 'water-food' },
  { id: '2', icon: 'package', name: 'Emergency rations', qty: '3 days · expires Mar 2026', status: 'expired', category: 'water-food' },
  { id: '3', icon: 'package', name: 'First aid kit', qty: 'Complete set', status: 'ok', category: 'medical' },
  { id: '4', icon: 'pill', name: 'Prescription meds', qty: 'Not added yet', status: 'missing', category: 'medical' },
  { id: '5', icon: 'zap', name: 'Flashlight + batteries', qty: '2 units', status: 'ok', category: 'tools' },
];

const initialContacts: Contact[] = [
  { id: '1', name: 'Maria A.', role: 'Primary contact · Mom', initials: 'MA', phone: '+40 123 456 789', isPrimary: true },
  { id: '2', name: 'Dan P.', role: 'Neighbor', initials: 'DP', phone: '+40 234 567 890' },
  { id: '3', name: 'Emergency Room', role: 'Floreasca Hospital', initials: 'ER', phone: '+40 345 678 901' },
];

const initialPlans: EvacPlan[] = [
  { id: '1', icon: 'map', title: 'Route A — Primary exit', sub: 'Via Calea Victoriei → Piața Unirii shelter', type: 'route' },
  { id: '2', icon: 'map', title: 'Meeting point', sub: 'Parcul Cișmigiu — main fountain', type: 'route' },
  { id: '3', icon: 'map', title: 'Nearest shelter', sub: 'Liceul Teoretic No. 1 · 1.2 km away', type: 'route' },
  { id: '4', icon: 'flame', title: 'Fire', sub: 'Floor plan + 2 exits mapped', type: 'disaster', disasterType: 'fire' },
  { id: '5', icon: 'waves', title: 'Flood', sub: 'High-ground route selected', type: 'disaster', disasterType: 'flood' },
  { id: '6', icon: 'zap', title: 'Earthquake', sub: 'Shelter-in-place protocol set', type: 'disaster', disasterType: 'earthquake' },
];

export interface StepPrepProps {
  initialTheme?: Theme;
  initialScreen?: Screen;
  showThemeSwitcher?: boolean;
  onThemeChange?: (theme: Theme) => void;
  onScreenChange?: (screen: Screen) => void;
}

export function StepPrep({
  initialTheme = 'modern',
  initialScreen = 'home',
  showThemeSwitcher = true,
  onThemeChange,
  onScreenChange,
}: StepPrepProps) {
  const [theme, setTheme] = useState<Theme>(initialTheme);
  const [screen, setScreen] = useState<Screen>(initialScreen);
  const [tasks, setTasks] = useState<Task[]>(initialTasks);
  const [kitItems, setKitItems] = useState<KitItem[]>(initialKitItems);
  const [contacts, setContacts] = useState<Contact[]>(initialContacts);
  const [plans, setPlans] = useState<EvacPlan[]>(initialPlans);
  const [showAlert, setShowAlert] = useState(true);

  const currentTheme = themes[theme];

  const handleThemeChange = (newTheme: Theme) => {
    setTheme(newTheme);
    onThemeChange?.(newTheme);
  };

  const handleScreenChange = (newScreen: Screen) => {
    setScreen(newScreen);
    onScreenChange?.(newScreen);
  };

  const toggleTask = (id: string) => {
    setTasks(tasks.map(task => task.id === id ? { ...task, done: !task.done } : task));
    const task = tasks.find(t => t.id === id);
    if (task) {
      toast.success(task.done ? 'Task marked incomplete' : 'Task completed!');
    }
  };

  const handleSOSPress = () => {
    toast.error('🚨 SOS Alert Sent! Location shared with all emergency contacts.');
  };

  const handleCall = (contact: Contact) => {
    toast.success(`Calling ${contact.name} at ${contact.phone}...`);
  };

  const handleEditReadiness = () => {
    toast.info('Edit readiness settings');
  };

  const handleSeeAllTasks = () => {
    toast.info('Viewing all tasks');
  };

  const handleAddKitItem = (category: string) => {
    toast.info(`Add new ${category} item`);
  };

  const handleManageContacts = () => {
    toast.info('Manage emergency contacts');
  };

  const handleEditPlans = () => {
    toast.info('Edit evacuation plans');
  };

  const handleViewPlanDetails = (plan: EvacPlan) => {
    toast.info(`Viewing details: ${plan.title}`);
  };

  const handleAlertClick = () => {
    toast.warning('Severe storm warning details: High winds expected until 11 PM');
  };

  const handleNationalEmergency = () => {
    toast.error('Calling 112 - National Emergency Services');
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4" style={{ background: currentTheme.bgSecondary }}>
      {/* Theme Switcher */}
      {showThemeSwitcher && (
        <div className="fixed top-4 left-4 z-50 flex gap-2 flex-wrap max-w-xs">
          {(Object.keys(themes) as Theme[]).map((t) => (
            <button
              key={t}
              onClick={() => handleThemeChange(t)}
              className="px-3 py-1.5 rounded-lg text-xs font-medium transition-all hover:scale-105 active:scale-95"
              style={{
                background: theme === t ? currentTheme.primary : currentTheme.bg,
                color: theme === t ? '#fff' : currentTheme.text,
                border: `1px solid ${currentTheme.border}`,
              }}
            >
              {themes[t].name}
            </button>
          ))}
        </div>
      )}

      {/* Phone Frame */}
      <div className="w-full max-w-sm" style={{ background: currentTheme.border, borderRadius: '32px', padding: '12px' }}>
        <div className="overflow-hidden rounded-3xl shadow-2xl" style={{ background: currentTheme.bg }}>
          {/* Status Bar */}
          <div className="px-6 py-2 flex justify-between items-center text-xs font-medium" style={{ background: currentTheme.primary, color: '#fff' }}>
            <span>9:41</span>
            <span>100%</span>
          </div>

          {/* Header */}
          <div className="px-6 py-4" style={{ background: currentTheme.primary, color: '#fff' }}>
            <h1 className="text-xl font-bold">StepPrep</h1>
            <p className="text-xs opacity-80 mt-0.5">Bucharest · Last updated: today</p>
          </div>

          {/* Screen Content */}
          <div className="min-h-[500px]" style={{ background: currentTheme.bg }}>
            {screen === 'home' && (
              <HomeScreen
                theme={currentTheme}
                tasks={tasks}
                showAlert={showAlert}
                onToggleTask={toggleTask}
                onEditReadiness={handleEditReadiness}
                onSeeAllTasks={handleSeeAllTasks}
                onAlertClick={handleAlertClick}
                onDismissAlert={() => setShowAlert(false)}
              />
            )}
            {screen === 'kit' && (
              <KitScreen
                theme={currentTheme}
                kitItems={kitItems}
                onAddItem={handleAddKitItem}
              />
            )}
            {screen === 'sos' && (
              <SOSScreen
                theme={currentTheme}
                contacts={contacts}
                onSOSPress={handleSOSPress}
                onCall={handleCall}
                onManageContacts={handleManageContacts}
                onNationalEmergency={handleNationalEmergency}
              />
            )}
            {screen === 'plan' && (
              <PlanScreen
                theme={currentTheme}
                plans={plans}
                onEditPlans={handleEditPlans}
                onViewDetails={handleViewPlanDetails}
              />
            )}
          </div>

          {/* Bottom Navigation */}
          <div className="flex border-t" style={{ borderColor: currentTheme.border }}>
            {[
              { id: 'home' as Screen, icon: Home, label: 'Home' },
              { id: 'kit' as Screen, icon: Package, label: 'Kit' },
              { id: 'sos' as Screen, icon: Phone, label: 'SOS' },
              { id: 'plan' as Screen, icon: Map, label: 'Plan' },
              { id: 'settings' as Screen, icon: Settings, label: 'Settings' },
            ].map(({ id, icon: Icon, label }) => (
              <button
                key={id}
                onClick={() => {
                  if (id === 'settings') {
                    toast.info('Settings screen coming soon');
                  } else {
                    handleScreenChange(id);
                  }
                }}
                className="flex-1 flex flex-col items-center gap-1 py-2 text-xs font-medium transition-colors hover:opacity-80"
                style={{
                  color: screen === id ? currentTheme.primary : currentTheme.textSecondary,
                }}
              >
                <Icon size={20} />
                <span>{label}</span>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

export { themes, HomeScreen, KitScreen, SOSScreen, PlanScreen };
export type { Theme, Screen, Task, KitItem, Contact, EvacPlan };
