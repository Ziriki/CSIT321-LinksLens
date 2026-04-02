import { recognizeText } from "@infinitered/react-native-mlkit-text-recognition";
import * as ImagePicker from "expo-image-picker";
import { router } from "expo-router";
import { Upload } from "lucide-react-native";
import React, { useState } from "react";
import { Image, Pressable, Text, TextInput, View } from "react-native";
import {
  AppButton,
  ScreenHeader,
} from "../components/ui-components";
import { URL_PATTERN } from "../lib/url-validation";

const isValidUrl = (urlString: string) => {
  // Remove whitespace/newlines that OCR often adds
  const cleaned = urlString.trim().replace(/\s/g, '');
  return !!URL_PATTERN.test(cleaned);
};

export default function scanImage() {
  const [imageUri, setImageUri] = useState<string | null>(null);
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const [isUrl, setIsUrl] = useState(false); // New state

  const handlePickImage = async () => {
    try {
      const result = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ImagePicker.MediaTypeOptions.Images,
        allowsEditing: true,
        quality: 1,
      });

      if (!result.canceled) {
        const uri = result.assets[0].uri;
        setImageUri(uri);
        setLoading(true);

        const response = await recognizeText(uri);
        
        // 1. Clean the text (ML Kit sometimes adds extra spaces)
        const cleanedText = response.text.trim().replace(/\s/g, '');
        
        // 2. Validate
        const valid = isValidUrl(cleanedText);
        
        setText(cleanedText);
        setIsUrl(valid);
        setLoading(false);
      }
    } catch (error) {
      console.error("Error recognizing text:", error);
      setText("Error: Could not recognize text");
      setIsUrl(false);
      setLoading(false);
    }
  };

  return (
    <View className="flex-1 bg-background">
      <ScreenHeader title="Upload Photo" />

      <View className="flex-1 px-4 py-6">
        <Pressable 
          className="h-64 items-center justify-center rounded-2xl border-2 border-dashed border-border overflow-hidden"
          onPress={handlePickImage}
        >
          {imageUri ? (
            <Image source={{ uri: imageUri }} className="w-full h-full" />
          ) : (
            <>
              <Upload size={48} color="#6b7280" />
              <Text className="mt-4 font-medium text-foreground">Tap to select image</Text>
            </>
          )}
        </Pressable>

        {text && (
          <View className="mt-6 p-4 rounded-xl bg-secondary/20">
            <Text className="text-xs uppercase text-muted-foreground font-bold">
              Detected Content:
            </Text>
            <TextInput
              className={`mt-2 text-lg ${isUrl ? 'text-blue-500' : 'text-foreground'}`}
              value={text}
              onChangeText={(val) => {
                setText(val);
                setIsUrl(isValidUrl(val));
              }}
              autoCapitalize="none"
              autoCorrect={false}
              keyboardType="url"
            />
            
            {/* Feedback for the user */}
            <Text className="mt-1 text-sm">
              {isUrl ? "✅ Valid URL found" : "❌ No valid URL detected"}
            </Text>
          </View>
        )}

        <View className="mt-8">
          <AppButton
            fullWidth
            size="lg"
            disabled={!isUrl || loading} // Disable button if not a URL
            onPress={() => router.push({ pathname: "/scan-processing", params: { url: text } })}
          >
            {loading ? "Processing..." : "Scan URL"}
          </AppButton>
        </View>
      </View>
    </View>
  );
}