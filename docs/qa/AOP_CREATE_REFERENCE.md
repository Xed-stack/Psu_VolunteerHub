# Director Create Goal Reference

Implemented locally on 24 November 2026 on `codex/ui-workflow-overhaul`.

## Design and Behavior

The new unpublished Director goal form follows the supplied reference on desktop.
It has Drafting Mode context, a navy broadcast notice with the official campus
count, paired year/baseline fields, title and scope description, character counts,
a grouped delivery period, date guidance, cancellation, Save Draft and a gold
Publish AOP Goal action. Existing revision screens retain their presentation.

Design read is a focused PSU university-planning form for Directors. Energy 2 /
Rhythm 2 / Motion 1. Navy distinguishes the broadcast notice, gold emphasizes
publication, and a white form panel groups the work. Existing PSU typography and
date controls are reused. New styling applies from 1024px. Additional reference
copy is hidden at narrower widths.

The coverage label is derived from the entered January 1 and December 31 dates.
Counts and year guidance update from form values. Cancellation uses the existing
unsaved-change warning and preserves any saved draft. Backend required fields,
date validation, concurrency checks, publication notifications and revision impact
confirmation remain in place. The description remains plain text. The reference's
example target and dates are not inserted as authored data.

## Verification and Critique

22 focused AOP workflow tests passed in 36.99 seconds. The disposable Chromium
runner `.qa-overhaul-temp/check_aop_create_reference.py` passed these checks.

- Save draft, reopen, publish, goal details and revision entry.
- Cancel navigation with an unsaved-change warning.
- Desktop layout at 1440, 1280 and 1024px with no horizontal overflow.
- Character count, truthful full-year coverage and native date dialog operation.
- Enlarged text at 200% root font size and keyboard reachability.
- JavaScript-disabled native date inputs and Save Draft action.

All templates parsed. CSS build, JavaScript syntax and whitespace checks passed.
The prepared local preview was restarted without seed or migration operations.
Browser evidence and results are in `.qa-overhaul-temp/aop-create-reference/`.

Rendered Design Critique addressed moderate excess spacing and a high-priority
enlarged-text overflow in action groups. Zero minimum widths and wrapping button
labels resolved the overflow, verified by the rerun. Other priorities were a
truthful coverage state and clear cancellation behavior. Required fields and the
existing focused error alert remain available.

Current Web Design Guidelines were fetched and applied on 24 November 2026.
New gold-button text is 9.91:1 and gold notice-heading text is 13.68:1. Controls
retain visible focus, explicit labels, 44px targets and native form behavior.

Antislop delivery gate passes for the requested desktop scope. All applicable
R-01 through R-38 checks were reviewed against the prior AOP gate. The new notice
uses live campus data, the approved reference establishes direction, every action
was exercised, the badge reflects actual dates, and no new asset or unsupported
workflow was introduced. Craftsmanship checks pass with rendered evidence and
the four browser groups above. Mobile-specific rules remain outside this change.

Full-suite, physical-device and manual screen-reader checks were not performed.
The enlarged-text check uses root font resizing rather than browser UI zoom.

## Delivery and Rollback

The isolated local preview serves port 5000. Changes remain local and uncommitted.
Rollback restores this task's creation-form markup, desktop CSS, character/coverage
script additions and route campus-count context. Preserve prior AOP and unrelated
working changes. No database rollback applies.
