# find-schools-by-time

A personal, local web app: enter a UK postcode and a time limit, get the post-16 schools and colleges in England reachable by 08:30 on a weekday, with their 2024/25 A level results, sortable and downloadable as CSV. Minimal MVP by design: no framework, no database, no deployment.

## Run and test

- `make run` starts the server on http://127.0.0.1:8000. It needs the TravelTime keys, which arrive through `op run` and `.env.tpl`; see `.envrc` for how secrets work here and never put values in the repo.
- `make build` regenerates `schools.json` from the two CSVs under `data/` (gitignored, downloaded by hand). Only needed when the source data changes.
- `uv run --with pyproj python -m unittest` and `node check_sort.mjs` are the whole test suite. Both must pass before a commit.

## Read before changing anything

- `docs/superpowers/specs/` holds the contracts, one per iteration. The design is decided there, not in the code.
- `docs/superpowers/research/2026-09-13-results-data.md` explains the results dataset, its columns, and its coverage gaps.
- `docs/superpowers/plans/` holds the implementation plans that were executed. Reference only.
- `docs/decisions/` holds one file per design decision with its rationale. Check there before proposing a change to how travel times, coverage, or secrets work.
- `docs/agent-workflow.md` describes the multi-agent setup and delivery pipeline. Read it only if you are coordinating other agents.

## How work happens here

- Keep it minimal. Prefer deleting to adding. No new dependencies without a reason the user has agreed to.
- Two writing skills are mandatory for every agent: replies follow `communicating-clearly`, and prose deliverables (specs, plans, decision records, research notes, issue comments, pull request bodies) follow `writing-clearly`. Read both before writing. Every agent also has the superpowers skills: use `brainstorming` before a spec, `writing-plans` before a plan and `test-driven-development` before a build.
- Every data source, API or tool gets a row in `LICENSES/README.md` before it is used, and its verbatim licence text goes in `LICENSES/`.
- The backlog is the GitHub milestones and issues on `mnbf9rca/find-schools-by-time`, worked in milestone order. Each issue states its done condition and links to the research it rests on. Read the issue before starting it.
- Design before building: a change gets a short spec in `docs/superpowers/specs/` and the user's approval, then a build with tests first.
- Small changes get at most one review. Once built and passing, stop.
- Never detach a process with `nohup`, `disown`, `setsid` or a bare `&` you walk away from. Every long-running job (imports, servers, downloads) runs under a harness-controlled task that can be stopped, so nothing is left running when the session ends.
- Codex's sandbox kills backgrounded children: run short jobs in the foreground with escalation, and servers only in a Codex-managed background terminal you can stop. Stop servers yourself and confirm with escalated `pgrep` that none remain before replying.
- Never merge to main, open terminal panes, or start the server on the user's behalf. Tell them the branch and the command.
- Address the user as "human meatbag".
