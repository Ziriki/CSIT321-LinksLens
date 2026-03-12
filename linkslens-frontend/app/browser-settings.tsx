import { View, Text } from "react-native"
import { Check } from "lucide-react-native"
import { ScreenHeader, ListItem } from "../components/ui-components"

export default function browserSettings() {
  const browsers = [
    { id: "system", name: "System Default", selected: false },
    { id: "chrome", name: "Google Chrome", subtitle: "Detected", selected: false },
    { id: "firefox", name: "Firefox", subtitle: "Detected", selected: false },
    { id: "edge", name: "Microsoft Edge", subtitle: "Not installed", selected: false },
  ]

  return (
    <View className="flex-1 bg-background">
      <ScreenHeader title="Default Browser" />

      <View className="flex-1 px-4 py-4">
        <Text className="mb-4 text-sm text-muted-foreground">
          Select which browser is used to open links from the scan result page.
        </Text>

        <View className="flex-col gap-2">
          {browsers.map((browser) => (
            <ListItem
              key={browser.id}
              title={browser.name}
              subtitle={browser.subtitle}
              rightElement={
                browser.selected ? <Check size={20} color="#2563eb" /> : undefined
              }
            />
          ))}
        </View>
      </View>
    </View>
  )
}