1. **Runtime recommendation — JavaScript.** Assessment, checked 13 September 2026. Read `app.py`, `index.html`, `sort.js`, and `Makefile`: the server is actually 188 lines, including HTTP plumbing; its business logic is small. Each search selects 2,000 nearest schools, makes one TravelTime request, joins results, and sorts before rounding. Postcodes.io lookup and CSV generation happen in the browser. Keep the Python data builder and port the request handler to plain JavaScript, without a framework.

   Python Workers remain **beta**, running CPython compiled to WebAssembly through Pyodide inside V8. Cloudflare snapshots imports at deployment to reduce initialization. [Python runtime](https://developers.cloudflare.com/workers/languages/python/how-python-workers-work/), [status](https://developers.cloudflare.com/workers/languages/python/).

   `urllib.parse` works; the existing blocking `urllib.request.urlopen` is not a drop-in networking solution. Pyodide lacks ordinary sockets: use asynchronous `workers.fetch`. Likewise, `http.server.HTTPServer(...).serve_forever()` cannot serve a listening port; replace it with `WorkerEntrypoint.fetch`. `zoneinfo` works with timezone data supplied through `tzdata`; do not assume an OS timezone database. [Pyodide constraints](https://pyodide.org/en/stable/usage/wasm-constraints.html), [Python fetch](https://developers.cloudflare.com/workers/examples/fetch-json/), [entrypoint](https://developers.cloudflare.com/workers/languages/python/basics/).

   Cloudflare's December 2025 benchmark measured **1,027 ms mean cold start**, importing httpx/FastAPI/Pydantic; that is neither this app's latency nor an SLA. Snapshotting avoids booting everything afresh, but Python still adds runtime/tooling complexity. A JS port is my simpler-path recommendation. Preserve next-weekday **08:30 Europe/London minus requested minutes**, including BST transitions; test Friday/weekend and clock-change boundaries. [Benchmark](https://developers.cloudflare.com/changelog/post/2025-12-08-python-cold-start-improvements/).

2. **Dataset placement — bundle a JSON import.** Locally measured: **4,373 records; 2,004,320 bytes (1.91 MiB); gzip 248,164 bytes (242.35 KiB)**. Current limits specify **64 MiB uncompressed**, with **no compressed-size limit**, for paid Workers. Older 10 MB gzip guidance is outdated. Global initialization must finish within **1 second**; use `wrangler deploy --dry-run --outdir bundled` to inspect the actual generated bundle. [Size/startup limits](https://developers.cloudflare.com/workers/platform/limits/#worker-size).

   | Option | Assessment |
   |---|---|
   | Inline JS data | Fits comfortably; avoid manually duplicating generated JSON. |
   | `import schools from './schools.json'` | **Recommended.** Wrangler/esbuild bundles JSON into JS; it still counts toward script size. No storage calls, bindings, or independent data rollout. |
   | KV | Fits its **25 MiB/value** limit; adds a namespace, reads, and eventual consistency. Useful if data must update independently. |
   | R2 | Easily stores this object; adds bucket/upload/read plumbing. Standard free allowance: **10 GB-month, 1M writes, 10M reads/month**. Unnecessary here. |
   | Static Asset | Fits **25 MiB/file**; free storage/serving. Worker can load it through `ASSETS.fetch` and retain parsed data per isolate, but this adds initialization I/O. Best fallback if bundle startup becomes problematic. |

   [Bundling](https://developers.cloudflare.com/workers/wrangler/bundling/), [JSON loader](https://esbuild.github.io/content-types/#json), [KV limits](https://developers.cloudflare.com/kv/platform/limits/), [R2 allowances](https://developers.cloudflare.com/r2/pricing/#free-tier), [assets](https://developers.cloudflare.com/workers/static-assets/billing-and-limitations/).

3. **Request limits.** Paid HTTP Workers have **30 seconds default CPU**, configurable to **300 seconds**, and **128 MB memory per isolate**. Network waiting does not consume CPU. HTTP wall time and individual subrequest duration have no fixed runtime limit while the client remains connected. Consequently, a 30-second TravelTime wait is acceptable. Explicitly abort the upstream fetch after **30,000 ms**, covering response-body reading too; avoid automatic metered retries. `waitUntil` provides only **30 seconds** after disconnect/response. Incoming bodies depend on the zone plan: **100 MB Free/Pro, 200 MB Business, up to 5 GB Enterprise**. Preserve the app's **4,096-byte** application cap, enforced on bytes read, including requests without Content-Length. [Limits](https://developers.cloudflare.com/workers/platform/limits/).

   Paid subrequests now default to **10,000/request**, configurable up to **10 million**. This app needs one TravelTime fetch, plus one Siteverify fetch with Turnstile, and cache operations. Browser geocoding is separate. [February 2026 change](https://developers.cloudflare.com/changelog/post/2026-02-11-subrequests-limit/).

4. **Secrets and 1Password.** Set `TRAVELTIME_APP_ID`, `TRAVELTIME_API_KEY`, and `TURNSTILE_SECRET_KEY` through `npx wrangler secret put NAME`; access them as `env.NAME`. Values stay outside the script, browser, and Wrangler `vars`. Secret updates create and deploy a Worker version. [Secrets](https://developers.cloudflare.com/workers/configuration/secrets/).

   Keep 1Password as the source of truth and keep `op run --env-file=.env.tpl` inside Makefile targets, matching the existing decision. A secrets-sync target can run a child process under `op run`, serialize **only the required keys** as JSON, and pipe directly to `wrangler secret bulk` inside that child. No plaintext file, shell tracing, or secret-bearing command arguments; never upload the 1Password service-account token. Rotation requires re-syncing Cloudflare's stored copy. Existing local `make run` remains valid. [1Password process injection](https://www.1password.dev/cli/secrets-scripts), [Wrangler stdin support](https://github.com/cloudflare/workers-sdk/blob/main/packages/wrangler/src/secret/index.ts).

5. **Minimum public-endpoint protection.** Use **Turnstile + a Workers rate-limiting binding + a short Cache API cache**. Validate method, bounded JSON and fields; rate-limit before external calls; verify Turnstile server-side before spending TravelTime credit. Start with **5 searches/60 seconds/IP**, using Cloudflare's connecting IP; this is a tunable compromise for anonymous users sharing networks. Binding periods are **10 or 60 seconds**; counters are permissive, eventually consistent and local to each Cloudflare location, not a global spending cap. [Binding](https://developers.cloudflare.com/workers/runtime-apis/bindings/rate-limit/).

   Turnstile Free includes unlimited challenges/verifications. Tokens expire after **300 seconds** and are single-use: validate `success`, expected hostname and action, and refresh the token for every submission. Fail closed on verification failure. [Plan](https://developers.cloudflare.com/turnstile/plans/), [validation](https://developers.cloudflare.com/turnstile/get-started/server-side-validation/).

   WAF rate-limiting rules can reject requests before Worker execution on a proxied custom domain. Zone **Free/Pro/Business include 1/2/5 rules**; Free supports IP counting with **10-second** counting/mitigation periods. Workers Paid does **not** buy Pro WAF features. A Free-zone `/search` burst rule is optional additional protection; the binding also protects `workers.dev`. [WAF availability](https://developers.cloudflare.com/waf/rate-limiting-rules/).

   Cache successful searches for **15 minutes**, using a synthetic GET key hashing canonical validated coordinates, minutes, mode, computed departure timestamp and dataset version; omit Turnstile tokens. Store a cacheable internal response while retaining browser `no-store`. Cache API is per-location and can evict entries; concurrent misses can still spend multiple calls. KV shares results across locations but propagation can take **60 seconds or longer** and it adds storage operations. Start with Cache API. Neither cache prevents deliberately unique searches. [Cache API](https://developers.cloudflare.com/workers/runtime-apis/cache/), [KV consistency](https://developers.cloudflare.com/kv/concepts/how-kv-works/).

   For a hard budget, require an upstream-enforced quota if available; otherwise add one Durable Object that atomically reserves a global allowance before each paid call. IP limits and Turnstile alone cannot guarantee bounded third-party spending.

6. **Estimated monthly Cloudflare cost, USD.** Assume one Worker invocation/search, **10 ms average CPU** (estimate, not measured), spare account allowances, bundled data, and the minimum above.

   | Searches/month | CPU/month | Total paid subscription | Increment above existing plan |
   |---|---:|---:|---:|
   | 1,000 | 10,000 ms | $5 | $0 |
   | 100,000 | 1,000,000 ms | $5 | $0 |

   Paid includes **10M requests and 30M CPU-ms/month**; overages are **$0.30/M requests + $0.02/M CPU-ms**. Even 100 ms/search fits at 100,000 searches. If other apps exhaust allowances, these workloads add approximately **$0.0005/$0.05** respectively. Static Assets, egress and waiting time add no charge in this configuration. TravelTime, domain registration, optional Durable Objects and taxes are excluded. Cache hit rates reduce TravelTime calls, not incoming Worker invocations. [Pricing](https://developers.cloudflare.com/workers/platform/pricing/).

7. **Shape and illustrative `wrangler.jsonc`.** Yes: one Worker application with Static Assets and one dynamic endpoint, `POST /search`. Stage only `index.html` and `sort.js` into `public/`; import JSON from outside it. Retain browser sorting/CSV and add Turnstile. This config uses the free `workers.dev` hostname; no separate zone route is necessary. Handler rejects other methods/paths. [Asset routing](https://developers.cloudflare.com/workers/static-assets/), [configuration](https://developers.cloudflare.com/workers/wrangler/configuration/).

   ```json
   {
     "name": "find-schools-by-time",
     "main": "worker.js",
     "compatibility_date": "2026-09-13",
     "workers_dev": true,
     "assets": {
       "directory": "./public",
       "run_worker_first": ["/search"]
     },
     "limits": { "cpu_ms": 1000 },
     "ratelimits": [{
       "name": "SEARCH_LIMITER",
       "namespace_id": "1001",
       "simple": { "limit": 5, "period": 60 }
     }]
   }
   ```

   Choose an unused account namespace ID. `cpu_ms` limits computation, not the 30-second network wait. No deployment or app modifications were performed.
