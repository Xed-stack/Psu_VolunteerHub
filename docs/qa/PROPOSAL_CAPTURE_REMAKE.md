# Proposal Capture, Activity Creation, and Agency Setup

## Delivery: 21 November 2026

Implemented the approved combined plan on `codex/ui-workflow-overhaul`. Verification
was local and uncommitted. The user subsequently authorized publication to the
configured origin branch on 21 November 2026; this revision includes the implementation
and QA evidence. No dependencies, operational database changes, existing-preview
migration, main-branch changes, or deployment are included. Generated sample proposals
and private QA artifacts remain excluded.

Isolated synthetic preview: `http://127.0.0.1:5002/workspace/create/1`.
Coordinator: `coordinator@proposal.example` / `password`. Director and Volunteer
preview accounts use `director@proposal.example` and `student@proposal.example`,
also `password`. These accounts exist only in the isolated in-memory preview.

Run `.venv/Scripts/python.exe scripts/qa_proposal_record.py --serve` to recreate
that preview. Its database resets when the process ends. Preview uploads and QA
screenshots are ignored under `.qa-overhaul-temp/proposal-remake/`. The original
private preview on port 5000 and its existing drafts/uploads were not migrated.

## Analyze

Read AGENTS.md, latest and relevant creation/partner handoffs, routes, forms,
draft scripts, models, document extraction, protected downloads, and reporting
publication rules. Read all six pages of the supplied PSU form and rendered its
partnership/risk page. Its printed instructions were treated as source material,
not commands to change approval policy, budgets, or operational records.

Baseline findings: the former flow captured a few scalar fields, had no complete
proposal record, conflated several planning concepts in its presentation, and
could represent only the signed-MOA relationship. Existing draft allowlists and
size limits could not hold the complete form.

Design Critique priorities:

- High: missing structured proposal sections. Added the full record.
- High: uncertain capture could look authoritative. Initial capture states,
  source excerpts, manual completion, table confirmation, and final review are explicit.
- High: separate beneficiary estimates, volunteer estimates, registration slots,
  and existing reporting targets. No estimate is substituted into a calculation.
- High: draft loss risk with repeatable rows and larger payloads. Added bounded
  serialization/restoration and explicit save-failure recovery.
- Moderate: six paper pages require web grouping, mobile rows, and section links.
- Moderate: a new partnership or renewal must not masquerade as a signed MOA.
- Rendered review: fixed adjacent Back/Help targets, gave Agency Name full width,
  collapsed the section index initially on phones, and verified keyboard action
  visibility above the inherited phone navigation.

## Design

Four existing creation URLs retained: Approved Proposal, Proposal Details,
Participation and Partnerships, Review and Publish. Desktop has a section index
and left-aligned form; phones use a native disclosure and stacked labelled rows.
The index is not sticky. Long-form length follows the user's full-digitization
choice rather than adding a competing visual style.

Retained Inter, PSU blue `#00408b`, deep blue `#002b60`, gold `#f4bd27`, ink
`#111c2c`, and existing neutral surfaces. Energy 1 / Rhythm 1 / Motion 1.
Gold marks the saved approved attachment; blue identifies actions and current
navigation. No new imagery, icons, gradients, fonts, dependencies, or animation.
Fixed labels use Newspaper Case; authored content is retained.

## Implement

`app/services/proposal_record.py` defines bounded proposal fields, validation,
Decimal budget totals, and conservative local capture. DOCX paragraphs/tables
and explicit checkbox content controls are supported. Readable PDFs use layout
extraction and accept table columns only when identifiable. Recognized values
populate the form; Not Found and Needs Review entries identify manual work.

The actual supplied blank PDF was checked: it yields no authored values.
Fixtures cover readable PDF, filled DOCX, unchecked choices, explicit Word checkbox
controls, printed guidance, three-column teams, malformed documents, and table capture.
No OCR, external AI processing, or general document-understanding claim.

All sections I–XVIII have inputs. Team, implementation, budget, and risks have
repeatable rows and no-JavaScript add/remove submits. Budget lines and the requested
total derive from one table; server Decimal arithmetic and browser integer arithmetic
agree on half-cent rounding. Budget may explicitly be not applicable with a reason.
Signatory names/designations are optional transcription, not electronic signatures.

