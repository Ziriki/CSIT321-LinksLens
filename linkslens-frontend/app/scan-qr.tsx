import { CameraView, useCameraPermissions } from "expo-camera";
import { router } from "expo-router";
import { ShieldAlert } from "lucide-react-native";
import { useEffect, useRef, useState } from "react";
import { Text, View } from "react-native";
import { AppButton, ScreenHeader } from "../components/ui-components";
import { URL_PATTERN } from "../lib/url-validation";

type QRScanState = "idle" | "found" | "invalid";

export default function ScanQR() {
  const [permission, requestPermission] = useCameraPermissions();
  const [status, setStatus] = useState<QRScanState>("idle");
  const scanned = useRef(false);
  const timersRef = useRef<ReturnType<typeof setTimeout>[]>([]);

  // Clear all pending timers on unmount to prevent navigation/state updates on a dead screen
  useEffect(() => {
    return () => timersRef.current.forEach(clearTimeout);
  }, []);

  const handleBarcodeScanned = ({ data }: { data: string }) => {
    if (scanned.current) return;
    const url = data.trim();
    if (URL_PATTERN.test(url)) {
      scanned.current = true;
      setStatus("found");
      timersRef.current.push(
        setTimeout(() => {
          router.push({ pathname: "/scan-processing", params: { url } });
        }, 400)
      );
    } else {
      setStatus("invalid");
      timersRef.current.push(
        setTimeout(() => setStatus("idle"), 2000)
      );
    }
  };

  if (!permission) {
    return <View className="flex-1 bg-background" />;
  }

  if (!permission.granted) {
    return (
      <View className="flex-1 bg-background">
        <ScreenHeader title="Scan QR Code" />
        <View className="flex-1 items-center justify-center px-8">
          <View className="mb-6 h-20 w-20 items-center justify-center rounded-full bg-primary/10">
            <ShieldAlert size={40} color="#2563eb" />
          </View>
          <Text className="mb-2 text-center text-lg font-semibold text-foreground">
            Camera Access Required
          </Text>
          <Text className="mb-8 text-center text-sm text-muted-foreground">
            LinksLens needs camera access to decode QR codes and check them for phishing links.
          </Text>
          <AppButton fullWidth onPress={requestPermission}>
            Grant Permission
          </AppButton>
        </View>
      </View>
    );
  }

  const statusText =
    status === "found" ? "URL found — scanning…" :
    status === "invalid" ? "Not a URL — try another code" :
    "Point camera at a QR code";

  const statusColor =
    status === "found" ? "text-green-400" :
    status === "invalid" ? "text-red-400" :
    "text-white";

  const frameColor =
    status === "found" ? "#4ade80" :
    status === "invalid" ? "#f87171" :
    "#ffffff";

  return (
    <View className="flex-1 bg-black">
      <ScreenHeader title="Scan QR Code" />
      <CameraView
        style={{ flex: 1 }}
        facing="back"
        barcodeScannerSettings={{ barcodeTypes: ["qr"] }}
        onBarcodeScanned={handleBarcodeScanned}
      >
        {/* Overlay */}
        <View className="absolute inset-0">
          {/* Top dark region */}
          <View className="flex-1 bg-black/60" />

          {/* Middle row: dark | finder frame | dark */}
          <View className="flex-row" style={{ height: 256 }}>
            <View className="flex-1 bg-black/60" />

            {/* Finder frame — transparent with corner accents */}
            <View style={{ width: 256, height: 256 }}>
              {/* Top-left */}
              <View
                className="absolute left-0 top-0 h-8 w-8"
                style={{ borderLeftWidth: 3, borderTopWidth: 3, borderColor: frameColor }}
              />
              {/* Top-right */}
              <View
                className="absolute right-0 top-0 h-8 w-8"
                style={{ borderRightWidth: 3, borderTopWidth: 3, borderColor: frameColor }}
              />
              {/* Bottom-left */}
              <View
                className="absolute bottom-0 left-0 h-8 w-8"
                style={{ borderLeftWidth: 3, borderBottomWidth: 3, borderColor: frameColor }}
              />
              {/* Bottom-right */}
              <View
                className="absolute bottom-0 right-0 h-8 w-8"
                style={{ borderRightWidth: 3, borderBottomWidth: 3, borderColor: frameColor }}
              />
            </View>

            <View className="flex-1 bg-black/60" />
          </View>

          {/* Bottom dark region + status text */}
          <View className="flex-[1.5] items-center bg-black/60 pt-8">
            <Text className={`text-base font-medium ${statusColor}`}>
              {statusText}
            </Text>
          </View>
        </View>
      </CameraView>
    </View>
  );
}
