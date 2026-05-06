import { useEffect, useRef, useState } from "react"
import { View, Text } from "react-native"
import { router, useLocalSearchParams } from "expo-router"
import { Zap } from "lucide-react-native"
import { Card } from "../components/ui-components"
import * as Haptics from "expo-haptics"
import { scanUrl } from "../lib/api"
import { notifyScanComplete } from "../lib/notifications"
import type { ScanStatus } from "../lib/types"

// Timings mirror the real backend pipeline so messages stay accurate.
// Extra steps beyond 21s cover slow urlscan.io responses (max ~69s).
const STEPS = [
  { at: 0,  message: "Checking Google Safe Browsing database...", progress: 10 },
  { at: 2,  message: "Submitting URL to security scanner...",      progress: 22 },
  { at: 4,  message: "Waiting for scan analysis to complete...",   progress: 35 },
  { at: 14, message: "Retrieving server location...",              progress: 55 },
  { at: 17, message: "Checking domain registration age...",        progress: 68 },
  { at: 19, message: "Analysing redirect chain...",                progress: 78 },
  { at: 21, message: "Finalising verdict...",                      progress: 86 },
  { at: 35, message: "Still analysing, almost there...",           progress: 93 },
  { at: 55, message: "Wrapping up...",                             progress: 97 },
]

export default function ScanProcessing() {
  const { url } = useLocalSearchParams<{ url: string }>()

  const [stepIndex, setStepIndex] = useState(0)
  const timersRef = useRef<ReturnType<typeof setTimeout>[]>([])

  const { message, progress } = STEPS[stepIndex]

  useEffect(() => {
    if (!url) {
      router.back()
      return
    }

    timersRef.current = []

    for (let i = 1; i < STEPS.length; i++) {
      const id = setTimeout(() => setStepIndex(i), STEPS[i].at * 1000)
      timersRef.current.push(id)
    }

    scanUrl(url)
      .then((result) => {
        timersRef.current.forEach(clearTimeout)
        setStepIndex(STEPS.length - 1)
        const status = result.status_indicator as ScanStatus
        try {
          Haptics.notificationAsync(
            status === "SAFE"
              ? Haptics.NotificationFeedbackType.Success
              : status === "SUSPICIOUS"
                ? Haptics.NotificationFeedbackType.Warning
                : Haptics.NotificationFeedbackType.Error,
          )
        } catch { /* haptics unavailable on some devices */ }
        notifyScanComplete(status, url, result.scan_id)
        router.replace({
          pathname: "/scan-results",
          params: { result: JSON.stringify(result) },
        })
      })
      .catch((err) => {
        console.error("Scan error:", err?.message ?? err)
        timersRef.current.forEach(clearTimeout)
        router.replace({
          pathname: "/scan-results",
          params: { error: "Scan failed. Please try again." },
        })
      })

    return () => timersRef.current.forEach(clearTimeout)
  }, [url])

  return (
    <View className="flex-1 items-center justify-center bg-background px-6">
      {/* Scanning Visual */}
      <View className="relative mb-8">
        <View className="h-32 w-32 items-center justify-center rounded-full border-4 border-secondary">
          <View className="h-24 w-24 rounded-full border-4 border-primary" />
        </View>

        <View className="absolute inset-0 items-center justify-center">
          <Zap size={40} color="#2563eb" />
        </View>
      </View>

      <Text className="mb-2 text-xl font-bold text-foreground">
        Analyzing URL
      </Text>

      <Text className="mb-6 text-center text-muted-foreground">
        {message}
      </Text>

      {/* Progress Bar */}
      <View className="w-full">
        <View className="h-2 overflow-hidden rounded-full bg-secondary">
          <View
            className="h-full rounded-full bg-primary"
            style={{ width: `${progress}%` }}
          />
        </View>

        <Text className="mt-2 text-center text-sm text-muted-foreground">
          {progress}%
        </Text>
      </View>

      {/* URL Preview */}
      <Card className="mt-8 w-full">
        <Text className="mb-1 text-xs text-muted-foreground">
          Scanning
        </Text>

        <Text className="text-sm text-foreground" numberOfLines={1}>
          {url ?? "..."}
        </Text>
      </Card>
    </View>
  )
}
