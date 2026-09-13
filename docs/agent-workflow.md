# Agent workflow

How the user runs work on this repo with several agents in Herdr. Read this only when you are coordinating other agents.

## Layout

- The main Claude session is the coordinator. It briefs other agents, triages review findings, reruns the checks, and reports. It does not design or build.
- `builder` is a Codex agent started with `-m gpt-6-astra -c model_reasoning_effort=high`. It builds and fixes. The spec is its contract; a plan is only a reference, and it may write the code differently where it sees a simpler or more correct way.
- `design` is a Claude agent started with `--model opus`. It writes specs and plans, applies review findings to them, and reviews code against the spec.
- One-off reviews of a spec can run as parallel subagents on Sonnet or Opus.
- Clearing any agent's context with `/clear` before a new task is always fine.
- Tabs and panes are created only when the user asks. Never open a pane or start the server for the user.

## Pipeline after the user approves a spec

Run this without check-ins and report once at the end, unless something blocks:

1. Codex reviews the spec with an open brief; the design agent applies accepted findings.
2. The design agent writes the plan; Codex reviews it; the design agent applies findings.
3. Codex builds on a branch, tests first, one commit per task, with a live smoke check at the end.
4. The design agent reviews the branch against the spec; Codex fixes accepted findings.
5. The coordinator reruns `uv run --with pyproj python -m unittest` and `node check_sort.mjs`, checks for stray server or browser processes, and reports the branch and the command to try it.

Scale it to the change. A few columns or a button gets a short spec, at most one review, and stops once built and passing. Skip the plan document for changes that small. The user merges to main.

## Briefing agents

Put triaged findings in one brief with three sections: accepted (apply), rejected (do not apply, do not re-argue), and open (leave alone, the user is deciding). Tell each agent exactly which files to read and what to reply with. Ask for numbered actionable findings and nothing else.
