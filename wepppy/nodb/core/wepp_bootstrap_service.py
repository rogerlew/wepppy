from __future__ import annotations

import json
import os
import subprocess
from os.path import exists as _exists
from os.path import join as _join
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from wepppy.nodb.core.wepp import Wepp


class WeppBootstrapService:
    def load_bootstrap_push_log(self, wepp: "Wepp") -> dict[str, str]:
        log_path = wepp._bootstrap_push_log_path()
        if not _exists(log_path):
            return {}

        mapping: dict[str, str] = {}
        with open(log_path, "r") as handle:
            for line_no, line in enumerate(handle, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise RuntimeError(f"Invalid bootstrap push log entry at line {line_no}") from exc
                sha = payload.get("sha")
                user = payload.get("user")
                if not isinstance(sha, str) or not isinstance(user, str):
                    raise RuntimeError(f"Invalid bootstrap push log entry at line {line_no}")
                mapping[sha] = user
        return mapping

    def run_git(self, wepp: "Wepp", args: list[str]) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            ["git", *args],
            cwd=wepp.wd,
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"git {' '.join(args)} failed: {result.stdout.strip()} {result.stderr.strip()}".strip()
            )
        return result

    def write_bootstrap_gitignore(self, wepp: "Wepp") -> None:
        lines = [
            "# Bootstrap-managed inputs only",
            "*",
            "!.gitignore",
            "!wepp/",
            "!wepp/runs/",
            "!wepp/runs/**",
            "!swat/",
            "!swat/TxtInOut/",
            "!swat/TxtInOut/**",
            "wepp/runs/tc_out.txt",
            "",
        ]
        gitignore_path = _join(wepp.wd, ".gitignore")
        with open(gitignore_path, "w") as handle:
            handle.write("\n".join(lines))

    def install_bootstrap_hook(self, wepp: "Wepp") -> None:
        hooks_dir = _join(wepp._bootstrap_git_dir(), "hooks")
        os.makedirs(hooks_dir, exist_ok=True)
        hook_path = _join(hooks_dir, "pre-receive")
        hook_lines = [
            "#!/usr/bin/env bash",
            "set -euo pipefail",
            'if [[ -n "${WEPPPY_SOURCE_ROOT:-}" ]]; then',
            '  export PYTHONPATH="${WEPPPY_SOURCE_ROOT}${PYTHONPATH:+:$PYTHONPATH}"',
            "fi",
            "exec python3 -m wepppy.weppcloud.bootstrap.pre_receive",
            "",
        ]
        with open(hook_path, "w") as handle:
            handle.write("\n".join(hook_lines))
        os.chmod(hook_path, 0o755)

    def init_bootstrap(self, wepp: "Wepp") -> None:
        if not wepp._bootstrap_repo_exists():
            try:
                self.run_git(wepp, ["init", "-b", "main"])
            except RuntimeError:
                self.run_git(wepp, ["init"])
                self.run_git(wepp, ["checkout", "-b", "main"])

        self.run_git(wepp, ["config", "receive.denyCurrentBranch", "updateInstead"])
        self.run_git(wepp, ["config", "receive.denyNonFastForwards", "true"])
        self.run_git(wepp, ["config", "http.receivepack", "true"])
        self.run_git(wepp, ["config", "user.name", "WEPPcloud"])
        self.run_git(wepp, ["config", "user.email", "noreply@wepp.cloud"])

        self.write_bootstrap_gitignore(wepp)

        add_paths: list[str] = [".gitignore"]
        if _exists(_join(wepp.wd, "wepp", "runs")):
            add_paths.append("wepp/runs")
        if _exists(_join(wepp.wd, "swat", "TxtInOut")):
            add_paths.append("swat/TxtInOut")

        self.run_git(wepp, ["add", "--"] + add_paths)
        self.run_git(wepp, ["commit", "--allow-empty", "-m", "Bootstrap: initial input state"])

        self.install_bootstrap_hook(wepp)

        wepp.bootstrap_enabled = True

    def mint_bootstrap_jwt(
        self,
        wepp: "Wepp",
        user_email: str,
        user_id: str,
        expires_seconds: int,
    ) -> str:
        from wepppy.weppcloud.utils import auth_tokens

        external_host = os.getenv("EXTERNAL_HOST") or os.getenv("OAUTH_REDIRECT_HOST")
        if not external_host:
            raise RuntimeError("EXTERNAL_HOST must be set to mint bootstrap tokens")

        issued = auth_tokens.issue_token(
            user_email,
            audience=external_host,
            expires_in=expires_seconds,
            extra_claims={"runid": wepp.runid},
        )
        token = issued["token"]
        prefix = wepp.runid[:2]
        return f"https://{user_id}:{token}@{external_host}/git/{prefix}/{wepp.runid}/.git"

    def get_bootstrap_commits(self, wepp: "Wepp") -> list[dict]:
        if not wepp._bootstrap_repo_exists():
            return []
        result = self.run_git(
            wepp,
            [
                "log",
                "main",
                "--pretty=format:%H%x1f%an%x1f%ad%x1f%s%x1e",
                "--date=iso",
            ],
        )
        entries: list[dict] = []
        for chunk in result.stdout.strip("\n\x1e").split("\x1e"):
            if not chunk.strip():
                continue
            parts = chunk.strip().split("\x1f")
            if len(parts) != 4:
                continue
            sha, author, date_str, message = parts
            entries.append(
                {
                    "sha": sha,
                    "short_sha": sha[:7],
                    "message": message,
                    "author": author,
                    "date": date_str,
                }
            )

        pusher_map = self.load_bootstrap_push_log(wepp)
        for entry in entries:
            pusher = pusher_map.get(entry["sha"])
            entry["pusher"] = pusher
            entry["git_author"] = entry["author"]
            entry["author"] = pusher or "unknown"
        return entries

    def checkout_bootstrap_commit(self, wepp: "Wepp", sha: str) -> bool:
        if not wepp._bootstrap_repo_exists():
            return False
        try:
            self.run_git(wepp, ["checkout", sha])
        except RuntimeError:
            return False
        return True

    def get_bootstrap_current_ref(self, wepp: "Wepp") -> str:
        if not wepp._bootstrap_repo_exists():
            return ""
        try:
            result = self.run_git(wepp, ["symbolic-ref", "--short", "HEAD"])
            return result.stdout.strip()
        except RuntimeError:
            result = self.run_git(wepp, ["rev-parse", "--short", "HEAD"])
            return result.stdout.strip()

    def ensure_bootstrap_main(self, wepp: "Wepp") -> None:
        if not wepp.bootstrap_enabled:
            return
        if not wepp._bootstrap_repo_exists():
            raise RuntimeError("Bootstrap repo not initialized")
        if self.get_bootstrap_current_ref(wepp) == "main":
            return
        self.run_git(wepp, ["checkout", "main"])

    def bootstrap_commit_inputs(self, wepp: "Wepp", stage: str) -> str | None:
        if not wepp.bootstrap_enabled:
            return None
        if not wepp._bootstrap_repo_exists():
            raise RuntimeError("Bootstrap repo not initialized")

        self.ensure_bootstrap_main(wepp)
        managed_paths = wepp._bootstrap_managed_paths()
        if not managed_paths:
            return None

        status = self.run_git(wepp, ["status", "--porcelain", "--"] + managed_paths)
        if not status.stdout.strip():
            return None

        self.run_git(wepp, ["add", "--"] + managed_paths)

        stage_label = " ".join(str(stage).split()) or "inputs"
        self.run_git(wepp, ["commit", "-m", f"Pipeline: rebuilt {stage_label}"])
        sha = self.run_git(wepp, ["rev-parse", "HEAD"]).stdout.strip()
        wepp.logger.info(f"Bootstrap auto-commit created {sha[:7]} for {stage_label}")
        return sha

    def disable_bootstrap(self, wepp: "Wepp") -> None:
        from wepppy.weppcloud.app import Run, db

        run = Run.query.filter(Run.runid == wepp.runid).first()
        if run is None:
            raise RuntimeError(f"Run record not found for {wepp.runid}")
        run.bootstrap_disabled = True
        db.session.commit()
