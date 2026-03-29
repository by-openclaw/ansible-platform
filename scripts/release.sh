#!/usr/bin/env bash
# release.sh — Conventional Commits release via commitizen
# Usage: ./scripts/release.sh [--dry-run] [--increment PATCH|MINOR|MAJOR]
# Requires: cz (commitizen), git, gh (optional for GitHub Release)
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
DRY_RUN=false
INCREMENT=""

for arg in "$@"; do
  case $arg in
    --dry-run) DRY_RUN=true ;;
    --increment) INCREMENT="$2"; shift ;;
    --increment=*) INCREMENT="${arg#*=}" ;;
  esac
done

cd "$REPO_ROOT"

echo "🔍 Checking working tree..."
if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "❌ Uncommitted changes present. Commit or stash first."
  exit 1
fi

echo "📦 Current version: $(cz version --project)"
echo "📝 Commits since last tag:"
git log "$(git describe --tags --abbrev=0)..HEAD" --oneline 2>/dev/null || echo "  (no previous tag)"

if $DRY_RUN; then
  echo ""
  echo "🔍 Dry run — next version would be:"
  cz bump --dry-run ${INCREMENT:+--increment $INCREMENT}
  exit 0
fi

echo ""
echo "🚀 Bumping version..."
cz bump --yes --changelog ${INCREMENT:+--increment $INCREMENT}

NEW_TAG=$(git describe --tags --abbrev=0)
echo "✅ Bumped to $NEW_TAG"

echo "📤 Pushing commits + tags..."
git push && git push --tags

# GitHub Release (optional — requires gh CLI)
if command -v gh &>/dev/null; then
  echo "📋 Creating GitHub Release..."
  # Extract changelog section for this version
  VERSION="${NEW_TAG#v}"
  NOTES=$(awk "/^## \[$VERSION\]/,/^## \[/{if (/^## \[/ && !/^## \[$VERSION\]/) exit; print}" CHANGELOG.md | tail -n +2)
  gh release create "$NEW_TAG" --title "$NEW_TAG" --notes "$NOTES"
  echo "✅ GitHub Release created: $NEW_TAG"
fi

echo ""
echo "🎉 Release $NEW_TAG complete."
