import { useEffect, useState } from "react"
import { View, Text, Alert } from "react-native"
import { router } from "expo-router"
import { User } from "lucide-react-native"
import {
  AppButton,
  InputField,
  ScreenHeader,
} from "../components/ui-components"
import { fetchAccount, fetchDetails, updateDetails, getCurrentUserId } from "../lib/api"

export default function EditProfile() {
  const [fullName, setFullName] = useState("")
  const [email, setEmail] = useState("")
  const [loading, setLoading] = useState(false)
  const [userId, setUserId] = useState<number | null>(null)

  useEffect(() => {
    (async () => {
      try {
        const id = await getCurrentUserId()
        if (!id) return
        setUserId(id)
        const [account, details] = await Promise.all([
          fetchAccount(id),
          fetchDetails(id).catch(() => null),
        ])
        setEmail(account.EmailAddress)
        setFullName(details?.FullName ?? "")
      } catch {
        // Silently fail — show defaults
      }
    })()
  }, [])

  async function handleSave() {
    if (!userId) return
    setLoading(true)
    try {
      await updateDetails(userId, { FullName: fullName.trim() })
      Alert.alert("Success", "Profile updated.")
      router.back()
    } catch (e: any) {
      Alert.alert("Error", e.message ?? "Failed to save.")
    } finally {
      setLoading(false)
    }
  }

  return (
    <View className="flex-1 bg-background">
      <ScreenHeader title="Edit Profile" />

      <View className="flex-1 px-4 py-6">
        {/* Avatar */}
        <View className="mb-6 items-center">
          <View className="mb-2 h-24 w-24 items-center justify-center rounded-full bg-secondary">
            <User size={48} color="#6b7280" />
          </View>
        </View>

        {/* Form */}
        <View className="gap-4">
          <InputField label="Full Name" placeholder="Enter name" value={fullName} onChangeText={setFullName} />
          <InputField label="Email" placeholder="Enter email" value={email} />
        </View>
      </View>

      {/* Footer */}
      <View className="border-t border-border px-4 py-4">
        <AppButton fullWidth disabled={loading} onPress={handleSave}>
          {loading ? "Saving..." : "Save Changes"}
        </AppButton>
      </View>
    </View>
  )
}
