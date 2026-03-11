import { View, Text, ScrollView } from "react-native"
import { router } from "expo-router"
import {
  Settings,
  LogOut,
  ChevronRight,
  Home, 
  ScanLine,
  Clock,
  User, 
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

const bottomNavItems = [
    {
        icon: <Home size={20} />,
        label: "Home",
        href: "/home",
    },
    {
        icon: <ScanLine size={20} />,
        label: "Scan",
        href: "/scan",
    },
    {
        icon: <Clock size={20} />,
        label: "History",
        href: "/scan-history",
    },
    {
        icon: <User size={20} />,
        label: "Profile",
        href: "/profile",
    },
]
export default function profile() {
  return (
    <View className="flex-1 bg-background">
      <ScreenHeader title="Profile" showBack={false} />

      <ScrollView className="flex-1 px-4 py-4">

        {/* User Info */}
        <View className="items-center py-6">
          <View className="mb-4 h-20 w-20 items-center justify-center rounded-full bg-secondary">
            <User size={40} color="#6b7280" />
          </View>

          <Text className="text-xl font-bold text-foreground">
            User Name
          </Text>

          <Text className="text-muted-foreground">
            user@email.com
          </Text>
        </View>


        {/* Stats */}
        <View className="mb-6 flex-row gap-4">

          <Card className="flex-1 items-center">
            <Text className="text-2xl font-bold text-foreground">
              --
            </Text>

            <Text className="text-sm text-muted-foreground">
              This Month
            </Text>
          </Card>

          <Card className="flex-1 items-center">
            <Text className="text-2xl font-bold text-foreground">
              --
            </Text>

            <Text className="text-sm text-muted-foreground">
              Total Scans
            </Text>
          </Card>

        </View>


        {/* Actions */}
        <View className="gap-2">

          <ListItem
            title="Edit Profile"
            leftIcon={<User size={20} />}
            rightElement={<ChevronRight size={20} color="#6b7280" />}
            onPress={() => router.push("/edit-profile")}
          />

          <ListItem
            title="Settings"
            leftIcon={<Settings size={20} />}
            rightElement={<ChevronRight size={20} color="#6b7280" />}
            onPress={() => router.push("/settings")}
          />

          <ListItem
            title="Sign Out"
            leftIcon={<LogOut size={20} />}
            onPress={() => router.replace("/")}
          />

        </View>

      </ScrollView>

      <BottomNav activeIndex={3} items={bottomNavItems} />

    </View>
  )
}