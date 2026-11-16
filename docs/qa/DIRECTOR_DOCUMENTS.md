# Director Documents

## Analysis and design before implementation

Proposal/evidence downloads already authorize Directors across campuses. The
Documents directory remains Coordinator-only and the activity workspace lacks a
Director Documents tab. Activity Overview already links to the proposal, but below
the long description. Publication stores the proposal reference on Event; staging
and Coordinator drafts are separate and must remain private.

Use UI/UX Pro Max for discoverability and Frontend Design for composition, with
the established PSU Inter/blue/gold tokens, native links and 44px controls. Apply
antislop during work per the existing session choice and Ponytail full: reuse the
existing file list and protected downloads, with no new routes or schema.

Desktop/mobile wireframe:

```text
Director Activity Overview
Overview | Registrations | Documents | Report
Activity title / campus / lifecycle
Approved Proposal          Download Approved Proposal
stored filename            View All Documents
Schedule / existing activity content

Director Documents
Activity Identity / Documents selected
Documents                    Document Help
Read-only scope explanation
Approved Proposal
stored filename              Download Approved Proposal
Supporting Evidence / existing pagination
file / uploader / date       Download
```

Phones wrap actions below filenames. Reuse restrained dividers; no extra cards,
status metrics, preview library or approval workflow. Director pages never query
announcement history or draft resumes. Director view=announcements is treated as
Documents. Missing attachments have neutral copy, existing private 404/410 responses
remain. Coordinator views/actions/legacy links remain unchanged. Help is Director-
accessible and filters/Back context are retained.

## Preservation checklist

- [x] Director read/download across campuses after publication.
- [x] No unfinished proposal/draft disclosure or Director mutation permissions.
- [x] Proposal filename first; one Overview proposal section; supporting evidence.
- [x] No Director announcement content, controls or legacy draft Resume actions.
- [x] Coordinator campus boundaries, drafts, publish/upload and report links.
- [x] Native navigation, pagination, missing files, mobile and keyboard behavior.

Evidence will be captured under `.qa-overhaul-temp/director-documents/`.

## Implementation

Extended only the existing Documents GET permission to Director/Coordinator. Existing
`owned_event` scope provides university-wide Director access and campus-only Coordinator
access. A Director always gets the evidence dataset, including when requesting
`view=announcements`. Announcement history and draft Resume queries are never executed
for the Director. Upload/compose/staging and legacy mutation guards are unchanged.

Director activity navigation now has Documents. Its single Approved Proposal section
is above Schedule/long description and includes the stored filename, private download
and View All Documents. The previous lower section remains only for Coordinators,
so neither role has duplicate proposal sections. Reports retain existing proposal links.

The reused Documents list has a Director heading, read-only explanation, proposal
filename, existing paginated supporting evidence, and Director-accessible Reports Help.
No upload, compose, announcement, draft Resume or discard controls. Director empty
copy explains that campus Coordinator uploads will appear here; it does not direct
the Director to an unavailable upload action. Coordinator UI is preserved.

No new route, file-serving code, model, library or approval step. Source files remain
private and download names unchanged. Publication still stores the proposal reference
only on successful activity submission; staging creates no published activity.

## Verification completed 16 November 2026

- **34 focused tests passed**: 8 new Director cases and 26 existing document/update
  regressions. Full Coordinator proposal upload → reviewed details/audience → publish
  → Director Overview/Documents → exact original DOCX download was tested for campuses
  1 and 2. Staging did not create a published Event; Director draft access was denied.
- New checks verify one prominent proposal section, preserved source filters, matching
  report access, file pagination, neutral absent proposal, private 404/410 behavior,
  Coordinator foreign-campus denial, Volunteer denial and all four forged Director
  write endpoints. A query-capture test confirms no announcement or draft Resume
  query is executed for a Director, even with forged view/resume parameters.
- The earlier role assertion now explicitly permits only Director Documents GET;
  Director form GET/POST restrictions remain asserted separately. Existing Coordinator
  file validation, staged references, legacy draft cleanup, notification recipients
  and failure rollback tests all passed. No existing failures in this focused run.
- **18 final Chromium groups passed**: Overview/Documents at 320, 390, 768, 844
  landscape, 1024 and 1440px; two-campus PDF proposal/evidence downloads; selected
  navigation; hidden mutation/history controls; source query/pagination; Help and
  Back; 44px links; long unbroken filename, 200% CSS text sizing, actual keyboard
  focus, print and empty states. No JavaScript page errors.
- **4 baseline capture groups** recorded before implementation, including the
  formerly denied Director Documents page and the proposal below long descriptions.
- Tailwind build, **124 templates**, changed Python compilation, existing document
  script syntax and standard Git whitespace check passed. Existing Inter/PSU token
  colors retained (blue/white 9.97:1 and slate/white 7.58:1 as previously measured).

Current [Web Interface Guidelines](https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md)
fetched/reviewed 16 November 2026. Reviewed read-only semantics, real links, authorized
destinations, visible focus, long content, target sizes, empty states and print.
The empty-state role wording was corrected during review. No outstanding in-scope
finding. Antislop gate passed: compact real-document hierarchy, existing identity,
no decorative cards/metrics, invented metadata or additional approval requirements.

Skills used: UI/UX Pro Max for discoverability, Frontend Design for composition,
Ponytail full, antislop core/UI/human/mobile during work, Webapp Testing and current
Web Design Guidelines. No full-suite, MySQL, physical-device, actual toolbar-zoom
or manual screen-reader claim. Downloads use the existing attachment behavior;
no inline document viewer was added. Private unavailable files retain 404/410.

## Evidence and local review

Before/after screenshots and final `results.json`:
`.qa-overhaul-temp/director-documents/{before,after}/`. Key images include
`overview-1440.png`, `documents-390.png`, `*-200.png` and `documents-empty.png`.

Repeat: `npm run build`,
`.venv/Scripts/python.exe -m pytest tests/test_director_documents.py tests/test_documents_announcements_ui.py -q`,
and `.venv/Scripts/python.exe scripts/qa_director_documents.py --stage after`.
Use task-local pytest temporary folders and normal Windows subprocess permissions.

Isolated preview refreshed at `http://127.0.0.1:5000/`. Director and Coordinator
received 200 for existing activity 7 Documents; Volunteer received 403. Director
read-only controls and Coordinator upload controls were checked against that preview.
No operational proposals/files/announcements or notifications were inserted.

## Scoped rollback

Undo only this pass's Director permission/view flag, conditional document heading/
controls/empty copy, added Director Documents tab/title, moved Director proposal
section and its CSS, and one shared Help paragraph. Restore the previous role
assertion only when undoing the permission change. Rebuild and restart the isolated
launcher. Preserve earlier Documents/Announcements, roster, profile, navigation and
all other uncommitted changes; do not reset shared files wholesale.

Local/uncommitted on `codex/ui-workflow-overhaul`; no migration, new dependency,
commit/push, deployment or operational database changes. No data rollback is needed.
