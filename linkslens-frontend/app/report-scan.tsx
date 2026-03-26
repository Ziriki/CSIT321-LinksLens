import { useState } from "react"
import { View, Text, ScrollView, TextInput, Pressable, Alert } from "react-native"
import { router, useLocalSearchParams } from "expo-router"
import { CheckCircle, AlertTriangle, XCircle, Flag } from "lucide-react-native"
import { AppButton, ScreenHeader } from "../components/ui-components"
import { submitScanFeedback, getCurrentUserId } from "../lib/api"

type SuggestedStatus = "SAFE" | "SUSPICIOUS" | "MALICIOUS"

const OPTIONS: { value: SuggestedStatus; label: string; icon: React.ReactNode }[] = [
  { value: "SAFE", label: "Safe", icon: <CheckCircle size={16} color="#16a34a" /> },
  { value: "SUSPICIOUS", label: "Suspicious", icon: <AlertTriangle size={16} color="#f59e0b" /> },
  { value: "MALICIOUS", label: "Malicious", icon: <XCircle size={16} color="#dc2626" /> },
]

export default function ReportScan() {
  const { scanId } = useLocalSearchParams<{ scanId?: string }>()
  const [selected, setSelected] = useState<SuggestedStatus>("SUSPICIOUS")
  const [comments, setComments] = useState("")
  const [loading, setLoading] = useState(false)

  async function handleSubmit() {
    if (!scanId) {
      Alert.alert("Error", "No scan to report.")
      return
    }
    setLoading(true)
    try {
      const userId = await getCurrentUserId()
      if (!userId) throw new Error("Not logged in.")
      await submitScanFeedback(Number(scanId), userId, selected, comments.trim())
      Alert.alert("Thank you!", "Your report has been submitted for review.")
      router.back()
    } catch (e: any) {
      Alert.alert("Error", e.message ?? "Failed to submit report.")
    } finally {
      setLoading(false)
    }
  }

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

          {OPTIONS.map((opt) => {
            const isSelected = selected === opt.value
            return (
              <Pressable
                key={opt.value}
                onPress={() => setSelected(opt.value)}
                className={`flex-row items-center rounded-xl px-4 py-3 ${
                  isSelected ? "border-2 border-primary bg-card" : "border border-border bg-card"
                }`}
              >
                <View
                  className={`h-5 w-5 items-center justify-center rounded-full border-2 ${
                    isSelected ? "border-primary" : "border-muted-foreground"
                  }`}
                >
                  {isSelected && <View className="h-2.5 w-2.5 rounded-full bg-primary" />}
                </View>
                <Text className={`ml-3 text-sm ${isSelected ? "font-medium" : ""} text-foreground`}>
                  {opt.label}
                </Text>
                <View className="ml-auto">{opt.icon}</View>
              </Pressable>
            )
          })}
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
            value={comments}
            onChangeText={setComments}
            className="h-28 rounded-xl border border-input bg-card px-4 py-3 text-foreground"
          />
        </View>
      </ScrollView>

      <View className="border-t border-border px-4 py-4">
        <AppButton fullWidth disabled={loading} onPress={handleSubmit}>
          <View className="flex-row items-center justify-center">
            <Flag size={16} />
            <Text className="ml-2">{loading ? "Submitting..." : "Submit Report"}</Text>
          </View>
        </AppButton>
      </View>
    </View>
  )
}
