import { QueryClientProvider } from "@tanstack/react-query";
import { useFonts } from "expo-font";
import { Stack } from "expo-router";
import * as SplashScreen from "expo-splash-screen";
import { StatusBar } from "expo-status-bar";
import { useEffect } from "react";
import { LogBox, Pressable, Text, View } from "react-native";
import { GestureHandlerRootView } from "react-native-gesture-handler";
import { KeyboardProvider } from "react-native-keyboard-controller";

import { ErrorBoundary } from "@/src/components/error-boundary";
import { SessionProvider, useSession } from "@/src/auth";
import { queryClient } from "@/src/query-client";
import { useTheme } from "@/src/theme";
import { WebShell } from "@/src/web/WebShell";

// Disable logbox errors etc so that users can see the app
// and agent works as expected.
LogBox.ignoreAllLogs(true);

SplashScreen.preventAutoHideAsync().catch(() => {});

function RootNavigator({ fontsReady }: { fontsReady: boolean }) {
  const { colors } = useTheme();
  const { user, loading, startupError, retry } = useSession();

  useEffect(() => {
    if (fontsReady && !loading) SplashScreen.hideAsync().catch(() => {});
  }, [fontsReady, loading]);

  if (!fontsReady || loading) return null;
  if (startupError && !user) {
    return (
      <View
        style={{
          flex: 1,
          alignItems: "center",
          justifyContent: "center",
          padding: 24,
          gap: 12,
          backgroundColor: colors.surface,
        }}
        testID="startup-error"
      >
        <Text
          style={{
            fontFamily: "PlusJakartaSans-SemiBold",
            fontSize: 18,
            color: colors.onSurface,
            textAlign: "center",
          }}
        >
          Serveur momentanément indisponible
        </Text>
        <Text
          style={{
            fontFamily: "PlusJakartaSans-Regular",
            fontSize: 14,
            color: colors.onSurfaceTertiary,
            textAlign: "center",
          }}
        >
          {startupError}
        </Text>
        <Pressable
          testID="startup-retry"
          accessibilityRole="button"
          onPress={retry}
          style={{
            minHeight: 48,
            paddingHorizontal: 24,
            borderRadius: 12,
            backgroundColor: colors.brandPrimary,
            alignItems: "center",
            justifyContent: "center",
            marginTop: 8,
          }}
        >
          <Text
            style={{
              fontFamily: "PlusJakartaSans-SemiBold",
              fontSize: 15,
              color: colors.onBrandPrimary,
            }}
          >
            Réessayer
          </Text>
        </Pressable>
      </View>
    );
  }
  const signedIn = !!user;
  return (
    <WebShell>
      <Stack
        screenOptions={{
          headerShown: false,
          contentStyle: { backgroundColor: colors.surface },
          animation: "slide_from_right",
        }}
      >
        <Stack.Screen name="welcome" />
        <Stack.Protected guard={!signedIn}>
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
          <Stack.Screen name="property/[id]/vente" />
          <Stack.Screen name="property/[id]/vendu" />
          <Stack.Screen name="property/[id]/edit" />
          <Stack.Screen name="property/[id]/environment" />
          <Stack.Screen name="property/[id]/visites" />
          <Stack.Screen name="property/[id]/comparables" />
          <Stack.Screen name="property/[id]/dossier" />
          <Stack.Screen name="property/[id]/listing" />
          <Stack.Screen name="property/[id]/photos" />
          <Stack.Screen name="property/[id]/pack" />
          <Stack.Screen name="property/[id]/document/[docId]" />
        </Stack.Protected>
        <Stack.Screen name="reset-password" />
        <Stack.Screen name="privacy" />
      </Stack>
    </WebShell>
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
