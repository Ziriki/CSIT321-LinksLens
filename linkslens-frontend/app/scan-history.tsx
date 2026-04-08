import { useEffect, useState, useMemo } from "react"
import { View, Text, ScrollView, Pressable, Alert, TextInput } from "react-native"
import { router } from "expo-router"
import {
  Search,
  ScanLine,
  Trash2,
} from "lucide-react-native"

import {
  RiskBadge,
  BottomNav,
} from "../components/ui-components"
import { fetchScanHistory, clearScanHistory, getCurrentUserId } from "../lib/api"
import type { ScanHistoryItem, ScanResponse } from "../lib/api"
import { statusToRisk } from "../lib/types"
import { bottomNavItems } from "../lib/navigation"
import { useIconColor } from "../lib/theme"

const FILTER_OPTIONS = ["ALL", "SAFE", "SUSPICIOUS", "MALICIOUS"] as const
type FilterOption = (typeof FILTER_OPTIONS)[number]

const FILTER_COLORS: Record<FilterOption, string> = {
  ALL:        "bg-primary",
  SAFE:       "bg-green-600",
  SUSPICIOUS: "bg-yellow-500",
  MALICIOUS:  "bg-red-600",
}

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
  const iconColor = useIconColor()
  const [scans, setScans] = useState<ScanHistoryItem[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState("")
  const [filterStatus, setFilterStatus] = useState<FilterOption>("ALL")

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
    () =>
      scans.filter((s: ScanHistoryItem) => {
        const matchesStatus =
          filterStatus === "ALL" || s.StatusIndicator === filterStatus
        const matchesSearch =
          !search ||
          s.InitialURL.toLowerCase().includes(search.toLowerCase())
        return matchesStatus && matchesSearch
      }),
    [scans, search, filterStatus],
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
          <Search size={20} color={iconColor} />
          <TextInput
            className="flex-1 text-foreground"
            placeholder="Search scans..."
            placeholderTextColor="#9ca3af"
            value={search}
            onChangeText={setSearch}
            autoCapitalize="none"
            autoCorrect={false}
          />
        </View>
      </View>

      {/* Status filter chips */}
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        className="px-4 pt-2"
        style={{ flexGrow: 0 }}
        contentContainerStyle={{ paddingRight: 16 }}
      >
        {FILTER_OPTIONS.map((opt) => (
          <Pressable
            key={opt}
            className={`mr-2 rounded-full px-4 py-1.5 h-10 flex items-center justify-center ${
              filterStatus === opt ? FILTER_COLORS[opt] : "bg-secondary"
            }`}
            onPress={() => setFilterStatus(opt)}
          >
            <Text
              className={`text-xs font-medium ${
                filterStatus === opt ? "text-white" : "text-foreground"
              }`}
            >
              {opt}
            </Text>
          </Pressable>
        ))}
      </ScrollView>

      {/* List */}
      <ScrollView className="flex-1 px-4 py-3">
        {loading && (
          <Text className="py-8 text-center text-muted-foreground">
            Loading...
          </Text>
        )}

        {!loading && filtered.length === 0 && (
          <Text className="py-8 text-center text-muted-foreground">
            No scans found.
          </Text>
        )}

        {filtered.map((scan: ScanHistoryItem) => (
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
                    redirect_chain: scan.RedirectChain ?? null,
                    status_indicator: (scan.StatusIndicator ?? "UNAVAILABLE") as ScanResponse["status_indicator"],
                    score: 0,
                    domain_age_days: scan.DomainAgeDays ?? null,
                    server_location: scan.ServerLocation,
                    ip_address: null,
                    screenshot_url: scan.ScreenshotURL,
                    brands: [],
                    tags: [],
                    result_url: "",
                    gsb_flagged: false,
                    gsb_threat_types: [],
                    script_analysis: scan.ScriptAnalysis ?? null,
                    homograph_analysis: scan.HomographAnalysis ?? null,
                    scanned_at: scan.ScannedAt,
                  } satisfies ScanResponse),
                },
              })
            }
          >
            <View className="h-10 w-10 items-center justify-center rounded-full bg-secondary">
              <ScanLine size={20} color={iconColor} />
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
