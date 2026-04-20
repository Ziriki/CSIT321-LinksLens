import * as SecureStore from "expo-secure-store";
import { router } from "expo-router";
import { Alert } from "react-native";

const API_BASE_URL =
  process.env.EXPO_PUBLIC_API_URL ?? "https://api.linkslens.com";

const TOKEN_KEY = "access_token";

async function throwApiError(res: Response, msg: string): Promise<never> {
  const err = await res.json().catch(() => ({}));
  throw new Error((err as any).detail ?? `${msg}: ${res.status}`);
}

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

/**
 * Authenticated fetch wrapper. On 401 (expired/invalid token) it clears the
 * stored token and redirects to the login screen before throwing, so callers
 * never need to handle session expiry themselves.
 */
async function apiFetch(url: string, options: RequestInit = {}): Promise<Response> {
  const headers = await authHeaders();
  const res = await fetch(url, {
    ...options,
    headers: { ...headers, ...(options.headers as Record<string, string> ?? {}) },
  });
  if (res.status === 401) {
    await clearToken();
    Alert.alert(
      "Session Expired",
      "Your session has expired. Please log in again.",
      [{ text: "OK", onPress: () => router.replace("/") }]
    );
    throw new Error("Session expired. Please log in again.");
  }
  return res;
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
  if (!res.ok) await throwApiError(res, "Login failed");
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
  if (!res.ok) await throwApiError(res, "Signup failed");
}

export async function logout(): Promise<void> {
  try {
    await apiFetch(`${API_BASE_URL}/api/auth/logout`, { method: "POST" });
  } catch {
    // 401 (expired token) is already handled by apiFetch — it clears the token
    // and redirects to login. Any other error (network) is safe to ignore here.
  } finally {
    await clearToken();
  }
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
  const res = await apiFetch(`${API_BASE_URL}/api/accounts/${userId}`);
  if (!res.ok) throw new Error(`Failed to fetch account: ${res.status}`);
  return res.json();
}

export async function fetchDetails(userId: number): Promise<UserDetails> {
  const res = await apiFetch(`${API_BASE_URL}/api/details/${userId}`);
  if (!res.ok) throw new Error(`Failed to fetch details: ${res.status}`);
  return res.json();
}

export async function updateDetails(
  userId: number,
  data: Partial<Pick<UserDetails, "FullName" | "PhoneNumber" | "Address" | "Gender" | "DateOfBirth">>,
): Promise<void> {
  const res = await apiFetch(`${API_BASE_URL}/api/details/${userId}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(`Failed to update details: ${res.status}`);
}

// ─── Scan ─────────────────────────────────────────────────────────────────────

export interface ScriptAnalysis {
  total: number;
  trusted_count: number;
  ad_count: number;
  ad_heavy: boolean;
  crypto_miners: string[];
  malicious_scripts: string[];
  suspicious_patterns: { url: string; reason: string }[];
  tech_stack: { name: string; categories: string[] }[];
  script_risk_score: number;
}

export interface HomographAnalysis {
  is_homograph: boolean;
  risk_score: number;
  punycode: string | null;
  mixed_scripts: string[];
  confusable_chars: string[];
  details: string | null;
}

export interface SslInfo {
  issuer: string;
  subject: string | null;
  valid_from: string | null;
  valid_to: string | null;
  protocol: string;
}

export interface ScanResponse {
  scan_id: number;
  user_id: number;
  uuid: string | null;
  initial_url: string;
  redirect_url: string | null;
  redirect_chain: string[] | null;
  status_indicator: "SAFE" | "SUSPICIOUS" | "MALICIOUS" | "UNAVAILABLE";
  domain_age_days: number | null;
  server_location: string | null;
  ip_address: string | null;
  asn_name: string | null;
  page_title: string | null;
  apex_domain: string | null;
  screenshot_url: string | null;
  brands: string[];
  tags: string[];
  result_url: string;
  gsb_flagged: boolean;
  gsb_threat_types: string[];
  script_analysis: ScriptAnalysis | null;
  homograph_analysis: HomographAnalysis | null;
  ssl_info: SslInfo | null;
  scanned_at: string;
}

export async function scanUrl(url: string): Promise<ScanResponse> {
  const res = await apiFetch(`${API_BASE_URL}/scan`, {
    method: "POST",
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
  RedirectChain: string[] | null;
  StatusIndicator: string | null;
  DomainAgeDays: number | null;
  ServerLocation: string | null;
  IpAddress: string | null;
  AsnName: string | null;
  PageTitle: string | null;
  ApexDomain: string | null;
  SslInfo: SslInfo | null;
  ScreenshotURL: string | null;
  ScriptAnalysis: ScriptAnalysis | null;
  HomographAnalysis: HomographAnalysis | null;
  ScannedAt: string;
}

export function scanHistoryToResponse(scan: ScanHistoryItem): ScanResponse {
  return {
    scan_id: scan.ScanID,
    user_id: scan.UserID,
    uuid: null,
    initial_url: scan.InitialURL,
    redirect_url: scan.RedirectURL,
    redirect_chain: scan.RedirectChain ?? null,
    status_indicator: (scan.StatusIndicator ?? "UNAVAILABLE") as ScanResponse["status_indicator"],
    domain_age_days: scan.DomainAgeDays ?? null,
    server_location: scan.ServerLocation,
    ip_address: scan.IpAddress ?? null,
    asn_name: scan.AsnName ?? null,
    page_title: scan.PageTitle ?? null,
    apex_domain: scan.ApexDomain ?? null,
    screenshot_url: scan.ScreenshotURL,
    brands: [],
    tags: [],
    result_url: "",
    gsb_flagged: false,
    gsb_threat_types: [],
    script_analysis: scan.ScriptAnalysis ?? null,
    homograph_analysis: scan.HomographAnalysis ?? null,
    ssl_info: scan.SslInfo ?? null,
    scanned_at: scan.ScannedAt,
  }
}

export async function fetchScanHistory(): Promise<ScanHistoryItem[]> {
  const res = await apiFetch(`${API_BASE_URL}/api/scans/`);
  if (!res.ok) throw new Error(`Failed to fetch scan history: ${res.status}`);
  return res.json();
}

export async function fetchScanById(scanId: number): Promise<ScanHistoryItem> {
  const res = await apiFetch(`${API_BASE_URL}/api/scans/${scanId}`);
  if (!res.ok) throw new Error(`Failed to fetch scan: ${res.status}`);
  return res.json();
}

export async function deleteScan(scanId: number): Promise<void> {
  const res = await apiFetch(`${API_BASE_URL}/api/scans/${scanId}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`Failed to delete scan: ${res.status}`);
}

