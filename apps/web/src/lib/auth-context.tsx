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
  demoSignIn: (tenantId?: string) => void;
  signOut: () => Promise<void>;
};

const AuthContext = createContext<AuthContextType>({
  user: null,
  loading: true,
  signIn: async () => ({}),
  signUp: async () => ({}),
  demoSignIn: () => {},
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
        } else if (mounted) {
          try {
            const customSession = localStorage.getItem("voxflow_session");
            if (customSession) {
              const parsed = JSON.parse(customSession);
              if (parsed?.user) {
                setUser({
                  id: parsed.user.id,
                  email: parsed.user.email || "",
                  name: parsed.user.name || parsed.user.user_metadata?.full_name || parsed.user.email?.split("@")[0],
                  tenant_id: parsed.user.tenant_id || "varun",
                });
                return;
              }
            }
            const saved = localStorage.getItem("voxflow_demo_user");
            if (saved) {
              setUser(JSON.parse(saved));
            }
          } catch {}
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
        try {
          const customSession = localStorage.getItem("voxflow_session");
          if (customSession) {
            const parsed = JSON.parse(customSession);
            if (parsed?.user) {
              setUser({
                id: parsed.user.id,
                email: parsed.user.email || "",
                name: parsed.user.name || parsed.user.user_metadata?.full_name || parsed.user.email?.split("@")[0],
                tenant_id: parsed.user.tenant_id || "varun",
              });
              setLoading(false);
              return;
            }
          }
          const saved = localStorage.getItem("voxflow_demo_user");
          if (!saved) setUser(null);
        } catch {
          setUser(null);
        }
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

    if (data.user) {
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

    return { error: "Failed to create user." };
  };

  const demoSignIn = (_tenantId = "varun") => {
    const demoUser: User = {
      id: "demo-user-" + Date.now(),
      email: "demo@voxflow.invalid",
      name: "Read-Only Demo Viewer",
      tenant_id: "varun",
    };
    setUser(demoUser);
    try {
      localStorage.setItem("voxflow_demo_user", JSON.stringify(demoUser));
      document.cookie = `voxflow_demo_user=${encodeURIComponent(JSON.stringify(demoUser))}; path=/; max-age=86400; SameSite=Lax`;
    } catch {}
  };

  const signOut = async () => {
    const supabase = createClient();
    try {
      localStorage.removeItem("voxflow_demo_user");
      document.cookie = "voxflow_demo_user=; path=/; max-age=0";
    } catch {}
    await supabase.auth.signOut();
    setUser(null);
    router.push("/sign-in");
  };

  return (
    <AuthContext.Provider value={{ user, loading, signIn, signUp, demoSignIn, signOut }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
