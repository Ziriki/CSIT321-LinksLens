import { View, Text, Pressable } from "react-native"
import { Shield, Eye } from "lucide-react-native"
import { router } from "expo-router"
import {
  AppButton,
  InputField,
  TextLink,
} from "../components/ui-components"


export default function login() {
  return (
    <View className="flex-1 bg-white">
      <View className="flex-1 justify-center px-6">
        {/* Logo */}
        <View className="mb-10 items-center">
          <View className="mb-4 h-20 w-20 items-center justify-center rounded-2xl bg-primary">
            <Shield size={40} color="white" />
          </View>
          <Text className="text-2xl font-bold text-foreground">LinksLens</Text>
          <Text className="mt-1 text-muted-foreground">OCR URL Scanner</Text>
        </View>

        {/* Form */}
        <View className="gap-4">
          <InputField label="Email" placeholder="Enter your email" />

          <View className="relative">
            <InputField label="Password" placeholder="Enter your password" secureTextEntry />
            <View className="absolute right-4 top-10">
              <Eye size={20} color="gray" />
            </View>
          </View>

          <Pressable className="self-end">
            <Text className="text-sm font-medium text-primary">Forgot Password?</Text>
          </Pressable>

          <AppButton fullWidth size="lg" className="mt-4" onPress={() => router.replace("/home")}>
            Sign In
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