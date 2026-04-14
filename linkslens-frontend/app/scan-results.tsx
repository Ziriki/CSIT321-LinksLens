import { useState, useRef, useEffect, useMemo } from "react"
import { View, Text, ScrollView, Image, Linking, Pressable, Alert, Modal } from "react-native"
import { captureRef } from "react-native-view-shot"
import * as MediaLibrary from "expo-media-library"
import { router, useLocalSearchParams } from "expo-router"
import {
  CheckCircle,
  ExternalLink,
  Info,
  ChevronRight,
  ChevronDown,
  Flag,
  Camera,
  XCircle,
  AlertTriangle,
  ImageIcon,
  GitBranch,
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
 *   GSB (40) > urlscan score (35) > script analysis (15) > homograph (10)
 * Signals that contradict the verdict lower the score; missing signals
 * (script analysis unavailable, homograph N/A) reduce the denominator.
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

  // urlscan.io score alignment (weight 35)
  total += 35
  const urlscanScore = scan.score ?? 0
  if (status === "MALICIOUS") {
    if (urlscanScore >= 70) earned += 35
    else if (urlscanScore >= 50) earned += 25
    else if (urlscanScore >= 30) earned += 15
    else earned += 5
  } else if (status === "SUSPICIOUS") {
    if (urlscanScore >= 30 && urlscanScore < 70) earned += 30
    else if (urlscanScore >= 15) earned += 20
    else earned += 10
  } else {
    // SAFE
    if (urlscanScore < 20) earned += 35
    else if (urlscanScore < 40) earned += 20
    else earned += 5
  }

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

export default function ScanResults() {
  const { result, error } = useLocalSearchParams<{ result?: string; error?: string }>();
  const iconColor = useIconColor();
  const [showScreenshot, setShowScreenshot] = useState(true);
  const [fullscreenImage, setFullscreenImage] = useState(false);
  const [showRedirects, setShowRedirects] = useState(true);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [browser, setBrowser] = useState<BrowserId>("system");
  const exportRef = useRef<View>(null);

  useEffect(() => {
    getCurrentUserId().then((id) => {
      if (id) fetchPreferences(id).then((p) => { if (p.browser) setBrowser(p.browser) }).catch(() => {})
    })
  }, [])

  function openURL(url: string) {
    const pkg = BROWSER_PACKAGES[browser]
    if (pkg) {
      // intent:// URIs target the browser package directly — works on Android 11+
      // without requiring <queries> manifest entries for custom browser schemes.
      try {
        const parsed = new URL(url)
        const intentUri = `intent://${parsed.host}${parsed.pathname}${parsed.search}#Intent;scheme=${parsed.protocol.replace(":", "")};package=${pkg};S.browser_fallback_url=${encodeURIComponent(url)};end`
        Linking.openURL(intentUri).catch(() => Linking.openURL(url))
      } catch {
        Linking.openURL(url)
      }
    } else {
      Linking.openURL(url)
    }
  }

  async function handleExport() {
    try {
      const { status } = await MediaLibrary.requestPermissionsAsync();
      if (status !== "granted") {
        Alert.alert("Permission needed", "Allow photo library access to save the report.");
        return;
      }
      const uri = await captureRef(exportRef, { format: "jpg", quality: 0.9, snapshotContentContainer: true });
      await MediaLibrary.saveToLibraryAsync(uri);
      Alert.alert("Saved", "Scan report saved to your gallery.");
    } catch {
      Alert.alert("Export failed", "Could not save the scan report.");
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
  const threatDescription = scanData.gsb_threat_types.length > 0
    ? `Threats: ${scanData.gsb_threat_types.join(", ")}`
    : scanData.tags.length > 0
      ? `Flagged: ${scanData.tags.join(", ")}`
      : "Suspicious activity detected";

  return (
    <View className="flex-1 bg-background">

      <ScreenHeader title="Scan Results" />

      <ScrollView className="flex-1 px-4 py-4">
        <View ref={exportRef} collapsable={false}>

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

        {/* Screenshot */}
        {scanData.screenshot_url && (
          <>
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
          </>
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
              onPress={() => openURL(scanData!.initial_url)}
            >
              <ExternalLink size={16} color="#2563eb" />
              <Text className="text-sm font-medium text-primary">
                Open URL
              </Text>
            </Pressable>
          </View>
        </Card>

        {/* Confidence */}
        <Card className="mt-4">
          <Text className="mb-3 text-sm font-medium text-foreground">
            Analysis Confidence
          </Text>
          <ConfidenceIndicator value={confidence} />
        </Card>

        {/* Advanced Analysis toggle */}
        <Card className="mt-4" onPress={() => setShowAdvanced(!showAdvanced)}>
          <View className="flex-row items-center justify-between">
            <View className="flex-row items-center gap-3">
              <Info size={20} color={iconColor} />
              <Text className="text-sm font-medium text-foreground">
                Advanced Analysis
              </Text>
            </View>
            {showAdvanced ? <ChevronDown size={20} color={iconColor} /> : <ChevronRight size={20} color={iconColor} />}
          </View>
          {!showAdvanced && (
            <Text className="mt-2 text-sm text-muted-foreground">
              Domain age, server info, script analysis, and more
            </Text>
          )}
        </Card>

        {showAdvanced && (
          <Card className="mt-1">

            {/* Domain age */}
            {scanData.domain_age_days != null && (
              <View className="mb-4">
                <Text className="text-sm text-muted-foreground">Domain Age</Text>
                <Text className="mt-1 text-sm text-foreground">
                  {scanData.domain_age_days} days
                  {scanData.domain_age_days < 90 ? " (recently registered)" : ""}
                </Text>
              </View>
            )}

            {/* Server location */}
            {scanData.server_location && (
              <View className="mb-4">
                <Text className="text-sm text-muted-foreground">Server Location</Text>
                <Text className="mt-1 text-sm text-foreground">{scanData.server_location}</Text>
              </View>
            )}

            {sa && (
              <>
                {/* Script risk score */}
                <View className="mb-4">
                  <Text className="text-sm text-muted-foreground">Script Risk Score</Text>
                  <View className="mt-2 flex-row items-center gap-3">
                    <View className="h-2 flex-1 overflow-hidden rounded-full bg-secondary">
                      <View
                        style={{ width: `${sa.script_risk_score}%` }}
                        className={`h-full rounded-full ${
                          sa.script_risk_score >= 50
                            ? "bg-red-500"
                            : sa.script_risk_score >= 25
                              ? "bg-yellow-500"
                              : "bg-green-500"
                        }`}
                      />
                    </View>
                    <Text className="w-12 text-right text-sm font-medium text-foreground">
                      {sa.script_risk_score}/100
                    </Text>
                  </View>
                </View>

                {/* Tech stack */}
                {sa.tech_stack.length > 0 && (
                  <View className="mb-4">
                    <Text className="text-sm text-muted-foreground">Technologies Detected</Text>
                    <View className="mt-2 flex-row flex-wrap gap-1">
                      {sa.tech_stack.map((tech, i) => (
                        <View key={i} className="rounded-full bg-secondary px-2 py-1">
                          <Text className="text-sm text-foreground">{tech}</Text>
                        </View>
                      ))}
                    </View>
                  </View>
                )}

                {/* Ad scripts */}
                <View className="mb-4">
                  <Text className="text-sm text-muted-foreground">Ad Scripts</Text>
                  <Text className="mt-1 text-sm text-foreground">
                    {sa.ad_count} found
                    {sa.ad_heavy ? " — ad-heavy site" : ""}
                  </Text>
                </View>

                {/* Script counts */}
                <View className="mb-4 flex-row gap-4">
                  <View>
                    <Text className="text-sm text-muted-foreground">Total Scripts</Text>
                    <Text className="mt-1 text-sm text-foreground">{sa.total}</Text>
                  </View>
                  <View>
                    <Text className="text-sm text-muted-foreground">Trusted CDN</Text>
                    <Text className="mt-1 text-sm text-foreground">{sa.trusted_count}</Text>
                  </View>
                </View>

                <ThreatList title="Crypto Miners Detected" items={sa.crypto_miners} color="text-red-600" />
                <ThreatList title="Malicious Scripts" items={sa.malicious_scripts} color="text-red-600" />
                <ThreatList title="Suspicious Patterns" items={sa.suspicious_patterns} color="text-yellow-600" />
              </>
            )}

            {/* Homograph / IDN attack risk */}
            {scanData.homograph_analysis?.is_homograph && (
              <View className="mb-4 rounded-xl border border-red-200 bg-red-50 px-3 py-2">
                <Text className="text-sm font-semibold text-red-700">IDN Homograph Risk Detected</Text>
                <Text className="mt-1 text-sm text-foreground">{scanData.homograph_analysis.details}</Text>
                <Text className="mt-1 text-sm text-muted-foreground">
                  Confusable chars: {scanData.homograph_analysis.confusable_chars.join(", ")}
                </Text>
              </View>
            )}

            {!sa && !scanData.domain_age_days && !scanData.server_location && (
              <Text className="text-sm text-muted-foreground">
                No additional analysis data available for this scan.
              </Text>
            )}
          </Card>
        )}

        {/* Report incorrect */}
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

        </View>{/* end exportRef */}

        {/* Export */}
        <View className="mt-4">
          <AppButton variant="outline" fullWidth onPress={handleExport}>
            <View className="flex-row items-center justify-center gap-2">
              <Camera size={16} color={iconColor} />
              <Text className="text-foreground">Export Screenshot</Text>
            </View>
          </AppButton>
          <Text className="mt-2 text-center text-xs text-muted-foreground">
            Saves a screenshot of results to your gallery
          </Text>
        </View>

      </ScrollView>

      {/* Footer */}
      <View className="border-t border-border px-4 py-4">
        <AppButton fullWidth onPress={() => router.push("/home")}>
          Done
        </AppButton>
      </View>
    </View>
  )
}
