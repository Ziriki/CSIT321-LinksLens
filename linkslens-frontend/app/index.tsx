import { View, Text, Pressable, Image } from "react-native"
import { Eye } from "lucide-react-native"
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
          <Image
            source={require("../assets/logo.png")}
            className="mb-4 h-40 w-40 rounded-2xl"
            resizeMode="contain"
          />
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