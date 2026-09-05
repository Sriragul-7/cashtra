## Backend

- [x] Data contract complete for Account, Category, Transaction, Tag (see contract/SCHEMA.md and contract/API.md).
- [x] Account DocType fully implemented and verified — owner-scoped permissions, name uniqueness per owner, autoname via `field:account_name`, balance initialization on create.
- [x] Category DocType fully implemented and verified — type-matching, cycle prevention, parent-scoped uniqueness, autoname via `field:category_name`.
- [x] Tag DocType fully implemented and verified — owner-scoped uniqueness, autoname via `field:tag_name`.
- [x] Transaction DocType fully implemented and verified — conditional validation for Income/Expense/Transfer types, soft-delete support, autoname via Random.
- [x] Balance recalculation implemented and verified — `current_balance` recalculated on Transaction create/edit/soft-delete/restore via `on_update` hook. 9-step verification test passing with all affected accounts tracked.

CRUD is complete for v1's core data model. Next phase: custom endpoints (dashboard aggregates, sync protocol).

## Mobile

- [ ] Not started yet
