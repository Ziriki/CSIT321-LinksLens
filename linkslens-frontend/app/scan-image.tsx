import { recognizeText } from "@infinitered/react-native-mlkit-text-recognition";
import * as ImagePicker from "expo-image-picker";
import { router } from "expo-router";
import { ChevronDown, ChevronUp, Upload } from "lucide-react-native";
import React, { useState } from "react";
import { Image, Pressable, ScrollView, Text, TextInput, View } from "react-native";
import { AppButton, ScreenHeader } from "../components/ui-components";

/**
 * Extract all URL-like strings from raw OCR text.
 * Matches http/https URLs first, then bare www. domains.
 * Trailing punctuation (., ; : ! ?) is stripped — OCR often captures it.
 */
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
  const [imageUri, setImageUri]       = useState<string | null>(null);
  const [extractedUrls, setExtractedUrls] = useState<string[]>([]);
  const [selectedUrl, setSelectedUrl] = useState("");
  const [rawOcrText, setRawOcrText]   = useState("");
  const [loading, setLoading]         = useState(false);
  const [showRaw, setShowRaw]         = useState(false);

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
        setExtractedUrls([]);
        setSelectedUrl("");
        setRawOcrText("");
        setShowRaw(false);

        const response = await recognizeText(uri);
        const raw = response.text ?? "";
        const urls = extractUrlsFromText(raw);

        setRawOcrText(raw);
        setExtractedUrls(urls);
        setSelectedUrl(urls[0] ?? "");
        setLoading(false);
      }
    } catch (error) {
      console.error("Error recognizing text:", error);
      setRawOcrText("Error: Could not recognise text from image.");
      setLoading(false);
    }
  };

  const normalise = (url: string) =>
    /^https?:\/\//i.test(url) ? url : `http://${url}`;

  return (
    <View className="flex-1 bg-background">
      <ScreenHeader title="Upload Photo" />

      <ScrollView className="flex-1 px-4 py-6" keyboardShouldPersistTaps="handled">

        {/* Image picker */}
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

        {/* Crop hint */}
        <Text className="mt-3 text-xs text-muted-foreground text-center">
          For best results, crop the image tightly around the URL before selecting.
          OCR captures all visible text — extra words may prevent detection.
        </Text>

        {/* Results */}
        {!loading && rawOcrText !== "" && (
          <View className="mt-6 gap-4">

            {/* Found URLs */}
            {extractedUrls.length > 0 ? (
              <View className="p-4 rounded-xl bg-secondary/20">
                <Text className="text-xs uppercase text-muted-foreground font-bold mb-2">
                  {extractedUrls.length === 1 ? "URL Extracted" : `${extractedUrls.length} URLs Found — tap to select`}
                </Text>

                {/* Selectable URL chips when multiple found */}
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

                {/* Editable selected URL */}
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
              <View className="p-4 rounded-xl bg-secondary/20">
                <Text className="text-xs uppercase text-muted-foreground font-bold mb-2">No URL Detected</Text>
                <Text className="text-sm text-muted-foreground mb-3">
                  No URL was found in the image. Try cropping tighter around the link, or enter it manually below.
                </Text>
                <TextInput
                  className="text-base text-foreground border border-border rounded-lg px-3 py-2"
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

            {/* Collapsible raw OCR output */}
            <Pressable
              onPress={() => setShowRaw(v => !v)}
              className="flex-row items-center gap-1"
            >
              {showRaw
                ? <ChevronUp size={14} color="#9ca3af" />
                : <ChevronDown size={14} color="#9ca3af" />
              }
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
              params: { url: normalise(selectedUrl.trim()) },
            })}
          >
            {loading ? "Scanning image…" : "Scan URL"}
          </AppButton>
        </View>

      </ScrollView>
    </View>
  );
}
