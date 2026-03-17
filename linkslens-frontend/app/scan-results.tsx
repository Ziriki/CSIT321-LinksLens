import { View, Text, ScrollView } from "react-native"
import { router, useLocalSearchParams } from "expo-router"
import {
  CheckCircle,
  ExternalLink,
  Info,
  ChevronRight,
  Flag,
  Camera,
  XCircle,
} from "lucide-react-native"

import {
  Card,
  RiskBadge,
  AppButton,
  ConfidenceIndicator,
  ScreenHeader,
} from "../components/ui-components"
import type { ScanResponse } from "../lib/api"
import type { RiskLevel } from "../lib/types"

function verdictToRiskLevel(verdict: ScanResponse["verdict"]): RiskLevel {
  return verdict === "SAFE" ? "safe" : "malicious";
}

export default function scanResults() {
  const { result, error } = useLocalSearchParams<{ result?: string; error?: string }>();

  const scanData: ScanResponse | null = result ? JSON.parse(result) : null;
  const riskLevel: RiskLevel = scanData ? verdictToRiskLevel(scanData.verdict) : "safe";
  const isSafe = riskLevel === "safe";

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
            <AppButton fullWidth onPress={() => router.push("/")}>
              Go Home
            </AppButton>
          </View>
        </View>
      </View>
    );
  }

  return (
    <View className="flex-1 bg-background">

      <ScreenHeader title="Scan Results" />

      <ScrollView className="flex-1 px-4 py-4">

        {/* Result */}
        <View className="items-center py-6">
          {isSafe ? (
            <CheckCircle size={64} color="#16a34a" />
          ) : (
            <XCircle size={64} color="#dc2626" />
          )}

          <View className="mt-4">
            <RiskBadge riskLevel={riskLevel} size="lg" />
          </View>

          <Text className="mt-4 px-4 text-center text-muted-foreground">
            {isSafe
              ? "This URL appears to be safe. No security threats detected."
              : `Threats detected: ${scanData.threats.join(", ") || "Suspicious activity"}`}
          </Text>
        </View>

        {/* URL */}
        <Card className="mt-4">
          <Text className="mb-1 text-xs text-muted-foreground">
            Scanned URL
          </Text>

          <Text className="text-sm text-foreground">
            {scanData.url}
          </Text>

          <View className="mt-3 flex-row items-center gap-2 border-t border-border pt-3">
            <View className="flex-row items-center gap-1">
              <ExternalLink size={16} />
              <Text className="text-sm font-medium text-primary">
                Open URL
              </Text>
            </View>
          </View>
        </Card>

        {/* Confidence */}
        <Card className="mt-4">
          <Text className="mb-3 text-sm font-medium text-foreground">
            Analysis Confidence
          </Text>

          <ConfidenceIndicator value={scanData.safety_score} />
        </Card>

        {/* Advanced */}
        <Card
          className="mt-4"
          onPress={() => router.push("/scan-results-advanced")}
        >
          <View className="flex-row items-center justify-between">
            <View className="flex-row items-center gap-3">
              <Info size={20} />

              <Text className="text-sm font-medium text-foreground">
                Advanced Analysis
              </Text>
            </View>

            <ChevronRight size={20} />
          </View>

          <Text className="mt-2 text-xs text-muted-foreground">
            View WHOIS data, SSL info, DNS records, and more
          </Text>
        </Card>

        {/* Report incorrect */}
        <Card
          className="mt-4"
          onPress={() => router.push("/report-scan")}
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

        {/* Export */}
        <View className="mt-4">
          <AppButton variant="outline" fullWidth>

            <View className="flex-row items-center justify-center gap-2">
              <Camera size={16} />
              <Text>Export Screenshot</Text>
            </View>

          </AppButton>

          <Text className="mt-2 text-center text-xs text-muted-foreground">
            Saves a screenshot of results to your device
          </Text>
        </View>

      </ScrollView>

      {/* Footer */}
      <View className="border-t border-border px-4 py-4">

        <AppButton
          fullWidth
          onPress={() => router.push("/home")}
        >
          Done
        </AppButton>
      </View>
    </View>
  )
}
