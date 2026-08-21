"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { TenantMembership, TenantRole } from "@/lib/types";

export type Tenant = {
  id: string;
  name: string;
  logo_url?: string | null;
  agent_name?: string | null;
  plan?: string | null;
  role: TenantRole;
};

const DEMO_TENANT: Tenant = {
  id: "varun",
  name: "VoxFlow Demonstration Workspace",
  role: "viewer",
};

const EMPTY_TENANT: Tenant = {
  id: "",
  name: "No authorized workspace",
  role: "viewer",
};

type TenantContextType = {
  activeTenantId: string;
  activeTenant: Tenant;
  tenants: Tenant[];
  loading: boolean;
  demoMode: boolean;
  setActiveTenantId: (id: string) => void;
  refreshTenants: () => Promise<void>;
};

const TenantContext = createContext<TenantContextType>({
  activeTenantId: "",
  activeTenant: EMPTY_TENANT,
  tenants: [],
  loading: true,
  demoMode: false,
  setActiveTenantId: () => {},
  refreshTenants: async () => {},
});

function membershipToTenant(membership: TenantMembership): Tenant | null {
  if (membership.status !== "active" || !membership.tenant) return null;
  return {
    id: membership.tenant.id,
    name: membership.tenant.name,
    logo_url: membership.tenant.logo_url,
    agent_name: membership.tenant.agent_name,
    plan: membership.tenant.plan,
    role: membership.role,
  };
}

export function TenantProvider({ children }: { children: ReactNode }) {
  const { user, loading: authLoading } = useAuth();
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [activeTenantId, setActiveTenantIdState] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [demoMode, setDemoMode] = useState(false);

  const refreshTenants = useCallback(async () => {
    if (!user) {
      setTenants([]);
      setActiveTenantIdState("");
      setDemoMode(false);
      setLoading(false);
      return;
    }

    setLoading(true);
    try {
      const response = await api.myMemberships();
      const authorized = response.memberships
        .map(membershipToTenant)
        .filter((tenant): tenant is Tenant => tenant !== null);
      const resolved = response.demo_mode && !authorized.length ? [DEMO_TENANT] : authorized;
      setTenants(resolved);
      setDemoMode(response.demo_mode);
      const saved = typeof window !== "undefined" ? localStorage.getItem("voxflow_active_tenant") : null;
      const nextActive = resolved.some((tenant) => tenant.id === saved)
        ? saved!
        : resolved[0]?.id || "";
      setActiveTenantIdState(nextActive);
      if (nextActive && typeof window !== "undefined") {
        localStorage.setItem("voxflow_active_tenant", nextActive);
      }
    } catch {
      // A cold backend must not silently make a real browser-selected tenant
      // authoritative. Keep an empty list until the membership service responds.
      setTenants([]);
      setActiveTenantIdState("");
      setDemoMode(false);
    } finally {
      setLoading(false);
    }
  }, [user]);

  useEffect(() => {
    if (authLoading) return;
    void refreshTenants();
  }, [authLoading, refreshTenants]);

  const setActiveTenantId = useCallback((id: string) => {
    if (!tenants.some((tenant) => tenant.id === id)) return;
    setActiveTenantIdState(id);
    localStorage.setItem("voxflow_active_tenant", id);
  }, [tenants]);

  const activeTenant = useMemo(
    () => tenants.find((tenant) => tenant.id === activeTenantId) || tenants[0] || EMPTY_TENANT,
    [activeTenantId, tenants],
  );

  return (
    <TenantContext.Provider value={{ activeTenantId, activeTenant, tenants, loading, demoMode, setActiveTenantId, refreshTenants }}>
      {children}
    </TenantContext.Provider>
  );
}

export function useTenant() {
  return useContext(TenantContext);
}
