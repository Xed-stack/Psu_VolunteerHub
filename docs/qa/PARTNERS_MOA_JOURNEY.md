# Partners and MOAs — Analysis and Design

## Design read before implementation — 14 November 2026

Audience: campus Extension Coordinators managing partner contact records and signed
agreements while preparing an activity. Keep PSU blue/gold, Inter and existing
Tailwind controls. ENERGY 2 / RHYTHM 2 / MOTION 1. Frontend-design supplies the visual
direction; design-system, Search UX, human/mobile checks and antislop support it.

Existing behavior: `/workspace/partners` mixes a campus list and agency creation;
`/workspace/partners/<id>` mixes MOAs and document upload. All routes are Coordinator
only, campus scoped. The `/moa/<id>` URL downloads a private file. Publication checks
inclusive validity on the activity start date, not today or the event end date.
Keep these routes/POST contracts and PDF/DOCX validation (10 MB). Existing draft keys
derive from URLs, so Saved Drafts must bridge old keys without losing uploaded files.

## Wireframes and components

Desktop:

    Partners [campus]                              [Add Agency]
    Search [________________] [Apply Filters] [Reset Filters]
    Agency / contact / agreement count / View Agency
    Pagination

    Agency name                                   [Add MOA]
    Contact details | Edit Agency Details
    Agreements: reference / dates / Current Validity / View MOA

    MOA reference
    Agency / full dates / Current Validity
    Private document [Download Document]
    If coming from creation: activity title/date / applicability [Use This MOA]

Mobile: single-column identity and contact facts; full-width focused forms; record
rows reflow using the existing responsive table pattern. Wide agreement tables have
contained keyboard-accessible scrolling. Native controls and 44px targets throughout.
No decorative imagery, animation or new dependencies. Blue identifies the primary
task; supporting explanations remain readable rather than hidden in tooltips.

States: empty agency/agreement lists, search-empty, pending/saved/failed drafts,
inline validation with focused summaries, valid/upcoming/expired MOAs, applicable or
inapplicable activity date, missing draft/date, private document unavailable.

## Preservation checklist

- Campus permissions, private downloads, legacy POST routes and optional MOAs.
- Inclusive start-date validity and separate current-date labels.
- Search/page Back context, sidebar origin versus activity creation origin.
- New and legacy draft Resume, submitted values, upload retention and cleanup.
- Explicit selection changes only agreement_id; no activity publication.
- Existing account/import work and unrelated files remain untouched.

## Implemented feature coverage

| Feature | Destination and preservation |
| --- | --- |
| Campus agencies | Searchable agency rows, contact, aggregate MOA count, Add Agency and View Agency; 25 rows/page |
| Agency record | Contact details, Edit Agency Details, Add MOA, paginated agreement table |
| Agency create/edit | Dedicated stable-key form, field limits, retained values, linked/inline errors and autosave |
| MOA create | Dedicated reference/date/document form; existing PDF/DOCX validation and private storage |
| Agreement record | Reference, agency, signed filename, dates, current validity, protected download |
| Activity applicability | Explicit separate start-date check and Use This MOA only in creation context |
| Activity detour | Await pending saves/uploads; failed save stays on form; successful use merges only agreement_id |
| Legacy forms/drafts | Existing POST handlers delegate to new forms; Saved Drafts bridges legacy URL keys including query strings |
| Return context | Filtered list → record → edit/details preserves Back context; standalone visits do not imply an activity |

Current validity uses Philippine local today. Applicability uses the saved activity
start date inclusively; publication retains its existing independent checks. Missing
draft/proposal/date does not create a replacement draft or change its values.
No Director/Volunteer permission expansion, agreement editing/replacement/deletion,
agency deletion, schema migration, added libraries, expiry notifications or publishing.

Agency lists aggregate counts in SQL. Agency records explicitly avoid loading all
agreements before paginating them. Query-count verification with 1 versus 26 agencies
remains bounded. Agency identity/campus are retained during contact editing.

## Verification — 14 November 2026

- Focused partner tests: **19 passed**, then **3** additional validity/CSRF/legacy
  isolation cases and **1** bounded-query case passed: **23 focused cases total**.
- Connected workspace, literal-search and shared-submit regression run: **51 passed**.
  Includes original staged-upload restoration via legacy POST, activity publication,
  registration, consent exclusion, attendance boundaries, and exports.
