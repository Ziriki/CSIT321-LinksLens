import { View, Text, ScrollView } from "react-native"
import { router } from "expo-router"
import {
  Globe,
  ExternalLink,
  Bell,
  Moon,
  MessageSquare,
  ChevronRight,
} from "lucide-react-native"

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


export default function settings() {
  return (
    <View className="flex-1 bg-background">
      <ScreenHeader title="Settings" />

      <ScrollView className="flex-1 px-4 py-4">

        <View className="gap-2">

          <ListItem
            title="Language"
            subtitle="English"
            leftIcon={<Globe size={20} />}
            rightElement={<ChevronRight size={20} color="#6b7280" />}
            onPress={() => router.push("/language-settings")}
          />

          <ListItem
            title="Default Browser"
            subtitle="In-App Browser"
            leftIcon={<ExternalLink size={20} />}
            rightElement={<ChevronRight size={20} color="#6b7280" />}
            onPress={() => router.push("/browser-settings")}
          />

          <ListItem
            title="Notifications"
            leftIcon={<Bell size={20} />}
            rightElement={
              <View className="h-6 w-11 rounded-full bg-primary">
                <View className="absolute right-0.5 top-0.5 h-5 w-5 rounded-full bg-white" />
              </View>
            }
          />

          <ListItem
            title="Dark Mode"
            leftIcon={<Moon size={20} />}
            rightElement={
              <View className="h-6 w-11 rounded-full bg-secondary">
                <View className="absolute left-0.5 top-0.5 h-5 w-5 rounded-full bg-white" />
              </View>
            }
          />

          <ListItem
            title="App Feedback"
            leftIcon={<MessageSquare size={20} />}
            rightElement={<ChevronRight size={20} color="#6b7280" />}
            onPress={() => router.push("/app-feedback")}
          />

        </View>

        <Text className="mt-8 text-center text-sm text-muted-foreground">
          LinksLens v1.0.0
        </Text>
      </ScrollView>
    </View>
  )
}