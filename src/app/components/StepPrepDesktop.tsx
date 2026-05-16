import { useState, useRef, useEffect } from 'react';
import { Camera, MapPin, Package, Settings, AlertTriangle, Phone, Globe, User, Shield, Volume2, Hand, Zap, Clock, CheckCircle, XCircle, Plus, Trash2, Save, Search, Edit, X, MessageSquare } from 'lucide-react';
import { toast } from 'sonner';
import { STEP_PREP_API_BASE, getStepPrepStatus, type StepPrepApiState } from '../api/stepPrepApi';

type Language = 'en' | 'uk';
type TabType = 'monitoring' | 'shelter' | 'gobag' | 'settings';

interface Translation {
  monitoring: string;
  shelter: string;
  goBag: string;
  settings: string;
  riskScore: string;
  alarmStatus: string;
  active: string;
  inactive: string;
  demoMode: string;
  emergencyContact: string;
  detectionSystems: string;
  camera: string;
  microphone: string;
  gesture: string;
  motion: string;
  sound: string;
  emergency: string;
  recentEvents: string;
  noEvents: string;
  findShelters: string;
  searchingShelters: string;
  nearbyShelters: string;
  openInMaps: string;
  noSheltersFound: string;
  distance: string;
  emergencySupplies: string;
  addItem: string;
  saveList: string;
  itemName: string;
  language: string;
  emergencyContacts: string;
  contactName: string;
  phoneNumber: string;
  location: string;
  demoModeLabel: string;
  enableDemo: string;
  testAlarm: string;
  currentLocation: string;
  last24Hours: string;
  addContact: string;
  editContact: string;
  deleteContact: string;
  callContact: string;
  messageContact: string;
  addNewContact: string;
  saveContact: string;
  cancel: string;
  gestureList: string;
  rescueGestures: string;
  closeGestures: string;
}

export const translations: Record<Language, Translation> = {
  en: {
    monitoring: 'Monitoring',
    shelter: 'Shelter',
    goBag: 'Go Bag',
    settings: 'Settings',
    riskScore: 'Risk Score',
    alarmStatus: 'Alarm Status',
    active: 'Active',
    inactive: 'Inactive',
    demoMode: 'Demo Mode Enabled',
    emergencyContact: 'Emergency Contact',
    detectionSystems: 'Detection Systems',
    camera: 'Camera',
    microphone: 'Microphone',
    gesture: 'Gesture',
    motion: 'Motion Detection',
    sound: 'Sound Detection',
    emergency: 'Emergency',
    recentEvents: 'Recent Events',
    noEvents: 'No events detected in the last 24 hours',
    findShelters: 'Find Nearby Shelters',
    searchingShelters: 'Searching for shelters...',
    nearbyShelters: 'Nearby Emergency Shelters',
    openInMaps: 'Open in Maps',
    noSheltersFound: 'No shelters found nearby',
    distance: 'Distance',
    emergencySupplies: 'Emergency Supplies Checklist',
    addItem: 'Add Item',
    saveList: 'Save List',
    itemName: 'Item name...',
    language: 'Language',
    emergencyContacts: 'Emergency Contacts',
    contactName: 'Contact Name',
    phoneNumber: 'Phone Number',
    location: 'Location',
    demoModeLabel: 'Demo Mode',
    enableDemo: 'Enable safe testing mode',
    testAlarm: 'Test Alarm',
    currentLocation: 'Current Location',
    last24Hours: 'Last 24 Hours',
    addContact: 'Add Contact',
    editContact: 'Edit',
    deleteContact: 'Delete',
    callContact: 'Call',
    messageContact: 'Message',
    addNewContact: 'Add New Contact',
    saveContact: 'Save',
    cancel: 'Cancel',
    gestureList: 'Gesture List',
    rescueGestures: 'Emergency Rescue Gestures',
    closeGestures: 'Close',
  },
  uk: {
    monitoring: 'Моніторинг',
    shelter: 'Укриття',
    goBag: 'Тривожна валіза',
    settings: 'Налаштування',
    riskScore: 'Рівень ризику',
    alarmStatus: 'Статус тривоги',
    active: 'Активна',
    inactive: 'Неактивна',
    demoMode: 'Демо-режим увімкнено',
    emergencyContact: 'Екстрений контакт',
    detectionSystems: 'Системи виявлення',
    camera: 'Камера',
    microphone: 'Мікрофон',
    gesture: 'Жести',
    motion: 'Виявлення руху',
    sound: 'Виявлення звуку',
    emergency: 'Екстрений виклик',
    recentEvents: 'Останні події',
    noEvents: 'Жодних подій за останні 24 години',
    findShelters: 'Знайти укриття поблизу',
    searchingShelters: 'Пошук укриттів...',
    nearbyShelters: 'Найближчі укриття',
    openInMaps: 'Відкрити на карті',
    noSheltersFound: 'Укриття не знайдено',
    distance: 'Відстань',
    emergencySupplies: 'Список екстрених припасів',
    addItem: 'Додати',
    saveList: 'Зберегти',
    itemName: 'Назва предмету...',
    language: 'Мова',
    emergencyContacts: 'Екстрені контакти',
    contactName: "Ім'я контакту",
    phoneNumber: 'Номер телефону',
    location: 'Розташування',
    demoModeLabel: 'Демо-режим',
    enableDemo: 'Увімкнути безпечний тестовий режим',
    testAlarm: 'Тестова тривога',
    currentLocation: 'Поточне розташування',
    last24Hours: 'Останні 24 години',
    addContact: 'Додати контакт',
    editContact: 'Редагувати',
    deleteContact: 'Видалити',
    callContact: 'Подзвонити',
    messageContact: 'Повідомлення',
    addNewContact: 'Додати новий контакт',
    saveContact: 'Зберегти',
    cancel: 'Скасувати',
    gestureList: 'Список жестів',
    rescueGestures: 'Екстрені рятувальні жести',
    closeGestures: 'Закрити',
  },
};

interface Shelter {
  id: string;
  name: string;
  distance: string;
  address: string;
  lat: number;
  lon: number;
}

interface GoBagItem {
  id: string;
  name: string;
  checked: boolean;
}

