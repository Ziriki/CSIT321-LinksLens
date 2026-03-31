import '../global.css';
import { useEffect, useState } from 'react';
import { View } from 'react-native';
import { Stack } from 'expo-router';
import { useColorScheme } from 'nativewind';
import * as SecureStore from 'expo-secure-store';
import { lightVars, darkVars, THEME_KEY } from '../lib/theme';
import { initNotificationHandler, requestNotificationPermission } from '../lib/notifications';

export default function RootLayout() {
  const { colorScheme, setColorScheme } = useColorScheme();
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    SecureStore.getItemAsync(THEME_KEY).then((saved) => {
      setColorScheme(saved === 'dark' ? 'dark' : 'light');
      setLoaded(true);
    });
    initNotificationHandler();
    requestNotificationPermission();
  }, []);

  if (!loaded) return null;

  const themeVars = colorScheme === 'dark' ? darkVars : lightVars;

  return (
    <View style={{ flex: 1, ...themeVars }}>
      <Stack screenOptions={{ headerShown: false }} />
    </View>
  );
}