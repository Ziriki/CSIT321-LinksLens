import { View, Text, TextInput } from "react-native"
import { router } from "expo-router"
import {
  Card,
  RiskBadge,
  AppButton,
  InputField,
  ListItem,
  SectionHeader,
  ScreenHeader,
  BottomNav,
  ConfidenceIndicator,
  TextLink,
} from "../components/ui-components"

export default function appFeedback() {
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
              className="h-40 w-full rounded-xl border border-input bg-card px-4 py-3 text-foreground"
            />
          </View>
        </View>
      </View>

      <View className="border-t border-border px-4 py-4">
        <AppButton fullWidth 
            variant="primary"
            onPress={() => router.push("/profile")}
        >
          Submit
        </AppButton>
      </View>
    </View>
  )
}