export async function clearScanHistory(userId: number): Promise<void> {
  const res = await apiFetch(`${API_BASE_URL}/api/scans/clear/${userId}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`Failed to clear scan history: ${res.status}`);
}

// ─── Preferences ──────────────────────────────────────────────────────────────

export const PREF_HAS_SEEN_ONBOARDING = "has_seen_onboarding"

export async function fetchPreferences(userId: number): Promise<Record<string, string>> {
  const res = await apiFetch(`${API_BASE_URL}/api/preferences/${userId}`);
  if (res.status === 404) return {};
  if (!res.ok) throw new Error(`Failed to fetch preferences: ${res.status}`);
  const data = await res.json();
  return data.Preferences ?? {};
}

export async function updatePreferences(userId: number, patch: Record<string, string>, currentPrefs?: Record<string, string>): Promise<void> {
  // Merge with existing prefs so saving one key never wipes the others.
  // Callers that already have fresh prefs can pass them to skip the extra GET.
  const current = currentPrefs ?? await fetchPreferences(userId);
  const merged = { ...current, ...patch };
  const res = await apiFetch(`${API_BASE_URL}/api/preferences/${userId}`, {
    method: "PUT",
    body: JSON.stringify({ Preferences: merged }),
  });
  if (res.status === 404) {
    // No preferences row exists yet — create it
    const createRes = await apiFetch(`${API_BASE_URL}/api/preferences/`, {
      method: "POST",
      body: JSON.stringify({ UserID: userId, Preferences: merged }),
    });
    if (!createRes.ok) throw new Error(`Failed to create preferences: ${createRes.status}`);
    return;
  }
  if (!res.ok) throw new Error(`Failed to update preferences: ${res.status}`);
}

// ─── Feedback ─────────────────────────────────────────────────────────────────

export async function submitAppFeedback(userId: number, feedback: string): Promise<void> {
  const res = await apiFetch(`${API_BASE_URL}/api/feedback/`, {
    method: "POST",
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
  const res = await apiFetch(`${API_BASE_URL}/api/scan-feedback/`, {
    method: "POST",
    body: JSON.stringify({
      ScanID: scanId,
      UserID: userId,
      SuggestedStatus: suggestedStatus,
      Comments: comments,
    }),
  });
  if (!res.ok) await throwApiError(res, "Failed to submit report");
}
