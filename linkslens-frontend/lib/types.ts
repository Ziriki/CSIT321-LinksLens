
export type RiskLevel = 'safe' | 'suspicious' | 'malicious'

export type ScanStatus = 'SAFE' | 'SUSPICIOUS' | 'MALICIOUS' | 'UNAVAILABLE'

export function statusToRisk(status: string | null): RiskLevel {
  if (status === "SAFE") return "safe"
  if (status === "SUSPICIOUS") return "suspicious"
  return "malicious"
}

export function countScansThisMonth<T extends { ScannedAt: string }>(scans: T[]): number {
  const now = new Date()
  return scans.filter((s) => {
    const d = new Date(s.ScannedAt)
    return d.getMonth() === now.getMonth() && d.getFullYear() === now.getFullYear()
  }).length
}

export interface ScanResult {
  id: string
  url: string
  riskLevel: RiskLevel
  confidence: number
  scannedAt: string
  source: 'gallery' | 'manual'
  member?: string
  channel?: string
  riskFactors?: string[]
  technicalIndicators?: string[]
  analysisSummary?: string
}

export interface User {
  id: string
  name: string
  email: string
  avatar?: string
  scansThisMonth: number
  totalScans: number
}
