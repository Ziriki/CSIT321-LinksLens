import { View, Text, Pressable } from "react-native"
import { router } from "expo-router"
import { Upload } from "lucide-react-native"
import {
  ScreenHeader,
  AppButton,
} from "../components/ui-components"

export default function scanImage() {
  return (
    <View className="flex-1 bg-background">
      <ScreenHeader title="Upload Photo" />

      <View className="flex-1 px-4 py-6">
        <Pressable className="h-64 items-center justify-center rounded-2xl border-2 border-dashed border-border">
          <Upload size={48} color="#6b7280" />
          <Text className="mt-4 font-medium text-foreground">
            Tap to select image
          </Text>
          <Text className="mt-1 text-sm text-muted-foreground">
            Select an image containing a link
          </Text>
        </Pressable>

        <View className="mt-8">
          <AppButton
            fullWidth
            size="lg"
            onPress={() => router.push("/scan-processing")}
          >
            Scan URL
          </AppButton>
        </View>
      </View>
    </View>
  )
}