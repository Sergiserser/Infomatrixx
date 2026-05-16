export const STEP_PREP_API_BASE =
  import.meta.env.VITE_STEP_PREP_API_BASE ?? 'http://127.0.0.1:8080';

export interface StepPrepApiState {
  app: string;
  language: 'en' | 'uk';
  languageName: string;
  mode: 'demo' | 'real';
  demoMode: boolean;
  riskScore: number;
  riskState: string;
  alarmActive: boolean;
  alarmRemainingSeconds: number;
  alarmStatus: string;
  reason: string;
  message: string;
  cameraOnline: boolean;
  cameraError: string;
  emergencyContact: string;
  shelterStatus: string;
  shelters: Array<{
    id: string;
    name: string;
    address: string;
    distance: string;
    distanceKm: number | null;
    lat: number | null;
    lon: number | null;
    note: string;
    phone: string;
    source: string;
  }>;
  goBagItems: Array<{
    id: string;
    name: string;
    detail: string;
    checked: boolean;
  }>;
  events: Array<{
    id: string;
    type: 'motion' | 'sound' | 'gesture';
    timestamp: number;
    description: string;
    severity: 'low' | 'medium' | 'high';
  }>;
  urls: {
    snapshot: string;
    stream: string;
  };
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${STEP_PREP_API_BASE}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
  });
  if (!response.ok) {
    throw new Error(`StepPrep API ${response.status}: ${response.statusText}`);
  }
  return response.json() as Promise<T>;
}

export function getStepPrepStatus(): Promise<StepPrepApiState> {
  return requestJson<StepPrepApiState>('/api/status');
}

export function performStepPrepAction(action: string, payload: Record<string, unknown> = {}) {
  return requestJson<{ ok: boolean; message: string; state: StepPrepApiState }>('/api/actions', {
    method: 'POST',
    body: JSON.stringify({ action, ...payload }),
  });
}

export function setStepPrepLanguage(language: 'en' | 'uk') {
  return requestJson<{ ok: boolean; message: string; state: StepPrepApiState }>('/api/language', {
    method: 'POST',
    body: JSON.stringify({ language }),
  });
}

export function saveStepPrepGoBag(text: string) {
  return requestJson<{ ok: boolean; message: string; state: StepPrepApiState }>('/api/supplies', {
    method: 'POST',
    body: JSON.stringify({ text }),
  });
}
