#!/usr/bin/env bash
# Commit bot state (data/) and push it, retrying on races. FAILS LOUDLY:
# losing a push after posting would make the next run post the same video again.
# Checkout runs with persist-credentials: false, so the write token (GH_TOKEN) exists only in this step.
set -euo pipefail
msg="$1"
git config user.name "flatframedocs-bot"
git config user.email "flatframedocs-bot@users.noreply.github.com"
git config merge.jsonstate.driver "python3 tools/merge_state.py %O %A %B"   # Make + Post may save at once (.gitattributes)
: "${GH_TOKEN:?GH_TOKEN is required to save state}"
AUTH="AUTHORIZATION: basic $(printf 'x-access-token:%s' "$GH_TOKEN" | base64 | tr -d '\n')"
echo "::add-mask::$AUTH"
REMOTE="https://github.com/${GITHUB_REPOSITORY}.git"
git add data
if git diff --cached --quiet; then
  echo "No state changes to save."
  exit 0
fi
git commit -q -m "$msg"
for attempt in 1 2 3 4; do
  if git -c http.extraheader="$AUTH" pull --rebase -q "$REMOTE" "${GITHUB_REF_NAME:-main}"; then
    if git -c http.extraheader="$AUTH" push -q "$REMOTE" "HEAD:${GITHUB_REF_NAME:-main}"; then
      echo "State saved (attempt $attempt)."
      exit 0
    fi
  else
    git rebase --abort 2>/dev/null || true
    echo "::error::Rebase conflict while saving bot state. Someone edited data/ at the same time."
    exit 1
  fi
  sleep $((attempt * 5))
done
echo "::error::Could not push bot state after 4 attempts. Check Settings > Actions > Workflow permissions (Read and write)."
exit 1
