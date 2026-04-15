import { View, Text, ScrollView } from "react-native"
import { useCallback, useState } from "react"
import { router } from "expo-router"
import { useFocusEffect } from "@react-navigation/native"
import {
  ExternalLink,
  Bell,
  Moon,
  MessageSquare,
  ChevronRight,
} from "lucide-react-native"
import { useColorScheme } from "nativewind"
import * as SecureStore from "expo-secure-store"
import {
  ListItem,
  ScreenHeader,
} from "../components/ui-components"
import { THEME_KEY, useIconColor } from "../lib/theme"
import {
  getNotificationsEnabled,
  setNotificationsEnabled,
  requestNotificationPermission,
} from "../lib/notifications"
import { BROWSERS, type BrowserId, getInstalledBrowserIds } from "../lib/browsers"
import { fetchPreferences, getCurrentUserId } from "../lib/api"

export default function Settings() {
  const { colorScheme, setColorScheme } = useColorScheme()
  const isDark = colorScheme === "dark"
  const iconColor = useIconColor()
  const mutedColor = useIconColor("muted")
  const [notifsEnabled, setNotifsEnabled] = useState(true)
  const [browserName, setBrowserName] = useState("System Default")

  useFocusEffect(useCallback(() => {
    getNotificationsEnabled().then(setNotifsEnabled)

    getCurrentUserId().then((id) => {
      if (!id) return
      fetchPreferences(id).then((prefs) => {
        const browserId = prefs.browser as BrowserId | undefined
        const match = BROWSERS.find((b) => b.id === browserId)
        setBrowserName(match?.name ?? "System Default")
      }).catch(() => {})
    })
  }, []))

  const toggleTheme = async () => {
    const next = isDark ? "light" : "dark"
    setColorScheme(next)
    await SecureStore.setItemAsync(THEME_KEY, next)
  }

  const toggleNotifications = async () => {
    const next = !notifsEnabled
    if (next) await requestNotificationPermission()
    await setNotificationsEnabled(next)
    setNotifsEnabled(next)
  }

  return (
    <View className="flex-1 bg-background">
      <ScreenHeader title="Settings" />

      <ScrollView className="flex-1 px-4 py-4">

        <View className="gap-2">

          <ListItem
            title="Default Browser"
            subtitle={browserName}
            leftIcon={<ExternalLink size={20} color={iconColor} />}
            rightElement={<ChevronRight size={20} color={mutedColor} />}
            onPress={() => router.push("/browser-settings")}
          />

          <ListItem
            title="Notifications"
            leftIcon={<Bell size={20} color={iconColor} />}
            onPress={toggleNotifications}
            rightElement={
              <View className={`h-6 w-11 rounded-full ${notifsEnabled ? "bg-primary" : "bg-secondary"}`}>
                <View
                  className={`absolute top-0.5 h-5 w-5 rounded-full bg-white ${notifsEnabled ? "right-0.5" : "left-0.5"}`}
                />
              </View>
            }
          />

          <ListItem
            title="Dark Mode"
            leftIcon={<Moon size={20} color={iconColor} />}
            onPress={toggleTheme}
            rightElement={
              <View className={`h-6 w-11 rounded-full ${isDark ? "bg-primary" : "bg-secondary"}`}>
                <View
                  className={`absolute top-0.5 h-5 w-5 rounded-full bg-white ${isDark ? "right-0.5" : "left-0.5"}`}
                />
              </View>
            }
          />

          <ListItem
            title="App Feedback"
            leftIcon={<MessageSquare size={20} color={iconColor} />}
            rightElement={<ChevronRight size={20} color={mutedColor} />}
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