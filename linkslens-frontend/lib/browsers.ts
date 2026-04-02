export const BROWSERS = [
  { id: "system",  name: "System Default" },
  { id: "chrome",  name: "Google Chrome" },
  { id: "firefox", name: "Firefox" },
  { id: "edge",    name: "Microsoft Edge" },
] as const

export type BrowserId = (typeof BROWSERS)[number]["id"]

// "system" is intentionally absent — callers use undefined as the signal to open the URL directly
export const BROWSER_SCHEMES: Record<string, string> = {
  chrome:  "googlechrome://",
  firefox: "firefox://open-url?url=",
  edge:    "microsoft-edge://",
}
