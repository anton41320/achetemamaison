import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { Platform } from "react-native";
import * as SecureStore from "expo-secure-store";

import { AuthResponse, AuthUser, authApi, setApiToken, setUnauthorizedHandler } from "@/src/api";
import { queryClient } from "@/src/query-client";

const KEY = "estimo_session_token";

async function readToken(): Promise<string | null> {
  if (Platform.OS === "web") return typeof localStorage !== "undefined" ? localStorage.getItem(KEY) : null;
  return SecureStore.getItemAsync(KEY);
}
async function writeToken(v: string | null) {
  if (Platform.OS === "web") {
    if (typeof localStorage === "undefined") return;
    if (v) localStorage.setItem(KEY, v);
    else localStorage.removeItem(KEY);
    return;
  }
  if (v) await SecureStore.setItemAsync(KEY, v);
  else await SecureStore.deleteItemAsync(KEY);
}

interface Session {
  user: AuthUser | null;
  loading: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (email: string, password: string) => Promise<void>;
  acceptAuth: (r: AuthResponse) => Promise<void>;
  signOut: () => Promise<void>;
}

const Ctx = createContext<Session | null>(null);

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  const acceptAuth = useCallback(async (r: AuthResponse) => {
    setApiToken(r.access_token);
    await writeToken(r.access_token);
    queryClient.clear();
    setUser(r.user);
  }, []);

  const signOut = useCallback(async () => {
    setApiToken(null);
    await writeToken(null);
    queryClient.clear();
    setUser(null);
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(() => {
      signOut().catch(() => {});
    });
    (async () => {
      try {
        const t = await readToken();
        if (t) {
          setApiToken(t);
          setUser(await authApi.me());
        }
      } catch {
        setApiToken(null);
        await writeToken(null).catch(() => {});
      } finally {
        setLoading(false);
      }
    })();
    return () => setUnauthorizedHandler(null);
  }, [signOut]);

  const value = useMemo<Session>(
    () => ({
      user,
      loading,
      acceptAuth,
      signOut,
      signIn: async (email, password) => acceptAuth(await authApi.login(email.trim().toLowerCase(), password)),
      signUp: async (email, password) => acceptAuth(await authApi.register(email.trim().toLowerCase(), password)),
    }),
    [user, loading, acceptAuth, signOut],
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useSession(): Session {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useSession must be used within SessionProvider");
  return ctx;
}

/** Public https origin used for links in emails (reset password). */
export function appOrigin(): string {
  if (Platform.OS === "web" && typeof window !== "undefined") return window.location.origin;
  return process.env.EXPO_PUBLIC_BACKEND_URL!;
}

export function passwordIssue(pw: string): string | undefined {
  if (pw.length < 8) return "8 caractères minimum";
  if (!/[A-Za-z]/.test(pw) || !/\d/.test(pw)) return "Mélangez lettres et chiffres";
  return undefined;
}
