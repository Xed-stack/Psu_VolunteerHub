# Activity Documents and Announcements

## Analysis completed before application changes

The Coordinator Documents page currently combines two lists and two forms. Evidence
uses the existing private milestone validator and download route. Metadata includes
filename, category, uploader and UTC upload time; file size is not stored. Proposal
download remains a separate protected route. Retired `uploads/` files return 410.

Publishing stores an announcement and in-app notifications in one transaction for
pending/confirmed account registrations only. External/completed/cancelled records
are excluded. Schedule Notice does not change lifecycle or dates. Neither operation
has an attendance-time restriction; preserve that behavior, including ended events.

Generic drafts already support file references and message/type fields. Old combined
page keys may contain both fields and a staged file. New forms need explicit separate
keys plus authorized legacy Resume support. Successful partial legacy submission must
consume only that form's fields, leaving the other form and its attachment intact.
The upload validator must also protect replacement staging for these forms so an
invalid replacement cannot destroy an already valid staged attachment.

## Design completed before application changes

Audience: campus Coordinators managing activity records and communication. Reuse
PSU blue #00408b, navy #002b60, ink #111c2c, slate #475569, white, Inter, and existing
shell gold accents. Divided records communicate a document register and update
history; avoid matching decorative cards or added metrics. Body text is 16px,
controls 44px, fixed labels Newspaper Case and authored content unchanged.

Desktop wireframe:

```text
Activity Identity / Shared Workspace Navigation
Documents and Updates                  contextual Help
Documents | Announcements
Approved Proposal              Open Approved Proposal
Supporting Evidence                     Upload Evidence
filename.pdf                  uploader / date / Download
Previous Page                              Next Page

Announcements                        Compose Announcement
Event Update / publication date / author
Full readable message
```

Upload screen: predictable Back, compact activity identity, supported formats/size,
one labelled file field or saved reference, linked errors and Upload Evidence.
Compose screen: Back, type, full message, 1000-character counter, visible recipient
rules, escaped inline preview and one Publish Announcement. Desktop compose can
place preview beside the form; phones stack preview below its fields. No separate
review step, recipient selector, email/SMS claim or automatic publishing.

States: empty list, missing proposal, retired file, restored/saving/failed draft,
invalid upload, unavailable author, validation error, submission pending/success/
failure, long content, no JavaScript, and print. Essential privacy and recipient
rules stay visible. Switching views resets pages; Cancel/Back keep source context;
success opens the correct view/page one and the new record anchor. Preserve local
return paths and all existing authorization; no new lifecycle restrictions.

## Preservation checklist

- [x] Private downloads, campus ownership, Director download access and CSRF.
- [x] Existing formats/size/content checks, failed-file cleanup and legacy endpoints.
- [x] Same recipient dataset, atomic notifications and unchanged schedule behavior.
- [x] Separate drafts, upload retention, validated legacy Resume and partial cleanup.
- [x] Escaped content, readable metadata, pagination, return paths and no-JS forms.
- [x] Mobile, enlarged text, focus, preview, loading and print states.

Baseline/final fixtures and images live in `.qa-overhaul-temp/documents-announcements/`.

## Implementation

The existing Documents route now accepts `view=documents|announcements`; missing or
invalid values select Documents. Each list has 25 rows, newest timestamp/ID first,
with eagerly loaded uploader/author metadata. Page indicators remain visible in
print. Proposal and unavailable legacy files are distinct from supporting evidence.
No inferred size, author, approval date or source metadata is displayed.

Added Coordinator-only GET/POST `/workspace/activities/<id>/documents/upload` and
`/workspace/activities/<id>/announcements/new`. New POSTs invoke the existing guarded
coordinator handlers, preserving format checks and recipient queries. Shared form
helpers validate source draft and local return context. Cancel/Back retain source
view/page; success returns to page one with a new-record anchor. Identity and
Documents and Updates navigation stay selected across connected forms/errors.

Compose has a text-only inline preview, a native 1000-character limit/counter,
visible recipient rules and Schedule Notice limitations. Preview/type/counter
refresh after draft restoration and discard without inserting HTML. No recipient
chooser, email/SMS delivery, extra review step, or schedule policy change.

Uploads use the established private UUID path and sanitized download name.
Document-specific staged replacements now run the same milestone validator before
replacing the previous staged attachment. Invalid replacements leave the original
saved file intact. Final file/database failures roll back and remove only the new
UUID file; staged references remain available. Validation errors retain ordinary
values and saved references. Existing GET/download URLs and legacy POSTs still work.

Forms have separate canonical keys and support validated legacy Documents-page keys.
The legacy directory and Saved Drafts expose appropriate Resume actions. Upload
submission consumes only its file/category; announcement submission consumes only
message/type. Draft consumption commits with the evidence/announcement transaction,
so failures preserve the draft and successful partial submissions preserve the
other half. The generic after-request cleanup skips these already-handled drafts.
Staged bytes are removed only after a successful final upload commit.

Discard is explicit: a legacy shared draft carries a visible warning and a specific
native confirmation that both parts will be removed. The new scoped reset clears
displayed values, attachment labels, required state and preview after discard.
Other forms retain their existing discard behavior. Password/consent exclusions
remain unchanged. No-JavaScript forms expose saved values and native submission;
unsubmitted edits/files require JavaScript for refresh persistence, as explained.

