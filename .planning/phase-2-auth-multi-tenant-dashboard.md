# Phase 2 — Authentication, Multi-Tenancy & Operations Dashboard (Day 2)

Phase 2 establishes working staff authentication, dynamic multi-tenant company workspace isolation, and direct dashboard integration for managing multi-company voice operations.

## Theory & Architecture

### 1. Staff & Workspace Authentication
Staff access is handled via session-based workspace authentication. Upon signing up or signing in, the user selects or registers a company workspace (e.g. Varun Beverages, Amul Dairy, Apple, or custom operation). The session persists in `localStorage` (`voxflow_session` & `voxflow_active_tenant`), locking all dashboard views, call logs, orders, and stock data to the active `tenant_id`.

### 2. Multi-Tenant Isolation Pattern
Every DB query and frontend store scopes calls, shipments, stock SKUs, and appointments to the resolved `tenant_id`:
- **Active Tenant Context**: `TenantProvider` in `apps/web/src/lib/tenant-context.tsx`.
- **Dynamic Tenant Onboarding**: Users can register new companies dynamically at sign-up or via the Dashboard Topbar switcher.
- **Data Scoping**: Dashboard modules (`/dashboard/calls`, `/dashboard/orders`, `/dashboard/stock`, etc.) filter records by active tenant context.

---

## Phase 2 Checklist

- [x] **Sign-Up Flow**: Wire `/sign-up` form to create/register company workspace and redirect directly to `/dashboard`.
- [x] **Sign-In Flow**: Wire `/sign-in` form with company tenant selector, credentials validation, and 1-click Quick Demo login.
- [x] **Dynamic Multi-Tenancy**: Support adding new company workspaces (e.g., Apple, Shree Traders) on the fly and persisting in storage.
- [x] **Dashboard Workspace Switcher**: Add inline tenant switcher and "Add Company" action in `Topbar.tsx`.
- [x] **Session Persistence**: Persist active tenant and admin session across page reloads.
- [x] **Security Audit**: Verify zero exposed API secrets, sanitized form inputs, and RLS data boundary isolation.

---

## Definition of Done

1. A user navigating to `/sign-up` can register a new company (e.g. "Apple" or "ZenithTech"), submit the form, and immediately land on `/dashboard`.
2. A user navigating to `/sign-in` can select a company, authenticate, or use 1-click Quick Demo access to enter `/dashboard`.
3. The dashboard header allows switching between companies (Varun Beverages, Amul, Haldirams, Britannia, Apple) and adding new ones dynamically.
4. All static build checks (`npm run build --workspace=apps/web`) compile with 0 errors.
