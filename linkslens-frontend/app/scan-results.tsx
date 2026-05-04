import React, { useState, useEffect, useMemo } from "react"
import { View, Text, ScrollView, Image, Linking, Pressable, Modal, Alert } from "react-native"
import { router, useLocalSearchParams } from "expo-router"
import {
  CheckCircle,
  ExternalLink,
  Info,
  ChevronRight,
  ChevronDown,
  Flag,
  XCircle,
  AlertTriangle,
  ImageIcon,
  GitBranch,
  Lock,
  MapPin,
  Shield,
  Link2,
} from "lucide-react-native"

import {
  Card,
  RiskBadge,
  AppButton,
  ConfidenceIndicator,
  ScreenHeader,
} from "../components/ui-components"
import type { ScanResponse } from "../lib/api"
import { fetchPreferences, getCurrentUserId } from "../lib/api"
import { BROWSER_PACKAGES, type BrowserId } from "../lib/browsers"
import { statusToRisk, type RiskLevel } from "../lib/types"
import { useIconColor } from "../lib/theme"

/**
 * Derives a confidence percentage (15–97) from how many independent signals
 * agree with the final verdict. Each signal is weighted by its authority:
 *   GSB (40) > script analysis (15) > homograph (10)
 * Missing signals (script analysis unavailable, homograph N/A) reduce the denominator.
 */
function computeConfidence(scan: ScanResponse): number {
  if (scan.status_indicator === "UNAVAILABLE") return 15

  const status = scan.status_indicator
  let earned = 0
  let total = 0

  // GSB — most authoritative signal (weight 40)
  total += 40
  if (status === "SAFE" && !scan.gsb_flagged) earned += 40
  else if (status !== "SAFE" && scan.gsb_flagged) earned += 40
  else if (status !== "SAFE" && !scan.gsb_flagged) earned += 15

  // Script analysis (weight 15, only if the scan returned data)
  const sa = scan.script_analysis
  if (sa !== null) {
    total += 15
    const hasThreats = sa.malicious_scripts.length > 0 || sa.crypto_miners.length > 0
    if (status === "MALICIOUS" && hasThreats) earned += 15
    else if (status === "SUSPICIOUS" && (hasThreats || sa.script_risk_score >= 30)) earned += 12
    else if (status === "SAFE" && !hasThreats && sa.script_risk_score < 25) earned += 15
    else earned += 5
  }

  // Homograph / IDN analysis (weight 10)
  total += 10
  const isHomograph = scan.homograph_analysis?.is_homograph ?? false
  if (status === "SAFE" && !isHomograph) earned += 10
  else if (status !== "SAFE" && isHomograph) earned += 10
  else earned += 5

  return Math.min(97, Math.max(15, Math.round((earned / total) * 100)))
}

function ThreatList({ title, items, color }: { title: string; items: string[]; color: string }) {
  if (items.length === 0) return null
  return (
    <View className="mb-4">
      <Text className={`text-xs font-semibold ${color}`}>{title}</Text>
      {items.map((item, i) => (
        <Text key={i} className="mt-1 text-xs text-foreground">{item}</Text>
      ))}
    </View>
  )
}

function InfoRow({ label, value, valueColor }: { label: string; value: string; valueColor?: string }) {
  return (
    <View className="mb-2 flex-row items-start justify-between gap-2">
      <Text className="flex-shrink-0 text-sm text-muted-foreground">{label}</Text>
      <Text className={`flex-1 text-right text-sm ${valueColor ?? "text-foreground"}`} numberOfLines={2}>{value}</Text>
    </View>
  )
}

function DetailSectionHeader({ icon, title }: { icon: React.ReactNode; title: string }) {
  return (
    <View className="mb-3 flex-row items-center gap-2 border-b border-border pb-2">
      {icon}
      <Text className="text-sm font-semibold text-foreground">{title}</Text>
    </View>
  )
}

function formatDomainAge(days: number | null): string {
  if (days == null) return "Unknown"
  if (days < 90) return `${days} days old (new)`
  if (days < 365) return `${Math.floor(days / 30)} months old`
  const y = Math.floor(days / 365)
  return `${y} year${y > 1 ? "s" : ""} old`
}

