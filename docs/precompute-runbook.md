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

Record two numbers against the prediction, in `motis-spike/NOTES.md` and in a comment on issue #17. Wall time: expect about 2.5 hours at eight workers, the 1.5 hours that batching at 20,000 origins implies plus about an hour for the three modes that now send the whole grid. Time the transpose separately; it was never measured. Peak server resident set size: expect 9.7 GB, the peak measured before the run was stopped at 1,686 schools. Expect about 3.8 GB of disk, the school files plus the records.

The run of version 20260914T220224Z started 2026-09-14T22:02:24Z and finished 2026-09-15T00:35:38Z: 9,194 seconds of wall time, 2 hours 33 minutes, against the 2.5 hours predicted. Peak server resident set was 9.95 GB against 9.7 GB predicted, and 8.8 GB in the original four-school projection. It issued 48,103 requests with none retried, and the transpose took 25.5 seconds. Output was 3,261,103,528 bytes of records plus 445,633,004 bytes of school files. Walk coverage missed 1,865 of 52,548 near pairs, 3.5 percent.

To re-measure the pruning radii rather than trust them, use `fixtures/measure_reach.py`. The issue #18 validator checks the published data.

Public transport allows 1,800 seconds of walking before transit and 900 afterwards. Both limits are recorded in the manifest and resume parameters.

After the school sweeps, empty origins receive outward walking, cycling and driving requests to the schools selected for this run. Completed origins, including those still unreachable, are saved atomically under `fallback/<origin-id>.bin`. Each file uses the school checkpoint layout with full school indices in place of origin indices; its public transport section stays empty. Resume validates and reuses these files before writing origin records.