- Existing account form/draft regressions: **2 passed**.
- Chromium partner run: **34 groups passed**, no page errors. Six screens at 320,
  390, 768, 844 landscape and 1440px; explicit MOA application, pending-save detour,
  failed-save recovery/retry, contact editing, filtered Back, Enter/reset search,
  agency draft refresh, uploaded agreement refresh/submission, 200% text, keyboard,
  reduced motion and print capture. Before: **10** layout captures/checks.
- Existing account/import Chromium runner: **60 groups passed** after shared draft
  changes, including all three import reviews, account draft restoration and secret
  exclusion. The account/import implementation from the previous pass is preserved.
- `npm run build`, **116 compiled Jinja templates**, `node --check
  static/scripts/drafts.js`, and `git diff --check` passed.
- Contrast: PSU blue/white **9.97:1**, slate-600/white **7.58:1**, error red/white
  **6.47:1**; all pass AA normal text.
- Refreshed private preview: three-role sign-in smoke passed, Coordinator Partner
  Agencies/Add Agency/Saved Drafts and Director Management/Imports returned 200.

Fixed during verification: Flask scalar pagination initially reduced projected agency
rows to IDs; switched the aggregate query to Query pagination. Windows download test
needed its response closed before deleting the fixture file. Legacy query-string draft
tests now URL-encode the key exactly as browser autosave does. Final checks pass.

Existing Matplotlib/Pyparsing deprecation warnings remain. Previously documented
legacy Admin-role fixtures and older journey redirect assertions were not globally
rewritten. The full historical test suite was not claimed as passing. Physical-device,
manual screen-reader and general multi-tab draft-conflict testing were not performed;
the existing draft model still represents one new activity per user/campus.

## UI audit and delivery gate

Reviewed changed templates, navigation helpers and draft script against the
[current Web Interface Guidelines](https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md),
fetched 14 November 2026. In-scope fixes: meaningful labels, separate links outside
form labels, visible essential validity requirements, linked/focused error summaries,
inline described errors, native actions, stable URL context, 44px controls, mobile
record rows, empty/recovery states and shared loading/focus behavior. Supporting MOA
help remains keyboard/touch operable. No remaining changed-screen audit findings.

Antislop during-work gate: ENERGY 2 / RHYTHM 2 / MOTION 1. Existing PSU identity and
selected-navigation gold accent; one clear task per screen. Lists show actual records,
forms are dedicated, and agreement applicability explains a real domain rule. No fake
metrics, new imagery, decorative animation, template marketing or unused controls.
All preserved features have a visible authorized destination and return path.

## Review, artifacts and rollback

Preview: `http://127.0.0.1:5000`. Coordinator: `coordinator@psu.edu` / `password`.
Open Partners → View Agency → Edit Agency Details / Add MOA → View MOA.
From Create Activity → Audience and Partners, choose “Choose an MOA or Add a Partner,”
then View Agency → View MOA → Use This MOA. It returns to the populated activity draft.
Sign in again after restart. Mail stays suppressed; live preview data was not reseeded.

Screenshots/JSON: `.qa-overhaul-temp/partners/before/` and `after/`. Corresponding
agency list/record images are `0-1440.png`, `1-1440.png`, and 390px variants. New
agreement image: `5-1440.png` / `5-390.png`; additional evidence includes
`empty-search.png`, `agreement-200.png`, and `agreement-print.png`.

Repeat:

```powershell
npm run build
.venv/Scripts/python.exe -m pytest tests/test_partner_journey.py -q
.venv/Scripts/python.exe scripts/qa_partners.py --stage after
```

QA runs use disposable fixtures. The local launcher remains
`.venv/Scripts/python.exe .qa-overhaul-temp/run_local_preview.py`.

Rollback must preserve the earlier, still-uncommitted Accounts/Imports work. Copy the
current diff/new files first. Reverse only this pass's partner-route block, partner
Saved Drafts resume additions, partner navigation entries and draft-exit/upload-failure/
hidden-key-reuse edits. Restore only the Partners/Create Activity/Saved Drafts template
changes from their previous versions; remove only this pass's four added partner/MOA
templates, QA runner and focused test if rolling back. Rebuild compiled Tailwind and
restart the private preview. Do **not** restore entire shared files from the published
baseline, reset the branch, touch the unrelated DOCX or replace databases/uploads.
