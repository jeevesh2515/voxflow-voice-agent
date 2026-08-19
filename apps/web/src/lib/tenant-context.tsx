"use client";

import { createContext, useContext, useEffect, useState, ReactNode, useCallback } from "react";
import { createClient } from "@/lib/supabase/client";
import { api } from "@/lib/api";

export type Tenant = {
  id: string;
  name: string;
  logo_url?: string;
  agent_name?: string;
  plan?: string;
  custom?: boolean;
};

const DEFAULT_TENANTS: Tenant[] = [
  { id: "varun", name: "Varun Beverages (PepsiCo)" },
  { id: "amul", name: "Amul Dairy Products" },
  { id: "haldirams", name: "Haldirams Snacks & Sweets" },
  { id: "britannia", name: "Britannia Foods" },
];

type TenantContextType = {
  activeTenantId: string;
  activeTenant: Tenant;
  tenants: Tenant[];
  setActiveTenantId: (id: string) => void;
  addTenant: (name: string) => Tenant;
  refreshTenants: () => Promise<void>;
};

const TenantContext = createContext<TenantContextType>({
  activeTenantId: "varun",
  activeTenant: DEFAULT_TENANTS[0],
  tenants: DEFAULT_TENANTS,
  setActiveTenantId: () => {},
  addTenant: () => DEFAULT_TENANTS[0],
  refreshTenants: async () => {},
});

export function TenantProvider({ children }: { children: ReactNode }) {
  const [tenants, setTenants] = useState<Tenant[]>(DEFAULT_TENANTS);
  const [activeTenantId, setActiveTenantIdState] = useState<string>("varun");

  const refreshTenants = useCallback(async () => {
    try {
      const backendTenants = await api.tenants();
      if (Array.isArray(backendTenants) && backendTenants.length > 0) {
        const mergedMap = new Map<string, Tenant>();
        // Add defaults first
        DEFAULT_TENANTS.forEach((t) => mergedMap.set(t.id, t));
        // Add custom from localStorage
        try {
          const customStr = localStorage.getItem("voxflow_custom_tenants");
          if (customStr) {
            const customTenants: Tenant[] = JSON.parse(customStr);
            customTenants.forEach((t) => mergedMap.set(t.id, { ...t, custom: true }));
          }
        } catch {}
        // Overlay backend database tenants
        backendTenants.forEach((t) => {
          mergedMap.set(t.id, {
            id: t.id,
            name: t.name || t.id,
            logo_url: t.logo_url,
            agent_name: t.agent_name,
            plan: t.plan,
            custom: !DEFAULT_TENANTS.some((dt) => dt.id === t.id),
          });
        });
        setTenants(Array.from(mergedMap.values()));
      }
    } catch (e) {
      // Offline fallback: keep local tenants
    }
  }, []);

  useEffect(() => {
    // Load custom tenants from localStorage
    try {
      const customStr = localStorage.getItem("voxflow_custom_tenants");
      if (customStr) {
        const customTenants: Tenant[] = JSON.parse(customStr);
        setTenants((prev) => {
          const map = new Map(prev.map((t) => [t.id, t]));
          customTenants.forEach((ct) => map.set(ct.id, ct));
          return Array.from(map.values());
        });
      }
    } catch (e) {
      console.error("Error loading custom tenants", e);
    }

    const savedActive = localStorage.getItem("voxflow_active_tenant");
    if (savedActive) setActiveTenantIdState(savedActive);

    // Initial backend fetch
    refreshTenants();

    // Subscribe to Supabase Auth session changes
    try {
      const supabase = createClient();
      supabase.auth.getSession().then(({ data: { session } }) => {
        const tenantId = session?.user?.user_metadata?.tenant_id;
        if (tenantId) {
          setActiveTenantIdState(tenantId);
        }
      });

      const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
        const tenantId = session?.user?.user_metadata?.tenant_id;
        if (tenantId) {
          setActiveTenantIdState(tenantId);
        }
      });

      return () => {
        subscription?.unsubscribe();
      };
    } catch (e) {
      console.warn("Supabase auth context init:", e);
    }
  }, [refreshTenants]);

  const setActiveTenantId = (id: string) => {
    setActiveTenantIdState(id);
    localStorage.setItem("voxflow_active_tenant", id);
  };

  const addTenant = (name: string): Tenant => {
    const slug = name
      .toLowerCase()
      .trim()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "") || `tenant-${Date.now()}`;

    const existing = tenants.find((t) => t.id === slug);
    if (existing) {
      setActiveTenantId(existing.id);
      return existing;
    }

    const newTenant: Tenant = {
      id: slug,
      name: name.trim() || "New Company",
      custom: true,
    };

    const updated = [...tenants, newTenant];
    setTenants(updated);
    setActiveTenantId(newTenant.id);

    try {
      const customOnly = updated.filter((t) => t.custom);
      localStorage.setItem("voxflow_custom_tenants", JSON.stringify(customOnly));
    } catch (e) {
      console.error("Error saving custom tenant", e);
    }

    return newTenant;
  };

  const activeTenant = tenants.find((t) => t.id === activeTenantId) || tenants[0] || DEFAULT_TENANTS[0];

  return (
    <TenantContext.Provider value={{ activeTenantId, activeTenant, tenants, setActiveTenantId, addTenant, refreshTenants }}>
      {children}
    </TenantContext.Provider>
  );
}

export function useTenant() {
  return useContext(TenantContext);
}
