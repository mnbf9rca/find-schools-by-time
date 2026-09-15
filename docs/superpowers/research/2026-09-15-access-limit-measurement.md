## Access limit measurement (issue #18)

Version 20260915T010905Z ran 100 schools with eight workers into motis-spike/runner18-access-fallback. Transit access was 1,800 seconds before boarding and 900 after alighting. Wall time was 468.927 seconds. The 8,513 requests included 7,413 fallback requests across 2,471 empty origins; 1,260 gained street values. No requests retried. Peak server RSS was 10,655,580,160 bytes. Transpose took 15.084 seconds. Nearby walk misses remained 43 of 1,161.

The run took 6.60 times the 71 second baseline, projecting 16 hours 51 minutes from run two's 2 hours 33 minutes. This comparison includes fallback and unpruned candidates; the old baseline used 382 requests. It does not isolate access cost. MOTIS stopped and escalated process checks were clean.

Command, run from issue-18-runner-fixes at commit 770af63:

```sh
uv run --with pyproj fixtures/precompute.py \
  /Users/rob/git/find-schools-by-time/motis-spike/runner18-access-fallback \
  --schools fixtures/spike-sample.csv --workers 8 \
  --graph-dir /Users/rob/git/find-schools-by-time/motis-spike/data.rail
```
