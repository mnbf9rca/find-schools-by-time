# Running the full England precompute

Date: September 14, 2026

Commands for the issue #17 run of `fixtures/precompute.py`. Its contract is `docs/superpowers/specs/2026-09-14-precompute-runner-design.md`; read `docs/local-setup.md` first. Every long job runs under a task you can stop, and you never wait synchronously.

1. Verify the feeds: `uv run fixtures/check_manifest.py .`
2. In `motis-spike/data.rail/config.yml`, set `limits.onetomany_max_many` to 20000, all the batches need, and `routing_max_timeout_seconds` to 600.
3. Start the server in a stoppable task: `cd motis-spike && ./motis server -d data.rail`. Watch its output until it reports that it is listening.
4. Hold off sleep in a second stoppable task, against the server's process: `caffeinate -i -w $(pgrep -x motis)`. Do not wrap the server in `caffeinate -is ./motis ...`: stopping that task sends SIGTERM to `caffeinate` and orphans the server. `-s` applies only on AC power, and neither flag keeps the machine awake with the lid closed.
5. Run the 100 school sample end to end, issue #14's done condition: `uv run --with pyproj fixtures/precompute.py motis-spike/sample --schools fixtures/spike-sample.csv --workers 8`. Check its walk coverage first: an origin within 2 kilometres of a school with no walking value is a defect to chase now, not after the full run.
6. Start the full run in a third stoppable task: `uv run --with pyproj fixtures/precompute.py motis-spike/precompute --workers 8`.
7. Watch the progress line's school counter and sampled resident set size, checking the task's output from time to time rather than blocking on it.
8. After an interruption, restart the server if it stopped, restart `caffeinate` with the new process identifier, then rerun step 6. Completed schools are skipped.
9. To stop, stop the run's task, then the `caffeinate` task, then the server's task. Confirm `pgrep -x motis` and `pgrep -f precompute.py` both print nothing; if either still shows a process, kill it by its process identifier and check again.

Record two numbers against the prediction, in `motis-spike/NOTES.md` and in a comment on issue #17. Wall time: expect about 1.5 hours at eight workers, because batching at 20,000 origins makes the driving search three requests per school rather than the two the 1.2 hour projection assumed. Time the transpose separately; it was never measured. Peak server resident set size: predicted 8.8 GB. Expect about 3.8 GB of disk, the school files plus the records.

To re-measure the pruning radii rather than trust them, use `fixtures/measure_reach.py`. The issue #18 validator checks the published data.

Keep each version's local directory until `--delete-version` has run for it, because deletion reads that version's manifest for its keys.
