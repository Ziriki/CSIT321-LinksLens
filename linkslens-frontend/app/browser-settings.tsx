import { useEffect, useRef, useState } from "react"
import { View, Text, Alert } from "react-native"
import { Check } from "lucide-react-native"
import { ScreenHeader, ListItem } from "../components/ui-components"
import { fetchPreferences, updatePreferences, getCurrentUserId } from "../lib/api"
import { BROWSERS, type BrowserId } from "../lib/browsers"

export default function BrowserSettings() {
  const [selected, setSelected] = useState<BrowserId>("system")
  const userIdRef = useRef<number | null>(null)

  useEffect(() => {
    getCurrentUserId().then((id) => {
      userIdRef.current = id
      if (id) {
        fetchPreferences(id)
          .then((prefs) => { if (prefs.browser) setSelected(prefs.browser as BrowserId) })
          .catch(() => {})
      }
    })
  }, [])

  async function handleSelect(browserId: BrowserId) {
    setSelected(browserId)
    if (!userIdRef.current) return
    try {
      await updatePreferences(userIdRef.current, { browser: browserId })
    } catch {
      Alert.alert("Error", "Could not save browser preference.")
    }
  }

  return (
    <View className="flex-1 bg-background">
      <ScreenHeader title="Default Browser" />

      <View className="flex-1 px-4 py-4">
        <Text className="mb-4 text-sm text-muted-foreground">
          Select which browser is used to open links from the scan result page.
        </Text>

        <View className="flex-col gap-2">
          {BROWSERS.map((browser) => (
            <ListItem
              key={browser.id}
              title={browser.name}
              onPress={() => handleSelect(browser.id)}
              rightElement={
                selected === browser.id
                  ? <Check size={20} color="#2563eb" />
                  : undefined
              }
            />
          ))}
        </View>
      </View>
    </View>
  )
}
