# Railway demo image: local Docker verification

Date: 21 October 2026. No cloud deployment, original-database access, commit or push.

## Build

Built `psu-volunteer-hub:railway-demo` successfully using Docker Desktop's Linux
engine and the repository Dockerfile. Sandbox access to Docker/build cache was
denied; build and container checks ran with approved outside-sandbox permission.
Existing pinned dependencies installed, including compiled mysqlclient.

Image size reported by Docker: 1,703,608,402 bytes (about 1.70 GB decimal).
Image manifest-list digest from build:
`sha256:97eafee99c129d0f19f1169e8b1d7a88b02fa8b173b5161a60d89349007a4883`.
This is a local image, not uploaded to a registry. Root dependencies are pinned,
but transitive dependencies/base tag are not a fully reproducible lockfile.

## Actual container checks

- Used two separately named containers with network mode `none`, no host ports,
  no source database credentials or original file mounts, and a 512 MiB limit.
- Real image CMD started Gunicorn on supplied PORT=8123. Internal HTTP GET to
  `/auth/login` returned 200. Production startup left the isolated SQLite schema
  empty until explicit provisioning. This checks Docker startup, not Railway MySQL.
- Image contains PSU logo/assets, but no `.env`, `.git`, Database/, instance/ or
  tests/. Public upload volume started empty; original uploaded files excluded.
- `/app/static/uploads` resolved to `/data/public`. Explicit initializer created
  one synthetic test Admin and no events in `/data/demo-smoke.sqlite`.
- Wrote synthetic public/private file probes to the new named volume; stopped
  first container, started replacement from same image/volume. Database and both
  file probes persisted. Public probe served through /static/uploads; private
  probe was not exposed by the tested /static/private URL (404).
- Observed memory after checks: 124.6 MiB then 123.8 MiB under a 512 MiB cap.
  These are light smoke-test observations, not peak/load-test or billing estimates.
- Both containers stopped. Synthetic test volume retained:
  `psu-demo-smoke-20261021-383787a9`; stopped containers end in `-1` and `-2`.
  Random test credentials were not printed or written to the repository.

## Regression checks

18 startup/provisioning tests passed inside the built Linux environment in 2.30s,
with test sources mounted read-only. First attempt had 17 passed / 1 missing-file
failure because a test references development-only app.py, intentionally absent
from the image; rerun mounted that source read-only too and all 18 passed. No
application or assertion changes were made to obtain those passes.

Earlier host deployment-file/startup/provisioning selection: 20 passed.
Full suite not rerun for these deployment-file-only additions; previous published
initialization release had 352 passed. `git diff --check` passed.

## Still pending

Railway trial allowance, MySQL network/driver connection in cloud, actual persistent
volume mounts, proxy/HTTPS behavior, four-role browser workflows, private milestone
authorization and upload persistence after a Railway redeploy. No paid upgrade or
account/project/service changes. Do not treat a SQLite/no-network smoke as those
cloud checks. Pending backup/runbook documents remain preserved separately.
