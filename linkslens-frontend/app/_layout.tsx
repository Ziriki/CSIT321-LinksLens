import '../global.css';
import { useEffect, useState } from 'react';
import { View } from 'react-native';
import { Stack, router } from 'expo-router';
import { useColorScheme } from 'nativewind';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import * as Linking from 'expo-linking';
import * as SecureStore from 'expo-secure-store';
import { lightVars, darkVars, THEME_KEY } from '../lib/theme';
import { initNotificationHandler, requestNotificationPermission } from '../lib/notifications';

function extractSharedURL(raw: string): string | null {
  if (/^https?:\/\//i.test(raw)) return raw;
  try {
    const parsed = Linking.parse(raw);
    const text = parsed.queryParams?.text;
    if (typeof text === 'string' && /^https?:\/\//i.test(text)) return text;
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
      if (target) router.push({ pathname: '/scan-processing', params: { url: target } });
    });

    const sub = Linking.addEventListener('url', ({ url }) => {
      const target = extractSharedURL(url);
      if (target) router.push({ pathname: '/scan-processing', params: { url: target } });
    });
    return () => sub.remove();
  }, [loaded]);

  if (!loaded) return null;

  const themeVars = colorScheme === 'dark' ? darkVars : lightVars;

  return (
    <View style={{ flex: 1, paddingTop: insets.top, ...themeVars }}>
      <Stack screenOptions={{ headerShown: false }} />
    </View>
  );
}