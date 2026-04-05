import * as Notifications from "expo-notifications"
import type { ScanStatus } from "./types"

export function initNotificationHandler() {
  Notifications.setNotificationHandler({
    handleNotification: async () => ({
      shouldShowAlert: true,
      shouldPlaySound: true,
      shouldSetBadge: false,
      shouldShowBanner: true,
      shouldShowList: true,
    }),
  })
}

/** Request notification permissions. Safe to call multiple times. */
export async function requestNotificationPermission(): Promise<boolean> {
  const { status } = await Notifications.requestPermissionsAsync()
  return status === "granted"
}

const STATUS_LABEL: Record<ScanStatus, string> = {
  SAFE:        "Safe",
  SUSPICIOUS:  "Suspicious",
  MALICIOUS:   "Malicious",
  UNAVAILABLE: "Unavailable",
}

const STATUS_BODY: Record<ScanStatus, string> = {
  SAFE:        "No threats detected. The URL appears safe to visit.",
  SUSPICIOUS:  "This URL may be suspicious. Proceed with caution.",
  MALICIOUS:   "This URL is flagged as malicious. Do not visit it.",
  UNAVAILABLE: "The URL could not be reached or analysed.",
}

/**
 * Fire an immediate local notification showing the scan result.
 * Fails silently — a notification failure must never block navigation.
 */
export async function notifyScanComplete(
  status: ScanStatus,
  url: string,
): Promise<void> {
  try {
    const label = STATUS_LABEL[status] ?? status
    const body  = STATUS_BODY[status]  ?? "Scan complete."

    await Notifications.scheduleNotificationAsync({
      content: {
        title: `Scan Complete: ${label}`,
        body,
        subtitle: url.length > 60 ? url.slice(0, 57) + "…" : url,
        data: { status, url },
      },
      trigger: null,
    })
  } catch {
    // Non-blocking — notification failure should never affect the scan flow
  }
}
