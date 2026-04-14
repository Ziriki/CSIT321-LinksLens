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
