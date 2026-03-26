import * as SecureStore from "expo-secure-store";

const API_BASE_URL =
  process.env.EXPO_PUBLIC_API_URL ?? "https://api.linkslens.com";

const TOKEN_KEY = "access_token";

// ─── Token helpers ────────────────────────────────────────────────────────────

export async function saveToken(token: string): Promise<void> {
  await SecureStore.setItemAsync(TOKEN_KEY, token);
}

export async function getToken(): Promise<string | null> {
  return SecureStore.getItemAsync(TOKEN_KEY);
}

export async function clearToken(): Promise<void> {
  await SecureStore.deleteItemAsync(TOKEN_KEY);
}

async function authHeaders(): Promise<Record<string, string>> {
  const token = await getToken();
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

// ─── Auth ─────────────────────────────────────────────────────────────────────

export interface LoginResponse {
  access_token: string;
  token_type: string;
  message: string;
}

export async function login(email: string, password: string): Promise<LoginResponse> {
  const res = await fetch(`${API_BASE_URL}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      EmailAddress: email,
      Password: password,
      ClientType: "mobile",
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? `Login failed: ${res.status}`);
  }
  const data: LoginResponse = await res.json();
  await saveToken(data.access_token);
  return data;
}

export async function logout(): Promise<void> {
  await clearToken();
}

// ─── Scan ─────────────────────────────────────────────────────────────────────

export interface ScanResponse {
  scan_id: number;
  initial_url: string;
  redirect_url: string | null;
  status_indicator: "SAFE" | "SUSPICIOUS" | "MALICIOUS";
  score: number;
  server_location: string | null;
  screenshot_url: string | null;
  brands: string[];
  tags: string[];
  result_url: string;
  gsb_flagged: boolean;
  gsb_threat_types: string[];
  scanned_at: string;
}

export async function scanUrl(url: string): Promise<ScanResponse> {
  const res = await fetch(`${API_BASE_URL}/scan`, {
    method: "POST",
    headers: await authHeaders(),
    body: JSON.stringify({ urls: url }),
  });
  if (!res.ok) throw new Error(`Scan request failed: ${res.status}`);
  const data = await res.json();
  // Backend returns an array; we submitted one URL so take the first result
  return Array.isArray(data) ? data[0] : data;
}
