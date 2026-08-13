"use client";

import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { createClient } from "@/lib/supabase/client";
import { useRouter } from "next/navigation";

export type User = {
  id: string;
  email: string;
  name?: string;
  tenant_id?: string;
};

type AuthContextType = {
  user: User | null;
  loading: boolean;
  signIn: (email: string, password: string) => Promise<{ error?: string }>;
  signUp: (email: string, password: string, metadata?: Record<string, any>) => Promise<{ error?: string }>;
  signOut: () => Promise<void>;
};

const AuthContext = createContext<AuthContextType>({
  user: null,
  loading: true,
  signIn: async () => ({}),
  signUp: async () => ({}),
  signOut: async () => {},
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    const supabase = createClient();
    let mounted = true;

    const initAuth = async () => {
      try {
        const {
          data: { session },
        } = await supabase.auth.getSession();
        if (mounted && session?.user) {
          const metadata = session.user.user_metadata || {};
          setUser({
            id: session.user.id,
            email: session.user.email || "",
            name: metadata.name || metadata.full_name || session.user.email?.split("@")[0],
            tenant_id: metadata.tenant_id || "varun",
          });
        }
      } catch (e) {
        console.error("Auth init error:", e);
      } finally {
        if (mounted) setLoading(false);
      }
    };

    initAuth();

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      if (session?.user) {
        const metadata = session.user.user_metadata || {};
        setUser({
          id: session.user.id,
          email: session.user.email || "",
          name: metadata.name || metadata.full_name || session.user.email?.split("@")[0],
          tenant_id: metadata.tenant_id || "varun",
        });
      } else {
        setUser(null);
      }
      setLoading(false);
    });

    return () => {
      mounted = false;
      subscription.unsubscribe();
    };
  }, [router]);

  const signIn = async (email: string, password: string) => {
    const supabase = createClient();
    const { data, error } = await supabase.auth.signInWithPassword({
      email: email.trim(),
      password: password.trim(),
    });

    if (error) {
      return { error: error.message };
    }

    if (data.session && data.user) {
      const userMetadata = data.user.user_metadata || {};
      const authUser: User = {
        id: data.user.id,
        email: data.user.email || email.trim(),
        name: userMetadata.name || userMetadata.full_name || email.trim().split("@")[0],
        tenant_id: userMetadata.tenant_id || "varun",
      };
      setUser(authUser);
      return {};
    }

    return { error: "No session returned" };
  };

  const signUp = async (email: string, password: string, metadata?: Record<string, any>) => {
    const supabase = createClient();
    const { data, error } = await supabase.auth.signUp({
      email: email.trim(),
      password: password.trim(),
      options: {
        data: metadata || {},
      },
    });

    if (error) {
      return { error: error.message };
    }

    if (data.session && data.user) {
      const userMetadata = data.user.user_metadata || metadata || {};
      const authUser: User = {
        id: data.user.id,
        email: data.user.email || email.trim(),
        name: userMetadata.name || userMetadata.full_name || email.trim().split("@")[0],
        tenant_id: userMetadata.tenant_id || "varun",
      };
      setUser(authUser);
      return {};
    }

    return { error: "Signup succeeded but no session returned. Check your email to confirm." };
  };

  const signOut = async () => {
    const supabase = createClient();
    await supabase.auth.signOut();
    setUser(null);
    router.push("/sign-in");
  };

  return (
    <AuthContext.Provider value={{ user, loading, signIn, signUp, signOut }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
