# Nexus ERP — tenant-route authentication audit

Date: 2026-11-20
Scope: Stage 22 source snapshot imported under `stage22-import/`.

## Critical finding

The FastAPI application does not register `TenantMiddleware` in `backend/app/main.py`. The middleware hardening in the Stage 23 candidate therefore does not establish request tenant context at runtime.

A route-level scan also found 13 tenant-sensitive billing endpoints in `backend/app/api/v1/endpoints/billing.py` with no authenticated-user dependency. The file's own comments on subscription creation and checkout state that `tenant_id` should come from the authentication context in production, but the current implementation accepts it as a request parameter.

## Unprotected tenant-sensitive billing endpoints

- `POST /api/v1/billing/subscriptions`
- `GET /api/v1/billing/subscriptions/{tenant_id}`
- `POST /api/v1/billing/subscriptions/{tenant_id}/cancel`
- `POST /api/v1/billing/subscriptions/{tenant_id}/reactivate`
- `POST /api/v1/billing/checkout/session`
- `GET /api/v1/billing/portal/{tenant_id}`
- `GET /api/v1/billing/invoices/{tenant_id}`
- `GET /api/v1/billing/invoices/{tenant_id}/{invoice_id}`
- `GET /api/v1/billing/payment-methods/{tenant_id}`
- `POST /api/v1/billing/payment-methods/{tenant_id}/attach`
- `DELETE /api/v1/billing/payment-methods/{payment_method_id}`
- `POST /api/v1/billing/trials/{tenant_id}/start`
- `POST /api/v1/billing/trials/{tenant_id}/extend`

The unauthenticated Stripe webhook is a separate public integration route and must be protected by Stripe signature verification, not by a user session. The plan-list/read endpoints are public catalog reads and should remain explicitly classified as public if intended.

## Required correction before enabling tenant middleware or production

1. Resolve the authenticated user from the validated access token and derive the tenant ID from that user's database record; do not trust a caller-supplied tenant ID.
2. Add authentication and authorization dependencies to all 13 tenant-sensitive billing routes.
3. Enforce tenant ownership on every subscription, invoice, payment method, and billing portal operation; verify resource ownership before mutation.
4. Restrict trial start/extension to an authorized platform-administration or billing-management permission.
5. Verify Stripe webhook signatures and reject missing/invalid signatures.
6. Audit all other routers for route-level and object-level tenant scoping, including cross-tenant IDOR negative tests.
7. Only then register tenant middleware, after reconciling its public-path allowlist with actual auth, verification, webhook, and health routes.

## Current verification status

- Static route scan: 13 tenant-sensitive billing routes identified without an authenticated-user dependency.
- No billing endpoint code was changed in this audit.
- No production database or deployment was touched.
- This is a confirmed release blocker, not a production penetration-test certification.
