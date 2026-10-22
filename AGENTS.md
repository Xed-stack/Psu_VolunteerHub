<!-- antislop:start -->
## UI design workflow

For user-facing UI, copy, people, mobile layout, or code-comment work, first
read the `antislop` core skill and the skill(s) that match the work.

Before starting UI work, ask whether antislop applies during the work or after
it is done. If the user has already chosen during-work application in the
current conversation, apply it during the work without asking again.

For every user-facing UI change, read and apply:

- `ponytail` at full intensity: reuse existing patterns, prefer native
  platform behavior, and make the smallest safe change.
- `frontend-design`: complete a deliberate design read for the PSU audience,
  task, hierarchy, typography, spacing, and visual direction before building.
- `antislop` and `antislop-ui`: make purposeful visual decisions that retain
  the existing PSU identity rather than adding generic decoration.
- `antislop-human`: verify labels, contrast, visible focus, keyboard operation,
  errors, loading, selected, and empty states.
- `antislop-layoutmobile` when layouts reflow or controls are used on mobile:
  verify intentional reflow, 44px targets, wrapping, and contained overflow.

Before handoff, use `web-design-guidelines` as the UI audit gate: fetch its
current guidelines, review the changed UI files, address in-scope findings, and
report any remaining limitations.

When an installed skill does not cover a real design need, use `find-skills` to
search first. Evaluate source reputation and adoption before recommending a
skill; never install one without explicit user approval. One optional,
uninstalled candidate is `bergside/typeui@typeui-fundamentals` (2.1K installs)
for typography and interface foundations. The current PSU workflow does not
require it.
<!-- antislop:end -->
