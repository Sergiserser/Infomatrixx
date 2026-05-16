/**
 * SafeReady - Complete Disaster Preparedness App
 *
 * This file contains everything you need for the SafeReady app:
 * - 4 design theme variations (Modern, Bold, Calm, Vibrant)
 * - 4 interactive screens (Home, Kit, SOS, Plan)
 * - All TypeScript types and interfaces
 * - Full interactivity with toast notifications
 * - Complete text customization (60+ options)
 * - Complete data customization (tasks, kit, contacts, plans)
 *
 * BASIC USAGE:
 *
 * 1. Copy this entire file to your project
 * 2. Install dependencies: pnpm install lucide-react sonner
 * 3. Import and use:
 *
 *    import { SafeReady } from './SafeReady-Complete';
 *    import { Toaster } from 'sonner';
 *
 *    function App() {
 *      return (
 *        <>
 *          <SafeReady showThemeSwitcher={true} />
 *          <Toaster position="top-center" richColors />
 *        </>
 *      );
 *    }
 *
 * CUSTOMIZE TEXT (60+ options):
 *
 *    <SafeReady
 *      customTexts={{
 *        appName: 'My Emergency App',
 *        navHome: 'Dashboard',
 *        sosButtonText: 'HELP',
 *        kitAddButton: '+ New',
 *      }}
 *    />
 *
 * CUSTOMIZE DATA (tasks, kit, contacts, plans):
 *
 *    import { type Task, type KitItem, type Contact, type EvacPlan } from './SafeReady-Complete';
 *
 *    const myTasks: Task[] = [
 *      { id: '1', text: 'Check smoke alarm', done: false }
 *    ];
 *
 *    const myKitItems: KitItem[] = [
 *      { id: '1', icon: 'droplet', name: 'Water', qty: '5 gallons', status: 'ok', category: 'water-food' }
 *    ];
 *
 *    <SafeReady
 *      initialTasks={myTasks}
 *      initialKitItems={myKitItems}
 *      onTasksChange={(tasks) => console.log('Tasks updated:', tasks)}
 *    />
 *
 * COMPLETE EXAMPLE:
 *
 * See COMPLETE_CUSTOMIZATION_EXAMPLE.tsx for a full working example
 * See TEXT_CUSTOMIZATION_EXAMPLE.md for all text options
 * See DATA_CUSTOMIZATION_EXAMPLE.md for all data customization options
 */

import { useState } from 'react';
import {
  Home, Package, Phone, Map, Settings, AlertTriangle, CheckCircle,
  X, Droplet, Pill, Zap, Plus, PhoneCall, ChevronRight, Flame, Waves
} from 'lucide-react';
import { toast } from 'sonner';

// ============================================================================
// TYPES & INTERFACES
// ============================================================================

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

export interface TextCustomization {
  // App Header
  appName?: string;
  appLocation?: string;

  // Navigation
  navHome?: string;
  navKit?: string;
  navSOS?: string;
  navPlan?: string;
  navSettings?: string;

  // Home Screen
  homeAlertTitle?: string;
  homeAlertSubtitle?: string;
  homeReadinessTitle?: string;
  homeReadinessEdit?: string;
  homeTasksTitle?: string;
  homeTasksSeeAll?: string;
  homeCardSupplyKit?: string;
  homeCardEvacPlan?: string;
  homeCardContacts?: string;
  homeCardChecklist?: string;

  // Kit Screen
  kitOverallReadiness?: string;
  kitWaterFoodTitle?: string;
  kitMedicalTitle?: string;
  kitToolsTitle?: string;
  kitAddButton?: string;
  kitStatusOK?: string;
  kitStatusExpired?: string;
  kitStatusMissing?: string;
  kitStatusLow?: string;

  // SOS Screen
  sosButtonText?: string;
  sosButtonSubtitle?: string;
  sosContactsTitle?: string;
  sosManageButton?: string;
  sosNationalTitle?: string;
  sosNationalSubtitle?: string;

  // Plan Screen
  planDisasterTitle?: string;
  planEditAll?: string;

