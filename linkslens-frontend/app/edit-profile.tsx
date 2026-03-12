import { View, Text } from "react-native"
import { router } from "expo-router"
import {  User} from "lucide-react-native"
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


export default function editProfile() {
  return (
    <View className="flex-1 bg-background">
      <ScreenHeader title="Edit Profile" />

      <View className="flex-1 px-4 py-6">

        {/* Avatar */}
        <View className="mb-6 items-center">
          <View className="mb-2 h-24 w-24 items-center justify-center rounded-full bg-secondary">
            <User size={48} color="#6b7280" />
          </View>

          <Text className="text-sm font-medium text-primary">
            Change Photo
          </Text>
        </View>

        {/* Form */}
        <View className="gap-4">
          <InputField label="Full Name" placeholder="Enter name" />
          <InputField label="Email" placeholder="Enter email" />
        </View>
      </View>
        
      {/* Footer */}
      <View className="border-t border-border px-4 py-4">
        <AppButton
          fullWidth
          onPress={() => router.push("/profile")}>
        Save Changes
        </AppButton>
      </View>
    </View>
  )
}