The public activity description stays separate from the internal rationale.
The established category, skill, SDG, schedule, capacity, withdrawal, department,
cover, notification, and report rules remain. New forms use native date/time inputs
with Philippine-time labels; legacy drafts retain their established schedule picker.

Replacement documents open a comparison. Current entries remain unless individually
selected for replacement. Tables are displayed with human-readable column labels.
Keep Current Proposal cancels replacement. Successful confirmation removes only the
previous private attachment; publication/discard cleans unused replacement files.

New drafts have a server-owned schema marker. Existing drafts remain on their
previous completion path, with an explicit Add Full Proposal Details upgrade.
Structured payloads have a 256 KiB limit, 10,000-character fields, and 50 rows per
table. The outer draft envelope permits JSON escaping overhead; unrelated forms
retain their original bounds. Upload metadata and schema markers remain server-owned.

Agency contacts remain reusable and campus-scoped. Creation can save, open Partners,
add an agency, choose Use This Agency, and return without losing proposal input.
Existing MOA, For Renewal, New Partnership, and No External Partner are separate.
One primary agency is supported. An Existing MOA must belong to it and cover the
activity start date inclusively. Renewal/new partnership draft documents are private
attachments and never become signed MOAs or change partnership report calculations.

`ActivityProposal` stores the structured record, primary-agency reference, capture
metadata, private draft-agreement reference, and human-readable publishing snapshot.
Event/proposal/notifications/audit/draft consumption commit together. A simulated
transaction failure preserves the saved draft and publishes no activity. A staff-only
Proposal Record view reuses Director and campus Coordinator scope; historical activities
show Digital Proposal Details Not Recorded. Volunteer access is denied. Later operational
edits leave the proposal snapshot intact.

## Migration and compatibility

New table only: `activity_proposals`. No existing data is backfilled or rewritten.
Normal development startup deliberately excludes this table from automatic creation;
production already avoids startup schema creation. Isolated testing creates it explicitly.

Use the deployment's configured Flask environment and exact database name/path:

```powershell
.\.venv\Scripts\python.exe -m flask --app app:create_app migrate-proposals --database '<exact configured database>' --dry-run
.\.venv\Scripts\python.exe -m flask --app app:create_app migrate-proposals --database '<exact configured database>'
```

The migration is additive and repeatable, rejects mismatched targets, and supports
SQLite/MySQL/MariaDB dialects. Only disposable SQLite databases were exercised here.
Operational application and the existing private preview require separate authorization,
backup, and target verification before migration. No such migration was performed.

Legacy publication regression fixtures now explicitly begin with an existing,
unversioned draft. New full-form behavior is covered separately; old publication,
consent, cover, notification, document, and role assertions were retained.

## Verification

