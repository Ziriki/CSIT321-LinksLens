import { View, Text } from "react-native"
import { Check } from "lucide-react-native"
import { ScreenHeader, ListItem } from "../components/ui-components"

export default function languageSettings() {
  const languages = [
    { code: "en", name: "English", selected: true },
    { code: "es", name: "Spanish", selected: false },
    { code: "fr", name: "French", selected: false },
    { code: "de", name: "German", selected: false },
    { code: "zh", name: "Chinese", selected: false },
  ]

  return (
    <View className="flex-1 bg-background">
      <ScreenHeader title="Language" />

      <View className="flex-1 px-4 py-4">
        <Text className="mb-4 text-sm text-muted-foreground">
            Select the language you want the app to be displayed in. 
        </Text>
        
        <View className="flex-col gap-2">
          {languages.map((lang) => (
            <ListItem
              key={lang.code}
              title={lang.name}
              rightElement={
                lang.selected ? <Check size={20} color="#2563eb" /> : undefined
              }
            />
          ))}
        </View>
          <Text className="mt-2 text-center text-xs text-muted-foreground">
            Images are always downloaded in English regardless of the selected language.
          </Text>
      </View>
    </View>
  )
}