interface EmergencyContact {
  id: string;
  name: string;
  phone: string;
}

interface DetectionEvent {
  id: string;
  type: 'motion' | 'sound' | 'gesture';
  timestamp: Date;
  description: string;
  severity: 'low' | 'medium' | 'high';
}

interface PersistedStepPrepDesktopState {
  activeTab?: TabType;
  language?: Language;
  demoMode?: boolean;
  shelters?: Shelter[];
  goBagItems?: GoBagItem[];
  emergencyContacts?: EmergencyContact[];
  recentEvents?: Array<Omit<DetectionEvent, 'timestamp'> & { timestamp: string }>;
}

const STEP_PREP_DESKTOP_STORAGE_KEY = 'stepprep.desktop.state.v1';

const DEFAULT_GO_BAG_ITEMS: GoBagItem[] = [
  { id: '1', name: 'Water (3 days supply)', checked: true },
  { id: '2', name: 'Non-perishable food', checked: true },
  { id: '3', name: 'First aid kit', checked: true },
  { id: '4', name: 'Flashlight + batteries', checked: false },
  { id: '5', name: 'Radio', checked: false },
  { id: '6', name: 'Important documents', checked: false },
  { id: '7', name: 'Medications', checked: false },
  { id: '8', name: 'Cash', checked: false },
];

const DEFAULT_EMERGENCY_CONTACTS: EmergencyContact[] = [
  { id: '1', name: 'Emergency Services', phone: '112' },
  { id: '2', name: 'Family Contact', phone: '+40 123 456 789' },
];

function loadPersistedDesktopState(): PersistedStepPrepDesktopState {
  if (typeof window === 'undefined') {
    return {};
  }

  try {
    const raw = window.localStorage.getItem(STEP_PREP_DESKTOP_STORAGE_KEY);
    if (!raw) {
      return {};
    }
    const parsed = JSON.parse(raw) as PersistedStepPrepDesktopState;
    return parsed && typeof parsed === 'object' ? parsed : {};
  } catch {
    return {};
  }
}

function serializeEvents(events: DetectionEvent[]): PersistedStepPrepDesktopState['recentEvents'] {
  return events.map((event) => ({
    ...event,
    timestamp: event.timestamp.toISOString(),
  }));
}

function deserializeEvents(events: PersistedStepPrepDesktopState['recentEvents']): DetectionEvent[] {
  if (!Array.isArray(events)) {
    return [];
  }

  return events.map((event) => ({
    ...event,
    timestamp: new Date(event.timestamp),
  }));
}

function apiEventsToDetectionEvents(state: StepPrepApiState): DetectionEvent[] {
  return state.events.map((event) => ({
    id: event.id,
    type: event.type,
    timestamp: new Date(event.timestamp * 1000),
    description: event.description,
    severity: event.severity,
  }));
}

function apiSheltersToShelters(state: StepPrepApiState): Shelter[] {
  return state.shelters.map((shelter) => ({
    id: shelter.id,
    name: shelter.name,
    distance: shelter.distance || (shelter.distanceKm !== null ? `${shelter.distanceKm.toFixed(2)} km` : ''),
    address: shelter.address,
    lat: shelter.lat ?? 0,
    lon: shelter.lon ?? 0,
  }));
}

