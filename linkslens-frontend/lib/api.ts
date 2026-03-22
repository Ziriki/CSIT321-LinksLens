const API_BASE_URL =
  process.env.EXPO_PUBLIC_API_URL ?? "https://api.linkslens.com";

export interface ScanResponse {
  url: string;
  safety_score: number;
  verdict: "SAFE" | "DANGEROUS";
  threats: string[];
}

export async function scanUrl(url: string): Promise<ScanResponse> {
  const res = await fetch(`${API_BASE_URL}/scan`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });
  if (!res.ok) throw new Error(`Scan request failed: ${res.status}`);
  return res.json();
}
