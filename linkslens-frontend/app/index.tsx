import { View, Text, Pressable, Image, Alert, Linking } from "react-native"
import { Eye } from "lucide-react-native"
import { router } from "expo-router"
import { useState } from "react"
import {
  AppButton,
  InputField,
  TextLink,
} from "../components/ui-components"
import { login, decodeToken, fetchPreferences, PREF_HAS_SEEN_ONBOARDING } from "../lib/api"

export default function LoginScreen() {
  //TODO: Change back after Demo!
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [loading, setLoading] = useState(false)

  const handleLogin = async () => {
    if (!email || !password) {
      Alert.alert("Error", "Please enter your email and password.")
      return
    }
    setLoading(true)
    try {
      const data = await login(email, password)
      const userId = decodeToken(data.access_token)?.user_id
      if (userId) {
        const prefs = await fetchPreferences(userId).catch(() => ({} as Record<string, string>))
        if (!prefs[PREF_HAS_SEEN_ONBOARDING]) {
          router.replace("/onboarding")
          return
        }
      }
      router.replace("/home")
    } catch (err: any) {
      Alert.alert("Login Failed", err.message ?? "Invalid email or password.")
    } finally {
      setLoading(false)
    }
  }

  return (
    <View className="flex-1 bg-background">
      <View className="flex-1 justify-center px-6">
        {/* Logo */}
        <View className="mb-10 items-center">
          <Image
            source={require("../assets/logo.png")}
            className="mb-4 h-40 w-40 rounded-2xl"
            resizeMode="contain"
          />
        </View>

        {/* Form */}
        <View className="gap-4">
          <InputField
            label="Email"
            placeholder="Enter your email"
            value={email}
            onChangeText={setEmail}
          />

          <View className="relative">
            <InputField
              label="Password"
              placeholder="Enter your password"
              secureTextEntry
              value={password}
              onChangeText={setPassword}
            />
            <View className="absolute right-4 top-10">
              <Eye size={20} color="gray" />
            </View>
          </View>

          <Pressable className="self-end" onPress={() => Linking.openURL("https://linkslens.com/forgot-password")}>
            <Text className="text-sm font-medium text-primary">Forgot Password?</Text>
          </Pressable>

          <AppButton fullWidth size="lg" className="mt-4" onPress={handleLogin} disabled={loading}>
            {loading ? "Signing in..." : "Sign In"}
          </AppButton>
        </View>
      </View>

      <View className="items-center py-6">
        <Text className="text-muted-foreground">
          {"Don't have an account? "}
          <TextLink onPress={() => router.push("/signup")}>Sign Up</TextLink>
        </Text>
      </View>
    </View>
  )
}
