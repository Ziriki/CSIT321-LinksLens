import '../global.css';
import { Stack } from 'expo-router';
import { useColorScheme } from 'nativewind';

export default function RootLayout() {
  const { setColorScheme } = useColorScheme();

  // force light mode for now
  setColorScheme('light');

  return <Stack screenOptions={{ headerShown: false }} />;
}