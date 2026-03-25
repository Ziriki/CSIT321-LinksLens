import { View, Text, Image } from "react-native"
import { Eye } from "lucide-react-native"
import { router } from "expo-router"
import {
  AppButton,
  InputField,
  TextLink,
} from "../components/ui-components"

export default function signup() {
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
          <InputField label="Full Name" placeholder="Enter your name" />

          <InputField label="Email" placeholder="Enter your email" />

          <View className="relative">
            <InputField
              label="Password"
              placeholder="Create a password"
              secureTextEntry
            />

            <View className="absolute right-4 top-9">
              <Eye size={20} color="#6b7280" />
            </View>
          </View>

          <InputField
            label="Confirm Password"
            placeholder="Confirm your password"
            secureTextEntry
          />

          <AppButton
            fullWidth
            size="lg"
            className="mt-4"
            onPress={() => router.replace("/home")}
          >
            Create Account
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