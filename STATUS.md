## Backend

- [x] Data contract complete for Account, Category, Transaction, Tag (see contract/SCHEMA.md and contract/API.md).
- [x] Account DocType fully implemented and verified — owner-scoped permissions, name uniqueness per owner, autoname via `field:account_name`, balance initialization on create.
- [x] Category DocType fully implemented and verified — type-matching, cycle prevention, parent-scoped uniqueness, autoname via `field:category_name`.
- [x] Tag DocType fully implemented and verified — owner-scoped uniqueness, autoname via `field:tag_name`.
- [x] Transaction DocType fully implemented and verified — conditional validation for Income/Expense/Transfer types, soft-delete support, autoname via Random.
- [x] Balance recalculation implemented and verified — `current_balance` recalculated on Transaction create/edit/soft-delete/restore via `on_update` hook. 9-step verification test passing with all affected accounts tracked.

- [x] Offline sync protocol implemented and verified — `pull(since)` returns all records (including soft-deleted transactions); `push()` batch-processes in dependency order (Accounts/Tags → Categories → Transactions) with client_id-based idempotency (stale-rejection via last-write-wins), same-batch reference resolution (`{"client_id": "..."}` objects resolved progressively), and unresolved-reference rejection. 6-test suite passing.

CRUD and sync are complete for v1's core data model. `client_id` field is in place on all four DocTypes for offline sync idempotency. Next phase: dashboard/aggregate endpoints — likely the final piece of the v1 backend API surface.

## Mobile

- [ ] Not started yet
