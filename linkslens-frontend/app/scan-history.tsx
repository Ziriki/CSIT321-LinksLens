import { useEffect, useState, useMemo } from "react"
import { View, Text, ScrollView, Pressable, Alert, TextInput } from "react-native"
import { router } from "expo-router"
import {
  Search,
  ScanLine,
  Trash2,
  X,
  CheckSquare,
  Square,
} from "lucide-react-native"

import {
  RiskBadge,
  BottomNav,
} from "../components/ui-components"
import { fetchScanHistory, deleteScan, scanHistoryToResponse } from "../lib/api"
import type { ScanHistoryItem } from "../lib/api"
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
  const [selectMode, setSelectMode] = useState(false)
  const [selected, setSelected] = useState<Set<number>>(new Set())

  useEffect(() => { loadScans() }, [])

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

  const filtered = useMemo(
    () =>
      scans.filter((s: ScanHistoryItem) => {
        const matchesStatus = filterStatus === "ALL" || s.StatusIndicator === filterStatus
        const matchesSearch = !search || s.InitialURL.toLowerCase().includes(search.toLowerCase())
        return matchesStatus && matchesSearch
      }),
    [scans, search, filterStatus],
  )

  function exitSelectMode() {
    setSelectMode(false)
    setSelected(new Set())
  }

  function toggleSelect(scanId: number) {
    setSelected(prev => {
      const next = new Set(prev)
      next.has(scanId) ? next.delete(scanId) : next.add(scanId)
      return next
    })
  }

  const allFilteredSelected = filtered.length > 0 && filtered.every(s => selected.has(s.ScanID))

  function toggleSelectAll() {
    setSelected(prev => {
      const next = new Set(prev)
      filtered.forEach((s: ScanHistoryItem) => allFilteredSelected ? next.delete(s.ScanID) : next.add(s.ScanID))
      return next
    })
  }

  async function handleDeleteSingle(scanId: number) {
    Alert.alert("Delete Scan", "Delete this scan from your history?", [
      { text: "Cancel", style: "cancel" },
      {
        text: "Delete",
        style: "destructive",
        onPress: async () => {
          try {
            await deleteScan(scanId)
            setScans(prev => prev.filter(s => s.ScanID !== scanId))
          } catch {
            Alert.alert("Error", "Failed to delete scan.")
          }
        },
      },
    ])
  }

  async function handleDeleteSelected() {
    if (selected.size === 0) return
    Alert.alert(
      "Delete Scans",
      `Delete ${selected.size} selected scan${selected.size > 1 ? "s" : ""}?`,
      [
        { text: "Cancel", style: "cancel" },
        {
          text: "Delete",
          style: "destructive",
          onPress: async () => {
            try {
              await Promise.all([...selected].map(id => deleteScan(id)))
              setScans(prev => prev.filter(s => !selected.has(s.ScanID)))
              exitSelectMode()
            } catch {
              Alert.alert("Error", "Failed to delete selected scans.")
            }
          },
        },
      ]
    )
  }

  return (
    <View className="flex-1 bg-background">

      {/* Header */}
      <View className="flex-row items-center justify-between border-b border-border bg-background px-4 py-3">
        {selectMode ? (
          <Pressable className="p-2" onPress={exitSelectMode}>
            <X size={20} color={iconColor} />
          </Pressable>
        ) : (
          <View className="w-10" />
        )}

        <Text className="text-lg font-semibold text-foreground">
          {selectMode
            ? selected.size > 0 ? `${selected.size} selected` : "Select Scans"
            : "Previous Scans"}
        </Text>

        <View className="flex-row items-center gap-1">
          {selectMode ? (
            <>
              <Pressable className="p-2" onPress={toggleSelectAll}>
                {allFilteredSelected
                  ? <CheckSquare size={20} color="#2563eb" />
                  : <Square size={20} color={iconColor} />}
              </Pressable>
              <Pressable
                className="p-2"
                onPress={handleDeleteSelected}
                disabled={selected.size === 0}
              >
                <Trash2 size={20} color={selected.size > 0 ? "#dc2626" : "#6b7280"} />
              </Pressable>
            </>
          ) : (
            <Pressable className="p-2" onPress={() => setSelectMode(true)}>
              <CheckSquare size={20} color={iconColor} />
            </Pressable>
          )}
        </View>
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
        className="px-4 pt-2 pb-2"
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
            <Text className={`text-xs font-medium ${filterStatus === opt ? "text-white" : "text-foreground"}`}>
              {opt}
            </Text>
          </Pressable>
        ))}
      </ScrollView>

      {/* List */}
      <ScrollView className="flex-1 px-4 py-3">
        {loading && (
          <Text className="py-8 text-center text-muted-foreground">Loading...</Text>
        )}

        {!loading && filtered.length === 0 && (
          <Text className="py-8 text-center text-muted-foreground">No scans found.</Text>
        )}

        {filtered.map((scan: ScanHistoryItem) => {
          const isSelected = selected.has(scan.ScanID)
          return (
            <Pressable
              key={scan.ScanID}
              className={`mb-2 flex-row items-center gap-3 rounded-xl border px-4 py-3 ${
                isSelected ? "border-primary bg-primary/10" : "border-border bg-card"
              }`}
              onPress={() => {
                if (selectMode) {
                  toggleSelect(scan.ScanID)
                } else {
                  router.push({
                    pathname: "/scan-results",
                    params: { result: JSON.stringify(scanHistoryToResponse(scan)) },
                  })
                }
              }}
              onLongPress={() => {
                if (!selectMode) {
                  setSelectMode(true)
                  setSelected(new Set([scan.ScanID]))
                }
              }}
            >
              {selectMode ? (
                <View className={`h-6 w-6 items-center justify-center rounded-full border-2 ${
                  isSelected ? "border-primary bg-primary" : "border-border"
                }`}>
                  {isSelected && <Text className="text-xs font-bold text-white">✓</Text>}
                </View>
              ) : (
                <View className="h-10 w-10 items-center justify-center rounded-full bg-secondary">
                  <ScanLine size={20} color={iconColor} />
                </View>
              )}

              <View className="flex-1">
                <Text className="font-medium text-foreground" numberOfLines={1}>
                  {scan.InitialURL}
                </Text>
                <Text className="text-sm text-muted-foreground">
                  {timeAgo(scan.ScannedAt)}
                </Text>
              </View>

              <View className="flex-row items-center gap-2">
                <RiskBadge riskLevel={statusToRisk(scan.StatusIndicator)} size="sm" />
                {!selectMode && (
                  <Pressable
                    hitSlop={8}
                    onPress={() => handleDeleteSingle(scan.ScanID)}
                  >
                    <Trash2 size={18} color="#dc2626" />
                  </Pressable>
                )}
              </View>
            </Pressable>
          )
        })}
      </ScrollView>

      <BottomNav activeIndex={2} items={bottomNavItems} />
    </View>
  )
}
