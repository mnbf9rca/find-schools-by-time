# Precompute runner implementation plan

**Goal:** Build and verify the resumable school sweeps and per-origin dataset.

**Contract:** `docs/superpowers/specs/2026-09-14-precompute-runner-design.md` and `docs/precompute-runbook.md`.

**Architecture:** One worker owns a school's three request groups and atomic checkpoint. A separate transpose allocates one complete matrix and writes every origin record. The school index always covers the full school list. A recursive standard-library checker validates the final manifest before publishing the current pointer.

## One implementation commit

1. Write request, rounding, cell-centre candidate, school checkpoint, and transpose tests in `test_precompute.py`.
2. Add a subprocess resume test against a local stub on a non-default base URL. Use a small origin fixture while retaining the full school index.
3. Implement `fixtures/precompute.py`, including parameter checks, atomic checkpoints, accumulated metrics, and SIGTERM handling.
4. Independently implement `fixtures/manifest.schema.json`, `fixtures/check_dataset_manifest.py`, and schema tests.
5. Run both existing test commands and feed verification.
6. Run the 100-school live sample with eight workers. Interrupt and resume one run, compare school files and all records against an uninterrupted baseline, and inspect missing walks within two kilometres.
7. Record timings, counts, memory, output size, and coverage in the spike notes. Stop MOTIS and verify no process remains. Commit and push without a pull request.
