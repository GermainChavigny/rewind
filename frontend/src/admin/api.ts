/** Phone admin client: the same origin as the TV UI, PIN sent when the server wants one. */

export type Cfg = Record<string, any>; // the config as the API returns it (secrets masked)

export interface Status {
  first_run: boolean;
  has_pin: boolean;
  channels: number;
  power: string;
  weather: boolean;
  library: boolean;
  version: string;
}

export class NeedsPin extends Error {}

const PIN_KEY = 'rewind-admin-pin';

export function savedPin(): string {
  try {
    return sessionStorage.getItem(PIN_KEY) ?? '';
  } catch {
    return '';
  }
}

export function rememberPin(pin: string): void {
  try {
    sessionStorage.setItem(PIN_KEY, pin);
  } catch {
    /* private mode: the PIN is simply asked again */
  }
}

async function call<T>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await fetch(path, {
    method,
    headers: {
      ...(body === undefined ? {} : { 'Content-Type': 'application/json' }),
      'X-Rewind-Pin': savedPin(),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (res.status === 401) throw new NeedsPin('PIN');
  if (!res.ok) {
    const data = await res.json().catch(() => null);
    const detail = data?.detail;
    const message =
      typeof detail === 'string'
        ? detail
        : Array.isArray(detail)
          ? detail.map((d: { loc: unknown[]; msg: string }) => `${d.loc.slice(1).join('.')}: ${d.msg}`).join('\n')
          : `${res.status}`;
    throw new Error(message);
  }
  return res.json() as Promise<T>;
}

export const adminApi = {
  status: () => call<Status>('GET', '/api/admin/status'),
  config: () => call<Cfg>('GET', '/api/admin/config'),
  save: (cfg: Cfg) => call<Cfg>('PUT', '/api/admin/config', cfg),
  startLearn: (action: string) => call<{ action: string | null }>('POST', '/api/admin/learn', { action }),
  learnState: () => call<{ action: string | null; key: string | null; waiting: boolean }>('GET', '/api/admin/learn'),
  cancelLearn: () => call<unknown>('DELETE', '/api/admin/learn'),
  completeSetup: () => call<unknown>('POST', '/api/admin/setup/complete'),
};

/** Turns a channel name into a stable id ("Making Of" → "making-of"). */
export function slug(name: string): string {
  return name
    .normalize('NFKD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 40) || 'channel';
}
