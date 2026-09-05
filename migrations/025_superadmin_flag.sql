-- 025_superadmin_flag.sql
-- Phase 0 step 5: platform superadmin visibility.
--
-- Pairs with apps/api/voxflow_api/auth.py::require_superadmin and
-- apps/api/voxflow_api/routes/superadmin.py.
--
-- Why a column as well as the existing env allow-list
-- --------------------------------------------------
-- `require_platform_admin` already gates on PLATFORM_ADMIN_USER_IDS, which is
-- read from the environment. That allow-list stays: it is the bootstrap path,
-- and it is the only way to grant the FIRST superadmin on a database whose
-- tenant_members table is still empty. This column is the durable path — it
-- grants an additional superadmin without a redeploy or a container restart.
--
-- Authorization therefore reads: env allow-list OR an ACTIVE membership row
-- with is_superadmin. A revoked or merely invited row must never confer it,
-- which is why the index below is partial on status = 'active'.

ALTER TABLE tenant_members
    ADD COLUMN IF NOT EXISTS is_superadmin BOOLEAN NOT NULL DEFAULT FALSE;

-- Partial index: superadmins are a handful of rows out of every membership, and
-- the only question ever asked is "is THIS active user one of them".
CREATE INDEX IF NOT EXISTS ix_tenant_member_superadmin
    ON tenant_members (user_id)
    WHERE is_superadmin AND status = 'active';

COMMENT ON COLUMN tenant_members.is_superadmin IS
    'Platform-wide admin. Confers cross-tenant read access via /api/superadmin; honored only while status = ''active''.';
