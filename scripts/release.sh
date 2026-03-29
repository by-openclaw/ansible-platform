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

echo "📊 Updating project stats in AGENTS.md..."
if command -v python3 &>/dev/null && [ -f "$REPO_ROOT/AGENTS.md" ]; then
  python3 - "$REPO_ROOT" << 'PYEOF'
import subprocess, sys, re
from pathlib import Path
from datetime import date

repo_path = Path(sys.argv[1])
def run(cmd): return subprocess.check_output(cmd, shell=True, cwd=repo_path, text=True).strip()

version = run("git describe --tags --abbrev=0 2>/dev/null || echo untagged")
stats = {
  "Version": version, "Tagged releases": run("git tag --list | wc -l"),
  "Total commits": run("git rev-list --count HEAD"),
  "Total files": run("find . -not -path './.git/*' -not -path './.venv/*' -type f | wc -l"),
  "Python source files": run("find . -name '*.py' -not -path './.git/*' -not -path './.venv/*' | wc -l"),
  "Test files": run("find tests/ -type f 2>/dev/null | wc -l || echo 0"),
  "Terraform files": run("find . -name '*.tf' -not -path './.git/*' | wc -l"),
  "YAML/Ansible files": run("find . -name '*.yml' -not -path './.git/*' -not -path './.venv/*' | wc -l"),
  "ADR decisions": run("ls docs/adr/*.md 2>/dev/null | wc -l || echo 0"),
  "CI workflows": run("ls .github/workflows/*.yml 2>/dev/null | wc -l || echo 0"),
}
rows = "\n".join(f"| {k} | {v} |" for k, v in stats.items())
block = f"\n## Project Stats\n\n> Auto-updated on every release. Last updated: {date.today().isoformat()}\n\n| Metric | Value |\n|---|---|\n{rows}\n"
p = repo_path / "AGENTS.md"
content = re.sub(r'\n## Project Stats.*?(?=\n## |\Z)', '', p.read_text(), flags=re.DOTALL)
p.write_text(content.rstrip() + "\n" + block)
print(f"  stats updated → {version}")
PYEOF
fi

echo "📤 Committing doc update + pushing..."
git add AGENTS.md 2>/dev/null
git diff --cached --quiet || git commit -m "docs: update project docs to ${NEW_TAG}"
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
