#!/usr/bin/env bash
set -euo pipefail

baseline=/workdir/wepp-forest_260430_baseline
study_root=/wc1/ablation/stevens-canyon-htcs-ensemble-20260803
expected_head=2f65506d239b449bbb73c6820ff9cb949fa55158
legacy_worktree="$study_root/legacy-reader-source"

test "$(git -C "$baseline" rev-parse HEAD)" = "$expected_head"
test -z "$(git -C "$baseline" status --short)"

if git -C "$baseline" worktree list --porcelain | grep -Fxq "worktree $legacy_worktree"; then
    git -C "$baseline" worktree remove --force "$legacy_worktree"
fi
git -C "$baseline" worktree prune

# These directories contain only interrupted experimental copies. They are
# named explicitly so cleanup cannot broaden to the study root or baseline.
for rejected in \
    "$study_root/build/repo-legacy-reader" \
    "$study_root/build/src-full-rebuild-rejected" \
    "$study_root/build/src-make-relink-rejected" \
    "$study_root/lanes/relink-parity" \
    "$study_root/lanes/legacy-reader-parity" \
    "$study_root/lanes/year34-legacy-baseline" \
    "$study_root/lanes/year34-legacy-baseline-v2" \
    "$study_root/lanes/year34-legacy-baseline-v3" \
    "$study_root/lanes/year34-sparse-legacy-baseline" \
    "$study_root/lanes/year34-sparse-legacy-baseline-v2" \
    "$study_root/lanes/year34-compact-smoke-cv10" \
    "$study_root/lanes/year34-compact-smoke-cv10-v2" \
    "$study_root/lanes/year34-compact-smoke-cv10-v3"
do
    if test -e "$rejected"; then
        rm -rf -- "$rejected"
    fi
done

for empty_tmp in \
    "$study_root/tmp/day203" \
    "$study_root/tmp/day203-v2"
do
    if test -d "$empty_tmp"; then
        rmdir "$empty_tmp"
    fi
done

test "$(git -C "$baseline" rev-parse HEAD)" = "$expected_head"
test -z "$(git -C "$baseline" status --short)"
sha256sum "$baseline/src/wepp"
