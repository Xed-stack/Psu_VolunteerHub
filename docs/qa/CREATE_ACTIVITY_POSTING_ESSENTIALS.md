# Create Activity: Posting Essentials

Date: 22 November 2026. Branch: `codex/ui-workflow-overhaul`. Local implementation only.

## Result

Create Activity retains its four routes/steps: Approved Proposal, Activity Details,
Registration and Partners, Review and Publish. The approved PDF/DOCX attachment,
conservative capture, manual fallback, replacement review, draft saving, cover,
skills, SDGs, schedule picker and partner return flow remain.

Budget, team, implementation, rationale/objectives/methodology, participation
planning estimates, outcomes/evaluation/sustainability/conclusion, risks and
signatories are no longer editable or required in this posting flow. Partnership
narratives are removed; status, campus agency, applicable signed MOA, optional
agreement upload and partner participant estimate remain. No placeholder budgets,
zero estimates or invented N/A values are written.

A separate posting validator is applied to advancement and publication. Final
publication rechecks both posting stages, including direct POST attempts. Full
proposal validation and decimal budget calculations remain available and tested.
Existing authored structured draft data survives normalization, saving and
publication; selecting No External Partner still clears the operational agency
and MOA selection intentionally. Legacy drafts retain their previous path and can
explicitly convert without losing input or uploads.

Newly published records carry `_form_profile: posting_essentials_v1` in existing
JSON content. Their staff record renders the operational publication snapshot and
partner summary without empty proposal sections or a misleading zero budget.
Historical full records retain their full presentation and private attachments.
Detailed saved data stays in the record; editing or displaying that retained data
in the shorter posting UI is outside this change.

Capture still fills only empty fields and replacement applies only selected
posting fields. Explicitly labelled public/activity descriptions can now be
captured. Private rationale text is never promoted to a public description.
Scanned/unreadable proposals still need manual posting details; there is no OCR,
automatic summarization, signature verification or approval verification.

## Analyze, Design and Critique

Audience: campus coordinators posting approved PSU volunteer activities.
Direction: existing Inter, PSU blue/deep blue, gold identity and white/slate forms;
Energy 2 / Rhythm 2 / Motion 1. Existing controls and native behavior are reused.

- High defect: hidden full-proposal requirements would block publication. Resolved
  with posting-specific validation and posting-only capture confirmations.
- Moderate usability defect: duplicating entire proposal sections obscured posting
  requirements. Removed duplicate entry and made the public description guidance
  explain the purpose, planned activity and beneficiaries.
- Moderate responsive defect: long review values overflowed at 320px. Resolved
  with shrinkable grid items, explicit single columns and wrapping.
- Minor hierarchy defect: Primary Agency required marker appeared on its own line.
  Grouped its label and marker; partner fields now have deliberate spacing.
- Moderate enlarged-text defect: step labels broke into narrow fragments. Step
  columns now adapt to text size and stack on narrow available widths.
- Partner controls hide when irrelevant with JavaScript; native server validation
  and visible controls preserve operation without JavaScript.

Desktop/mobile and enlarged-text screenshots were reviewed. No additional style,
chart, animation or design system was introduced. Global navigation remains the
existing shared component; its labels wrap at 200% text and were not redesigned.
Full-page captures include the existing fixed bottom navigation at the viewport
boundary; that capture placement does not represent a permanent form obstruction.

## Verification

**71 unique focused regression cases validated**: 56 existing cases across
`test_proposal_record.py`, `test_activity_forms.py`,
`test_ui_refinement_repairs.py` and `test_help_header.py`, plus all 15 new
`test_posting_essentials.py` cases. The combined run had 70 passes and one new-test
assertion expecting an absent agency key after choosing No External Partner.
That assertion was corrected to allow the intentional empty agency selection;
the complete 15-case posting suite then passed. Earlier fixture corrections
included posting the selected SDGs and comparing normalized table content.
No outstanding product failure remains from these runs.

Tests cover posting without full proposal fields, invalid/incomplete retained
budget data, required posting fields, direct publication validation, capture
confirmation scope, explicit public description capture, saved content, existing
partnership publication/MOA/campus checks, private downloads, immutable snapshots,
transaction failure, draft cleanup, legacy conversion and notification behavior.

**29 browser check groups passed**, using `scripts/qa_posting_essentials.py` with
synthetic in-memory SQLite, CSRF enabled and headless Chromium:

- All four steps at 1440, 1024, 768, 390 and 320px, without page overflow.
- Conditional partner controls, signed-MOA requirement and visible keyboard focus.
- Saving before agency selection and returning with the chosen agency.
- Autosave/refresh and preservation of hidden authored proposal data.
- Server errors, focused error summary and correction.
- Publication, staff snapshot, long text and print text values.
- Real DOCX upload/capture and replacement without overwriting retained edits.
- 200% text reflow and native no-JavaScript advancement.
- No browser page errors; reduced-motion context used.

Evidence: `.qa-overhaul-temp/posting-essentials/results.json` and screenshots in
that directory. Browser runner also parses every Jinja template before starting.
CSS build, changed Python compilation, JavaScript syntax and `git diff --check`
passed. Existing matplotlib/pyparsing deprecation warnings remain.

## Final UI Audit and Antislop Gate

Reviewed changed form/record templates, CSS and interaction code against the
[current Web Interface Guidelines](https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md),
fetched on 22 November 2026. Addressed in-scope wrapping, label grouping and
required-state findings. Native labels, visible focus, existing 44px controls,
field error associations, error-summary focus, draft navigation protection,
loading feedback, optional/empty text, conditional state and reduced-motion
behavior are retained. The posting form disables autocomplete to avoid irrelevant
password-manager completion. No new decorative content or motion.

Skills applied: UI/UX Pro Max (focused form UX search), Frontend Design,
Design Critique, Ponytail full, Antislop during, Antislop UI/Human/Layoutmobile,
Web Design Guidelines and Webapp Testing.

## Limits and Rollback

No full-suite, live/MySQL, physical-device, Firefox/Safari, manual screen-reader
or production deployment claim. No dependencies, migrations, operational data,
commit or push. Previously deferred audit findings remain deferred. Existing
SQL/guide/test, DOCX, output/tmp and their handoff entry remain unrelated and intact.

Rollback only this task's form/record templates, posting validation/capture changes,
JavaScript, help, CSS source/generated CSS, tests, browser runner and documentation.
Preserve unrelated HANDOFF changes and other working files. No database rollback
is required; do not delete historical records, documents or draft data.
