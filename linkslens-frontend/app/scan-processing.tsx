import { useEffect } from "react"
import { View, Text } from "react-native"
import { router, useLocalSearchParams } from "expo-router"
import { Zap } from "lucide-react-native"
import { Card } from "../components/ui-components"
import { scanUrl } from "../lib/api"

export default function scanProcessing() {
  const { url } = useLocalSearchParams<{ url: string }>();

  useEffect(() => {
    if (!url) {
      router.back();
      return;
    }

    scanUrl(url)
      .then((result) => {
        router.replace({
          pathname: "/scan-results",
          params: { result: JSON.stringify(result) },
        });
      })
      .catch(() => {
        router.replace({
          pathname: "/scan-results",
          params: { error: "Scan failed. Please try again." },
        });
      });
  }, [url]);

  return (
    <View className="flex-1 items-center justify-center bg-background px-6">
      {/* Scanning Visual */}
      <View className="relative mb-8">
        <View className="h-32 w-32 items-center justify-center rounded-full border-4 border-secondary">
          <View className="h-24 w-24 rounded-full border-4 border-primary" />
        </View>

        <View className="absolute inset-0 items-center justify-center">
          <Zap size={40} color="#2563eb" />
        </View>
      </View>

      <Text className="mb-2 text-xl font-bold text-foreground">
        Analyzing URL
      </Text>

      <Text className="mb-6 text-center text-muted-foreground">
        Cross-referencing databases...
      </Text>

      {/* Progress Bar */}
      <View className="w-full">
        <View className="h-2 overflow-hidden rounded-full bg-secondary">
          <View
            className="h-full rounded-full bg-primary"
            style={{ width: "72%" }}
          />
        </View>

        <Text className="mt-2 text-center text-sm text-muted-foreground">
          Analyzing...
        </Text>
      </View>

      {/* URL Preview */}
      <Card className="mt-8 w-full">
        <Text className="mb-1 text-xs text-muted-foreground">
          Scanning
        </Text>

        <Text className="text-sm text-foreground" numberOfLines={1}>
          {url ?? "..."}
        </Text>
      </Card>
    </View>
  )
}
