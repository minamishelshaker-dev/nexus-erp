# Nexus ERP — Billing authentication and authorization blockers

Date: 2026-11-20
Scope: static source review of `backend/app/api/v1/endpoints/billing.py`. No API was called and no database was modified.

## Finding: tenant billing operations do not establish caller identity

The billing router is declared without router-level dependencies. The following 13 operations have no `get_current_user`, authenticated principal, or tenant authorization dependency in their function signatures:

| Operation | Route | Risk |
|---|---|---|
| Create subscription | `POST /billing/subscriptions` | Caller supplies `tenant_id`; source comment explicitly says it should come from auth context in production |
| Read subscription | `GET /billing/subscriptions/{tenant_id}` | Tenant subscription disclosure |
| Cancel subscription | `POST /billing/subscriptions/{tenant_id}/cancel` | Unauthorized service cancellation |
| Reactivate subscription | `POST /billing/subscriptions/{tenant_id}/reactivate` | Unauthorized subscription mutation |
| Create checkout session | `POST /billing/checkout/session` | Caller supplies `tenant_id`; payment session can be initiated for another tenant |
| Create billing portal session | `GET /billing/portal/{tenant_id}` | Potential access to another tenant's billing portal |
| List invoices | `GET /billing/invoices/{tenant_id}` | Cross-tenant invoice disclosure |
| Read invoice | `GET /billing/invoices/{tenant_id}/{invoice_id}` | Cross-tenant invoice disclosure |
| List payment methods | `GET /billing/payment-methods/{tenant_id}` | Payment method metadata disclosure |
| Attach payment method | `POST /billing/payment-methods/{tenant_id}/attach` | Unauthorized payment-method mutation |
| Detach payment method | `DELETE /billing/payment-methods/{payment_method_id}` | No tenant identifier or caller ownership check is visible in the endpoint |
| Start trial | `POST /billing/trials/{tenant_id}/start` | Unauthorized entitlement/trial mutation |
| Extend trial | `POST /billing/trials/{tenant_id}/extend` | Unauthorized entitlement/trial mutation |

The public plan catalog endpoints (`GET /plans`, `GET /plans/{plan_id}`) can remain public if intended. The Stripe webhook (`POST /webhooks/stripe`) is expected to be public at the HTTP layer, but it must retain Stripe signature verification; the current handler checks for the signature header and calls the billing service verifier.

## Required correction

1. Derive tenant identity from the authenticated user/session, never from a caller-controlled `tenant_id` parameter for self-service operations.
2. Add explicit billing permissions (owner/admin or a dedicated billing role) to every subscription, invoice, payment-method, and trial mutation/read operation.
3. For `detach_payment_method`, resolve the payment method through the authenticated tenant's Stripe customer and verify ownership before detaching.
4. Keep the Stripe webhook isolated from user-session auth, verify its signature, and make event processing idempotent.
5. Add negative tests proving Tenant A cannot read, cancel, reactivate, attach, detach, start, or extend billing resources belonging to Tenant B.
6. Review whether trial extension is a platform-admin-only operation rather than a tenant self-service operation.

## Related tenancy gate

The current application entry point does not register `TenantMiddleware`. Do not enable it as a quick fix: middleware activation must wait until public authentication routes, billing/webhook exceptions, tenant lookup failure behavior, and route-level ownership checks have been audited. Application-level tenant checks remain mandatory even if middleware is later enabled.

## Release decision

**NO-GO for exposing billing endpoints to untrusted clients until authentication and tenant authorization are implemented and cross-tenant negative tests pass.** This is a source-level finding, not a claim that a live endpoint is currently exposed.
