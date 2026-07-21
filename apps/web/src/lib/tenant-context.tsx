"use client";

import { createContext, useContext, useEffect, useState, ReactNode } from "react";

export type Tenant = {
  id: string;
  name: string;
  logo_url?: string;
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
};

const TenantContext = createContext<TenantContextType>({
  activeTenantId: "varun",
  activeTenant: DEFAULT_TENANTS[0],
  tenants: DEFAULT_TENANTS,
  setActiveTenantId: () => {},
});

export function TenantProvider({ children }: { children: ReactNode }) {
  const [activeTenantId, setActiveTenantIdState] = useState<string>("varun");

  useEffect(() => {
    const saved = localStorage.getItem("voxflow_active_tenant");
    if (saved) setActiveTenantIdState(saved);
  }, []);

  const setActiveTenantId = (id: string) => {
    setActiveTenantIdState(id);
    localStorage.setItem("voxflow_active_tenant", id);
  };

  const activeTenant = DEFAULT_TENANTS.find((t) => t.id === activeTenantId) || DEFAULT_TENANTS[0];

  return (
    <TenantContext.Provider value={{ activeTenantId, activeTenant, tenants: DEFAULT_TENANTS, setActiveTenantId }}>
      {children}
    </TenantContext.Provider>
  );
}

export function useTenant() {
  return useContext(TenantContext);
}