function PillRow({ label, items, pillBg, pillText }: { label: string; items: string[]; pillBg: string; pillText: string }) {
  if (items.length === 0) return null
  return (
    <View className="mb-2 flex-row items-start justify-between gap-2">
      <Text className="flex-shrink-0 text-sm text-muted-foreground">{label}</Text>
      <View className="flex-1 flex-row flex-wrap justify-end gap-1">
        {items.map((item, i) => (
          <View key={i} className={`rounded-full ${pillBg} px-2 py-0.5`}>
            <Text className={`text-xs ${pillText}`}>{item}</Text>
          </View>
        ))}
      </View>
    </View>
  )
}

function HighlightRow({ label, value, ok, noBorder }: { label: string; value: string; ok: boolean | null; noBorder?: boolean }) {
  const dotColor = ok === null ? "#6b7280" : ok ? "#16a34a" : "#dc2626"
  const textClass = ok === null ? "text-muted-foreground" : ok ? "text-green-500" : "text-red-500"
  return (
    <View className={`flex-row items-center justify-between py-2.5 ${noBorder ? "" : "border-b border-border"}`}>
      <Text className="text-sm text-muted-foreground">{label}</Text>
      <View className="flex-row items-center gap-1.5">
        <View className="h-2 w-2 rounded-full" style={{ backgroundColor: dotColor }} />
        <Text className={`text-sm font-medium ${textClass}`}>{value}</Text>
      </View>
    </View>
  )
}

