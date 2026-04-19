import { useEffect, useState } from "react"
import { View, ScrollView, Alert } from "react-native"
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
  const [phoneNumber, setPhoneNumber] = useState("")
  const [address, setAddress] = useState("")
  const [gender, setGender] = useState("")
  const [dateOfBirth, setDateOfBirth] = useState("")
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
        setPhoneNumber(details?.PhoneNumber ?? "")
        setAddress(details?.Address ?? "")
        setGender(details?.Gender ?? "")
        setDateOfBirth((details?.DateOfBirth ?? "").replace(/\//g, "-"))
      } catch {
        // Silently fail — show defaults
      }
    })()
  }, [])

  async function handleSave() {
    if (!userId) return
    setLoading(true)
    try {
      await updateDetails(userId, {
        FullName: fullName.trim() || null,
        PhoneNumber: phoneNumber.trim() || null,
        Address: address.trim() || null,
        Gender: gender.trim() || null,
        DateOfBirth: dateOfBirth.trim().replace(/\//g, "-") || null,
      })
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

        <ScrollView className="flex-1 px-4 py-6" keyboardShouldPersistTaps="handled">
          {/* Avatar */}
          <View className="mb-6 items-center">
            <View className="mb-2 h-24 w-24 items-center justify-center rounded-full bg-secondary">
              <User size={48} color="#6b7280" />
            </View>
          </View>

          {/* Form */}
          <View className="gap-4">
            <InputField
              label="Full Name"
              placeholder="Enter your full name"
              value={fullName}
              onChangeText={setFullName}
            />
            <InputField
              label="Email"
              placeholder="Email address"
              value={email}
              editable={false}
            />
            <InputField
              label="Phone Number"
              placeholder="Enter your phone number"
              value={phoneNumber}
              onChangeText={setPhoneNumber}
            />
            <InputField
              label="Address"
              placeholder="Enter your address"
              value={address}
              onChangeText={setAddress}
            />
            <InputField
              label="Gender"
              placeholder="e.g. Male, Female, Other"
              value={gender}
              onChangeText={setGender}
            />
            <InputField
              label="Date of Birth"
              placeholder="YYYY-MM-DD"
              value={dateOfBirth}
              onChangeText={(v) => setDateOfBirth(v.replace(/\//g, "-"))}
            />
          </View>
        </ScrollView>

        {/* Footer */}
        <View className="border-t border-border px-4 py-4">
          <AppButton fullWidth disabled={loading} onPress={handleSave}>
            {loading ? "Saving..." : "Save Changes"}
          </AppButton>
        </View>
    </View>
  )
}
