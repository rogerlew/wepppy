#!/usr/bin/env bash
set -euo pipefail

baseline=/workdir/wepp-forest_260430_baseline
ablation=/wc1/ablation/stevens-canyon-synchronization-20260803
worktree="$ablation/source-worktree"
expected=2f65506d239b449bbb73c6820ff9cb949fa55158

test "$(git -C "$baseline" rev-parse HEAD)" = "$expected"
test -z "$(git -C "$baseline" status --porcelain=v1)"

if git -C "$baseline" worktree list --porcelain | grep -Fqx "worktree $worktree"; then
    test -f "$worktree/.git"
    git -C "$baseline" worktree remove --force "$worktree"
fi
git -C "$baseline" worktree prune

test "$(git -C "$baseline" rev-parse HEAD)" = "$expected"
test -z "$(git -C "$baseline" status --porcelain=v1)"
printf 'baseline source clean at %s\n' "$expected"