export default function ScanResults() {
  const { result, error } = useLocalSearchParams<{ result?: string; error?: string }>();
  const iconColor = useIconColor();
  const [showScreenshot, setShowScreenshot] = useState(true);
  const [fullscreenImage, setFullscreenImage] = useState(false);
  const [showRedirects, setShowRedirects] = useState(true);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [browser, setBrowser] = useState<BrowserId>("system");
  useEffect(() => {
    getCurrentUserId().then((id) => {
      if (id) fetchPreferences(id).then((p) => { if (p.browser) setBrowser(p.browser as BrowserId) }).catch(() => {})
    })
  }, [])

  async function openURL(url: string) {
    if (!url || (!url.startsWith("http://") && !url.startsWith("https://"))) {
      Alert.alert("Cannot open link", "This URL cannot be opened.")
      return
    }

    const pkg = BROWSER_PACKAGES[browser]
    if (pkg) {
      // intent:// URIs target a specific browser package on Android 11+.
      // We verify the URL parses first, then try the intent URI.
      // If Android dispatches but the browser still shows blank, we fall back
      // to Linking.openURL(url) which lets the OS pick the default browser.
      try {
        const parsed = new URL(url)
        const scheme = parsed.protocol.replace(":", "")
        const intentUri = [
          `intent://${parsed.host}${parsed.pathname}${parsed.search}`,
          `#Intent`,
          `scheme=${scheme}`,
          `package=${pkg}`,
          `S.browser_fallback_url=${encodeURIComponent(url)}`,
          `end`,
        ].join(";")

        const opened = await Linking.openURL(intentUri).then(() => true).catch(() => false)
        if (!opened) {
          await Linking.openURL(url).catch(() => {
            Alert.alert("Cannot open link", "No browser available to open this URL.")
          })
        }
      } catch {
        // URL parsing failed — fall back to system browser
        await Linking.openURL(url).catch(() => {
          Alert.alert("Cannot open link", "Could not open this URL.")
        })
      }
    } else {
      await Linking.openURL(url).catch(() => {
        Alert.alert("Cannot open link", "Could not open this URL.")
      })
    }
  }

  let scanData: ScanResponse | null = null;
  try { if (result) scanData = JSON.parse(result); } catch { /* corrupted param */ }
  const confidence = useMemo(() => scanData ? computeConfidence(scanData) : 15, [scanData]);
  const riskLevel: RiskLevel = scanData ? statusToRisk(scanData.status_indicator) : "safe";
  const isSafe = riskLevel === "safe";
  const isSuspicious = riskLevel === "suspicious";
  const isUnavailable = riskLevel === "unavailable";

  if (error || !scanData) {
    return (
      <View className="flex-1 bg-background">
        <ScreenHeader title="Scan Results" />
        <View className="flex-1 items-center justify-center px-6">
          <XCircle size={64} color="#dc2626" />
          <Text className="mt-4 text-center text-lg font-semibold text-foreground">
            {error ?? "No result data available."}
          </Text>
          <View className="mt-8 w-full">
            <AppButton fullWidth onPress={() => router.push("/home")}>
              Go Home
            </AppButton>
          </View>
        </View>
      </View>
    );
  }

  const sa = scanData.script_analysis;
  const hasRedirects = (scanData.redirect_chain?.length ?? 0) > 1;
  const redirectCount = Math.max(0, (scanData.redirect_chain?.length ?? 0) - 1);
  const threatDescription = scanData.gsb_threat_types.length > 0
    ? `Threats: ${scanData.gsb_threat_types.join(", ")}`
    : scanData.tags.length > 0
      ? `Flagged: ${scanData.tags.join(", ")}`
      : "Suspicious activity detected";

  return (
    <View className="flex-1 bg-background">

      <ScreenHeader title="Scan Results" />

      {scanData.screenshot_url && (
        <Modal visible={fullscreenImage} transparent animationType="fade" onRequestClose={() => setFullscreenImage(false)}>
          <Pressable
            className="flex-1 items-center justify-center bg-black/90"
            onPress={() => setFullscreenImage(false)}
          >
            <Image
              source={{ uri: scanData.screenshot_url }}
              style={{ width: "100%", height: "75%" }}
              resizeMode="contain"
            />
            <Text className="mt-4 text-sm text-white/60">Tap anywhere to close</Text>
          </Pressable>
        </Modal>
      )}

      <ScrollView className="flex-1 px-4 py-4">
        <View>

        {/* Result hero */}
        <View className="items-center py-6">
          {isSafe ? (
            <CheckCircle size={64} color="#16a34a" />
          ) : isSuspicious ? (
            <AlertTriangle size={64} color="#d97706" />
          ) : isUnavailable ? (
            <Info size={64} color="#6b7280" />
          ) : (
            <XCircle size={64} color="#dc2626" />
          )}

          <View className="mt-4">
            <RiskBadge riskLevel={riskLevel} size="lg" />
          </View>

          <Text className="mt-4 px-4 text-center text-muted-foreground">
            {isSafe
              ? "This URL appears to be safe. No security threats detected."
              : isUnavailable
                ? "Scan analysis could not be completed for this URL."
                : threatDescription}
          </Text>
        </View>

        {/* Key Highlights — hidden for UNAVAILABLE scans (no reliable data to show) */}
        {!isUnavailable && (
          <Card className="mt-2">
            <Text className="mb-1 text-sm font-semibold text-foreground">Security Highlights</Text>
            <HighlightRow
              label="Connection"
              value={scanData.initial_url.startsWith("https://") ? "Secure (HTTPS)" : "Not Secure (HTTP)"}
              ok={scanData.initial_url.startsWith("https://")}
            />
            <HighlightRow
              label="Redirects"
              value={
                (scanData.redirect_chain?.length ?? 0) === 0
                  ? "No redirects"
                  : `Redirects ${scanData.redirect_chain!.length} time${scanData.redirect_chain!.length > 1 ? "s" : ""}`
              }
              ok={(scanData.redirect_chain?.length ?? 0) === 0}
            />
            <HighlightRow
              label="Domain Age"
              value={formatDomainAge(scanData.domain_age_days)}
              ok={scanData.domain_age_days == null ? null : scanData.domain_age_days >= 90}
            />
            <HighlightRow
              label="Safety Databases"
              value={scanData.gsb_flagged ? "Flagged as threat" : "Not flagged"}
              ok={!scanData.gsb_flagged}
              noBorder
            />
          </Card>
        )}

        {/* Screenshot */}
        {scanData.screenshot_url && (
          <Card className="mt-4 overflow-hidden p-0" onPress={() => setShowScreenshot(v => !v)}>
            <View className="flex-row items-center justify-between px-4 py-3">
              <View className="flex-row items-center gap-3">
                <ImageIcon size={20} color={iconColor} />
                <Text className="text-sm font-medium text-foreground">Website Preview</Text>
              </View>
              {showScreenshot
                ? <ChevronDown size={20} color={iconColor} />
                : <ChevronRight size={20} color={iconColor} />}
            </View>
            {showScreenshot && (
              <Pressable onPress={() => setFullscreenImage(true)}>
                <Image
                  source={{ uri: scanData.screenshot_url }}
                  style={{ width: "100%", height: 192 }}
                  resizeMode="cover"
                />
              </Pressable>
            )}
          </Card>
        )}

        {/* Redirect chain */}
        {hasRedirects && (
          <Card className="mt-4" onPress={() => setShowRedirects(v => !v)}>
            <View className="flex-row items-center justify-between">
              <View className="flex-row items-center gap-3">
                <GitBranch size={20} color={iconColor} />
                <Text className="text-sm font-medium text-foreground">Redirect Chain</Text>
              </View>
              {showRedirects
                ? <ChevronDown size={20} color={iconColor} />
                : <ChevronRight size={20} color={iconColor} />}
            </View>
            {showRedirects && (
              <View className="mt-3 border-t border-border pt-3">
                {scanData.redirect_chain!.map((url, i) => (
                  <View key={i} className="flex-row items-start gap-2 py-1">
                    <Text className="min-w-[18px] text-sm text-muted-foreground">{i + 1}.</Text>
                    <Text className="flex-1 text-sm text-foreground" numberOfLines={2}>{url}</Text>
                  </View>
                ))}
              </View>
            )}
          </Card>
        )}

        {/* URL */}
        <Card className="mt-4">
          <Text className="mb-1 text-sm text-muted-foreground">
            Scanned URL
          </Text>

          <Text className="text-sm text-foreground">
            {scanData.initial_url}
          </Text>

          <View className="mt-3 border-t border-border pt-3">
            <Pressable
              className="flex-row items-center gap-1"
              onPress={() => void openURL(scanData!.initial_url)}
            >
              <ExternalLink size={16} color="#2563eb" />
              <Text className="text-sm font-medium text-primary">
                Open URL
              </Text>
            </Pressable>
          </View>
        </Card>

        {!isUnavailable && (
        <Card className="mt-4" onPress={() => setShowAdvanced(!showAdvanced)}>
          <View className="flex-row items-center justify-between">
            <View className="flex-row items-center gap-3">
              <Info size={20} color={iconColor} />
              <Text className="text-sm font-medium text-foreground">
                Technical Details
              </Text>
            </View>
            {showAdvanced ? <ChevronDown size={20} color={iconColor} /> : <ChevronRight size={20} color={iconColor} />}
          </View>
          {!showAdvanced && (
            <Text className="mt-2 text-sm text-muted-foreground">
              SSL certificate, IP geolocation, script analysis, and more
            </Text>
          )}
        </Card>
        )}

        {!isUnavailable && showAdvanced && (
          <Card className="mt-1">

            {/* ── Analysis Confidence ── */}
            <View className="mb-5">
              <DetailSectionHeader icon={<Info size={15} color="#6b7280" />} title="Analysis Confidence" />
              <ConfidenceIndicator value={confidence} />
            </View>

            {/* ── Page Identity ── is this site pretending to be someone else? */}
            <View className="mb-5">
              <DetailSectionHeader icon={<Shield size={15} color="#6b7280" />} title="Page Identity" />
              {scanData.page_title && <InfoRow label="Page Title" value={scanData.page_title} />}
              {scanData.apex_domain && <InfoRow label="Registered Domain" value={scanData.apex_domain} />}
              <PillRow label="Brand Impersonation" items={scanData.brands} pillBg="bg-red-500/10" pillText="font-medium text-red-500" />
              <PillRow label="Community Tags" items={scanData.tags} pillBg="bg-secondary" pillText="text-muted-foreground" />
              {!scanData.page_title && !scanData.apex_domain && scanData.brands.length === 0 && scanData.tags.length === 0 && (
                <Text className="text-sm text-muted-foreground">Identity data unavailable.</Text>
              )}
            </View>

            {/* ── SSL Certificate ── */}
            <View className="mb-5">
              <DetailSectionHeader icon={<Lock size={15} color="#6b7280" />} title="SSL Certificate" />
              {scanData.ssl_info ? (
                <>
                  <InfoRow label="Issuer" value={scanData.ssl_info.issuer} />
                  {scanData.ssl_info.subject && <InfoRow label="Subject" value={scanData.ssl_info.subject} />}
                  {scanData.ssl_info.valid_from && <InfoRow label="Valid From" value={scanData.ssl_info.valid_from} />}
                  {scanData.ssl_info.valid_to && <InfoRow label="Valid Until" value={scanData.ssl_info.valid_to} />}
                  <InfoRow label="Protocol" value={scanData.ssl_info.protocol} />
                </>
              ) : (
                <Text className="text-sm text-muted-foreground">
                  {scanData.initial_url.startsWith("https://")
                    ? "SSL details not available for this scan."
                    : "Site does not use HTTPS."}
                </Text>
              )}
            </View>

            {/* ── Redirects ── */}
            <View className="mb-5">
              <DetailSectionHeader icon={<Link2 size={15} color="#6b7280" />} title="Redirects" />
              <InfoRow
                label="Number of Redirects"
                value={String(redirectCount)}
              />
              {(scanData.redirect_chain?.length ?? 0) > 0 && (
                <View className="mt-1">
                  {scanData.redirect_chain!.map((url, i) => (
                    <View key={i} className="flex-row items-start gap-2 py-0.5">
                      <Text className="min-w-[18px] text-xs text-muted-foreground">{i + 1}.</Text>
                      <Text className="flex-1 text-xs text-foreground" numberOfLines={2}>{url}</Text>
                    </View>
                  ))}
                </View>
              )}
            </View>

            {/* ── Hosting & Network ── */}
            <View className="mb-5">
              <DetailSectionHeader icon={<MapPin size={15} color="#6b7280" />} title="Hosting & Network" />
              {scanData.ip_address && <InfoRow label="IP Address" value={scanData.ip_address} />}
              {scanData.server_location && <InfoRow label="Country" value={scanData.server_location} />}
              {scanData.asn_name && <InfoRow label="Hosting Provider" value={scanData.asn_name} />}
              {!scanData.ip_address && !scanData.server_location && !scanData.asn_name && (
                <Text className="text-sm text-muted-foreground">Network data unavailable.</Text>
              )}
            </View>

            {/* ── Threat Intelligence ── */}
            <View className="mb-5">
              <DetailSectionHeader icon={<AlertTriangle size={15} color="#6b7280" />} title="Threat Intelligence" />
              <InfoRow
                label="Blacklist Status"
                value={scanData.gsb_flagged ? "Flagged by Google Safe Browsing" : "Clean"}
                valueColor={scanData.gsb_flagged ? "text-red-500" : "text-green-500"}
              />
              {scanData.domain_age_days != null && (
                <InfoRow
                  label="Domain Age"
                  value={`${scanData.domain_age_days} days${scanData.domain_age_days < 90 ? " (recently registered)" : ""}`}
                  valueColor={scanData.domain_age_days < 90 ? "text-yellow-500" : undefined}
                />
              )}
              <PillRow label="Threat Types" items={scanData.gsb_threat_types} pillBg="bg-red-500/10" pillText="font-medium text-red-500" />
            </View>

            {/* ── Script Analysis ── */}
            {sa && (
              <View className="mb-5">
                <DetailSectionHeader icon={<Info size={15} color="#6b7280" />} title="Script Analysis" />

                <View className="mb-4">
                  <Text className="mb-2 text-sm text-muted-foreground">Script Risk Score</Text>
                  <View className="flex-row items-center gap-3">
                    <View className="h-2 flex-1 overflow-hidden rounded-full bg-secondary">
                      <View
                        style={{ width: `${sa.script_risk_score}%` }}
                        className={`h-full rounded-full ${
                          sa.script_risk_score >= 50 ? "bg-red-500"
                            : sa.script_risk_score >= 25 ? "bg-yellow-500"
                            : "bg-green-500"
                        }`}
                      />
                    </View>
                    <Text className="w-12 text-right text-sm font-medium text-foreground">
                      {sa.script_risk_score}/100
                    </Text>
                  </View>
                </View>

                <InfoRow label="Total Scripts" value={String(sa.total)} />
                <InfoRow label="Trusted CDN Scripts" value={String(sa.trusted_count)} />
                <InfoRow label="Ad Scripts" value={`${sa.ad_count}${sa.ad_heavy ? " (ad-heavy)" : ""}`} />

                {sa.tech_stack.length > 0 && (
                  <View className="mb-3 mt-1">
                    <Text className="mb-2 text-sm text-muted-foreground">Technologies Detected</Text>
                    <View className="flex-row flex-wrap gap-1">
                      {sa.tech_stack.map((tech, i) => (
                        <View key={i} className="rounded-full bg-secondary px-2 py-1">
                          <Text className="text-xs text-foreground">{tech.name}</Text>
                        </View>
                      ))}
                    </View>
                  </View>
                )}

                <ThreatList title="Crypto Miners Detected" items={sa.crypto_miners} color="text-red-600" />
                <ThreatList title="Malicious Scripts" items={sa.malicious_scripts} color="text-red-600" />
                {sa.suspicious_patterns.length > 0 && (
                  <View className="mb-4">
                    <Text className="text-xs font-semibold text-yellow-600">Suspicious Patterns</Text>
                    {sa.suspicious_patterns.map((p, i) => (
                      <View key={i} className="mt-1">
                        <Text className="text-xs text-foreground">{p.reason}</Text>
                        <Text className="text-xs text-muted-foreground" numberOfLines={1}>{p.url}</Text>
                      </View>
                    ))}
                  </View>
                )}
              </View>
            )}

            {/* ── Homograph / IDN Risk ── */}
            {scanData.homograph_analysis?.is_homograph && (
              <View className="mb-5 rounded-xl border border-red-200 bg-red-50 px-3 py-2">
                <Text className="text-sm font-semibold text-red-700">IDN Homograph Risk Detected</Text>
                <Text className="mt-1 text-sm text-foreground">{scanData.homograph_analysis.details}</Text>
                <Text className="mt-1 text-sm text-muted-foreground">
                  Confusable chars: {scanData.homograph_analysis.confusable_chars.join(", ")}
                </Text>
              </View>
            )}

            {/* ── Full Report Link ── */}
            {scanData.result_url ? (
              <Pressable
                className="flex-row items-center justify-center gap-2 rounded-xl border border-border py-2.5"
                onPress={() => Linking.openURL(scanData!.result_url).catch(() => {})}
              >
                <ExternalLink size={14} color="#6b7280" />
                <Text className="text-sm text-muted-foreground">View full urlscan.io report</Text>
              </Pressable>
            ) : null}

          </Card>
        )}

        {/* Report incorrect */}
        {!isUnavailable && (
        <Card
          className="mt-4"
          onPress={() =>
            router.push({
              pathname: "/report-scan",
              params: { scanId: String(scanData!.scan_id) },
            })
          }
        >
          <View className="flex-row items-center justify-between">
            <View className="flex-row items-center gap-3">
              <Flag size={20} color={iconColor} />
              <View>
                <Text className="text-sm font-medium text-foreground">
                  Report Incorrect Result
                </Text>
                <Text className="text-sm text-muted-foreground">
                  Think this scan is wrong? Let us know
                </Text>
              </View>
            </View>
            <ChevronRight size={20} color={iconColor} />
          </View>
        </Card>
        )}

        <Text className="mt-6 mb-12 px-1 text-center text-xs text-muted-foreground leading-5">
          This scan result is for advisory purposes only. LinksLens uses third-party services to assess URLs and does not guarantee complete accuracy. Always exercise caution before visiting any link.
        </Text>

        </View>

      </ScrollView>

      {/* Done — fixed footer, always visible */}
      <View className="border-t border-border px-4 pb-4 pt-3">
        <AppButton fullWidth onPress={() => router.push("/home")}>
          Done
        </AppButton>
      </View>

    </View>
  )
}
