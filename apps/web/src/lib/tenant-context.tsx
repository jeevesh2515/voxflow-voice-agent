"use client";

import { createContext, useContext, useEffect, useState, ReactNode } from "react";

export type Tenant = {
  id: string;
  name: string;
  logo_url?: string;
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
};

const TenantContext = createContext<TenantContextType>({
  activeTenantId: "varun",
  activeTenant: DEFAULT_TENANTS[0],
  tenants: DEFAULT_TENANTS,
  setActiveTenantId: () => {},
  addTenant: () => DEFAULT_TENANTS[0],
});

export function TenantProvider({ children }: { children: ReactNode }) {
  const [tenants, setTenants] = useState<Tenant[]>(DEFAULT_TENANTS);
  const [activeTenantId, setActiveTenantIdState] = useState<string>("varun");

  useEffect(() => {
    // Load custom tenants from localStorage
    try {
      const customStr = localStorage.getItem("voxflow_custom_tenants");
      if (customStr) {
        const customTenants: Tenant[] = JSON.parse(customStr);
        setTenants([...DEFAULT_TENANTS, ...customTenants]);
      }
    } catch (e) {
      console.error("Error loading custom tenants", e);
    }

    const savedActive = localStorage.getItem("voxflow_active_tenant");
    if (savedActive) setActiveTenantIdState(savedActive);
  }, []);

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
    <TenantContext.Provider value={{ activeTenantId, activeTenant, tenants, setActiveTenantId, addTenant }}>
      {children}
    </TenantContext.Provider>
  );
}

export function useTenant() {
  return useContext(TenantContext);
}
