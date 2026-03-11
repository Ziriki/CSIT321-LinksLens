import { View, Text, ScrollView, TextInput } from "react-native"
import { router } from "expo-router"
import { CheckCircle, AlertTriangle, XCircle, Flag } from "lucide-react-native"
import { AppButton, ScreenHeader } from "../components/ui-components"

export default function reportScan() {
  return (
    <View className="flex-1 bg-background">
      <ScreenHeader title="Report Incorrect Result" />

      <ScrollView className="flex-1 px-4 py-4">
        <Text className="mb-4 text-sm text-muted-foreground">
          If you believe this scan result is incorrect, please let us know. Our moderation team will review your report.
        </Text>

        {/* What should the result be */}
        <View className="mb-4 gap-2">
          <Text className="text-sm font-medium text-foreground">
            What should the result be?
          </Text>

          <View className="flex-row items-center rounded-xl border border-border bg-card px-4 py-3">
            <View className="h-5 w-5 rounded-full border-2 border-muted-foreground" />
            <Text className="ml-3 text-sm text-foreground">Safe</Text>
            <View className="ml-auto">
              <CheckCircle size={16} color="#16a34a" />
            </View>
          </View>

          <View className="flex-row items-center rounded-xl border-2 border-primary bg-card px-4 py-3">
            <View className="h-5 w-5 items-center justify-center rounded-full border-2 border-primary">
              <View className="h-2.5 w-2.5 rounded-full bg-primary" />
            </View>
            <Text className="ml-3 text-sm font-medium text-foreground">
              Suspicious
            </Text>
            <View className="ml-auto">
              <AlertTriangle size={16} color="#f59e0b" />
            </View>
          </View>

          <View className="flex-row items-center rounded-xl border border-border bg-card px-4 py-3">
            <View className="h-5 w-5 rounded-full border-2 border-muted-foreground" />
            <Text className="ml-3 text-sm text-foreground">Malicious</Text>
            <View className="ml-auto">
              <XCircle size={16} color="#dc2626" />
            </View>
          </View>
        </View>

        {/* Reason */}
        <View className="gap-2">
          <Text className="text-sm font-medium text-foreground">
            Why do you think this is incorrect?
          </Text>

          <TextInput
            multiline
            textAlignVertical="top"
            placeholder="Describe why you believe the result is wrong..."
            className="h-28 rounded-xl border border-input bg-card px-4 py-3 text-foreground"
          />
        </View>
      </ScrollView>

      <View className="border-t border-border px-4 py-4">
        <AppButton fullWidth onPress={() => router.push("/scan-results")}>
          <View className="flex-row items-center justify-center">
            <Flag size={16} />
            <Text className="ml-2">Submit Report</Text>
          </View>
        </AppButton>
      </View>
    </View>
  )
}