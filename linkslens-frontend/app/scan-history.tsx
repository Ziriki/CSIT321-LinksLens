import { View, Text, ScrollView,Pressable } from "react-native"
import { router } from "expo-router"
import { 
  Search, 
  ChevronDown, 
  ScanLine, 
  Square, 
  CheckSquare, 
  Trash2,
  Home,
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


export default function scanHistory() {
  return (
    <View className="flex-1 bg-background">

      {/* Header */}
      <View className="flex-row items-center justify-between border-b border-border bg-background px-4 py-3">
        <View className="w-10" />
        <Text className="text-lg font-semibold text-foreground">
          Previous Scans
        </Text>

        <Pressable className="p-2">
          <CheckSquare size={20} />
        </Pressable>
      </View>

      {/* Search */}
      <View className="px-4 pt-3">
        <View className="flex-row items-center gap-3 rounded-xl bg-secondary px-4 py-3">
          <Search size={20} />
          <Text className="text-muted-foreground">Search scans...</Text>
        </View>
      </View>

      {/* Filters */}
      <View className="flex-row gap-2 px-4 py-3">

        <View className="flex-1 flex-row items-center justify-between rounded-xl border border-border bg-card px-3 py-2.5">
          <View>
            <Text className="text-[10px] uppercase tracking-wide text-muted-foreground">
              Status
            </Text>
            <Text className="text-sm font-medium text-foreground">All</Text>
          </View>
          <ChevronDown size={16} />
        </View>

        <View className="flex-1 flex-row items-center justify-between rounded-xl border border-border bg-card px-3 py-2.5">
          <View>
            <Text className="text-[10px] uppercase tracking-wide text-muted-foreground">
              Date
            </Text>
            <Text className="text-sm font-medium text-foreground">All Time</Text>
          </View>
          <ChevronDown size={16} />
        </View>

        <View className="flex-1 flex-row items-center justify-between rounded-xl border border-border bg-card px-3 py-2.5">
          <View>
            <Text className="text-[10px] uppercase tracking-wide text-muted-foreground">
              Source
            </Text>
            <Text className="text-sm font-medium text-foreground">All</Text>
          </View>
          <ChevronDown size={16} />
        </View>

      </View>

      {/* List */}
      <ScrollView className="flex-1 px-4 pb-4">

        {/* Item 1 */}
        <View className="flex-row items-center gap-3 rounded-xl border border-border bg-card px-4 py-3">
          <CheckSquare size={20} />

          <View className="h-10 w-10 items-center justify-center rounded-full bg-secondary">
            <ScanLine size={20} />
          </View>

          <View className="flex-1">
            <Text className="font-medium text-foreground">
              example-url.com/page
            </Text>
            <Text className="text-sm text-muted-foreground">
              Gallery - 2 hours ago
            </Text>
          </View>

          <RiskBadge riskLevel="safe" size="sm" />
        </View>

        {/* Item 2 */}
        <View className="mt-2 flex-row items-center gap-3 rounded-xl border border-border bg-card px-4 py-3">
          <Square size={20} />

          <View className="h-10 w-10 items-center justify-center rounded-full bg-secondary">
            <ScanLine size={20} />
          </View>

          <View className="flex-1">
            <Text className="font-medium text-foreground">
              suspicious-link.net
            </Text>
            <Text className="text-sm text-muted-foreground">
              Manual - Yesterday
            </Text>
          </View>

          <RiskBadge riskLevel="suspicious" size="sm" />
        </View>

        {/* Item 3 */}
        <View className="mt-2 flex-row items-center gap-3 rounded-xl border-2 border-primary bg-card px-4 py-3">
          <CheckSquare size={20} />

          <View className="h-10 w-10 items-center justify-center rounded-full bg-secondary">
            <ScanLine size={20} />
          </View>

          <View className="flex-1">
            <Text className="font-medium text-foreground">
              malicious-site.xyz
            </Text>
            <Text className="text-sm text-muted-foreground">
              Gallery - 3 days ago
            </Text>
          </View>

          <RiskBadge riskLevel="malicious" size="sm" />
        </View>

      </ScrollView>

      {/* Delete bar */}
      <View className="border-t border-border bg-card px-4 py-3">

        <View className="mb-3 flex-row items-center justify-between">
          <Text className="text-sm text-muted-foreground">
            2 items selected
          </Text>

          <Text className="text-sm font-medium text-primary">
            Select All
          </Text>
        </View>

        <AppButton fullWidth variant="primary">
          <View className="flex-row items-center justify-center gap-2">
            <Trash2 size={16} color="white" />
            <Text className="text-white">Delete Selected</Text>
          </View>
        </AppButton>

      </View>

      <BottomNav activeIndex={2} items={bottomNavItems} />

    </View>
  )
}