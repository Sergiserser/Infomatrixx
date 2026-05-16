import { AlertTriangle, CheckCircle, X, Package, Map, Phone, Droplet, Pill, Zap, Plus, PhoneCall, ChevronRight, Flame, Waves } from 'lucide-react';

export type Theme = 'modern' | 'bold' | 'calm' | 'vibrant';
export type Screen = 'home' | 'kit' | 'sos' | 'plan' | 'settings';
export type Language = 'en' | 'uk';

export interface Task {
  id: string;
  text: string;
  done: boolean;
}

export interface KitItem {
  id: string;
  icon: string;
  name: string;
  qty: string;
  status: 'ok' | 'expired' | 'missing' | 'low';
  category: 'water-food' | 'medical' | 'tools';
}

export interface Contact {
  id: string;
  name: string;
  role: string;
  initials: string;
  phone: string;
  isPrimary?: boolean;
}

export interface EvacPlan {
  id: string;
  icon: string;
  title: string;
  sub: string;
  type?: 'route' | 'disaster';
  disasterType?: string;
}

export const themes = {
  modern: {
    name: 'Modern Minimal',
    primary: '#1a1a1a',
    secondary: '#6b7280',
    accent: '#3b82f6',
    danger: '#ef4444',
    success: '#10b981',
    warning: '#f59e0b',
    bg: '#ffffff',
    bgSecondary: '#f9fafb',
    border: '#e5e7eb',
    text: '#111827',
    textSecondary: '#6b7280',
  },
  bold: {
    name: 'Bold Urgent',
    primary: '#dc2626',
    secondary: '#991b1b',
    accent: '#ea580c',
    danger: '#b91c1c',
    success: '#16a34a',
    warning: '#d97706',
    bg: '#fef2f2',
    bgSecondary: '#fee2e2',
    border: '#fca5a5',
    text: '#450a0a',
    textSecondary: '#991b1b',
  },
  calm: {
    name: 'Calm Professional',
    primary: '#0891b2',
    secondary: '#0e7490',
    accent: '#06b6d4',
    danger: '#f43f5e',
    success: '#14b8a6',
    warning: '#f59e0b',
    bg: '#f0fdfa',
    bgSecondary: '#ccfbf1',
    border: '#5eead4',
    text: '#134e4a',
    textSecondary: '#0f766e',
  },
  vibrant: {
    name: 'Vibrant Friendly',
    primary: '#8b5cf6',
    secondary: '#7c3aed',
    accent: '#ec4899',
    danger: '#f43f5e',
    success: '#22c55e',
    warning: '#fbbf24',
    bg: '#faf5ff',
    bgSecondary: '#f3e8ff',
    border: '#d8b4fe',
    text: '#581c87',
    textSecondary: '#7c3aed',
  },
};

interface HomeScreenProps {
  theme: typeof themes.modern;
  tasks: Task[];
  showAlert: boolean;
  onToggleTask: (id: string) => void;
  onEditReadiness: () => void;
  onSeeAllTasks: () => void;
  onAlertClick: () => void;
  onDismissAlert: () => void;
}

