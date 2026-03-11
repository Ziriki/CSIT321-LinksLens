
export type RiskLevel = 'safe' | 'suspicious' | 'malicious'

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