  // Toast Messages
  toastTaskComplete?: string;
  toastTaskIncomplete?: string;
  toastSOSAlert?: string;
  toastCalling?: string;
  toastEditReadiness?: string;
  toastViewAllTasks?: string;
  toastAddItem?: string;
  toastManageContacts?: string;
  toastEditPlans?: string;
  toastViewDetails?: string;
  toastAlertDetails?: string;
  toastNationalEmergency?: string;
  toastSettingsComingSoon?: string;
}

const defaultTexts: TextCustomization = {
  appName: 'SafeReady',
  appLocation: 'Bucharest · Last updated: today',

  navHome: 'Home',
  navKit: 'Kit',
  navSOS: 'SOS',
  navPlan: 'Plan',
  navSettings: 'Settings',

  homeAlertTitle: 'Severe storm warning',
  homeAlertSubtitle: 'Active until 11 PM · Tap to see details',
  homeReadinessTitle: 'Your readiness',
  homeReadinessEdit: 'Edit',
  homeTasksTitle: "Today's tasks",
  homeTasksSeeAll: 'See all',
  homeCardSupplyKit: 'Supply kit',
  homeCardEvacPlan: 'Evac plan',
  homeCardContacts: 'Contacts',
  homeCardChecklist: 'Checklist',

  kitOverallReadiness: 'Overall readiness',
  kitWaterFoodTitle: 'Water & food',
  kitMedicalTitle: 'Medical',
  kitToolsTitle: 'Tools',
  kitAddButton: 'Add',
  kitStatusOK: 'OK',
  kitStatusExpired: 'Expired',
  kitStatusMissing: 'Missing',
  kitStatusLow: 'Low',

  sosButtonText: 'SOS',
  sosButtonSubtitle: 'Tap to send location + alert to all contacts',
  sosContactsTitle: 'Emergency contacts',
  sosManageButton: 'Manage',
  sosNationalTitle: 'National emergency',
  sosNationalSubtitle: 'Call 112 · Fire: 081 · Police: 112',

  planDisasterTitle: 'Plan for each disaster',
  planEditAll: 'Edit all',

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

const ukrainianTexts: TextCustomization = {
  appName: 'БезпекаГотова',
  appLocation: 'Бухарест · Оновлено: сьогодні',

  navHome: 'Головна',
  navKit: 'Набір',
  navSOS: 'SOS',
  navPlan: 'План',
  navSettings: 'Налаштування',

  homeAlertTitle: 'Попередження про сильний шторм',
  homeAlertSubtitle: 'Активне до 23:00 · Натисніть для деталей',
  homeReadinessTitle: 'Ваша готовність',
  homeReadinessEdit: 'Редагувати',
  homeTasksTitle: 'Завдання на сьогодні',
  homeTasksSeeAll: 'Показати всі',
  homeCardSupplyKit: 'Набір постачання',
  homeCardEvacPlan: 'План евакуації',
  homeCardContacts: 'Контакти',
  homeCardChecklist: 'Список завдань',

  kitOverallReadiness: 'Загальна готовність',
  kitWaterFoodTitle: 'Вода і їжа',
  kitMedicalTitle: 'Медичні засоби',
  kitToolsTitle: 'Інструменти',
  kitAddButton: 'Додати',
  kitStatusOK: 'ОК',
  kitStatusExpired: 'Прострочено',
  kitStatusMissing: 'Відсутнє',
  kitStatusLow: 'Мало',

  sosButtonText: 'SOS',
  sosButtonSubtitle: 'Натисніть, щоб надіслати геолокацію та сповіщення',
  sosContactsTitle: 'Екстрені контакти',
  sosManageButton: 'Керувати',
  sosNationalTitle: 'Національна служба порятунку',
  sosNationalSubtitle: 'Телефон 112 · Пожежна: 101 · Поліція: 102',

  planDisasterTitle: 'План для кожного лиха',
  planEditAll: 'Редагувати всі',

  toastTaskComplete: 'Завдання виконано!',
  toastTaskIncomplete: 'Завдання позначено як невиконане',
  toastSOSAlert: '🚨 SOS сповіщення надіслано! Локація відправлена всім екстреним контактам.',
  toastCalling: 'Дзвінок',
  toastEditReadiness: 'Редагування налаштувань готовності',
  toastViewAllTasks: 'Перегляд усіх завдань',
  toastAddItem: 'Додати нове',
  toastManageContacts: 'Керування екстреними контактами',
  toastEditPlans: 'Редагування планів евакуації',
  toastViewDetails: 'Перегляд деталей:',
  toastAlertDetails: 'Попередження про шторм: Очікуються сильні вітри до 23:00',
  toastNationalEmergency: 'Дзвінок 112 - Служба порятунку',
  toastSettingsComingSoon: 'Налаштування скоро з\'являться',
}

export const translations = {
  en: defaultTexts,
  uk: ukrainianTexts,
}

// ============================================================================
// THEME DEFINITIONS
// ============================================================================

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

// ============================================================================
// INITIAL DATA (Default Examples - Can be customized via props)
// ============================================================================

export const defaultTasks: Task[] = [
  { id: '1', text: 'Check water supply', done: true },
  { id: '2', text: 'Test emergency radio', done: true },
  { id: '3', text: 'Rotate food stock', done: false },
  { id: '4', text: 'Share plan with family', done: false },
];

export const defaultKitItems: KitItem[] = [
  { id: '1', icon: 'droplet', name: 'Bottled water', qty: '12 L · expires Aug 2026', status: 'ok', category: 'water-food' },
  { id: '2', icon: 'package', name: 'Emergency rations', qty: '3 days · expires Mar 2026', status: 'expired', category: 'water-food' },
  { id: '3', icon: 'package', name: 'First aid kit', qty: 'Complete set', status: 'ok', category: 'medical' },
  { id: '4', icon: 'pill', name: 'Prescription meds', qty: 'Not added yet', status: 'missing', category: 'medical' },
  { id: '5', icon: 'zap', name: 'Flashlight + batteries', qty: '2 units', status: 'ok', category: 'tools' },
];

export const defaultContacts: Contact[] = [
  { id: '1', name: 'Maria A.', role: 'Primary contact · Mom', initials: 'MA', phone: '+40 123 456 789', isPrimary: true },
  { id: '2', name: 'Dan P.', role: 'Neighbor', initials: 'DP', phone: '+40 234 567 890' },
  { id: '3', name: 'Emergency Room', role: 'Floreasca Hospital', initials: 'ER', phone: '+40 345 678 901' },
];

export const defaultPlans: EvacPlan[] = [
  { id: '1', icon: 'map', title: 'Route A — Primary exit', sub: 'Via Calea Victoriei → Piața Unirii shelter', type: 'route' },
  { id: '2', icon: 'map', title: 'Meeting point', sub: 'Parcul Cișmigiu — main fountain', type: 'route' },
  { id: '3', icon: 'map', title: 'Nearest shelter', sub: 'Liceul Teoretic No. 1 · 1.2 km away', type: 'route' },
  { id: '4', icon: 'flame', title: 'Fire', sub: 'Floor plan + 2 exits mapped', type: 'disaster', disasterType: 'fire' },
  { id: '5', icon: 'waves', title: 'Flood', sub: 'High-ground route selected', type: 'disaster', disasterType: 'flood' },
  { id: '6', icon: 'zap', title: 'Earthquake', sub: 'Shelter-in-place protocol set', type: 'disaster', disasterType: 'earthquake' },
];

// Keep backwards compatibility
const initialTasks = defaultTasks;
const initialKitItems = defaultKitItems;
const initialContacts = defaultContacts;
const initialPlans = defaultPlans;

// ============================================================================
// SCREEN COMPONENTS
// ============================================================================

interface HomeScreenProps {
  theme: typeof themes.modern;
  tasks: Task[];
  showAlert: boolean;
  texts: TextCustomization;
  onToggleTask: (id: string) => void;
  onEditReadiness: () => void;
  onSeeAllTasks: () => void;
  onAlertClick: () => void;
  onDismissAlert: () => void;
}

function HomeScreen({
  theme,
  tasks,
  showAlert,
  texts,
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
            <div className="text-sm font-semibold" style={{ color: theme.text }}>{texts.homeAlertTitle}</div>
            <div className="text-xs mt-0.5" style={{ color: theme.textSecondary }}>{texts.homeAlertSubtitle}</div>
          </button>
          <button onClick={onDismissAlert} className="flex-shrink-0 hover:opacity-70">
            <X size={16} style={{ color: theme.textSecondary }} />
          </button>
        </div>
      )}

      <div>
        <div className="flex justify-between items-center mb-3">
          <h2 className="text-sm font-semibold" style={{ color: theme.text }}>{texts.homeReadinessTitle}</h2>
          <button onClick={onEditReadiness} className="text-xs font-medium hover:underline" style={{ color: theme.accent }}>
            {texts.homeReadinessEdit}
          </button>
        </div>
        <div className="grid grid-cols-2 gap-2">
          {[
            { icon: Package, label: texts.homeCardSupplyKit!, value: '82% stocked', color: theme.success },
            { icon: Map, label: texts.homeCardEvacPlan!, value: 'Route A set', color: theme.accent },
            { icon: Phone, label: texts.homeCardContacts!, value: '5 people', color: theme.warning },
            { icon: CheckCircle, label: texts.homeCardChecklist!, value: `${totalTasks - completedTasks} items left`, color: theme.danger },
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
          <h2 className="text-sm font-semibold" style={{ color: theme.text }}>{texts.homeTasksTitle}</h2>
          <button onClick={onSeeAllTasks} className="text-xs font-medium hover:underline" style={{ color: theme.accent }}>
            {texts.homeTasksSeeAll}
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
  texts: TextCustomization;
  onAddItem: (category: string) => void;
}

function KitScreen({ theme, kitItems, texts, onAddItem }: KitScreenProps) {
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
        return { bg: `${theme.success}20`, color: theme.success, text: texts.kitStatusOK! };
      case 'expired':
        return { bg: `${theme.warning}20`, color: theme.warning, text: texts.kitStatusExpired! };
      case 'low':
        return { bg: `${theme.warning}20`, color: theme.warning, text: texts.kitStatusLow! };
      case 'missing':
        return { bg: `${theme.danger}20`, color: theme.danger, text: texts.kitStatusMissing! };
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
        <div className="text-xs" style={{ color: theme.textSecondary }}>{texts.kitOverallReadiness}</div>
        <div className="h-2 rounded-full overflow-hidden" style={{ background: theme.border }}>
          <div className="h-full rounded-full transition-all duration-500" style={{ width: `${readinessPercent}%`, background: theme.success }} />
        </div>
        <div className="text-sm font-semibold" style={{ color: theme.success }}>{readinessPercent}%</div>
      </div>

      <div>
        <div className="flex justify-between items-center mb-3">
          <h2 className="text-sm font-semibold" style={{ color: theme.text }}>{texts.kitWaterFoodTitle}</h2>
          <button onClick={() => onAddItem('water-food')} className="text-xs font-medium hover:underline flex items-center gap-1" style={{ color: theme.accent }}>
            <Plus size={14} /> {texts.kitAddButton}
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
          <h2 className="text-sm font-semibold" style={{ color: theme.text }}>{texts.kitMedicalTitle}</h2>
          <button onClick={() => onAddItem('medical')} className="text-xs font-medium hover:underline flex items-center gap-1" style={{ color: theme.accent }}>
            <Plus size={14} /> {texts.kitAddButton}
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
            <h2 className="text-sm font-semibold" style={{ color: theme.text }}>{texts.kitToolsTitle}</h2>
            <button onClick={() => onAddItem('tools')} className="text-xs font-medium hover:underline flex items-center gap-1" style={{ color: theme.accent }}>
              <Plus size={14} /> {texts.kitAddButton}
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
  texts: TextCustomization;
  onSOSPress: () => void;
  onCall: (contact: Contact) => void;
  onManageContacts: () => void;
  onNationalEmergency: () => void;
}

function SOSScreen({
  theme,
  contacts,
  texts,
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
          <span className="text-xs font-bold">{texts.sosButtonText}</span>
        </button>
        <p className="text-xs" style={{ color: theme.textSecondary }}>{texts.sosButtonSubtitle}</p>
      </div>

      <div>
        <div className="flex justify-between items-center mb-3">
          <h2 className="text-sm font-semibold" style={{ color: theme.text }}>{texts.sosContactsTitle}</h2>
          <button onClick={onManageContacts} className="text-xs font-medium hover:underline" style={{ color: theme.accent }}>
            {texts.sosManageButton}
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
          {texts.sosNationalTitle}
        </div>
        <div className="text-xs" style={{ color: theme.textSecondary }}>{texts.sosNationalSubtitle}</div>
      </button>
    </div>
  );
}

interface PlanScreenProps {
  theme: typeof themes.modern;
  plans: EvacPlan[];
  texts: TextCustomization;
  onEditPlans: () => void;
  onViewDetails: (plan: EvacPlan) => void;
}

function PlanScreen({ theme, plans, texts, onEditPlans, onViewDetails }: PlanScreenProps) {
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
          <h2 className="text-sm font-semibold" style={{ color: theme.text }}>{texts.planDisasterTitle}</h2>
          <button onClick={onEditPlans} className="text-xs font-medium hover:underline" style={{ color: theme.accent }}>
            {texts.planEditAll}
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

interface SettingsScreenProps {
  theme: typeof themes.modern;
  currentTheme: Theme;
  currentLanguage: Language;
  texts: TextCustomization;
  onThemeSelect: (theme: Theme) => void;
  onLanguageSelect: (language: Language) => void;
}

function SettingsScreen({
  theme,
  currentTheme,
  currentLanguage,
  texts,
  onThemeSelect,
  onLanguageSelect,
}: SettingsScreenProps) {
  const themeOptions = [
    { id: 'modern' as Theme, name: 'Modern Minimal', preview: themes.modern.primary },
    { id: 'bold' as Theme, name: 'Bold Urgent', preview: themes.bold.primary },
    { id: 'calm' as Theme, name: 'Calm Professional', preview: themes.calm.primary },
    { id: 'vibrant' as Theme, name: 'Vibrant Friendly', preview: themes.vibrant.primary },
  ];

  const languageOptions = [
    { id: 'en' as Language, name: 'English', flag: '🇬🇧' },
    { id: 'uk' as Language, name: 'Українська', flag: '🇺🇦' },
  ];

  return (
    <div className="p-4 space-y-6">
      {/* Appearance Section */}
      <div>
        <h2 className="text-sm font-semibold mb-3" style={{ color: theme.text }}>
          {currentLanguage === 'en' ? 'Appearance' : 'Зовнішній вигляд'}
        </h2>
        <p className="text-xs mb-4" style={{ color: theme.textSecondary }}>
          {currentLanguage === 'en' ? 'Choose your color theme' : 'Виберіть свою кольорову тему'}
        </p>
        <div className="space-y-2">
          {themeOptions.map((themeOption) => (
            <button
              key={themeOption.id}
              onClick={() => onThemeSelect(themeOption.id)}
              className="w-full rounded-lg p-3 flex items-center gap-3 transition-all hover:opacity-90"
              style={{
                background: currentTheme === themeOption.id ? theme.bgSecondary : theme.bg,
                border: `1.5px solid ${currentTheme === themeOption.id ? theme.primary : theme.border}`,
              }}
            >
              <div
                className="w-10 h-10 rounded-lg flex-shrink-0"
                style={{ background: themeOption.preview }}
              />
              <div className="flex-1 text-left">
                <div className="text-sm font-medium" style={{ color: theme.text }}>
                  {themeOption.name}
                </div>
              </div>
              {currentTheme === themeOption.id && (
                <CheckCircle size={20} style={{ color: theme.primary }} />
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Language Section */}
      <div>
        <h2 className="text-sm font-semibold mb-3" style={{ color: theme.text }}>
          {currentLanguage === 'en' ? 'Language' : 'Мова'}
        </h2>
        <p className="text-xs mb-4" style={{ color: theme.textSecondary }}>
          {currentLanguage === 'en' ? 'Select your preferred language' : 'Виберіть бажану мову'}
        </p>
        <div className="space-y-2">
          {languageOptions.map((langOption) => (
            <button
              key={langOption.id}
              onClick={() => onLanguageSelect(langOption.id)}
              className="w-full rounded-lg p-3 flex items-center gap-3 transition-all hover:opacity-90"
              style={{
                background: currentLanguage === langOption.id ? theme.bgSecondary : theme.bg,
                border: `1.5px solid ${currentLanguage === langOption.id ? theme.primary : theme.border}`,
              }}
            >
              <div className="text-2xl flex-shrink-0">{langOption.flag}</div>
              <div className="flex-1 text-left">
                <div className="text-sm font-medium" style={{ color: theme.text }}>
                  {langOption.name}
                </div>
              </div>
              {currentLanguage === langOption.id && (
                <CheckCircle size={20} style={{ color: theme.primary }} />
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Info Section */}
      <div className="rounded-lg p-3" style={{ background: theme.bgSecondary, border: `1px solid ${theme.border}` }}>
        <div className="text-xs" style={{ color: theme.textSecondary }}>
          <p className="mb-2">
            {currentLanguage === 'en'
              ? 'Changes will be applied immediately to all screens.'
              : 'Зміни будуть застосовані негайно до всіх екранів.'}
          </p>
          <p>
            {currentLanguage === 'en'
              ? 'Your preferences are saved automatically.'
              : 'Ваші налаштування зберігаються автоматично.'}
          </p>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// MAIN SAFEREADY COMPONENT
// ============================================================================

export interface SafeReadyProps {
  initialTheme?: Theme;
  initialScreen?: Screen;
  initialLanguage?: Language;
  showThemeSwitcher?: boolean;
  customTexts?: Partial<TextCustomization>;

  // Customizable Data
  initialTasks?: Task[];
  initialKitItems?: KitItem[];
  initialContacts?: Contact[];
  initialPlans?: EvacPlan[];
  showAlert?: boolean;

  // Event Handlers
  onThemeChange?: (theme: Theme) => void;
  onScreenChange?: (screen: Screen) => void;
  onLanguageChange?: (language: Language) => void;
  onTasksChange?: (tasks: Task[]) => void;
  onKitItemsChange?: (items: KitItem[]) => void;
  onContactsChange?: (contacts: Contact[]) => void;
  onPlansChange?: (plans: EvacPlan[]) => void;
}

export function SafeReady({
  initialTheme = 'modern',
  initialScreen = 'home',
  initialLanguage = 'en',
  showThemeSwitcher = true,
  customTexts = {},
  initialTasks: customInitialTasks,
  initialKitItems: customInitialKitItems,
  initialContacts: customInitialContacts,
  initialPlans: customInitialPlans,
  showAlert: customShowAlert = true,
  onThemeChange,
  onScreenChange,
  onLanguageChange,
  onTasksChange,
  onKitItemsChange,
  onContactsChange,
  onPlansChange,
}: SafeReadyProps) {
  const [theme, setTheme] = useState<Theme>(initialTheme);
  const [screen, setScreen] = useState<Screen>(initialScreen);
  const [language, setLanguage] = useState<Language>(initialLanguage);
  const [tasks, setTasks] = useState<Task[]>(customInitialTasks || initialTasks);
  const [kitItems, setKitItems] = useState<KitItem[]>(customInitialKitItems || initialKitItems);
  const [contacts, setContacts] = useState<Contact[]>(customInitialContacts || initialContacts);
  const [plans, setPlans] = useState<EvacPlan[]>(customInitialPlans || initialPlans);
  const [showAlert, setShowAlert] = useState(customShowAlert);

  const currentTheme = themes[theme];

  // Use custom texts if provided, otherwise use translation based on language
  const baseTexts = Object.keys(customTexts).length > 0 ? defaultTexts : translations[language];
  const texts: TextCustomization = { ...baseTexts, ...customTexts };

  const handleThemeChange = (newTheme: Theme) => {
    setTheme(newTheme);
    onThemeChange?.(newTheme);
    toast.success(language === 'en' ? `Theme changed to ${themes[newTheme].name}` : `Тему змінено на ${themes[newTheme].name}`);
  };

  const handleScreenChange = (newScreen: Screen) => {
    setScreen(newScreen);
    onScreenChange?.(newScreen);
  };

  const handleLanguageChange = (newLanguage: Language) => {
    setLanguage(newLanguage);
    onLanguageChange?.(newLanguage);
    toast.success(newLanguage === 'en' ? 'Language changed to English' : 'Мову змінено на Українську');
  };

  const toggleTask = (id: string) => {
    const updatedTasks = tasks.map(task => task.id === id ? { ...task, done: !task.done } : task);
    setTasks(updatedTasks);
    onTasksChange?.(updatedTasks);
    const task = tasks.find(t => t.id === id);
    if (task) {
      toast.success(task.done ? texts.toastTaskIncomplete : texts.toastTaskComplete);
    }
  };

  const handleSOSPress = () => {
    toast.error(texts.toastSOSAlert);
  };

  const handleCall = (contact: Contact) => {
    toast.success(`${texts.toastCalling} ${contact.name} at ${contact.phone}...`);
  };

  const handleEditReadiness = () => {
    toast.info(texts.toastEditReadiness);
  };

  const handleSeeAllTasks = () => {
    toast.info(texts.toastViewAllTasks);
  };

  const handleAddKitItem = (category: string) => {
    toast.info(`${texts.toastAddItem} ${category} item`);
  };

  const handleManageContacts = () => {
    toast.info(texts.toastManageContacts);
  };

  const handleEditPlans = () => {
    toast.info(texts.toastEditPlans);
  };

  const handleViewPlanDetails = (plan: EvacPlan) => {
    toast.info(`${texts.toastViewDetails} ${plan.title}`);
  };

  const handleAlertClick = () => {
    toast.warning(texts.toastAlertDetails);
  };

  const handleNationalEmergency = () => {
    toast.error(texts.toastNationalEmergency);
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4" style={{ background: currentTheme.bgSecondary }}>
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

      <div className="w-full max-w-sm" style={{ background: currentTheme.border, borderRadius: '32px', padding: '12px' }}>
        <div className="overflow-hidden rounded-3xl shadow-2xl" style={{ background: currentTheme.bg }}>
          <div className="px-6 py-2 flex justify-between items-center text-xs font-medium" style={{ background: currentTheme.primary, color: '#fff' }}>
            <span>9:41</span>
            <span>100%</span>
          </div>

          <div className="px-6 py-4" style={{ background: currentTheme.primary, color: '#fff' }}>
            <h1 className="text-xl font-bold">{texts.appName}</h1>
            <p className="text-xs opacity-80 mt-0.5">{texts.appLocation}</p>
          </div>

          <div className="min-h-[500px]" style={{ background: currentTheme.bg }}>
            {screen === 'home' && (
              <HomeScreen
                theme={currentTheme}
                tasks={tasks}
                showAlert={showAlert}
                texts={texts}
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
                texts={texts}
                onAddItem={handleAddKitItem}
              />
            )}
            {screen === 'sos' && (
              <SOSScreen
                theme={currentTheme}
                contacts={contacts}
                texts={texts}
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
                texts={texts}
                onEditPlans={handleEditPlans}
                onViewDetails={handleViewPlanDetails}
              />
            )}
            {screen === 'settings' && (
              <SettingsScreen
                theme={currentTheme}
                currentTheme={theme}
                currentLanguage={language}
                texts={texts}
                onThemeSelect={handleThemeChange}
                onLanguageSelect={handleLanguageChange}
              />
            )}
          </div>

          <div className="flex border-t" style={{ borderColor: currentTheme.border }}>
            {[
              { id: 'home' as Screen, icon: Home, label: texts.navHome! },
              { id: 'kit' as Screen, icon: Package, label: texts.navKit! },
              { id: 'sos' as Screen, icon: Phone, label: texts.navSOS! },
              { id: 'plan' as Screen, icon: Map, label: texts.navPlan! },
              { id: 'settings' as Screen, icon: Settings, label: texts.navSettings! },
            ].map(({ id, icon: Icon, label }) => (
              <button
                key={id}
                onClick={() => handleScreenChange(id)}
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
