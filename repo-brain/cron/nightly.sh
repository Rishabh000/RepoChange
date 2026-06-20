#!/usr/bin/env bash
# Nightly autonomous cleanup. Runs the full pipeline without prompting.
# Install with: crontab -e   then add:
#   0 2 * * * /Users/risha/source/RepoChange/repo-brain/cron/nightly.sh >> /tmp/repo-brain.log 2>&1
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
"$HERE/repo-brain" organize --auto
"$HERE/repo-brain" index
