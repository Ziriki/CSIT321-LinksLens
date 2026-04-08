import { useState, useEffect } from "react"
import { View, Text } from "react-native"
import { router, useLocalSearchParams } from "expo-router"
import {
  InputField,
  ScreenHeader,
  AppButton
} from "../components/ui-components"

export default function ScanLink() {
  const { url: sharedUrl } = useLocalSearchParams<{ url?: string }>()
  const [url, setUrl] = useState(sharedUrl ?? "")

  useEffect(() => {
    if (sharedUrl) setUrl(sharedUrl)
  }, [sharedUrl])

  return (
    <View className="flex-1 bg-background">
      <ScreenHeader title="Enter Link" />

      <View className="flex-1 px-4 py-6">

        <InputField
          label="Enter URL"
          placeholder="https://example.com"
          value={url}
          onChangeText={setUrl}
        />

        <Text className="mt-3 text-sm text-muted-foreground">
          Paste or type the link you want to scan
        </Text>

        <View className="mt-8">
          <AppButton
            fullWidth
            size="lg"
            disabled={!url.trim()}
            onPress={() => {
              const raw = url.trim()
              const normalized = /^https?:\/\//i.test(raw) ? raw : `http://${raw}`
              router.push({ pathname: "/scan-processing", params: { url: normalized } })
            }}
          >
            Scan URL
          </AppButton>
        </View>

      </View>
    </View>
  )
}
