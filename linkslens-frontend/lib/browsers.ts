import * as Linking from "expo-linking"

export const BROWSERS = [
  { id: "system",  name: "System Default" },
  { id: "chrome",  name: "Google Chrome" },
  { id: "firefox", name: "Firefox" },
  { id: "edge",    name: "Microsoft Edge" },
] as const

export type BrowserId = (typeof BROWSERS)[number]["id"]

// Android package names for each browser.
// "system" is absent — callers fall back to Linking.openURL(url) directly.
// intent:// URIs (built in scan-results.tsx) target the package directly,
// bypassing the Android 11+ <queries> manifest requirement for custom schemes.
export const BROWSER_PACKAGES: Partial<Record<BrowserId, string>> = {
  chrome:  "com.android.chrome",
  firefox: "org.mozilla.firefox",
  edge:    "com.microsoft.emmx",
}

// Custom URL schemes used to probe whether a browser is installed.
// "system" is always available so it has no entry.
const BROWSER_PROBE_URLS: Partial<Record<BrowserId, string>> = {
  chrome:  "googlechrome://",
  firefox: "firefox://",
  edge:    "microsoft-edge://",
}

/**
 * Returns the set of browser IDs that are installed on the device.
 * "system" is always included. Others are detected via Linking.canOpenURL.
 */
export async function getInstalledBrowserIds(): Promise<Set<BrowserId>> {
  const installed = new Set<BrowserId>(["system"])
  await Promise.all(
    (Object.entries(BROWSER_PROBE_URLS) as [BrowserId, string][]).map(
      async ([id, probeUrl]) => {
        try {
          if (await Linking.canOpenURL(probeUrl)) installed.add(id)
        } catch { /* treat as not installed */ }
      }
    )
  )
  return installed
}
