# Large demonstration dataset

Continuation note, 31 October 2026: the broader reset described here is a
separate local, unpublished workstream. The dashboard update does not require
running it, replacing activity records, or changing accounts. The published
performance fixture still uses the earlier marker-only confirmation. See
[HANDOFF.md](HANDOFF.md#current-handoff-31-october-2026) for current publication,
decisions, skills/rules, and handover verification. Preserve all target guards
and do not execute a reset as part of reading this document.

30 October 2026 follow-up. Ordinary activity titles and a complete reset keeping
only the three main accounts are implemented locally. The earlier prefix-based
command was published as `2872af3`; this revision is not yet published or hosted.

## Scope

`reset-and-seed-demo` clears ALL activity and participation data in the demo
database regardless of titles or ID markers. This includes activities,
registrations, attendance, external participants, cancellation requests,
recommendations, milestones, announcements, notifications, event/skill and
event/SDG associations, historical source records, cached analytics and activity
audit entries. Dependants are deleted before parents with foreign keys enabled.
Uploaded files stay untouched; database record removal does not erase files from
the upload volume.

Only `student@psu.edu`, `coordinator@psu.edu` and `director@psu.edu` retain their
existing account IDs and passwords. All other accounts, including other manually
created demo roles, are deleted with their profiles, interest/skill links,
reset tokens and policy acceptances. Synthetic volunteers and campus coordinators
are recreated. No administrator account is retained or generated.

These three main accounts must exist with their correct roles before any reset.
Missing student/coordinator campus links
are repaired using the first existing campus in alphabetical order; valid campus
links are retained. Their demographics, skills, interests, profile records and
policy acceptances are preserved; old profile participation history is cleared.
Policy revisions and reference catalogues remain; deleted publisher IDs become
null without changing publication status, text or versions.
An existing volunteer missing a sex response still completes the normal profile
gate after login. No consent is recorded on behalf of preserved accounts.

The new fixture contains:

- 750 participating internal volunteers (the existing student and 749 generated
  identities), across the existing campus catalogue (normally nine campuses).
- A synthetic coordinator for each campus not covered by the preserved
  coordinator. No new administrator or director accounts are generated.
- 200 activities: 165 past and 35 upcoming, spanning roughly 22 months before
  execution and ten weeks after it. There are full, available and zero-capacity
  examples, targets below/at/above verified attendance, missing/partial attendance,
  and optional NDA examples. There is no event-cancelled field in the current
  model, so no fictional event status or new schema field is introduced.
- 5,000 registrations, including 1,000 external registrations; 4,000 attendance
  records; 200 external identities; 150 cancellation requests (50 of each
  decision); 600 SDG mappings; 4,000 in-app notifications; 200 fixture audit rows.
- Pending registrations, completed participation with present/absent/excused
  attendance, and future approved cancellations. No attendance is dated in the
  future. Registrations without attendance include ended activities needing review.

Names, event details and sex responses are synthetic. Sex responses are generated
independently of names. Distribution is illustrative, not calibrated to the
original PDF or an asserted PSU demographic breakdown. Generated emails use the
reserved `.invalid` domain. New accounts have random undisclosed passwords; use
the three preserved accounts for the presentation. Repeat runs replace all
other accounts and regenerate the fixture. Activity titles have no visible
`[Demo Dataset]` or `[Demo Analytics]` prefix. Synthetic provenance remains here
and in generated fixture audit entries.

## Railway operation after deployment

This command is available only after the new source reaches the demo app.
Run in the **PSU-Volunteer-Hub-Demo application service console**, at the Linux
shell prompt. If the prompt is `>>>`, enter `exit()` first.

1. Back up the separate demo database. Check the demo application's DATABASE_URL
   reference points to the demo MySQL service, not the main MySQL service.
2. Inspect the target and replacement counts:

   ```bash
   flask --app wsgi:app reset-and-seed-demo --database railway --dry-run
   ```

3. After checking that the displayed database host belongs to the demo database:

   ```bash
   flask --app wsgi:app reset-and-seed-demo --database railway
   ```

4. Review the per-table deletion counts and number of other accounts to remove.
   Type the exact `RESET ALL DEMO <host>/railway` phrase shown by the command.
   The older `RESET DEMO` phrase is rejected because the deletion scope is broader.
   Only the three main accounts retain their passwords.
5. Check the reported counts and visit opportunities, both dashboards, analytics
   and the cancellation review workspace using the preserved accounts.

The command checks the approved demo app service ID
`5ba9ae8d-fdd4-4850-a193-dcb5760a6e72`, exact configured database name and three
account roles, then requires typed target confirmation. Service identity alone
cannot prove that DATABASE_URL was configured correctly, hence the separate host
check. The schema must already be complete. No create/drop/alter table, migration,
reference-policy publication, email delivery or deployment occurs in this command.
Replacement and generation share one database transaction and commit once.

## Verification

Isolated SQLite, foreign keys enabled:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_demo_dataset.py tests/test_historical_import.py tests/test_production_init.py -q -p no:cacheprovider
```

Current result: **15 passed in 27.23 seconds**. Includes exact fixture counts, cancelled
versus active registration decisions, future full/available events, partial
attendance, chronology, unchanged main account IDs/passwords,
repeat-run replacement, rollback after injected failure, wrong-service/database/
role/confirmation rejection, rejection of the older confirmation phrase,
no-write preview, unmarked-record removal, other-account deletion,
preserved main-account profiles/skills/interests/policy acceptances/reset tokens,
preserved policy text and catalogues, removal of obsolete profile history,
and HTTP 200 responses for public opportunities, Director dashboard/analytics/CSV
and Coordinator dashboard/analytics. New identity password hashing is stubbed in
the large database-logic test to keep the check fast; application hash verification
remains unchanged. This is not a new full-suite or hosted MySQL verification.

Historical verification for `2872af3`: 15 passed in 27.58 seconds, plus 15 passed
in 26.98 seconds against exactly its staged files. Those results covered the
older marker-only reset and all-account preservation, not the new reset scope.

No database write, backup, commit, push or deployment was performed for this
follow-up. Unrelated uncommitted security/recovery changes and attachments remain.
