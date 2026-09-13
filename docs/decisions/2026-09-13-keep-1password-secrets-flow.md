# Keep the 1Password and direnv secrets flow

Date: September 13, 2026

## Decision

The TravelTime keys reach the server only through `op run --env-file=.env.tpl` inside the Makefile. `.envrc` exports a per-project 1Password service account token and nothing else. Both files are committed because they hold references, not values.

## Why

Two spec reviewers proposed replacing this with a gitignored `.env` file as simpler for a one-person local tool. The user chose this flow deliberately; it is their standard pattern across projects (https://blog.cynexia.com/updated-using-1password-and-direnv-to-store-developer-secrets), and the Makefile is the one place `op run` is invoked, as the comments in `.envrc` require. Do not re-propose a plain `.env`.
