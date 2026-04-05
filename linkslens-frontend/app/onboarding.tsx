import { useState } from "react"
import { View, Text } from "react-native"
import { router } from "expo-router"
import { ShieldCheck, Camera, Link, BarChart2 } from "lucide-react-native"
import { AppButton, TextLink } from "../components/ui-components"
import { getCurrentUserId, updatePreferences, PREF_HAS_SEEN_ONBOARDING } from "../lib/api"

const SLIDES = [
  {
    icon: ShieldCheck,
    title: "Welcome to LinksLens",
    body: "Stay safe online — scan any link before you click it.",
  },
  {
    icon: Camera,
    title: "Scan with your camera",
    body: "Point your camera at any link or upload a photo from your gallery.",
  },
  {
    icon: Link,
    title: "Or type it manually",
    body: "Paste or type any URL directly for an instant safety check.",
  },
  {
    icon: BarChart2,
    title: "Understand the results",
    body: "Get a clear verdict — Safe, Suspicious, or Malicious — with a full breakdown.",
  },
]

export default function Onboarding() {
  const [step, setStep] = useState(0)
  const [completing, setCompleting] = useState(false)

  const { icon: Icon, title, body } = SLIDES[step]
  const isLast = step === SLIDES.length - 1

  async function completeOnboarding() {
    if (completing) return
    setCompleting(true)
    try {
      const userId = await getCurrentUserId()
      if (userId) await updatePreferences(userId, { [PREF_HAS_SEEN_ONBOARDING]: "true" })
    } catch { /* non-critical — proceed anyway */ }
    router.replace("/home")
  }

  return (
    <View className="flex-1 bg-background">

      {/* Slide content */}
      <View className="flex-1 items-center justify-center px-8">
        <View className="mb-8 h-32 w-32 items-center justify-center rounded-full bg-primary/10">
          <Icon size={64} color="#2563eb" />
        </View>

        <Text className="mb-4 text-center text-2xl font-bold text-foreground">
          {title}
        </Text>

        <Text className="text-center text-base leading-6 text-muted-foreground">
          {body}
        </Text>
      </View>

      {/* Progress dots */}
      <View className="flex-row items-center justify-center gap-2 pb-6">
        {SLIDES.map((_, i) => (
          <View
            key={i}
            className={`h-2 rounded-full ${
              i === step ? "w-6 bg-primary" : "w-2 bg-secondary"
            }`}
          />
        ))}
      </View>

      {/* Actions */}
      <View className="gap-3 px-6 pb-10">
        <AppButton
          fullWidth
          onPress={isLast ? completeOnboarding : () => setStep(step + 1)}
          disabled={completing}
        >
          {isLast ? "Get Started" : "Next"}
        </AppButton>

        {!isLast && (
          <View className="items-center py-1">
            <TextLink onPress={completeOnboarding}>Skip</TextLink>
          </View>
        )}
      </View>

    </View>
  )
}
