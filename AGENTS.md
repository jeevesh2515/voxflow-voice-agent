# VoxFlow — Agent Instructions & Universal Laws

## Universal Law: Ponytail Pre-Push Review & Code Pruning

Before executing `git commit` or `git push`, every agent (Antigravity, Claude Code, Cursor, OpenCode, Codex, Windsurf) MUST invoke `/ponytail-review` or apply its principles to the working diff:

1. **`delete` (Dead Code & Speculative Features)**:
   - Remove unused functions, variables, parameters, types, and imports.
   - Remove commented-out code, temporary debug logging, and scratch artifacts.
   - Delete speculative code built for hypothetical future requirements not explicitly requested.
2. **`stdlib` (Reinvented Wheels)**:
   - Replace hand-rolled utilities, helpers, or algorithms with language standard library functions.
3. **`native` (Platform Over Dependency)**:
   - Replace external packages or wrappers where native runtime or platform primitives already suffice.
4. **`yagni` (Premature Abstractions)**:
   - Flatten single-implementation interfaces, unnecessary wrapper classes, and superfluous indirection layers.
   - Prefer direct, boring, explicit code over generic architectures.
5. **`shrink` (Logic Condensation)**:
   - Simplify verbose logic and boilerplate into concise, idiomatic expressions without sacrificing clarity.

### Non-Negotiable Invariants
Never sacrifice:
- Security checks, authentication, authorization, and input validation at trust boundaries.
- Multi-tenant data isolation and query scoping (`tenant_id` filters, RLS policies).
- Error handling that prevents data loss, corruption, or unhandled exceptions.
- Automated tests verifying required business behavior.

### Verification Gate
1. Inspect working diff (`git diff HEAD`).
2. Actively prune over-engineered lines.
3. Run test suite (`pytest`, `npm test`) to guarantee zero regression.
4. When diff is verified lean ("Lean already. Ship."), proceed to commit and push.
