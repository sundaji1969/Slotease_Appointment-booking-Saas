const KEY = "slotease.token";
let memoryToken: string | null = null;

export function getToken(): string | null {
  if (memoryToken) return memoryToken;
  try {
    memoryToken = localStorage.getItem(KEY);
  } catch {
    memoryToken = null;
  }
  return memoryToken;
}

export function setToken(token: string): void {
  memoryToken = token;
  try {
    localStorage.setItem(KEY, token);
  } catch {
    /* storage unavailable (private mode) — memory only */
  }
}

export function clearToken(): void {
  memoryToken = null;
  try {
    localStorage.removeItem(KEY);
  } catch {
    /* ignore */
  }
}
