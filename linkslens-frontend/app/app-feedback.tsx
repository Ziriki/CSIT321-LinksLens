import { useState } from "react"
import { View, Text, TextInput, Alert } from "react-native"
import { router } from "expo-router"
import {
  AppButton,
  ScreenHeader,
} from "../components/ui-components"
import { submitAppFeedback, getCurrentUserId } from "../lib/api"

export default function AppFeedback() {
  const [feedback, setFeedback] = useState("")
  const [loading, setLoading] = useState(false)

  async function handleSubmit() {
    if (!feedback.trim()) return
    setLoading(true)
    try {
      const userId = await getCurrentUserId()
      if (!userId) throw new Error("Not logged in.")
      await submitAppFeedback(userId, feedback.trim())
      Alert.alert("Thank you!", "Your feedback has been submitted.")
      router.back()
    } catch (e: any) {
      Alert.alert("Error", e.message ?? "Failed to submit feedback.")
    } finally {
      setLoading(false)
    }
  }

  return (
    <View className="flex-1 bg-background">
      <ScreenHeader title="App Feedback" />

      <View className="flex-1 px-4 py-6">
        <Text className="mb-6 text-muted-foreground">
          Help us improve LinksLens by sharing your feedback!
        </Text>

        <View className="gap-4">
          <View className="gap-1.5">
            <Text className="text-sm font-medium text-foreground">
              Your Feedback
            </Text>

            <TextInput
              multiline
              textAlignVertical="top"
              placeholder="Share your thoughts, suggestions, or report issues..."
              placeholderTextColor="#6b7280"
              value={feedback}
              onChangeText={setFeedback}
              maxLength={2000}
              className="h-40 w-full rounded-xl border border-input bg-card px-4 py-3 text-foreground"
            />
          </View>
        </View>
      </View>

      <View className="border-t border-border px-4 py-4">
        <AppButton
          fullWidth
          variant="primary"
          disabled={!feedback.trim() || loading}
          onPress={handleSubmit}
        >
          {loading ? "Submitting..." : "Submit"}
        </AppButton>
      </View>
    </View>
  )
}
