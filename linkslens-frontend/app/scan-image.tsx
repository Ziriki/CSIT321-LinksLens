import { recognizeText } from "@infinitered/react-native-mlkit-text-recognition";
import * as ImagePicker from "expo-image-picker";
import { router } from "expo-router";
import { AlertCircle, Camera, ChevronDown, ChevronUp, Upload } from "lucide-react-native";
import React, { useState } from "react";
import { Image, Pressable, ScrollView, Text, TextInput, View } from "react-native";
import { AppButton, ScreenHeader } from "../components/ui-components";
import { normalizeUrl } from "../lib/url-validation";

function extractUrlsFromText(rawText: string): string[] {
  const httpMatches = rawText.match(/https?:\/\/[^\s\n\r<>"'`\]|\\]+/gi) ?? [];
  const wwwMatches  = rawText.match(/www\.[a-zA-Z0-9-]+(?:\.[a-zA-Z]{2,})+(?:\/[^\s\n\r<>"'`\]|\\]*)*/gi) ?? [];
  // Bare domains without protocol or www (e.g. m.youtube.com, maps.google.com, youtube.com)
  const bareMatches = rawText.match(
    /\b[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?)*\.[a-zA-Z]{2,}\b(?:\/[^\s\n\r<>"'`\]|\\]*)*/gi
  ) ?? [];

  return [...httpMatches, ...wwwMatches, ...bareMatches]
    .map(u => u.replace(/[.,;:!?)\]]+$/, ""))
    .filter((u, i, arr) => arr.indexOf(u) === i);
}

export default function ScanImage() {
  const [imageUri, setImageUri]           = useState<string | null>(null);
  const [extractedUrls, setExtractedUrls] = useState<string[]>([]);
  const [selectedUrl, setSelectedUrl]     = useState("");
  const [rawOcrText, setRawOcrText]       = useState("");
  const [loading, setLoading]             = useState(false);
  const [showRaw, setShowRaw]             = useState(false);

  async function processImage(uri: string) {
    setImageUri(uri);
    setLoading(true);
    setExtractedUrls([]);
    setSelectedUrl("");
    setRawOcrText("");
    setShowRaw(false);
    try {
      const response = await recognizeText(uri);
      const raw = response.text ?? "";
      const urls = extractUrlsFromText(raw);
      setRawOcrText(raw);
      setExtractedUrls(urls);
      setSelectedUrl(urls[0] ?? "");
    } catch {
      setRawOcrText("Error: Could not recognise text from image.");
    } finally {
      setLoading(false);
    }
  }

  const handlePickImage = async () => {
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: "images",
      allowsEditing: true,
      quality: 1,
    });
    if (!result.canceled) await processImage(result.assets[0].uri);
  };

  const handleTakePhoto = async () => {
    const { status } = await ImagePicker.requestCameraPermissionsAsync();
    if (status !== "granted") return;
    const result = await ImagePicker.launchCameraAsync({
      allowsEditing: true,
      quality: 1,
    });
    if (!result.canceled) await processImage(result.assets[0].uri);
  };


  return (
    <View className="flex-1 bg-background">
      <ScreenHeader title="Scan Image" />

      <ScrollView className="flex-1 px-4 py-6" keyboardShouldPersistTaps="handled">

        {/* Image preview */}
        <View className="h-56 items-center justify-center rounded-2xl border-2 border-dashed border-border overflow-hidden bg-secondary/10">
          {imageUri ? (
            <Image source={{ uri: imageUri }} className="w-full h-full" resizeMode="cover" />
          ) : (
            <>
              <Upload size={40} color="#6b7280" />
              <Text className="mt-3 font-medium text-muted-foreground">No image selected</Text>
            </>
          )}
        </View>

        {/* Source buttons */}
        <View className="mt-4 flex-row gap-3">
          <AppButton className="flex-1" onPress={handleTakePhoto}>
            <View className="flex-row items-center justify-center gap-2">
              <Camera size={20} color="#ffffff" />
              <Text className="text-sm font-medium text-primary-foreground">Take Photo</Text>
            </View>
          </AppButton>

          <AppButton className="flex-1" onPress={handlePickImage}>
            <View className="flex-row items-center justify-center gap-2">
              <Upload size={20} color="#ffffff" />
              <Text className="text-sm font-medium text-primary-foreground">Upload Photo</Text>
            </View>
          </AppButton>
        </View>

        {/* Crop hint */}
        <Text className="mt-3 text-xs text-muted-foreground text-center">
          For best results, crop tightly around the URL.
          OCR captures all visible text, extra words may prevent detection.
        </Text>

        {/* Results */}
        {!loading && rawOcrText !== "" && (
          <View className="mt-6 gap-4">

            {extractedUrls.length > 0 ? (
              <View className="p-4 rounded-xl bg-secondary/20">
                <Text className="text-xs uppercase text-muted-foreground font-bold mb-2">
                  {extractedUrls.length === 1 ? "URL Extracted" : `${extractedUrls.length} URLs Found — tap to select`}
                </Text>

                {extractedUrls.length > 1 && (
                  <View className="flex-row flex-wrap gap-2 mb-3">
                    {extractedUrls.map((url, i) => (
                      <Pressable
                        key={i}
                        onPress={() => setSelectedUrl(url)}
                        className={`px-3 py-1 rounded-full border ${
                          selectedUrl === url
                            ? "bg-blue-500 border-blue-500"
                            : "bg-transparent border-border"
                        }`}
                      >
                        <Text
                          className={`text-xs ${selectedUrl === url ? "text-white" : "text-muted-foreground"}`}
                          numberOfLines={1}
                        >
                          {url}
                        </Text>
                      </Pressable>
                    ))}
                  </View>
                )}

                <TextInput
                  className="text-base text-blue-500"
                  value={selectedUrl}
                  onChangeText={setSelectedUrl}
                  autoCapitalize="none"
                  autoCorrect={false}
                  keyboardType="url"
                  placeholder="Edit URL if needed"
                  placeholderTextColor="#9ca3af"
                />
                <Text className="mt-1 text-xs text-green-500">✓ URL extracted — edit above if needed</Text>
              </View>
            ) : (
              <View className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/30">
                <View className="flex-row items-center gap-2 mb-2">
                  <AlertCircle size={14} color="#f59e0b" />
                  <Text className="text-xs uppercase text-amber-600 font-bold">No URL Detected</Text>
                </View>
                <Text className="text-sm text-muted-foreground mb-3">
                  No URL was found in this image. Try cropping tighter around the link, or enter the URL manually below.
                </Text>
                <TextInput
                  className="text-base text-foreground border border-amber-500/40 rounded-lg px-3 py-2"
                  value={selectedUrl}
                  onChangeText={setSelectedUrl}
                  autoCapitalize="none"
                  autoCorrect={false}
                  keyboardType="url"
                  placeholder="Paste or type URL here"
                  placeholderTextColor="#9ca3af"
                />
              </View>
            )}

            <Pressable
              onPress={() => setShowRaw(v => !v)}
              className="flex-row items-center gap-1"
            >
              {showRaw
                ? <ChevronUp size={14} color="#9ca3af" />
                : <ChevronDown size={14} color="#9ca3af" />}
              <Text className="text-xs text-muted-foreground">
                {showRaw ? "Hide" : "Show"} full OCR text
              </Text>
            </Pressable>

            {showRaw && (
              <View className="p-3 rounded-xl bg-secondary/10 border border-border">
                <Text className="text-xs text-muted-foreground leading-5">{rawOcrText}</Text>
              </View>
            )}

          </View>
        )}

        <View className="mt-8 mb-8">
          <AppButton
            fullWidth
            size="lg"
            disabled={!selectedUrl.trim() || loading}
            onPress={() => router.push({
              pathname: "/scan-processing",
              params: { url: normalizeUrl(selectedUrl.trim()) },
            })}
          >
            {loading ? "Scanning image…" : "Scan URL"}
          </AppButton>
          {!loading && !selectedUrl.trim() && rawOcrText !== "" && extractedUrls.length === 0 && (
            <Text className="mt-2 text-xs text-center text-amber-500">
              No URL detected — type one in the field above to continue
            </Text>
          )}
        </View>

      </ScrollView>
    </View>
  );
}
