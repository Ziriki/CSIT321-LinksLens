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

/** Decode JWT payload to extract user_id and role_id. */
export function decodeToken(token: string): { user_id: number; role_id: number } | null {
  try {
    const payload = token.split(".")[1];
    const json = JSON.parse(atob(payload));
    return { user_id: Number(json.sub), role_id: Number(json.role) };
  } catch {
    return null;
  }
}

/** Get the current user's ID from the stored JWT. */
export async function getCurrentUserId(): Promise<number | null> {
  const token = await getToken();
  if (!token) return null;
  return decodeToken(token)?.user_id ?? null;
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

export async function signup(
  fullName: string,
  email: string,
  password: string,
): Promise<void> {
  const res = await fetch(`${API_BASE_URL}/api/accounts/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ EmailAddress: email, Password: password, FullName: fullName }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? `Signup failed: ${res.status}`);
  }
}

export async function logout(): Promise<void> {
  await clearToken();
}

// ─── User Profile ─────────────────────────────────────────────────────────────

export interface UserAccount {
  UserID: number;
  EmailAddress: string;
  RoleID: number;
  IsActive: boolean;
}

export interface UserDetails {
  UserID: number;
  FullName: string | null;
  PhoneNumber: string | null;
  Address: string | null;
  Gender: string | null;
  DateOfBirth: string | null;
}

export async function fetchAccount(userId: number): Promise<UserAccount> {
  const res = await fetch(`${API_BASE_URL}/api/accounts/${userId}`, {
    headers: await authHeaders(),
  });
  if (!res.ok) throw new Error(`Failed to fetch account: ${res.status}`);
  return res.json();
}

export async function fetchDetails(userId: number): Promise<UserDetails> {
  const res = await fetch(`${API_BASE_URL}/api/details/${userId}`, {
    headers: await authHeaders(),
  });
  if (!res.ok) throw new Error(`Failed to fetch details: ${res.status}`);
  return res.json();
}

export async function updateDetails(
  userId: number,
  data: Partial<Pick<UserDetails, "FullName" | "PhoneNumber" | "Address" | "Gender" | "DateOfBirth">>,
): Promise<void> {
  const res = await fetch(`${API_BASE_URL}/api/details/${userId}`, {
    method: "PUT",
    headers: await authHeaders(),
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(`Failed to update details: ${res.status}`);
}

// ─── Scan ─────────────────────────────────────────────────────────────────────

export interface ScanResponse {
  scan_id: number;
  user_id: number;
  uuid: string | null;
  initial_url: string;
  redirect_url: string | null;
  status_indicator: "SAFE" | "SUSPICIOUS" | "MALICIOUS";
  score: number;
  server_location: string | null;
  ip_address: string | null;
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
  const result = Array.isArray(data) ? data[0] : data;
  if (!result) throw new Error("No scan result returned from server.");
  return result;
}

// ─── Scan History ─────────────────────────────────────────────────────────────

export interface ScanHistoryItem {
  ScanID: number;
  UserID: number;
  FullName: string | null;
  InitialURL: string;
  RedirectURL: string | null;
  StatusIndicator: string | null;
  DomainAgeDays: number | null;
  ServerLocation: string | null;
  ScreenshotURL: string | null;
  RawText: string | null;
  AssociatedPerson: string | null;
  ScannedAt: string;
}

export async function fetchScanHistory(): Promise<ScanHistoryItem[]> {
  const res = await fetch(`${API_BASE_URL}/api/scans/`, {
    headers: await authHeaders(),
  });
  if (!res.ok) throw new Error(`Failed to fetch scan history: ${res.status}`);
  return res.json();
}

export async function deleteScan(scanId: number): Promise<void> {
  const res = await fetch(`${API_BASE_URL}/api/scans/${scanId}`, {
    method: "DELETE",
    headers: await authHeaders(),
  });
  if (!res.ok) throw new Error(`Failed to delete scan: ${res.status}`);
}

export async function clearScanHistory(userId: number): Promise<void> {
  const res = await fetch(`${API_BASE_URL}/api/scans/clear/${userId}`, {
    method: "DELETE",
    headers: await authHeaders(),
  });
  if (!res.ok) throw new Error(`Failed to clear scan history: ${res.status}`);
}

// ─── Feedback ─────────────────────────────────────────────────────────────────

export async function submitAppFeedback(userId: number, feedback: string): Promise<void> {
  const res = await fetch(`${API_BASE_URL}/api/feedback/`, {
    method: "POST",
    headers: await authHeaders(),
    body: JSON.stringify({ UserID: userId, Feedback: feedback }),
  });
  if (!res.ok) throw new Error(`Failed to submit feedback: ${res.status}`);
}

export async function submitScanFeedback(
  scanId: number,
  userId: number,
  suggestedStatus: "SAFE" | "SUSPICIOUS" | "MALICIOUS",
  comments: string,
): Promise<void> {
  const res = await fetch(`${API_BASE_URL}/api/scan-feedback/`, {
    method: "POST",
    headers: await authHeaders(),
    body: JSON.stringify({
      ScanID: scanId,
      UserID: userId,
      SuggestedStatus: suggestedStatus,
      Comments: comments,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? `Failed to submit report: ${res.status}`);
  }
}
