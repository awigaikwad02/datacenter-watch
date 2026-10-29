#!/usr/bin/env bash
# The Rack Report: hourly update loop.
#
# What it is for: GitHub starts scheduled workflows late or not at all (in October 2026 an
# hourly cron started only every 3 to 6 hours), so the update workflow does not rely on the
# schedule. Instead one job runs this script for about 5 hours 40 minutes, refreshing the data
# once an hour, and then starts the next run of the workflow itself (see update.yml).
#
# Each cycle, starting from the latest main:
#   1. python scripts/fetch_news.py          fetch feeds, rewrite data files and project pages
#                                            (exit 75 = Google rate limited us: skip this cycle)
#   2. python scripts/healthcheck.py --context update   a bad data file is never committed
#   3. python -m pytest -q tests             the tagging and registry tests must pass
#   4. python scripts/data_changed.py        no commit when only timestamps moved
#   5. commit and push "Update news data <time>"
# A failed cycle is logged as a warning and retried next hour; it never stops the loop.
#
# Reads: everything scripts/fetch_news.py reads. Writes: data/news.json, data/registry.json,
# data/status.json, data/archive/, projects/, sitemap.xml (through fetch_news.py) and git commits.
#
# Run by: .github/workflows/update.yml. Locally (one short cycle, no push):
#   LOOP_SECONDS=1 NO_PUSH=1 bash scripts/update_loop.sh
# Settings (environment): LOOP_SECONDS (default 20400 = 5h40m), CYCLE_SECONDS (default 3600).
set -u

LOOP_SECONDS=${LOOP_SECONDS:-20400}
CYCLE_SECONDS=${CYCLE_SECONDS:-3600}
DEADLINE=$(( $(date +%s) + LOOP_SECONDS ))
cycles=0
committed=0
succeeded=0

git config user.name "github-actions[bot]"
git config user.email "github-actions[bot]@users.noreply.github.com"

# Push the cycle's commit, rebasing on anything pushed meanwhile (the health check commits
# data/health.json). On a conflict the cycle gives up; the next one starts from main again.
push() {
  [ -n "${NO_PUSH:-}" ] && return 0
  for i in 1 2 3; do
    git push -q origin HEAD:main && return 0
    git fetch -q origin main
    if ! git rebase -q origin/main; then
      git rebase --abort
      echo "::warning::could not rebase this cycle's data commit on main; it will be redone next hour"
      return 1
    fi
    sleep $((i * 10))
  done
  return 1
}

# One refresh. Returns 0 when it finished (committed or nothing to commit), 1 when it failed.
cycle() {
  if [ -z "${NO_PUSH:-}" ]; then
    git fetch -q origin main && git reset -q --hard origin/main && git clean -qfd projects data
  fi
  python scripts/fetch_news.py
  code=$?
  if [ "$code" -eq 75 ]; then
    echo "::warning::Google rate limited most feeds; skipping this cycle and trying again next hour"
    return 1
  elif [ "$code" -ne 0 ]; then
    echo "::warning::fetch_news.py exited $code; trying again next hour"
    return 1
  fi
  if ! python scripts/healthcheck.py --context update; then
    echo "::error::the data health check failed; nothing committed this cycle"
    return 1
  fi
  if [ -d tests ] && ! python -m pytest -q tests; then
    echo "::error::tests failed; nothing committed this cycle"
    return 1
  fi
  if ! python scripts/data_changed.py; then
    echo "No new or changed items this cycle"
    git reset -q --hard && git clean -qfd projects data
    return 0
  fi
  git add data/news.json data/registry.json data/registry_rejects.json data/project_overrides.json data/status.json data/archive sitemap.xml
  git add -A projects
  if git diff --cached --quiet; then
    return 0
  fi
  git commit -q -m "Update news data $(date -u +'%Y-%m-%d %H:%M UTC')"
  if push; then
    committed=$((committed + 1))
    return 0
  fi
  return 1
}

while :; do
  start=$(date +%s)
  cycles=$((cycles + 1))
  echo "::group::Cycle $cycles at $(date -u +'%H:%M UTC')"
  if cycle; then succeeded=$((succeeded + 1)); fi
  echo "::endgroup::"
  next=$((start + CYCLE_SECONDS))
  # Stop when the next cycle would start after the deadline; the workflow then starts the next run.
  if [ "$next" -ge "$DEADLINE" ]; then break; fi
  sleep $((next - $(date +%s)))
done

echo "Loop finished: $cycles cycles, $succeeded succeeded, $committed committed data"
# Mark the run failed only when no cycle worked at all, so a broken pipeline shows up red.
[ "$succeeded" -gt 0 ]
