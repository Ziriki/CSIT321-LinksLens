import { useEffect, useState } from "react"
import { View, Text, ScrollView, Pressable } from "react-native"
import { router } from "expo-router"
import {
  User,
  Shield,
  Image as ImageIcon,
  Link2,
  QrCode,
  ChevronRight,
  ScanLine,
  Clock,
  Settings,
} from "lucide-react-native"
import {
  Card,
  RiskBadge,
  ListItem,
  SectionHeader,
  BottomNav,
} from "../components/ui-components"
import { fetchDetails, fetchScanHistory, getCurrentUserId, scanHistoryToResponse } from "../lib/api"
import type { ScanHistoryItem } from "../lib/api"
import { statusToRisk, countScansThisMonth } from "../lib/types"
import { bottomNavItems } from "../lib/navigation"
import { useIconColor } from "../lib/theme"

export default function HomePage() {
  const iconCol = useIconColor()
  const [name, setName] = useState("User")
  const [monthScans, setMonthScans] = useState(0)
  const [totalScans, setTotalScans] = useState(0)
  const [recentScans, setRecentScans] = useState<ScanHistoryItem[]>([])

  useEffect(() => {
    (async () => {
      try {
        const userId = await getCurrentUserId()
        if (!userId) return

        const [details, scans] = await Promise.all([
          fetchDetails(userId).catch(() => null),
          fetchScanHistory().catch(() => []),
        ])

        setName(details?.FullName ?? "User")
        setTotalScans(scans.length)
        setRecentScans(scans.slice(0, 3))

        setMonthScans(countScansThisMonth(scans))
      } catch {
        // Silently fail
      }
    })()
  }, [])

  return (
    <View className="flex-1 bg-background">
      {/* Header */}
      <View className="px-4 pt-4 pb-2">
        <View className="flex-row items-center justify-between">
          <View>
            <Text className="text-sm text-muted-foreground">Welcome back,</Text>
            <Text className="text-xl font-bold text-foreground">{name}</Text>
          </View>

          <Pressable
            className="h-11 w-11 items-center justify-center rounded-full bg-secondary"
            onPress={() => router.push("/profile")}
          >
            <User size={20} color={iconCol} />
          </Pressable>
        </View>
      </View>

      {/* Content */}
      <ScrollView className="flex-1 px-4" contentContainerStyle={{ paddingBottom: 16 }}>
        {/* Stats Card */}
        <Card className="mt-4 bg-primary p-6">
          <View className="flex-row items-center">
            <View className="mr-4 h-14 w-14 items-center justify-center rounded-xl bg-white/20">
              <Shield size={28} color="white" />
            </View>

            <View className="flex-1">
              <Text className="text-sm text-white/80">Scans this month</Text>
              <Text className="text-3xl font-bold text-white">{monthScans}</Text>
            </View>

            <View className="items-end">
              <Text className="text-sm text-white/80">Total scans</Text>
              <Text className="text-xl font-semibold text-white">{totalScans}</Text>
            </View>
          </View>
        </Card>

        {/* Scan Options */}
        <SectionHeader title="Start Scanning" className="mt-6" />

        <View className="mt-2 flex-row gap-2">
          <View className="flex-1">
            <Card className="items-center py-5" onPress={() => router.push("/scan-image")}>
              <View className="mb-2 h-12 w-12 items-center justify-center rounded-full bg-primary/10">
                <ImageIcon size={24} color="#2563eb" />
              </View>
              <Text className="text-xs font-medium text-foreground text-center">Scan Image</Text>
            </Card>
          </View>
          <View className="flex-1">
            <Card className="items-center py-5" onPress={() => router.push("/scan-qr")}>
              <View className="mb-2 h-12 w-12 items-center justify-center rounded-full bg-primary/10">
                <QrCode size={24} color="#2563eb" />
              </View>
              <Text className="text-xs font-medium text-foreground text-center">Scan QR</Text>
            </Card>
          </View>
          <View className="flex-1">
            <Card className="items-center py-5" onPress={() => router.push("/scan-link")}>
              <View className="mb-2 h-12 w-12 items-center justify-center rounded-full bg-primary/10">
                <Link2 size={24} color="#2563eb" />
              </View>
              <Text className="text-xs font-medium text-foreground text-center">Enter Link</Text>
            </Card>
          </View>
        </View>

        {/* Recent Scans */}
        <SectionHeader
          title="Recent Scans"
          className="mt-6"
          action={
            <View className="flex-row items-center">
              <Text className="mr-1 text-sm font-medium text-primary">View All</Text>
              <ChevronRight size={16} color="#2563eb" />
            </View>
          }
          onPressAction={() => router.push("/scan-history")}
        />

        <View className="mt-2 gap-2">
          {recentScans.length === 0 && (
            <Text className="text-sm text-muted-foreground py-2">No scans yet. Start scanning!</Text>
          )}
          {recentScans.map((scan) => (
            <ListItem
              key={scan.ScanID}
              title={scan.InitialURL}
              subtitle={new Date(scan.ScannedAt).toLocaleDateString("en-GB")}
              leftIcon={<ScanLine size={20} color={iconCol} />}
              rightElement={
                <RiskBadge riskLevel={statusToRisk(scan.StatusIndicator)} size="sm" />
              }
              onPress={() => router.push({
                pathname: "/scan-results",
                params: { result: JSON.stringify(scanHistoryToResponse(scan)) },
              })}
            />
          ))}
        </View>

        {/* Quick Actions */}
        <SectionHeader title="Quick Actions" className="mt-6" />

        <View className="mt-2 gap-2">
          <ListItem
            title="View History"
            subtitle="Browse all previous scans"
            leftIcon={<Clock size={20} color={iconCol} />}
            rightElement={<ChevronRight size={20} color={iconCol} />}
            onPress={() => router.push("/scan-history")}
          />

          <ListItem
            title="Settings"
            subtitle="Configure app preferences"
            leftIcon={<Settings size={20} color={iconCol} />}
            rightElement={<ChevronRight size={20} color={iconCol} />}
            onPress={() => router.push("/settings")}
          />
        </View>
      </ScrollView>

      <BottomNav activeIndex={0} items={bottomNavItems} />
    </View>
  )
}
