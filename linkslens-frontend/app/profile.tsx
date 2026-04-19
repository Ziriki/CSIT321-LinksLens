import { useState, useCallback } from "react"
import { View, Text, ScrollView, Alert } from "react-native"
import { router, useFocusEffect } from "expo-router"
import {
  Settings,
  LogOut,
  ChevronRight,
  User,
} from "lucide-react-native"

import {
  Card,
  ListItem,
  ScreenHeader,
  BottomNav,
} from "../components/ui-components"
import { logout, fetchAccount, fetchDetails, fetchScanHistory, getCurrentUserId } from "../lib/api"
import { countScansThisMonth } from "../lib/types"
import { bottomNavItems } from "../lib/navigation"
import { useIconColor } from "../lib/theme"

export default function Profile() {
  const iconColor = useIconColor()
  const [name, setName] = useState("Loading...")
  const [email, setEmail] = useState("")
  const [totalScans, setTotalScans] = useState(0)
  const [monthScans, setMonthScans] = useState(0)

  useFocusEffect(
    useCallback(() => {
      (async () => {
        try {
          const userId = await getCurrentUserId()
          if (!userId) return

          const [account, details, scans] = await Promise.all([
            fetchAccount(userId),
            fetchDetails(userId).catch(() => null),
            fetchScanHistory().catch(() => []),
          ])

          setEmail(account.EmailAddress)
          setName(details?.FullName ?? "User")
          setTotalScans(scans.length)
          setMonthScans(countScansThisMonth(scans))
        } catch {
          // Silently fail — show defaults
        }
      })()
    }, [])
  )

  return (
    <View className="flex-1 bg-background">
      <ScreenHeader title="Profile" showBack={false} />

      <ScrollView className="flex-1 px-4 py-4">
        {/* User Info */}
        <View className="items-center py-6">
          <View className="mb-4 h-20 w-20 items-center justify-center rounded-full bg-secondary">
            <User size={40} color="#6b7280" />
          </View>

          <Text className="text-xl font-bold text-foreground">{name}</Text>
          <Text className="text-muted-foreground">{email}</Text>
        </View>

        {/* Stats */}
        <View className="mb-6 flex-row gap-4">
          <Card className="flex-1 items-center">
            <Text className="text-2xl font-bold text-foreground">{monthScans}</Text>
            <Text className="text-sm text-muted-foreground">This Month</Text>
          </Card>

          <Card className="flex-1 items-center">
            <Text className="text-2xl font-bold text-foreground">{totalScans}</Text>
            <Text className="text-sm text-muted-foreground">Total Scans</Text>
          </Card>
        </View>

        {/* Actions */}
        <View className="gap-2">
          <ListItem
            title="Edit Profile"
            leftIcon={<User size={20} color={iconColor} />}
            rightElement={<ChevronRight size={20} color={iconColor} />}
            onPress={() => router.push("/edit-profile")}
          />

          <ListItem
            title="Settings"
            leftIcon={<Settings size={20} color={iconColor} />}
            rightElement={<ChevronRight size={20} color={iconColor} />}
            onPress={() => router.push("/settings")}
          />

          <ListItem
            title="Sign Out"
            leftIcon={<LogOut size={20} color={iconColor} />}
            onPress={() => {
              Alert.alert(
                "Sign Out",
                "Are you sure you want to sign out?",
                [
                  { text: "Cancel", style: "cancel" },
                  {
                    text: "Sign Out",
                    style: "destructive",
                    onPress: async () => {
                      await logout()
                      router.replace("/")
                    },
                  },
                ]
              )
            }}
          />
        </View>
      </ScrollView>

      <BottomNav activeIndex={3} items={bottomNavItems} />
    </View>
  )
}
