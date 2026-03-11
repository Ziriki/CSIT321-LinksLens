import { View, Text } from "react-native"
import { router } from "expo-router"
import { Link2 } from "lucide-react-native"
import {
  InputField,
  ScreenHeader,
  AppButton
} from "../components/ui-components"

export default function scanLink() {
  return (
    <View className="flex-1 bg-background">
      <ScreenHeader title="Enter Link" />

      <View className="flex-1 px-4 py-6">

        <InputField
          label="Enter URL"
          placeholder="https://example.com"
        />

        <Text className="mt-3 text-sm text-muted-foreground">
          Paste or type the link you want to scan
        </Text>

        <View className="mt-8">
          <AppButton
            fullWidth
            size="lg"
            onPress={() => router.push("/scan-processing")}
          >
            Scan URL
          </AppButton>
        </View>


        {/* Recent URLs */}
        <View className="mt-8">
          <Text className="mb-3 text-sm font-medium text-foreground">
            Recent URLs
          </Text>

          <View className="gap-2">

            {["https://...", "https://...", "https://..."].map((url, i) => (
              <View
                key={i}
                className="flex-row items-center gap-3 rounded-xl bg-secondary p-3"
              >
                <Link2 size={16} color="#6b7280" />

                <Text
                  className="flex-1 text-sm text-foreground"
                  numberOfLines={1}
                >
                  {url}
                </Text>

              </View>
            ))}

          </View>
        </View>

      </View>
    </View>
  )
}