export function StepPrepDesktop() {
  const persistedState = useRef(loadPersistedDesktopState()).current;
  const [activeTab, setActiveTab] = useState<TabType>(persistedState.activeTab ?? 'monitoring');
  const [language, setLanguage] = useState<Language>(persistedState.language ?? 'en');
  const [riskScore, setRiskScore] = useState(12);
  const [alarmActive, setAlarmActive] = useState(false);
  const [demoMode, setDemoMode] = useState(persistedState.demoMode ?? true);
  const [cameraActive, setCameraActive] = useState(false);
  const [videoStream, setVideoStream] = useState<MediaStream | null>(null);
  const [apiCameraActive, setApiCameraActive] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);

  const [shelters, setShelters] = useState<Shelter[]>(persistedState.shelters ?? []);
  const [searchingShelters, setSearchingShelters] = useState(false);

  const [goBagItems, setGoBagItems] = useState<GoBagItem[]>(persistedState.goBagItems ?? DEFAULT_GO_BAG_ITEMS);
  const [newItemName, setNewItemName] = useState('');

  const [emergencyContacts, setEmergencyContacts] = useState<EmergencyContact[]>(
    persistedState.emergencyContacts ?? DEFAULT_EMERGENCY_CONTACTS
  );

  const [newContactName, setNewContactName] = useState('');
  const [newContactPhone, setNewContactPhone] = useState('');
  const [editingContactId, setEditingContactId] = useState<string | null>(null);
  const [editContactName, setEditContactName] = useState('');
  const [editContactPhone, setEditContactPhone] = useState('');
  const [showGestureList, setShowGestureList] = useState(false);

  const [recentEvents, setRecentEvents] = useState<DetectionEvent[]>(
    deserializeEvents(persistedState.recentEvents)
  );

  const t = translations[language];

  useEffect(() => {
    const stateToSave: PersistedStepPrepDesktopState = {
      activeTab,
      language,
      demoMode,
      shelters,
      goBagItems,
      emergencyContacts,
      recentEvents: serializeEvents(recentEvents),
    };

    try {
      window.localStorage.setItem(STEP_PREP_DESKTOP_STORAGE_KEY, JSON.stringify(stateToSave));
    } catch {
      // Local storage can be unavailable in private/browser-restricted contexts.
    }
  }, [activeTab, language, demoMode, shelters, goBagItems, emergencyContacts, recentEvents]);

  // Camera activation
  const startCamera = async () => {
    try {
      const apiState = await getStepPrepStatus();
      setRiskScore(Math.round(apiState.riskScore));
      setAlarmActive(apiState.alarmActive);
      setRecentEvents(apiEventsToDetectionEvents(apiState));
      setShelters(apiSheltersToShelters(apiState));

      if (apiState.cameraOnline) {
        setApiCameraActive(true);
        setCameraActive(true);
        toast.success('Python camera stream active');
        return;
      }
    } catch {
      // Fall through to browser/demo camera if the Python API is not running.
    }

    setApiCameraActive(false);
    if (demoMode) {
      // In demo mode, just activate without real camera
      setCameraActive(true);
      toast.success('Demo camera feed activated (simulated)');
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 640, height: 480 }
      });
      setVideoStream(stream);
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
      setCameraActive(true);
      toast.success('Camera monitoring active');
    } catch (err) {
      toast.error('Camera access denied. Using demo mode instead.');
      setCameraActive(true);
      setDemoMode(true);
    }
  };

  const stopCamera = () => {
    setApiCameraActive(false);
    if (videoStream) {
      videoStream.getTracks().forEach(track => track.stop());
      setVideoStream(null);
    }
    setCameraActive(false);
    toast.info('Camera stopped');
  };

  // Shelter search
  const findShelters = async () => {
    setSearchingShelters(true);

    // Simulate geolocation and shelter search
    setTimeout(() => {
      const mockShelters: Shelter[] = [
        { id: '1', name: 'Liceul Teoretic No. 1', distance: '1.2 km', address: 'Str. Victoriei 45, Bucharest', lat: 44.4268, lon: 26.1025 },
        { id: '2', name: 'Metro Station Piața Unirii', distance: '2.3 km', address: 'Piața Unirii, Bucharest', lat: 44.4268, lon: 26.1025 },
        { id: '3', name: 'Community Center Parcul Cișmigiu', distance: '3.1 km', address: 'Parcul Cișmigiu, Bucharest', lat: 44.4368, lon: 26.0925 },
      ];
      setShelters(mockShelters);
      setSearchingShelters(false);
      toast.success(`Found ${mockShelters.length} shelters nearby`);
    }, 1500);
  };

  const openInMaps = (shelter: Shelter) => {
    const url = `https://www.google.com/maps/dir/?api=1&destination=${shelter.lat},${shelter.lon}`;
    window.open(url, '_blank');
    toast.info(`Opening ${shelter.name} in Google Maps`);
  };

  // Go Bag management
  const toggleItem = (id: string) => {
    setGoBagItems(items =>
      items.map(item => item.id === id ? { ...item, checked: !item.checked } : item)
    );
  };

  const addItem = () => {
    if (newItemName.trim()) {
      const newItem: GoBagItem = {
        id: Date.now().toString(),
        name: newItemName.trim(),
        checked: false,
      };
      setGoBagItems([...goBagItems, newItem]);
      setNewItemName('');
      toast.success('Item added to go bag list');
    }
  };

  const removeItem = (id: string) => {
    setGoBagItems(items => items.filter(item => item.id !== id));
    toast.info('Item removed');
  };

  const saveGoBagList = () => {
    toast.success('Go bag list saved successfully');
  };

  // Emergency contacts management
  const addContact = () => {
    if (newContactName.trim() && newContactPhone.trim()) {
      const newContact: EmergencyContact = {
        id: Date.now().toString(),
        name: newContactName.trim(),
        phone: newContactPhone.trim(),
      };
      setEmergencyContacts([...emergencyContacts, newContact]);
      setNewContactName('');
      setNewContactPhone('');
      toast.success('Emergency contact added');
    } else {
      toast.error('Please fill in both name and phone number');
    }
  };

  const startEditContact = (contact: EmergencyContact) => {
    setEditingContactId(contact.id);
    setEditContactName(contact.name);
    setEditContactPhone(contact.phone);
  };

  const saveEditContact = () => {
    if (editContactName.trim() && editContactPhone.trim()) {
      setEmergencyContacts(contacts =>
        contacts.map(contact =>
          contact.id === editingContactId
            ? { ...contact, name: editContactName.trim(), phone: editContactPhone.trim() }
            : contact
        )
      );
      setEditingContactId(null);
      setEditContactName('');
      setEditContactPhone('');
      toast.success('Contact updated');
    }
  };

  const cancelEdit = () => {
    setEditingContactId(null);
    setEditContactName('');
    setEditContactPhone('');
  };

  const deleteContact = (id: string) => {
    setEmergencyContacts(contacts => contacts.filter(contact => contact.id !== id));
    toast.info('Contact deleted');
  };

  const sendMessage = (contact: EmergencyContact) => {
    const emergencyMessage = language === 'en'
      ? 'EMERGENCY ALERT: I need immediate assistance. This is an automated message from StepPrep Emergency System.'
      : 'ТРИВОГА: Мені потрібна негайна допомога. Це автоматичне повідомлення від StepPrep Emergency System.';

    toast.success(
      <div>
        <div className="font-bold">Emergency Message Sent</div>
        <div className="text-xs mt-1">To: {contact.name} ({contact.phone})</div>
        <div className="text-xs mt-1 text-gray-300">Message: {emergencyMessage}</div>
      </div>,
      { duration: 5000 }
    );
  };

  // Test alarm
  const testAlarm = () => {
    if (demoMode) {
      setAlarmActive(true);
      setRiskScore(85);

      // Add test event
      const event: DetectionEvent = {
        id: Date.now().toString(),
        type: 'motion',
        timestamp: new Date(),
        description: 'Test alarm - sudden motion detected',
        severity: 'high',
      };
      setRecentEvents([event, ...recentEvents]);

      toast.warning('🚨 Test alarm triggered (Demo Mode)');

      setTimeout(() => {
        setAlarmActive(false);
        setRiskScore(12);
      }, 3000);
    } else {
      toast.error('Disable demo mode to test real alarms');
    }
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (videoStream) {
        videoStream.getTracks().forEach(track => track.stop());
      }
    };
  }, [videoStream]);

  useEffect(() => {
    if (!apiCameraActive) {
      return;
    }

    const interval = window.setInterval(async () => {
      try {
        const apiState = await getStepPrepStatus();
        setRiskScore(Math.round(apiState.riskScore));
        setAlarmActive(apiState.alarmActive);
        setRecentEvents(apiEventsToDetectionEvents(apiState));
        setShelters(apiSheltersToShelters(apiState));
        if (!apiState.cameraOnline) {
          setApiCameraActive(false);
          setCameraActive(false);
          toast.error(apiState.cameraError || 'Python camera stream unavailable');
        }
      } catch {
        setApiCameraActive(false);
        setCameraActive(false);
        toast.error('StepPrep API connection lost');
      }
    }, 1000);

    return () => window.clearInterval(interval);
  }, [apiCameraActive]);

  return (
    <div className="min-h-screen bg-[#0a0e17] text-white">
      {/* Header */}
      <div className="bg-[#111827] border-b border-[#1f2937] px-6 py-3 shadow-xl">
        <div className="max-w-[1800px] mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="p-2 bg-red-600 rounded-lg">
              <Shield className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight uppercase">StepPrep Emergency System</h1>
              <p className="text-xs text-gray-400 uppercase tracking-wider">Professional Monitoring Platform v2.1</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {demoMode && (
              <div className="flex items-center gap-2 px-4 py-2 bg-amber-900/30 border border-amber-600/50 rounded-lg">
                <AlertTriangle className="w-4 h-4 text-amber-500" />
                <span className="text-xs text-amber-500 uppercase tracking-wider font-semibold">{t.demoMode}</span>
              </div>
            )}

            <div className="flex items-center gap-2 px-4 py-2 bg-red-900/30 border border-red-600/50 rounded-lg">
              <Phone className="w-4 h-4 text-red-400" />
              <span className="text-xs uppercase tracking-wider font-semibold">{t.emergencyContact}: 112</span>
            </div>

            <button
              onClick={() => setLanguage(language === 'en' ? 'uk' : 'en')}
              className="flex items-center gap-2 px-4 py-2 bg-[#1f2937] hover:bg-[#374151] border border-[#374151] rounded-lg transition-colors"
            >
              <Globe className="w-4 h-4" />
              <span className="text-xs uppercase tracking-wider font-semibold">{language === 'en' ? 'EN' : 'UK'}</span>
            </button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-[1800px] mx-auto p-4">
        {/* Tabs */}
        <div className="flex gap-1 mb-4 bg-[#111827] border border-[#1f2937] p-1 rounded-lg">
          {[
            { id: 'monitoring' as TabType, label: t.monitoring, icon: Camera },
            { id: 'shelter' as TabType, label: t.shelter, icon: MapPin },
            { id: 'gobag' as TabType, label: t.goBag, icon: Package },
            { id: 'settings' as TabType, label: t.settings, icon: Settings },
          ].map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setActiveTab(id)}
              className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 font-semibold text-xs uppercase tracking-wider transition-all rounded-md ${
                activeTab === id
                  ? 'bg-red-600 text-white'
                  : 'bg-transparent text-gray-400 hover:bg-[#1f2937] hover:text-gray-200'
              }`}
            >
              <Icon className="w-4 h-4" />
              {label}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <div className="bg-[#111827] border border-[#1f2937] p-6 rounded-lg">
          {/* MONITORING TAB */}
          {activeTab === 'monitoring' && (
            <div className="space-y-4">
              {/* Top Stats */}
              <div className="grid grid-cols-4 gap-3">
                <div className="bg-[#0a0e17] border-2 border-[#1f2937] p-4 rounded-lg">
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-xs text-gray-400 uppercase tracking-wider font-semibold">{t.riskScore}</span>
                    <Zap className="w-5 h-5 text-cyan-400" />
                  </div>
                  <div className="text-4xl font-bold tracking-tight mb-1">{riskScore}<span className="text-xl text-gray-500">%</span></div>
                  <div className="flex items-center gap-2">
                    <div className={`w-2 h-2 rounded-full ${riskScore > 50 ? 'bg-red-500' : 'bg-green-500'}`}></div>
                    <span className={`text-xs uppercase tracking-wider font-semibold ${riskScore > 50 ? 'text-red-400' : 'text-green-400'}`}>
                      {riskScore > 50 ? 'ELEVATED' : 'NORMAL'}
                    </span>
                  </div>
                </div>

                <div className={`border-2 p-4 rounded-lg ${
                  alarmActive
                    ? 'bg-red-950/30 border-red-600'
                    : 'bg-[#0a0e17] border-[#1f2937]'
                }`}>
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-xs text-gray-400 uppercase tracking-wider font-semibold">{t.alarmStatus}</span>
                    <AlertTriangle className={`w-5 h-5 ${alarmActive ? 'text-red-500 animate-pulse' : 'text-gray-600'}`} />
                  </div>
                  <div className={`text-2xl font-bold tracking-tight uppercase ${alarmActive ? 'text-red-500' : 'text-gray-400'}`}>
                    {alarmActive ? t.active : t.inactive}
                  </div>
                  {alarmActive && (
                    <div className="mt-2 text-xs text-red-400 uppercase tracking-wider font-semibold">EMERGENCY DETECTED</div>
                  )}
                </div>

                <div className="bg-[#0a0e17] border-2 border-[#1f2937] p-4 rounded-lg">
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-xs text-gray-400 uppercase tracking-wider font-semibold">{t.camera}</span>
                    <Camera className="w-5 h-5 text-gray-400" />
                  </div>
                  <div className={`text-2xl font-bold tracking-tight uppercase mb-2 ${cameraActive ? 'text-green-500' : 'text-gray-500'}`}>
                    {cameraActive ? 'ONLINE' : 'OFFLINE'}
                  </div>
                  <button
                    onClick={cameraActive ? stopCamera : startCamera}
                    className={`w-full py-1.5 text-xs font-bold uppercase tracking-wider transition-colors rounded-md ${
                      cameraActive
                        ? 'bg-red-600 hover:bg-red-500 text-white'
                        : 'bg-[#1f2937] hover:bg-[#374151] text-gray-300'
                    }`}
                  >
                    {cameraActive ? 'STOP' : 'START'}
                  </button>
                </div>

                <div className="bg-[#0a0e17] border-2 border-[#1f2937] p-4 rounded-lg">
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-xs text-gray-400 uppercase tracking-wider font-semibold">{t.detectionSystems}</span>
                    <Shield className="w-5 h-5 text-gray-400" />
                  </div>
                  <div className="grid grid-cols-3 gap-2 mb-3">
                    <div className="text-center p-2 bg-green-950/30 border border-green-600/50 rounded-md">
                      <Camera className="w-4 h-4 mx-auto mb-1 text-green-500" />
                      <div className="text-xs text-green-400 font-semibold">CAM</div>
                    </div>
                    <div className="text-center p-2 bg-green-950/30 border border-green-600/50 rounded-md">
                      <Volume2 className="w-4 h-4 mx-auto mb-1 text-green-500" />
                      <div className="text-xs text-green-400 font-semibold">MIC</div>
                    </div>
                    <button
                      onClick={() => setShowGestureList(!showGestureList)}
                      className="text-center p-2 bg-green-950/30 border border-green-600/50 hover:bg-green-900/40 transition-colors rounded-md cursor-pointer"
                    >
                      <Hand className="w-4 h-4 mx-auto mb-1 text-green-500" />
                      <div className="text-xs text-green-400 font-semibold">GEST</div>
                    </button>
                  </div>
                  <button
                    onClick={() => setShowGestureList(!showGestureList)}
                    className="w-full py-1.5 text-xs font-bold uppercase tracking-wider bg-cyan-600 hover:bg-cyan-500 rounded-md transition-colors"
                  >
                    {t.gestureList}
                  </button>
                </div>
              </div>

              {/* Camera Feed and Events */}
              <div className="grid grid-cols-2 gap-3">
                {/* Camera Feed */}
                <div className="bg-black border-2 border-[#1f2937] overflow-hidden rounded-lg">
                  <div className="bg-[#0a0e17] px-4 py-2 border-b-2 border-[#1f2937] flex items-center justify-between">
                    <span className="font-bold text-xs uppercase tracking-wider">LIVE CAMERA FEED</span>
                    {cameraActive && (
                      <span className="flex items-center gap-2 text-xs text-red-500 font-bold uppercase tracking-wider">
                        <span className="w-2 h-2 bg-red-500 rounded-full animate-pulse"></span>
                        RECORDING
                      </span>
                    )}
                  </div>
                  <div className="aspect-video bg-black flex items-center justify-center relative border-t-2 border-[#1f2937]">
                    {cameraActive ? (
                      <>
                        {apiCameraActive ? (
                          <img
                            src={`${STEP_PREP_API_BASE}/api/stream`}
                            alt="Live camera feed"
                            className="w-full h-full object-cover"
                          />
                        ) : videoStream && !demoMode ? (
                          <video
                            ref={videoRef}
                            autoPlay
                            playsInline
                            muted
                            className="w-full h-full object-cover"
                          />
                        ) : (
                          <div className="w-full h-full bg-[#0a0e17] flex items-center justify-center relative overflow-hidden">
                            {/* Professional demo camera feed */}
                            <div className="absolute inset-0 opacity-5">
                              <div className="absolute inset-0 grid grid-cols-12 grid-rows-8 gap-px">
                                {Array.from({ length: 96 }).map((_, i) => (
                                  <div key={i} className="border border-cyan-500/20"></div>
                                ))}
                              </div>
                            </div>
                            <div className="absolute top-4 left-4 flex items-center gap-2 bg-red-600/90 px-3 py-1">
                              <div className="w-2 h-2 bg-white rounded-full animate-pulse"></div>
                              <span className="text-xs font-bold uppercase tracking-wider">REC</span>
                            </div>
                            <div className="absolute top-4 right-4 text-xs font-mono bg-black/80 px-3 py-1 border border-cyan-500/50">
                              {new Date().toLocaleTimeString()}
                            </div>
                            <div className="text-center z-10">
                              <Camera className="w-16 h-16 mx-auto mb-3 text-cyan-400 opacity-40" />
                              <p className="text-sm text-gray-400 uppercase tracking-wider font-semibold">DEMO CAMERA FEED</p>
                              <p className="text-xs text-gray-600 mt-1 uppercase tracking-wider">SIMULATED MONITORING</p>
                              <div className="mt-4 flex items-center justify-center gap-2 text-xs text-green-400 uppercase tracking-wider font-semibold">
                                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                                ALL SYSTEMS OPERATIONAL
                              </div>
                            </div>
                          </div>
                        )}
                      </>
                    ) : (
                      <div className="text-center text-gray-600">
                        <Camera className="w-16 h-16 mx-auto mb-3 opacity-20" />
                        <p className="text-sm uppercase tracking-wider font-semibold">CAMERA OFFLINE</p>
                        <p className="text-xs mt-1 uppercase tracking-wider">CLICK START TO ACTIVATE</p>
                      </div>
                    )}
                  </div>
                </div>

                {/* Recent Events */}
                <div className="bg-[#0a0e17] border-2 border-[#1f2937] rounded-lg">
                  <div className="bg-[#0a0e17] px-4 py-2 border-b-2 border-[#1f2937] flex items-center justify-between">
                    <span className="font-bold text-xs uppercase tracking-wider">{t.recentEvents}</span>
                    <Clock className="w-4 h-4 text-gray-500" />
                  </div>
                  <div className="p-3 max-h-[320px] overflow-y-auto space-y-2">
                    {recentEvents.length === 0 ? (
                      <div className="text-center text-gray-600 py-12">
                        <CheckCircle className="w-12 h-12 mx-auto mb-3 opacity-20" />
                        <p className="text-xs uppercase tracking-wider font-semibold">{t.noEvents}</p>
                      </div>
                    ) : (
                      recentEvents.map((event) => (
                        <div
                          key={event.id}
                          className={`p-3 border-l-4 ${
                            event.severity === 'high'
                              ? 'bg-red-950/30 border-red-600'
                              : event.severity === 'medium'
                              ? 'bg-amber-950/30 border-amber-600'
                              : 'bg-cyan-950/30 border-cyan-600'
                          }`}
                        >
                          <div className="flex items-start justify-between gap-2">
                            <div className="flex-1">
                              <div className="text-xs font-semibold uppercase tracking-wider mb-1">
                                {event.description}
                              </div>
                              <div className="text-xs text-gray-500 font-mono">
                                {event.timestamp.toLocaleTimeString()}
                              </div>
                            </div>
                            <div className={`p-1 ${
                              event.severity === 'high'
                                ? 'bg-red-600'
                                : event.severity === 'medium'
                                ? 'bg-amber-600'
                                : 'bg-cyan-600'
                            }`}>
                              {event.type === 'motion' && <Camera className="w-3 h-3" />}
                              {event.type === 'sound' && <Volume2 className="w-3 h-3" />}
                              {event.type === 'gesture' && <Hand className="w-3 h-3" />}
                            </div>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </div>

              {/* Gesture List Panel */}
              {showGestureList && (
                <div className="bg-[#0a0e17] border-2 border-cyan-600 p-6 rounded-lg">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-bold uppercase tracking-wider text-cyan-400">{t.rescueGestures}</h3>
                    <button
                      onClick={() => setShowGestureList(false)}
                      className="p-2 bg-red-600 hover:bg-red-500 rounded-lg transition-colors"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    {/* Gesture 1 */}
                    <div className="bg-cyan-950/20 border border-cyan-600/50 p-4 rounded-lg">
                      <div className="flex items-center gap-3 mb-2">
                        <div className="text-3xl">🆘</div>
                        <div>
                          <div className="font-bold text-sm uppercase tracking-wider">SOS Signal</div>
                          <div className="text-xs text-gray-400">Both hands raised above head</div>
                        </div>
                      </div>
                      <div className="text-xs text-gray-300 mt-2">
                        Universal distress signal - wave hands side to side
                      </div>
                    </div>

                    {/* Gesture 2 */}
                    <div className="bg-cyan-950/20 border border-cyan-600/50 p-4 rounded-lg">
                      <div className="flex items-center gap-3 mb-2">
                        <div className="text-3xl">🙋</div>
                        <div>
                          <div className="font-bold text-sm uppercase tracking-wider">Need Help</div>
                          <div className="text-xs text-gray-400">One hand raised high</div>
                        </div>
                      </div>
                      <div className="text-xs text-gray-300 mt-2">
                        Signal for non-critical assistance needed
                      </div>
                    </div>

                    {/* Gesture 3 */}
                    <div className="bg-cyan-950/20 border border-cyan-600/50 p-4 rounded-lg">
                      <div className="flex items-center gap-3 mb-2">
                        <div className="text-3xl">✋</div>
                        <div>
                          <div className="font-bold text-sm uppercase tracking-wider">Stop/Danger</div>
                          <div className="text-xs text-gray-400">Palm facing forward</div>
                        </div>
                      </div>
                      <div className="text-xs text-gray-300 mt-2">
                        Indicates immediate danger or stop motion
                      </div>
                    </div>

                    {/* Gesture 4 */}
                    <div className="bg-cyan-950/20 border border-cyan-600/50 p-4 rounded-lg">
                      <div className="flex items-center gap-3 mb-2">
                        <div className="text-3xl">👎</div>
                        <div>
                          <div className="font-bold text-sm uppercase tracking-wider">Injured</div>
                          <div className="text-xs text-gray-400">Thumbs down gesture</div>
                        </div>
                      </div>
                      <div className="text-xs text-gray-300 mt-2">
                        Signal that you or someone is injured
                      </div>
                    </div>

                    {/* Gesture 5 */}
                    <div className="bg-cyan-950/20 border border-cyan-600/50 p-4 rounded-lg">
                      <div className="flex items-center gap-3 mb-2">
                        <div className="text-3xl">👋</div>
                        <div>
                          <div className="font-bold text-sm uppercase tracking-wider">Attention</div>
                          <div className="text-xs text-gray-400">Rapid hand waving</div>
                        </div>
                      </div>
                      <div className="text-xs text-gray-300 mt-2">
                        Get attention of rescue personnel
                      </div>
                    </div>

                    {/* Gesture 6 */}
                    <div className="bg-cyan-950/20 border border-cyan-600/50 p-4 rounded-lg">
                      <div className="flex items-center gap-3 mb-2">
                        <div className="text-3xl">👍</div>
                        <div>
                          <div className="font-bold text-sm uppercase tracking-wider">OK/Safe</div>
                          <div className="text-xs text-gray-400">Thumbs up gesture</div>
                        </div>
                      </div>
                      <div className="text-xs text-gray-300 mt-2">
                        Signal that you are safe and okay
                      </div>
                    </div>
                  </div>

                  <div className="mt-4 p-3 bg-amber-950/30 border border-amber-600/50 rounded-lg">
                    <div className="text-xs text-amber-400 font-semibold uppercase tracking-wider mb-1">Important</div>
                    <div className="text-xs text-gray-300">
                      Make gestures clear and deliberate. Hold each gesture for 2-3 seconds. Repeat if not acknowledged by detection system.
                    </div>
                  </div>
                </div>
              )}

              {/* Test Alarm Button */}
              <div className="flex justify-center pt-2">
                <button
                  onClick={testAlarm}
                  disabled={!demoMode}
                  className="px-8 py-3 bg-red-600 hover:bg-red-500 border-2 border-red-700 font-bold uppercase tracking-wider text-sm transition-all disabled:opacity-30 disabled:cursor-not-allowed disabled:bg-gray-700 disabled:border-gray-600 rounded-lg"
                >
                  ⚠ {t.testAlarm}
                </button>
              </div>
            </div>
          )}

          {/* SHELTER TAB */}
          {activeTab === 'shelter' && (
            <div className="space-y-4">
              <div className="text-center bg-[#0a0e17] border-2 border-[#1f2937] p-8 rounded-lg">
                <h2 className="text-xl font-bold uppercase tracking-wider mb-2">{t.nearbyShelters}</h2>
                <p className="text-gray-500 mb-6 text-xs uppercase tracking-wider">EMERGENCY SHELTERS AND EVACUATION POINTS</p>

                <button
                  onClick={findShelters}
                  disabled={searchingShelters}
                  className="px-8 py-3 bg-cyan-600 hover:bg-cyan-500 border-2 border-cyan-700 font-bold uppercase tracking-wider text-sm transition-all disabled:opacity-50 disabled:bg-gray-700 disabled:border-gray-600 rounded-lg"
                >
                  {searchingShelters ? (
                    <span className="flex items-center gap-2">
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                      {t.searchingShelters}
                    </span>
                  ) : (
                    <span className="flex items-center gap-2">
                      <Search className="w-4 h-4" />
                      {t.findShelters}
                    </span>
                  )}
                </button>
              </div>

              {shelters.length > 0 && (
                <div className="grid grid-cols-1 gap-3">
                  {shelters.map((shelter) => (
                    <div
                      key={shelter.id}
                      className="bg-[#0a0e17] border-2 border-[#1f2937] p-4 hover:border-cyan-600 transition-all rounded-lg"
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-3 mb-2">
                            <div className="p-2 bg-cyan-600 rounded-lg">
                              <MapPin className="w-4 h-4 text-white" />
                            </div>
                            <h3 className="font-bold text-sm uppercase tracking-wider">{shelter.name}</h3>
                          </div>
                          <p className="text-gray-500 text-xs mb-3 uppercase tracking-wider">{shelter.address}</p>
                          <div className="flex items-center gap-2 text-xs">
                            <span className="px-3 py-1 bg-cyan-950/50 border border-cyan-600/50 text-cyan-400 uppercase tracking-wider font-semibold">
                              {t.distance}: {shelter.distance}
                            </span>
                          </div>
                        </div>
                        <button
                          onClick={() => openInMaps(shelter)}
                          className="px-4 py-2 bg-green-600 hover:bg-green-500 border-2 border-green-700 text-xs font-bold uppercase tracking-wider transition-colors rounded-lg"
                        >
                          {t.openInMaps}
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* GO BAG TAB */}
          {activeTab === 'gobag' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between bg-[#0a0e17] border-2 border-[#1f2937] p-4 rounded-lg">
                <h2 className="text-xl font-bold uppercase tracking-wider">{t.emergencySupplies}</h2>
                <button
                  onClick={saveGoBagList}
                  className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-500 border-2 border-green-700 font-bold text-xs uppercase tracking-wider transition-colors rounded-lg"
                >
                  <Save className="w-4 h-4" />
                  {t.saveList}
                </button>
              </div>

              <div className="flex gap-2 bg-[#0a0e17] border-2 border-[#1f2937] p-4 rounded-lg">
                <input
                  type="text"
                  value={newItemName}
                  onChange={(e) => setNewItemName(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && addItem()}
                  placeholder={t.itemName}
                  className="flex-1 px-4 py-2 bg-black border-2 border-[#1f2937] focus:border-cyan-600 focus:outline-none text-sm uppercase tracking-wider rounded-lg"
                />
                <button
                  onClick={addItem}
                  className="flex items-center gap-2 px-4 py-2 bg-cyan-600 hover:bg-cyan-500 border-2 border-cyan-700 font-bold text-xs uppercase tracking-wider transition-colors rounded-lg"
                >
                  <Plus className="w-4 h-4" />
                  {t.addItem}
                </button>
              </div>

              <div className="grid grid-cols-2 gap-3">
                {goBagItems.map((item) => (
                  <div
                    key={item.id}
                    className={`border-2 p-3 transition-all rounded-lg ${
                      item.checked ? 'border-green-600 bg-green-950/30' : 'border-[#1f2937] bg-[#0a0e17]'
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <label className="flex items-center gap-3 flex-1 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={item.checked}
                          onChange={() => toggleItem(item.id)}
                          className="w-4 h-4 accent-green-600"
                        />
                        <span className={`text-xs uppercase tracking-wider font-semibold ${item.checked ? 'line-through text-gray-600' : 'text-gray-300'}`}>
                          {item.name}
                        </span>
                      </label>
                      <button
                        onClick={() => removeItem(item.id)}
                        className="p-1 bg-red-600 hover:bg-red-500 transition-colors rounded"
                      >
                        <Trash2 className="w-3 h-3" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>

              <div className="bg-[#0a0e17] border-2 border-[#1f2937] p-4 rounded-lg">
                <div className="flex items-center justify-between mb-3">
                  <span className="font-bold uppercase tracking-wider text-sm">READINESS STATUS</span>
                  <span className="text-xs text-gray-500 uppercase tracking-wider font-semibold">
                    {goBagItems.filter(i => i.checked).length} / {goBagItems.length} ITEMS READY
                  </span>
                </div>
                <div className="bg-black h-6 border-2 border-[#1f2937] overflow-hidden">
                  <div
                    className="bg-green-600 h-full transition-all duration-300 flex items-center justify-center"
                    style={{ width: `${(goBagItems.filter(i => i.checked).length / goBagItems.length) * 100}%` }}
                  >
                    <span className="text-xs font-bold uppercase tracking-wider">
                      {Math.round((goBagItems.filter(i => i.checked).length / goBagItems.length) * 100)}%
                    </span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* SETTINGS TAB */}
          {activeTab === 'settings' && (
            <div className="space-y-4">
              <div className="bg-[#0a0e17] border-2 border-[#1f2937] p-4 rounded-lg">
                <h2 className="text-xl font-bold uppercase tracking-wider">{t.settings}</h2>
              </div>

              {/* Language */}
              <div className="bg-[#0a0e17] border-2 border-[#1f2937] p-6 rounded-lg">
                <label className="block font-bold text-xs uppercase tracking-wider mb-4 text-gray-400">{t.language}</label>
                <div className="grid grid-cols-2 gap-3">
                  <button
                    onClick={() => setLanguage('en')}
                    className={`py-3 font-bold text-xs uppercase tracking-wider transition-all border-2 rounded-lg ${
                      language === 'en'
                        ? 'bg-cyan-600 border-cyan-700 text-white'
                        : 'bg-transparent border-[#1f2937] text-gray-400 hover:border-gray-600'
                    }`}
                  >
                    English
                  </button>
                  <button
                    onClick={() => setLanguage('uk')}
                    className={`py-3 font-bold text-xs uppercase tracking-wider transition-all border-2 rounded-lg ${
                      language === 'uk'
                        ? 'bg-cyan-600 border-cyan-700 text-white'
                        : 'bg-transparent border-[#1f2937] text-gray-400 hover:border-gray-600'
                    }`}
                  >
                    Українська
                  </button>
                </div>
              </div>

              {/* Demo Mode */}
              <div className="bg-[#0a0e17] border-2 border-[#1f2937] p-6 rounded-lg">
                <label className="flex items-center justify-between cursor-pointer">
                  <div>
                    <div className="font-bold text-xs uppercase tracking-wider mb-1">{t.demoModeLabel}</div>
                    <div className="text-xs text-gray-500 uppercase tracking-wider">{t.enableDemo}</div>
                  </div>
                  <input
                    type="checkbox"
                    checked={demoMode}
                    onChange={(e) => setDemoMode(e.target.checked)}
                    className="w-16 h-8 appearance-none bg-[#1f2937] border-2 border-[#374151] rounded-full relative cursor-pointer transition-colors checked:bg-amber-600 checked:border-amber-700 before:content-[''] before:absolute before:w-6 before:h-6 before:rounded-full before:bg-white before:top-0.5 before:left-0.5 before:transition-transform checked:before:translate-x-8"
                  />
                </label>
              </div>

              {/* Emergency Contacts */}
              <div className="bg-[#0a0e17] border-2 border-[#1f2937] p-6 rounded-lg">
                <h3 className="font-bold text-xs uppercase tracking-wider mb-4 text-gray-400">{t.emergencyContacts}</h3>

                {/* Add New Contact */}
                <div className="mb-4 p-4 bg-black border-2 border-[#1f2937] rounded-lg">
                  <h4 className="text-xs font-bold uppercase tracking-wider mb-3 text-gray-500">{t.addNewContact}</h4>
                  <div className="grid grid-cols-2 gap-3 mb-3">
                    <input
                      type="text"
                      value={newContactName}
                      onChange={(e) => setNewContactName(e.target.value)}
                      placeholder={t.contactName}
                      className="px-3 py-2 bg-[#0a0e17] border-2 border-[#1f2937] focus:border-cyan-600 focus:outline-none text-xs uppercase tracking-wider rounded-lg"
                    />
                    <input
                      type="tel"
                      value={newContactPhone}
                      onChange={(e) => setNewContactPhone(e.target.value)}
                      placeholder={t.phoneNumber}
                      className="px-3 py-2 bg-[#0a0e17] border-2 border-[#1f2937] focus:border-cyan-600 focus:outline-none text-xs uppercase tracking-wider rounded-lg"
                    />
                  </div>
                  <button
                    onClick={addContact}
                    className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-cyan-600 hover:bg-cyan-500 border-2 border-cyan-700 font-bold text-xs uppercase tracking-wider transition-colors rounded-lg"
                  >
                    <Plus className="w-4 h-4" />
                    {t.addContact}
                  </button>
                </div>

                {/* Contacts List */}
                <div className="space-y-2">
                  {emergencyContacts.map((contact) => (
                    <div
                      key={contact.id}
                      className="p-3 bg-black border-2 border-[#1f2937] hover:border-gray-600 transition-colors rounded-lg"
                    >
                      {editingContactId === contact.id ? (
                        // Edit Mode
                        <div className="space-y-2">
                          <div className="grid grid-cols-2 gap-2">
                            <input
                              type="text"
                              value={editContactName}
                              onChange={(e) => setEditContactName(e.target.value)}
                              placeholder={t.contactName}
                              className="px-3 py-2 bg-[#0a0e17] border-2 border-[#1f2937] focus:border-cyan-600 focus:outline-none text-xs uppercase tracking-wider rounded-lg"
                            />
                            <input
                              type="tel"
                              value={editContactPhone}
                              onChange={(e) => setEditContactPhone(e.target.value)}
                              placeholder={t.phoneNumber}
                              className="px-3 py-2 bg-[#0a0e17] border-2 border-[#1f2937] focus:border-cyan-600 focus:outline-none text-xs uppercase tracking-wider rounded-lg"
                            />
                          </div>
                          <div className="flex gap-2">
                            <button
                              onClick={saveEditContact}
                              className="flex-1 flex items-center justify-center gap-1 px-3 py-2 bg-green-600 hover:bg-green-500 border-2 border-green-700 text-xs font-bold uppercase tracking-wider transition-colors rounded-lg"
                            >
                              <Save className="w-3 h-3" />
                              {t.saveContact}
                            </button>
                            <button
                              onClick={cancelEdit}
                              className="flex-1 flex items-center justify-center gap-1 px-3 py-2 bg-[#1f2937] hover:bg-[#374151] border-2 border-[#374151] text-xs font-bold uppercase tracking-wider transition-colors rounded-lg"
                            >
                              <X className="w-3 h-3" />
                              {t.cancel}
                            </button>
                          </div>
                        </div>
                      ) : (
                        // View Mode
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-3">
                            <div className="p-2 bg-cyan-600 rounded-lg">
                              <User className="w-5 h-5 text-white" />
                            </div>
                            <div>
                              <div className="font-bold text-xs uppercase tracking-wider">{contact.name}</div>
                              <div className="text-xs text-gray-500 font-mono">{contact.phone}</div>
                            </div>
                          </div>
                          <div className="flex items-center gap-1">
                            <button
                              onClick={() => toast.info(`Calling ${contact.phone}...`)}
                              className="p-2 bg-green-600 hover:bg-green-500 border-2 border-green-700 transition-colors rounded-lg"
                              title={t.callContact}
                            >
                              <Phone className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => sendMessage(contact)}
                              className="p-2 bg-blue-600 hover:bg-blue-500 border-2 border-blue-700 transition-colors rounded-lg"
                              title={t.messageContact}
                            >
                              <MessageSquare className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => startEditContact(contact)}
                              className="p-2 bg-cyan-600 hover:bg-cyan-500 border-2 border-cyan-700 transition-colors rounded-lg"
                              title={t.editContact}
                            >
                              <Edit className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => deleteContact(contact.id)}
                              className="p-2 bg-red-600 hover:bg-red-500 border-2 border-red-700 transition-colors rounded-lg"
                              title={t.deleteContact}
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// Export types for external use
export type { Language, TabType, Translation };
export type { Shelter, GoBagItem, EmergencyContact, DetectionEvent };
