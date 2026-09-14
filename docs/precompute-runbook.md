# Running the full England precompute

Date: September 14, 2026

These are the commands for the issue #17 run of `fixtures/precompute.py`. Its contract is `docs/superpowers/specs/2026-09-14-precompute-runner-design.md`. Read `docs/local-setup.md` first. Every long job runs under a task you can stop, and you never wait on one synchronously.

1. Verify the feeds: `uv run fixtures/check_manifest.py .`
2. In `motis-spike/data.rail/config.yml`, set `limits.onetomany_max_many` to 200000 and `routing_max_timeout_seconds` to 600.
3. Start the server in a stoppable background task: `cd motis-spike && caffeinate -is ./motis server -d data.rail`. Watch its output until it reports that it is listening.
4. Check pruning on a few contrasting schools: `uv run --with pyproj fixtures/precompute.py --verify-pruning 137353 131065 110533 150099`.
5. Start the run in a second stoppable task: `caffeinate -is uv run --with pyproj fixtures/precompute.py motis-spike/precompute --workers 8`.
6. Watch the progress line's school counter and its sampled resident set size. Check the task's output from time to time rather than blocking on it.
7. After an interruption of either process, restart the server if it stopped, then rerun the same command from step 5. Completed schools are skipped.
8. To stop, stop the run's task, then the server's task, then confirm that `pgrep -x motis` and `pgrep -f precompute.py` both print nothing.

Record two numbers against the prediction. Wall time: predicted 1.2 hours at eight workers, plus the transpose, which was not measured. Peak server resident set size: predicted 8.8 GB. Expect wall time a little above the prediction, because the projection assumed the driving search took two requests per school and batching at 20,000 origins makes it three.
