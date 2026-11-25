Use the security-reviewer subagent. Audit every router under backend/app/routers/owner and every
repository. For each endpoint confirm: tenant comes from TenantContext, query filters by business_id,
cross-tenant access → 404, and a test exists in tests/tenancy. Output a table: endpoint | ok? | evidence | fix.