export function HomeScreen({
  theme,
  tasks,
  showAlert,
  onToggleTask,
  onEditReadiness,
  onSeeAllTasks,
  onAlertClick,
  onDismissAlert,
}: HomeScreenProps) {
  const completedTasks = tasks.filter(t => t.done).length;
  const totalTasks = tasks.length;

  return (
    <div className="p-4 space-y-4">
      {showAlert && (
        <div className="rounded-lg p-3 flex gap-3 relative" style={{ background: `${theme.warning}15`, border: `1px solid ${theme.warning}50` }}>
          <AlertTriangle size={20} style={{ color: theme.warning }} className="flex-shrink-0" />
          <button onClick={onAlertClick} className="flex-1 text-left">
            <div className="text-sm font-semibold" style={{ color: theme.text }}>Severe storm warning</div>
            <div className="text-xs mt-0.5" style={{ color: theme.textSecondary }}>Active until 11 PM · Tap to see details</div>
          </button>
          <button onClick={onDismissAlert} className="flex-shrink-0 hover:opacity-70">
            <X size={16} style={{ color: theme.textSecondary }} />
          </button>
        </div>
      )}

      <div>
        <div className="flex justify-between items-center mb-3">
          <h2 className="text-sm font-semibold" style={{ color: theme.text }}>Your readiness</h2>
          <button onClick={onEditReadiness} className="text-xs font-medium hover:underline" style={{ color: theme.accent }}>
            Edit
          </button>
        </div>
        <div className="grid grid-cols-2 gap-2">
          {[
            { icon: Package, label: 'Supply kit', value: '82% stocked', color: theme.success },
            { icon: Map, label: 'Evac plan', value: 'Route A set', color: theme.accent },
            { icon: Phone, label: 'Contacts', value: '5 people', color: theme.warning },
            { icon: CheckCircle, label: 'Checklist', value: `${totalTasks - completedTasks} items left`, color: theme.danger },
          ].map(({ icon: Icon, label, value, color }, i) => (
            <div key={i} className="rounded-lg p-3 space-y-2 hover:opacity-90 transition-opacity cursor-pointer" style={{ background: theme.bgSecondary, border: `1px solid ${theme.border}` }}>
              <div className="w-8 h-8 rounded-full flex items-center justify-center" style={{ background: `${color}20` }}>
                <Icon size={16} style={{ color }} />
              </div>
              <div>
                <div className="text-xs font-medium" style={{ color: theme.text }}>{label}</div>
                <div className="text-xs mt-0.5" style={{ color: theme.textSecondary }}>{value}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div>
        <div className="flex justify-between items-center mb-3">
          <h2 className="text-sm font-semibold" style={{ color: theme.text }}>Today's tasks</h2>
          <button onClick={onSeeAllTasks} className="text-xs font-medium hover:underline" style={{ color: theme.accent }}>
            See all
          </button>
        </div>
        <div className="space-y-2">
          {tasks.map((task) => (
            <button
              key={task.id}
              onClick={() => onToggleTask(task.id)}
              className="w-full flex items-center gap-3 py-2 border-b hover:opacity-70 transition-opacity"
              style={{ borderColor: theme.border }}
            >
              <div className="w-5 h-5 rounded flex items-center justify-center flex-shrink-0 transition-all" style={{ border: `2px solid ${task.done ? theme.success : theme.border}`, background: task.done ? theme.success : 'transparent' }}>
                {task.done && <CheckCircle size={14} color="#fff" />}
              </div>
              <span className={`text-sm text-left ${task.done ? 'line-through opacity-60' : ''}`} style={{ color: theme.text }}>{task.text}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

interface KitScreenProps {
  theme: typeof themes.modern;
  kitItems: KitItem[];
  onAddItem: (category: string) => void;
}

export function KitScreen({ theme, kitItems, onAddItem }: KitScreenProps) {
  const getIconComponent = (iconName: string) => {
    const icons: Record<string, any> = {
      droplet: Droplet,
      package: Package,
      pill: Pill,
      zap: Zap,
    };
    return icons[iconName] || Package;
  };

  const getStatusStyle = (status: string) => {
    switch (status) {
      case 'ok':
        return { bg: `${theme.success}20`, color: theme.success, text: 'OK' };
      case 'expired':
      case 'low':
        return { bg: `${theme.warning}20`, color: theme.warning, text: status === 'expired' ? 'Expired' : 'Low' };
      case 'missing':
        return { bg: `${theme.danger}20`, color: theme.danger, text: 'Missing' };
      default:
        return { bg: `${theme.textSecondary}20`, color: theme.textSecondary, text: 'Unknown' };
    }
  };

  const okItems = kitItems.filter(i => i.status === 'ok').length;
  const readinessPercent = Math.round((okItems / kitItems.length) * 100);

  const waterFood = kitItems.filter(i => i.category === 'water-food');
  const medical = kitItems.filter(i => i.category === 'medical');
  const tools = kitItems.filter(i => i.category === 'tools');

  return (
    <div className="p-4 space-y-4">
      <div className="rounded-lg p-3 space-y-2" style={{ background: theme.bgSecondary }}>
        <div className="text-xs" style={{ color: theme.textSecondary }}>Overall readiness</div>
        <div className="h-2 rounded-full overflow-hidden" style={{ background: theme.border }}>
          <div className="h-full rounded-full transition-all duration-500" style={{ width: `${readinessPercent}%`, background: theme.success }} />
        </div>
        <div className="text-sm font-semibold" style={{ color: theme.success }}>{readinessPercent}%</div>
      </div>

      <div>
        <div className="flex justify-between items-center mb-3">
          <h2 className="text-sm font-semibold" style={{ color: theme.text }}>Water & food</h2>
          <button onClick={() => onAddItem('water-food')} className="text-xs font-medium hover:underline flex items-center gap-1" style={{ color: theme.accent }}>
            <Plus size={14} /> Add
          </button>
        </div>
        <div className="space-y-3">
          {waterFood.map((item) => {
            const Icon = getIconComponent(item.icon);
            const statusStyle = getStatusStyle(item.status);
            return (
              <div key={item.id} className="flex items-center gap-3 pb-3 border-b" style={{ borderColor: theme.border }}>
                <Icon size={20} style={{ color: theme.accent }} />
                <div className="flex-1">
                  <div className="text-sm font-medium" style={{ color: theme.text }}>{item.name}</div>
                  <div className="text-xs mt-0.5" style={{ color: theme.textSecondary }}>{item.qty}</div>
                </div>
                <span className="text-xs px-2 py-1 rounded-full font-medium" style={{ background: statusStyle.bg, color: statusStyle.color }}>
                  {statusStyle.text}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      <div>
        <div className="flex justify-between items-center mb-3">
          <h2 className="text-sm font-semibold" style={{ color: theme.text }}>Medical</h2>
          <button onClick={() => onAddItem('medical')} className="text-xs font-medium hover:underline flex items-center gap-1" style={{ color: theme.accent }}>
            <Plus size={14} /> Add
          </button>
        </div>
        <div className="space-y-3">
          {medical.map((item) => {
            const Icon = getIconComponent(item.icon);
            const statusStyle = getStatusStyle(item.status);
            return (
              <div key={item.id} className="flex items-center gap-3 pb-3 border-b" style={{ borderColor: theme.border }}>
                <Icon size={20} style={{ color: theme.accent }} />
                <div className="flex-1">
                  <div className="text-sm font-medium" style={{ color: theme.text }}>{item.name}</div>
                  <div className="text-xs mt-0.5" style={{ color: theme.textSecondary }}>{item.qty}</div>
                </div>
                <span className="text-xs px-2 py-1 rounded-full font-medium" style={{ background: statusStyle.bg, color: statusStyle.color }}>
                  {statusStyle.text}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {tools.length > 0 && (
        <div>
          <div className="flex justify-between items-center mb-3">
            <h2 className="text-sm font-semibold" style={{ color: theme.text }}>Tools</h2>
            <button onClick={() => onAddItem('tools')} className="text-xs font-medium hover:underline flex items-center gap-1" style={{ color: theme.accent }}>
              <Plus size={14} /> Add
            </button>
          </div>
          <div className="space-y-3">
            {tools.map((item) => {
              const Icon = getIconComponent(item.icon);
              const statusStyle = getStatusStyle(item.status);
              return (
                <div key={item.id} className="flex items-center gap-3 pb-3 border-b" style={{ borderColor: theme.border }}>
                  <Icon size={20} style={{ color: theme.accent }} />
                  <div className="flex-1">
                    <div className="text-sm font-medium" style={{ color: theme.text }}>{item.name}</div>
                    <div className="text-xs mt-0.5" style={{ color: theme.textSecondary }}>{item.qty}</div>
                  </div>
                  <span className="text-xs px-2 py-1 rounded-full font-medium" style={{ background: statusStyle.bg, color: statusStyle.color }}>
                    {statusStyle.text}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

interface SOSScreenProps {
  theme: typeof themes.modern;
  contacts: Contact[];
  onSOSPress: () => void;
  onCall: (contact: Contact) => void;
  onManageContacts: () => void;
  onNationalEmergency: () => void;
}

export function SOSScreen({
  theme,
  contacts,
  onSOSPress,
  onCall,
  onManageContacts,
  onNationalEmergency,
}: SOSScreenProps) {
  const getContactColor = (contact: Contact) => {
    if (contact.isPrimary) return theme.success;
    if (contact.role.includes('Hospital')) return theme.warning;
    return theme.accent;
  };

  return (
    <div className="p-4 space-y-4">
      <div className="text-center py-6">
        <button
          onClick={onSOSPress}
          className="w-20 h-20 rounded-full flex flex-col items-center justify-center gap-1 mx-auto mb-3 transition-transform hover:scale-105 active:scale-95 shadow-lg"
          style={{ background: theme.danger, color: '#fff' }}
        >
          <Phone size={32} />
          <span className="text-xs font-bold">SOS</span>
        </button>
        <p className="text-xs" style={{ color: theme.textSecondary }}>Tap to send location + alert to all contacts</p>
      </div>

      <div>
        <div className="flex justify-between items-center mb-3">
          <h2 className="text-sm font-semibold" style={{ color: theme.text }}>Emergency contacts</h2>
          <button onClick={onManageContacts} className="text-xs font-medium hover:underline" style={{ color: theme.accent }}>
            Manage
          </button>
        </div>
        <div className="space-y-3">
          {contacts.map((contact) => {
            const color = getContactColor(contact);
            return (
              <div key={contact.id} className="flex items-center gap-3 pb-3 border-b" style={{ borderColor: theme.border }}>
                <div className="w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold" style={{ background: `${color}20`, color }}>
                  {contact.initials}
                </div>
                <div className="flex-1">
                  <div className="text-sm font-medium" style={{ color: theme.text }}>{contact.name}</div>
                  <div className="text-xs mt-0.5" style={{ color: theme.textSecondary }}>{contact.role}</div>
                </div>
                <button onClick={() => onCall(contact)} className="hover:scale-110 transition-transform" aria-label={`Call ${contact.name}`}>
                  <PhoneCall size={20} style={{ color: theme.success }} />
                </button>
              </div>
            );
          })}
        </div>
      </div>

      <button
        onClick={onNationalEmergency}
        className="w-full rounded-lg p-3 text-left hover:opacity-90 transition-opacity"
        style={{ background: `${theme.danger}15`, border: `1px solid ${theme.danger}30` }}
      >
        <div className="text-sm font-semibold mb-1" style={{ color: theme.danger }}>
          <AlertTriangle size={14} className="inline mr-1" style={{ verticalAlign: '-2px' }} />
          National emergency
        </div>
        <div className="text-xs" style={{ color: theme.textSecondary }}>Call 112 · Fire: 081 · Police: 112</div>
      </button>
    </div>
  );
}

interface PlanScreenProps {
  theme: typeof themes.modern;
  plans: EvacPlan[];
  onEditPlans: () => void;
  onViewDetails: (plan: EvacPlan) => void;
}

export function PlanScreen({ theme, plans, onEditPlans, onViewDetails }: PlanScreenProps) {
  const getIconComponent = (iconName: string) => {
    const icons: Record<string, any> = {
      map: Map,
      flame: Flame,
      waves: Waves,
      zap: Zap,
    };
    return icons[iconName] || Map;
  };

  const getIconColor = (plan: EvacPlan) => {
    if (plan.type === 'route') return theme.accent;
    switch (plan.disasterType) {
      case 'fire':
        return theme.danger;
      case 'flood':
        return theme.accent;
      case 'earthquake':
        return theme.warning;
      default:
        return theme.primary;
    }
  };

  const routes = plans.filter(p => p.type === 'route');
  const disasters = plans.filter(p => p.type === 'disaster');

  return (
    <div className="p-4 space-y-4">
      <div className="space-y-2">
        {routes.map((plan) => {
          const Icon = getIconComponent(plan.icon);
          const color = getIconColor(plan);
          return (
            <button
              key={plan.id}
              onClick={() => onViewDetails(plan)}
              className="w-full rounded-lg p-3 flex items-center gap-3 hover:opacity-90 transition-opacity text-left"
              style={{ background: theme.bgSecondary, border: `1px solid ${theme.border}` }}
            >
              <Icon size={22} style={{ color }} />
              <div className="flex-1">
                <div className="text-sm font-medium" style={{ color: theme.text }}>{plan.title}</div>
                <div className="text-xs mt-0.5" style={{ color: theme.textSecondary }}>{plan.sub}</div>
              </div>
              <ChevronRight size={18} style={{ color: theme.textSecondary }} />
            </button>
          );
        })}
      </div>

      <div>
        <div className="flex justify-between items-center mb-3">
          <h2 className="text-sm font-semibold" style={{ color: theme.text }}>Plan for each disaster</h2>
          <button onClick={onEditPlans} className="text-xs font-medium hover:underline" style={{ color: theme.accent }}>
            Edit all
          </button>
        </div>
        <div className="space-y-2">
          {disasters.map((plan) => {
            const Icon = getIconComponent(plan.icon);
            const color = getIconColor(plan);
            return (
              <button
                key={plan.id}
                onClick={() => onViewDetails(plan)}
                className="w-full rounded-lg p-3 flex items-center gap-3 hover:opacity-90 transition-opacity text-left"
                style={{ background: theme.bgSecondary, border: `1px solid ${theme.border}` }}
              >
                <Icon size={22} style={{ color }} />
                <div className="flex-1">
                  <div className="text-sm font-medium" style={{ color: theme.text }}>{plan.title}</div>
                  <div className="text-xs mt-0.5" style={{ color: theme.textSecondary }}>{plan.sub}</div>
                </div>
                <ChevronRight size={18} style={{ color: theme.textSecondary }} />
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
