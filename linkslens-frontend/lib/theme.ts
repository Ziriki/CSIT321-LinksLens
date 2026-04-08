import { vars } from "nativewind"
import { useColorScheme } from "nativewind"

export const THEME_KEY = "app_theme"

export function getBackgroundColor(scheme: string | undefined | null): string {
  return scheme === "dark" ? "#0f172a" : "#ffffff"
}

export const lightVars = vars({
  "--background": "#ffffff",
  "--foreground": "#171717",
  "--card": "#ffffff",
  "--card-foreground": "#171717",
  "--secondary": "#f3f4f6",
  "--secondary-foreground": "#171717",
  "--muted": "#f3f4f6",
  "--muted-foreground": "#6b7280",
  "--border": "#e5e7eb",
  "--input": "#e5e7eb",
})

export const darkVars = vars({
  "--background": "#0f172a",
  "--foreground": "#f8fafc",
  "--card": "#1e293b",
  "--card-foreground": "#f8fafc",
  "--secondary": "#334155",
  "--secondary-foreground": "#f8fafc",
  "--muted": "#334155",
  "--muted-foreground": "#94a3b8",
  "--border": "#334155",
  "--input": "#334155",
})

const iconColor = {
  light: "#171717",
  dark: "#f8fafc",
  lightMuted: "#6b7280",
  darkMuted: "#94a3b8",
}

/** Returns the correct icon hex color for the current scheme. */
export function useIconColor(variant: "default" | "muted" = "default") {
  const { colorScheme } = useColorScheme()
  if (variant === "muted") {
    return colorScheme === "dark" ? iconColor.darkMuted : iconColor.lightMuted
  }
  return colorScheme === "dark" ? iconColor.dark : iconColor.light
}