## Verification completed 16 November 2026

- **26 new acceptance cases passed** across focused runs: directory defaults,
  newest-first pagination, escaped messages/filenames, unavailable metadata/legacy
  files, role/campus/CSRF boundaries, both legacy POST endpoints, original download
  naming, Director download access, exact recipient inclusion/exclusion, unchanged
  schedule/lifecycle, validation retention, shared legacy drafts submitted in both
  orders, separate canonical drafts, invalid replacement protection, failed commit
  rollback/file cleanup, mismatched resume keys, forged return destinations, size
  limits and restored JPEG/PNG/WebP/DOCX/PDF evidence.
- **7 existing focused regressions passed**: private milestone download, activity
  announcement notification, generic upload/secret exclusion, final attachment
  restoration/cleanup, legacy partner draft upload/cleanup, campus-change cleanup
  and draft-list/private upload discard. Combined focused coverage: **33 cases**.
  Initial new test assertions were corrected to distinguish pagination/download
  links; no existing regression failed. No full historical-suite claim.
- **34 final Chromium groups passed**, including four screens at 320, 390, 768,
  844 landscape, 1024 and 1440px; source-page restoration; escaped preview and type
  restoration; explicit publish and rapid duplicate click guard; staged upload
  refresh; invalid replacement recovery; authenticated download; injected HTTP 503
  draft save failure, retained input, blocked Cancel and successful retry/discard;
  native no-JavaScript compose/upload; 44px targets; long unbroken filename at 200%
  text; keyboard focus; list print; Help/Back and independent empty states. No
  JavaScript page errors. Fixture publication/drafts/files remained isolated.
- **2 original populated baseline captures** (desktop/phone) recorded before
  application changes. Final empty/error/restoration states are also captured.
- Tailwind build, **124 templates**, Python compilation, changed JavaScript syntax
  checks and standard Git whitespace check passed.
- Contrast measured: PSU blue on white **9.97:1**; slate metadata on white **7.58:1**.
  Existing focus indicators, selected borders/text and native controls retained.

### Audit outcome

Current [Web Interface Guidelines](https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md)
fetched/reviewed 16 November 2026. Checked native actions, labels/required indicators,
CSRF, escaped content, loading, feedback, URL state, dates, focus, overflow, targets
and print. Required markers were grouped with their labels after visual inspection.
Document-form Discard Draft now has an explicit 44px target.

The enlarged-text check found focused actions could remain offscreen after reflow,
including actual keyboard navigation. The page-scoped focus handler now checks
header/bottom-navigation visibility on the next frame and centers only an obscured
focused control. It ignores stale focus events, uses no animation, and does not
change unrelated screens. Final keyboard checks passed.

Antislop delivery gate passed: established PSU identity, one content workspace,
purposeful metadata/dividers, no decorative metrics/cards/motion, explicit privacy
and recipient rules, no invented source data. No outstanding in-scope audit finding.
UI/UX Pro Max was primary (verified local feedback/label guidance), Frontend Design
handled composition; Ponytail full, antislop core/UI/human/mobile during work,
Webapp Testing and current Web Design Guidelines were supporting skills.

Physical devices, manual screen readers, browser toolbar zoom, MySQL and the complete
historical test suite remain unverified. 200% above is CSS text sizing. Print shows
the selected list page, labelled with its page/total; no new export was introduced.
Full content/malware scanning is not provided by the existing milestone validator.

## Evidence and repeat commands

Artifacts: `.qa-overhaul-temp/documents-announcements/{before,after}/`.
Representative images: `documents-1440.png`, `announcements-390.png`,
`compose-restored-preview.png`, `compose-save-failure.png`, `upload-390.png`,
`*-200.png`, `*-focus-check.png`, `documents-empty.png`, `announcements-empty.png`.
The final browser check list is in `after/results.json`.

Build: `npm run build`.
Acceptance: `.venv/Scripts/python.exe -m pytest tests/test_documents_announcements_ui.py -q`.
Browser: `.venv/Scripts/python.exe scripts/qa_documents_announcements.py --stage after`.
Use task-local pytest temp folders and normal Windows subprocess permissions where
the sandbox blocks temporary files or Chromium.

## Local delivery and scoped rollback

Refreshed the existing isolated preview at `http://127.0.0.1:5000/`. Existing
Coordinator activity 7 returned HTTP 200 for Documents, Announcements, Upload Evidence,
Compose Announcement and the new Help article. Private database/uploads retained;
no operational evidence, announcements or notifications were created by this task.

Rollback only this pass: restore the Documents directory/form changes and new route
wrappers; undo document-specific handler error/transaction/draft consumption changes,
stage validation, after-request skip, legacy Resume mapping and scoped shared-draft
JavaScript changes. Remove the new document service, components/form/script and Help
topic after removing references; undo only the relevant navigation/style entries.
Rebuild Tailwind and restart the existing isolated launcher. Do not reset shared
workspace/coordinator routes, draft scripts, shell/context or stylesheet wholesale:
they contain earlier roster, profile, notification and other uncommitted work.
No schema or data rollback is required.

Local/uncommitted on `codex/ui-workflow-overhaul`; no new dependencies, migrations,
commits, pushes, publishing, deployment or operational database changes.
