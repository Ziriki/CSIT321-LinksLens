import '../global.css';
import { useEffect, useState } from 'react';
import { View } from 'react-native';
import { Stack, router } from 'expo-router';
import { useColorScheme } from 'nativewind';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import * as Linking from 'expo-linking';
import * as Notifications from 'expo-notifications';
import * as SecureStore from 'expo-secure-store';
import { lightVars, darkVars, THEME_KEY, getBackgroundColor } from '../lib/theme';
import { initNotificationHandler, requestNotificationPermission } from '../lib/notifications';
import { fetchScanById, scanHistoryToResponse } from '../lib/api';

function extractSharedURL(raw: string): string | null {
  if (/^https?:\/\//i.test(raw)) return raw;
  try {
    const parsed = Linking.parse(raw);
    // Ignore non-scan linkslens:// URLs (e.g., Expo dev-client launcher)
    if (parsed.hostname !== 'scan') return null;
    const url = parsed.queryParams?.url;
    if (typeof url === 'string' && /^https?:\/\//i.test(url)) return url;
  } catch { /* ignore */ }
  return null;
}

export default function RootLayout() {
  const { colorScheme, setColorScheme } = useColorScheme();
  const [loaded, setLoaded] = useState(false);
  const insets = useSafeAreaInsets();

  useEffect(() => {
    SecureStore.getItemAsync(THEME_KEY).then((saved) => {
      setColorScheme(saved === 'dark' ? 'dark' : 'light');
      setLoaded(true);
    });
    initNotificationHandler();
    requestNotificationPermission();
  }, []);

  useEffect(() => {
    if (!loaded) return;

    Linking.getInitialURL().then((url) => {
      const target = url ? extractSharedURL(url) : null;
      if (target) router.push({ pathname: '/scan-link', params: { url: target } });
    });

    const sub = Linking.addEventListener('url', ({ url }) => {
      const target = extractSharedURL(url);
      if (target) router.push({ pathname: '/scan-link', params: { url: target } });
    });

    const notifSub = Notifications.addNotificationResponseReceivedListener(async (response) => {
      const scanId = response.notification.request.content.data?.scan_id as number | null;
      if (!scanId) return;
      try {
        const scan = await fetchScanById(scanId);
        router.push({
          pathname: '/scan-results',
          params: { result: JSON.stringify(scanHistoryToResponse(scan)) },
        });
      } catch { /* silently fail — scan may have been deleted */ }
    });

    return () => {
      sub.remove();
      notifSub.remove();
    };
  }, [loaded]);

  if (!loaded) return null;

  const themeVars = colorScheme === 'dark' ? darkVars : lightVars;

  return (
    <View style={[{ flex: 1, paddingTop: insets.top, backgroundColor: getBackgroundColor(colorScheme) }, themeVars]}>
      <Stack screenOptions={{ headerShown: false }} />
    </View>
  );
}