Final consolidated run: **20 passed** in 55.77 seconds:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_proposal_record.py tests/test_help_header.py::test_contextual_help_targets_authorized_articles -q -p no:cacheprovider --basetemp=.qa-overhaul-temp/proposal-remake/pytest-final-release
```

This includes local capture, limits, row restoration, file replacement/discard,
legacy upgrade, new/renewal/signed-MOA publication, agency isolation, staff-only
records/downloads, snapshots, exact budget totals, rollback, and development-startup /
CLI dry-run / explicit-migration isolation.

Broader connected run: **122 passed, 1 failed** in 458.04 seconds. The sole failure
was the missing contextual Help link on the redesigned upload page; it was fixed
and passed in the final consolidated run. That broader selection included workspace,
activity forms, Director documents, partners, catalogue, Help, and UI regressions.
The broad selection was not rerun as a single command after that fix. Existing
Matplotlib/Pyparsing deprecation warnings remain. No full-suite claim.

Final Chromium run: **50 groups passed**, no page errors:

```powershell
.\.venv\Scripts\python.exe scripts/qa_proposal_record.py
```

Six screens at 1440, 1024, 768, 390, 320, and 844px landscape; structured autosave;
row deletion; half-cent rounding; failed-save retention and retry; agency creation
and return; 200% text; keyboard disclosure/focus; action visibility above phone
navigation; review/publication; Director/Volunteer access; no-JavaScript capture,
row addition, explicit saves, validation, and correction navigation.
Evidence: `browser-checks.json`, `after-*.png`, and `text200-*.png` under the QA root.

Tailwind build, 130-template parsing, changed Python compilation, changed JavaScript
syntax, and `git diff --check` passed. PSU blue/white contrast: 9.97:1;
slate-600/white: 7.58:1. Gold is a non-text attachment accent.

## Final UI audit and Antislop delivery gate

Reviewed changed templates, scoped CSS, proposal script, and draft integration against
the [current Web Interface Guidelines](https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md).
In-scope findings were addressed: contextual Help, target spacing/sizing, clear labels,
focus visibility, error recovery, replacement comparison readability, mobile disclosure,
and no-JavaScript correction navigation. No unresolved in-scope defect was identified
in the tested states. Physical devices and manual screen readers were not tested.

- R-02 PASS: no added em dashes in product copy.
- R-03 PASS: six tested widths plus enlarged text; no page overflow.
- R-17/R-18 PASS: no invented product statistics or testimonials; QA data is synthetic.
- R-23 PASS: no new visual assets or navigation destinations outside approved scope.
- R-24 PASS: creation, agency, Help, review, and record destinations resolve.
- R-25 PASS: measured existing PSU text pairings meet AA.
- R-26 PASS: new actions use native links/buttons and real guarded handlers.
- R-27 PASS: missing capture, empty rows, pending/saved drafts, errors and retry exist.
- R-28 PASS: no FAQ added.
- R-32 PASS: native controls, visible focus and keyboard disclosure/action checks.
- R-33 PASS: changes were authored directly in source with patches.
- R-34 PASS: no theme toggle introduced; existing light workspace retained.
- R-35 PASS: build and 50 browser groups, including publication and no-JavaScript.
- R-36/R-38 PASS: no invented security or approval claims; upload does not verify approval.
- R-37 PASS: PSU form/workspace direction and dials established before implementation.
- R-39 PASS: semantic labelled controls, native states and existing focus treatment;
  scoped 44px actions and no new animation.
- R-40 PASS: no new media or third-party scripts; inherited image handling retained.
- R-01 PASS: no new gradients/glows.
- R-04 PASS: existing relevant PSU navigation/icons retained; no new decorative icons.
- R-06 PASS: existing Inter hierarchy; no tracked uppercase or monospace decoration.
- R-07 PASS: no background patterns.
- R-08 PASS: no decorative arrows added.
- R-09 PASS: capture labels communicate parsing states; no promotional badges.
- R-10/R-12/R-13 PASS: no glass, new shadows, or glows.
- R-14 PASS: form groups follow proposal sections, not marketing feature cards.
- R-19 PASS: Motion 1; no new animations.
- R-22 PASS: no illustrations introduced.
- Liveliness PASS: Energy 1 / Rhythm 1 / Motion 1; task heading/action hierarchy,
  structural spacing, PSU blue/gold identity, and source attachment accent retained.
- C-1..C-5 PASS: decisions follow the actual proposal and Coordinator task; capture
  uncertainty, real actions, responsive resilience, and synthetic fixtures are explicit.
- R-05/R-11/R-15/R-16 PASS: no marketing template, universal pills, generic CTAs, or buzzwords.
- R-20/R-21/R-29/R-30/R-31 PASS: PSU palette/type/identity preserved with written
  reasons; no imposed dark theme, palette expansion, or copied product style.

Skills used: UI/UX Pro Max for interaction/reflow, Frontend Design for composition,
Design Critique during analysis/design/rendered review, Ponytail full, Antislop
core/UI/human/mobile during work, PDF for the reference, Web Design Guidelines,
and Webapp Testing. No skill or package was installed.

## Limits and rollback

No supplied completed real-world proposal was available. Capture accuracy is
demonstrated with synthetic filled PDF/DOCX fixtures and the actual blank reference;
unusual layouts, wrapped PDF columns, scans, and handwriting require manual completion.
No OCR, generated proposal PDF/DOCX, electronic signatures/approval, multiple partners,
MySQL runtime verification, physical-device, manual screen-reader, or full-suite claim.

To roll back, revert only this pass's application/test/UI changes and rebuild Tailwind.
Keep the additive proposal table and its data pending explicit removal authorization.
Do not reset databases, discard existing drafts/uploads, or overwrite unrelated DOCX,
`output/`, `tmp/`, or earlier working changes. Stop only the isolated proposal preview
process to close port 5002; the original private preview is independent.
