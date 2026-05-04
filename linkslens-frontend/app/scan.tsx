import { View, Text } from "react-native"
import { router } from "expo-router"
import { Image as ImageIcon, Link2, QrCode } from "lucide-react-native"
import {
  Card,
  ScreenHeader,
  BottomNav,
} from "../components/ui-components"
import { bottomNavItems } from "../lib/navigation"

export default function scan() {
  return (
    <View className="flex-1 bg-background">
      <ScreenHeader title="Scan Link" />

      <View className="flex-1 px-4 py-6">

        <Text className="mb-8 text-center text-muted-foreground">
          How do you want to provide the link?
        </Text>

        <View className="gap-4">

          {/* Gallery Upload */}
          <Card
            className="flex-row items-center"
            onPress={() => router.push("/scan-image")}
          >
            <View className="mr-4 h-14 w-14 items-center justify-center rounded-xl bg-primary/10">
              <ImageIcon size={28} color="#2563eb" />
            </View>

            <View className="flex-1">
              <Text className="font-semibold text-foreground">
                Scan Image
              </Text>

              <Text className="text-sm text-muted-foreground">
                Take or Upload an image with a link
              </Text>
            </View>
          </Card>

          {/* QR Code Scanner */}
          <Card
            className="flex-row items-center"
            onPress={() => router.push("/scan-qr")}
          >
            <View className="mr-4 h-14 w-14 items-center justify-center rounded-xl bg-primary/10">
              <QrCode size={28} color="#2563eb" />
            </View>

            <View className="flex-1">
              <Text className="font-semibold text-foreground">
                Scan QR code
              </Text>

              <Text className="text-sm text-muted-foreground">
                Detect phishing links hidden in QR codes
              </Text>
            </View>
          </Card>

          {/* Manual Entry */}
          <Card
            className="flex-row items-center"
            onPress={() => router.push("/scan-link")}
          >
            <View className="mr-4 h-14 w-14 items-center justify-center rounded-xl bg-primary/10">
              <Link2 size={28} color="#2563eb" />
            </View>

            <View className="flex-1">
              <Text className="font-semibold text-foreground">
                Enter link
              </Text>

              <Text className="text-sm text-muted-foreground">
                Type or paste a link directly
              </Text>
            </View>
          </Card>

        </View>

      </View>

      <BottomNav activeIndex={1} items={bottomNavItems} />
    </View>
  )
}