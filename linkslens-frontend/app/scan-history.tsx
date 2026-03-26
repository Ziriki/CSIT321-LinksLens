import { useEffect, useState, useMemo } from "react"
import { View, Text, ScrollView, Pressable, Alert } from "react-native"
import { router } from "expo-router"
import {
  Search,
  ScanLine,
  Trash2,
} from "lucide-react-native"

import {
  RiskBadge,
  AppButton,
  BottomNav,
} from "../components/ui-components"
import { fetchScanHistory, clearScanHistory, getCurrentUserId } from "../lib/api"
import type { ScanHistoryItem, ScanResponse } from "../lib/api"
import { statusToRisk } from "../lib/types"
import { bottomNavItems } from "../lib/navigation"

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  const days = Math.floor(hrs / 24)
  return `${days}d ago`
}

export default function ScanHistory() {
  const [scans, setScans] = useState<ScanHistoryItem[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState("")

  useEffect(() => {
    loadScans()
  }, [])

  async function loadScans() {
    setLoading(true)
    try {
      const data = await fetchScanHistory()
      setScans(data)
    } catch {
      // Silently fail
    } finally {
      setLoading(false)
    }
  }

  async function handleClearAll() {
    Alert.alert("Clear History", "Delete all scan history?", [
      { text: "Cancel", style: "cancel" },
      {
        text: "Delete All",
        style: "destructive",
        onPress: async () => {
          try {
            const userId = await getCurrentUserId()
            if (userId) await clearScanHistory(userId)
            setScans([])
          } catch {
            Alert.alert("Error", "Failed to clear history.")
          }
        },
      },
    ])
  }

  const filtered = useMemo(
    () => search
      ? scans.filter((s) => s.InitialURL.toLowerCase().includes(search.toLowerCase()))
      : scans,
    [scans, search],
  )

  return (
    <View className="flex-1 bg-background">
      {/* Header */}
      <View className="flex-row items-center justify-between border-b border-border bg-background px-4 py-3">
        <View className="w-10" />
        <Text className="text-lg font-semibold text-foreground">
          Previous Scans
        </Text>
        <Pressable className="p-2" onPress={handleClearAll}>
          <Trash2 size={20} color="#dc2626" />
        </Pressable>
      </View>

      {/* Search */}
      <View className="px-4 pt-3">
        <View className="flex-row items-center gap-3 rounded-xl bg-secondary px-4 py-3">
          <Search size={20} />
          <Text
            className="flex-1 text-muted-foreground"
            onPress={() => {/* TODO: open search input */}}
          >
            {search || "Search scans..."}
          </Text>
        </View>
      </View>

      {/* List */}
      <ScrollView className="flex-1 px-4 py-3">
        {loading && (
          <Text className="text-center text-muted-foreground py-8">Loading...</Text>
        )}

        {!loading && filtered.length === 0 && (
          <Text className="text-center text-muted-foreground py-8">No scans yet.</Text>
        )}

        {filtered.map((scan) => (
          <Pressable
            key={scan.ScanID}
            className="mb-2 flex-row items-center gap-3 rounded-xl border border-border bg-card px-4 py-3"
            onPress={() =>
              router.push({
                pathname: "/scan-results",
                params: {
                  result: JSON.stringify({
                    scan_id: scan.ScanID,
                    user_id: scan.UserID,
                    uuid: null,
                    initial_url: scan.InitialURL,
                    redirect_url: scan.RedirectURL,
                    status_indicator: scan.StatusIndicator,
                    score: 0,
                    server_location: scan.ServerLocation,
                    ip_address: null,
                    screenshot_url: scan.ScreenshotURL,
                    brands: [],
                    tags: [],
                    result_url: "",
                    gsb_flagged: false,
                    gsb_threat_types: [],
                    scanned_at: scan.ScannedAt,
                  } satisfies ScanResponse),
                },
              })
            }
          >
            <View className="h-10 w-10 items-center justify-center rounded-full bg-secondary">
              <ScanLine size={20} />
            </View>

            <View className="flex-1">
              <Text className="font-medium text-foreground" numberOfLines={1}>
                {scan.InitialURL}
              </Text>
              <Text className="text-sm text-muted-foreground">
                {timeAgo(scan.ScannedAt)}
              </Text>
            </View>

            <RiskBadge riskLevel={statusToRisk(scan.StatusIndicator)} size="sm" />
          </Pressable>
        ))}
      </ScrollView>

      <BottomNav activeIndex={2} items={bottomNavItems} />
    </View>
  )
}
