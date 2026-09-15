import { QueryClientProvider } from "@tanstack/react-query";
import { useFonts } from "expo-font";
import { Stack } from "expo-router";
import * as SplashScreen from "expo-splash-screen";
import { StatusBar } from "expo-status-bar";
import { useEffect } from "react";
import { LogBox } from "react-native";
import { GestureHandlerRootView } from "react-native-gesture-handler";
import { KeyboardProvider } from "react-native-keyboard-controller";

import { ErrorBoundary } from "@/src/components/error-boundary";
import { SessionProvider, useSession } from "@/src/auth";
import { queryClient } from "@/src/query-client";
import { useTheme } from "@/src/theme";

// Disable logbox errors etc so that users can see the app
// and agent works as expected.
LogBox.ignoreAllLogs(true);

SplashScreen.preventAutoHideAsync().catch(() => {});

function RootNavigator({ fontsReady }: { fontsReady: boolean }) {
  const { colors } = useTheme();
  const { user, loading } = useSession();

  useEffect(() => {
    if (fontsReady && !loading) SplashScreen.hideAsync().catch(() => {});
  }, [fontsReady, loading]);

  if (!fontsReady || loading) return null;
  const signedIn = !!user;
  return (
    <Stack
      screenOptions={{
        headerShown: false,
        contentStyle: { backgroundColor: colors.surface },
        animation: "slide_from_right",
      }}
    >
      <Stack.Protected guard={!signedIn}>
        <Stack.Screen name="welcome" />
        <Stack.Screen name="sign-in" />
        <Stack.Screen name="sign-up" />
        <Stack.Screen name="forgot-password" />
      </Stack.Protected>
      <Stack.Protected guard={signedIn}>
        <Stack.Screen name="index" />
        <Stack.Screen name="new" />
        <Stack.Screen name="data" />
        <Stack.Screen name="account" />
        <Stack.Screen name="property/[id]/index" />
        <Stack.Screen name="property/[id]/edit" />
        <Stack.Screen name="property/[id]/comparables" />
        <Stack.Screen name="property/[id]/dossier" />
        <Stack.Screen name="property/[id]/listing" />
        <Stack.Screen name="property/[id]/photos" />
        <Stack.Screen name="property/[id]/pack" />
        <Stack.Screen name="property/[id]/document/[docId]" />
      </Stack.Protected>
      <Stack.Screen name="reset-password" />
    </Stack>
  );
}

export default function RootLayout() {
  const [loaded, error] = useFonts({
    "PlusJakartaSans-Regular": require("../assets/fonts/PlusJakartaSans-Regular.ttf"),
    "PlusJakartaSans-Medium": require("../assets/fonts/PlusJakartaSans-Medium.ttf"),
    "PlusJakartaSans-SemiBold": require("../assets/fonts/PlusJakartaSans-SemiBold.ttf"),
    "PlusJakartaSans-Bold": require("../assets/fonts/PlusJakartaSans-Bold.ttf"),
  });

  // One app level ErrorBoundary; a render crash shows a reload screen
  // instead of a blank app.
  return (
    <ErrorBoundary>
      <GestureHandlerRootView style={{ flex: 1 }}>
        <KeyboardProvider>
          <QueryClientProvider client={queryClient}>
            <SessionProvider>
              <StatusBar style="dark" />
              <RootNavigator fontsReady={!!(loaded || error)} />
            </SessionProvider>
          </QueryClientProvider>
        </KeyboardProvider>
      </GestureHandlerRootView>
    </ErrorBoundary>
  );
}
