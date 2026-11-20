# Notification Tenant-Boundary Review — Stage 11

## Changes applied

- Added a single tenant-scoped user loader requiring `users.id`, `users.tenant_id`, and an active (not soft-deleted) user.
- Added a tenant-scoped notification loader and replaced direct primary-key `db.get()` calls for notifications.
- Scoped notification-batch loading by tenant.
- Validated all batch recipients against the active tenant before creating a batch; duplicate recipient IDs are normalized.
- Scoped email and SMS recipient resolution to the active tenant.
- Resolved push subscriptions through a join to the tenant-owned user record.
- Validated tenant membership before reading/updating user preferences and before subscribing/unsubscribing notification channels. Preference and subscription tables do not carry their own `tenant_id`, so their owner user is the tenant boundary.
- Validated the tenant owner before listing a user's notifications, unread count, or user-specific notification history.

## Async-session lifecycle correction

The prior service launched `asyncio.create_task()` with the same request-scoped `AsyncSession` used to create the notification or batch. That task could outlive the request and race with session closure or transaction rollback.

The fire-and-forget task launches were removed. New notifications remain `pending`; batches remain `pending` until processed. The internal batch processor records notifications as queued, not delivered. Actual delivery requires a durable outbox/worker that opens a fresh database session after the originating transaction commits.

## Verification

- `notification_service.py` and its regression tests compile.
- Tenant-scoped user and notification query smoke checks: 2/2.
- Focused isolated pytest regression module: 3 passed, 1 Pydantic deprecation warning.
- Full backend Python AST parse: 88/88 files passed.
- Static scan: no direct `self.db.get()` and no `asyncio.create_task()` remain in `NotificationService`.
- Notification service import passed with test-only environment values and a Stripe module stub.

## Limitations

- No live PostgreSQL test was run.
- No external email, SMS, push, or webhook provider was invoked.
- Delivery is intentionally deferred until a durable outbox/worker is implemented.
- The repository-wide pytest suite was not run; its global `conftest.py` imports `app.main` and depends on packages absent from this environment (including `python-jose`). The three focused tests were run in an isolated test invocation with a test-only Stripe stub.
