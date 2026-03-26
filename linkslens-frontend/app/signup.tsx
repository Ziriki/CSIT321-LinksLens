import { useState } from "react"
import { View, Text, Image, Alert, Pressable } from "react-native"
import { Eye, EyeOff } from "lucide-react-native"
import { router } from "expo-router"
import { signup } from "../lib/api"
import {
  AppButton,
  InputField,
  TextLink,
} from "../components/ui-components"

export default function Signup() {
  const [fullName, setFullName] = useState("")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")
  const [loading, setLoading] = useState(false)
  const [showPassword, setShowPassword] = useState(false)

  const canSubmit = fullName.trim() && email.trim() && password && confirmPassword

  async function handleSignup() {
    if (password !== confirmPassword) {
      Alert.alert("Error", "Passwords do not match.")
      return
    }
    if (password.length < 8) {
      Alert.alert("Error", "Password must be at least 8 characters.")
      return
    }
    setLoading(true)
    try {
      await signup(fullName.trim(), email.trim(), password)
      router.replace("/home")
    } catch (e: any) {
      Alert.alert("Signup Failed", e.message ?? "Please try again.")
    } finally {
      setLoading(false)
    }
  }

  return (
    <View className="flex-1 bg-background">
      <View className="flex-1 justify-center px-6">
        <View className="mb-8 items-center">
          <Image
            source={require("../assets/logo_no_text.png")}
            className="mb-4 h-20 w-20 rounded-2xl"
            resizeMode="contain"
          />
          <Text className="text-2xl font-bold text-foreground">
            Sign Up
          </Text>
          <Text className="mt-1 text-center text-muted-foreground px-6">
            Create an account to begin
          </Text>
        </View>

        <View className="flex-col gap-4">
          <InputField label="Full Name" placeholder="Enter your name" value={fullName} onChangeText={setFullName} />
          <InputField label="Email" placeholder="Enter your email" value={email} onChangeText={setEmail} />

          <View className="relative">
            <InputField label="Password" placeholder="Create a password" secureTextEntry={!showPassword} value={password} onChangeText={setPassword} />
            <Pressable className="absolute right-4 top-9" onPress={() => setShowPassword((v) => !v)}>
              {showPassword ? <EyeOff size={20} color="#6b7280" /> : <Eye size={20} color="#6b7280" />}
            </Pressable>
          </View>

          <InputField label="Confirm Password" placeholder="Confirm your password" secureTextEntry value={confirmPassword} onChangeText={setConfirmPassword} />

          <AppButton
            fullWidth
            size="lg"
            className="mt-4"
            disabled={!canSubmit || loading}
            onPress={handleSignup}
          >
            {loading ? "Creating Account..." : "Create Account"}
          </AppButton>
        </View>

        <Text className="mt-6 text-center text-xs text-muted-foreground">
          By creating an account, you agree to our{" "}
          <Text className="text-primary">Terms of Service</Text> and{" "}
          <Text className="text-primary">Privacy Policy</Text>
        </Text>
      </View>

      <View className="items-center py-6">
        <Text className="text-muted-foreground">
          Already have an account?{" "}
          <TextLink onPress={() => router.push("/")}>
            Sign In
          </TextLink>
        </Text>
      </View>
    </View>
  )
}
