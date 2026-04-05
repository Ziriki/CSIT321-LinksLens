import { useState, useRef, useEffect } from "react"
import { View, Text, ScrollView, Image, Linking, Pressable, Alert } from "react-native"
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
import { BROWSER_SCHEMES } from "../lib/browsers"
import { statusToRisk, type RiskLevel } from "../lib/types"

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
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [browser, setBrowser] = useState("system");
  const exportRef = useRef<View>(null);

  useEffect(() => {
    getCurrentUserId().then((id) => {
      if (id) fetchPreferences(id).then((p) => { if (p.browser) setBrowser(p.browser) }).catch(() => {})
    })
  }, [])

  function openURL(url: string) {
    const prefix = BROWSER_SCHEMES[browser]
    Linking.openURL(prefix ? `${prefix}${encodeURIComponent(url)}` : url).catch(() =>
      Linking.openURL(url)
    )
  }

  async function handleExport() {
    try {
      const { status } = await MediaLibrary.requestPermissionsAsync();
      if (status !== "granted") {
        Alert.alert("Permission needed", "Allow photo library access to save the report.");
        return;
      }
      const uri = await captureRef(exportRef, { format: "jpg", quality: 0.9 });
      await MediaLibrary.saveToLibraryAsync(uri);
      Alert.alert("Saved", "Scan report saved to your gallery.");
    } catch {
      Alert.alert("Export failed", "Could not save the scan report.");
    }
  }

  let scanData: ScanResponse | null = null;
  try { if (result) scanData = JSON.parse(result); } catch { /* corrupted param */ }
  const riskLevel: RiskLevel = scanData ? statusToRisk(scanData.status_indicator) : "safe";
  const isSafe = riskLevel === "safe";
  const isSuspicious = riskLevel === "suspicious";

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
          ) : (
            <XCircle size={64} color="#dc2626" />
          )}

          <View className="mt-4">
            <RiskBadge riskLevel={riskLevel} size="lg" />
          </View>

          <Text className="mt-4 px-4 text-center text-muted-foreground">
            {isSafe
              ? "This URL appears to be safe. No security threats detected."
              : threatDescription}
          </Text>
        </View>

        {/* Screenshot */}
        {scanData.screenshot_url && (
          <Card className="mt-4 overflow-hidden p-0">
            <Text className="px-4 pt-3 text-xs text-muted-foreground">
              Website Preview
            </Text>
            <Image
              source={{ uri: scanData.screenshot_url }}
              style={{ width: "100%", height: 192, marginTop: 8 }}
              resizeMode="cover"
            />
          </Card>
        )}

        {/* Redirect chain */}
        {hasRedirects && (
          <Card className="mt-4">
            <Text className="mb-2 text-sm font-medium text-foreground">
              Redirect Chain
            </Text>
            {scanData.redirect_chain!.map((url, i) => (
              <View key={i} className="flex-row items-start gap-2 py-1">
                <Text className="min-w-[18px] text-xs text-muted-foreground">
                  {i + 1}.
                </Text>
                <Text className="flex-1 text-xs text-foreground" numberOfLines={2}>
                  {url}
                </Text>
              </View>
            ))}
          </Card>
        )}

        {/* URL */}
        <Card className="mt-4">
          <Text className="mb-1 text-xs text-muted-foreground">
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
              <ExternalLink size={16} />
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
          <ConfidenceIndicator value={scanData.score} />
        </Card>

        {/* Advanced Analysis toggle */}
        <Card className="mt-4" onPress={() => setShowAdvanced(!showAdvanced)}>
          <View className="flex-row items-center justify-between">
            <View className="flex-row items-center gap-3">
              <Info size={20} />
              <Text className="text-sm font-medium text-foreground">
                Advanced Analysis
              </Text>
            </View>
            {showAdvanced ? <ChevronDown size={20} /> : <ChevronRight size={20} />}
          </View>
          {!showAdvanced && (
            <Text className="mt-2 text-xs text-muted-foreground">
              Domain age, server info, script analysis, and more
            </Text>
          )}
        </Card>

        {showAdvanced && (
          <Card className="mt-1">

            {/* Domain age */}
            {scanData.domain_age_days != null && (
              <View className="mb-4">
                <Text className="text-xs text-muted-foreground">Domain Age</Text>
                <Text className="mt-1 text-sm text-foreground">
                  {scanData.domain_age_days} days
                  {scanData.domain_age_days < 90 ? " (recently registered)" : ""}
                </Text>
              </View>
            )}

            {/* Server location */}
            {scanData.server_location && (
              <View className="mb-4">
                <Text className="text-xs text-muted-foreground">Server Location</Text>
                <Text className="mt-1 text-sm text-foreground">{scanData.server_location}</Text>
              </View>
            )}

            {sa && (
              <>
                {/* Script risk score */}
                <View className="mb-4">
                  <Text className="text-xs text-muted-foreground">Script Risk Score</Text>
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
                    <Text className="w-12 text-right text-xs font-medium text-foreground">
                      {sa.script_risk_score}/100
                    </Text>
                  </View>
                </View>

                {/* Tech stack */}
                {sa.tech_stack.length > 0 && (
                  <View className="mb-4">
                    <Text className="text-xs text-muted-foreground">Technologies Detected</Text>
                    <View className="mt-2 flex-row flex-wrap gap-1">
                      {sa.tech_stack.map((tech, i) => (
                        <View key={i} className="rounded-full bg-secondary px-2 py-1">
                          <Text className="text-xs text-foreground">{tech}</Text>
                        </View>
                      ))}
                    </View>
                  </View>
                )}

                {/* Ad scripts */}
                <View className="mb-4">
                  <Text className="text-xs text-muted-foreground">Ad Scripts</Text>
                  <Text className="mt-1 text-sm text-foreground">
                    {sa.ad_count} found
                    {sa.ad_heavy ? " — ad-heavy site" : ""}
                  </Text>
                </View>

                {/* Script counts */}
                <View className="mb-4 flex-row gap-4">
                  <View>
                    <Text className="text-xs text-muted-foreground">Total Scripts</Text>
                    <Text className="mt-1 text-sm text-foreground">{sa.total}</Text>
                  </View>
                  <View>
                    <Text className="text-xs text-muted-foreground">Trusted CDN</Text>
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
                <Text className="text-xs font-semibold text-red-700">IDN Homograph Risk Detected</Text>
                <Text className="mt-1 text-xs text-foreground">{scanData.homograph_analysis.details}</Text>
                <Text className="mt-1 text-xs text-muted-foreground">
                  Confusable chars: {scanData.homograph_analysis.confusable_chars.join(", ")}
                </Text>
              </View>
            )}

            {!sa && !scanData.domain_age_days && !scanData.server_location && (
              <Text className="text-xs text-muted-foreground">
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
              <Flag size={20} />
              <View>
                <Text className="text-sm font-medium text-foreground">
                  Report Incorrect Result
                </Text>
                <Text className="text-xs text-muted-foreground">
                  Think this scan is wrong? Let us know
                </Text>
              </View>
            </View>
            <ChevronRight size={20} />
          </View>
        </Card>

        </View>{/* end exportRef */}

        {/* Export */}
        <View className="mt-4">
          <AppButton variant="outline" fullWidth onPress={handleExport}>
            <View className="flex-row items-center justify-center gap-2">
              <Camera size={16} />
              <Text>Export Screenshot</Text>
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
