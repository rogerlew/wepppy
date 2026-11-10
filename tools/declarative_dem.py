#!/usr/bin/env python3
"""Private operator client for one reviewed, already-provisioned DEM worker Pod."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from wepppy.declarative.schema import (  # noqa: E402
    AdmissionError, PROTOCOL, loads, validate, validate_definition, verify_evidence,
)


def observe(pod, node, template, definition):
    """Only operator-observed Pod state can verify the selected runtime."""
    expected = template["spec"]
    actual = pod["spec"]
    if pod["metadata"]["namespace"] != "weppcloud" or pod["status"].get("phase") != "Running":
        raise AdmissionError("Dedicated Pod is not running in weppcloud")
    if (actual.get("automountServiceAccountToken") is not False
            or actual.get("initContainers") or actual.get("ephemeralContainers")
            or len(actual.get("containers", [])) != 1):
        raise AdmissionError("Unapproved execution containers or API token")
    for key in ("volumes", "securityContext", "serviceAccountName", "hostNetwork", "hostPID", "hostIPC",
                "nodeSelector", "affinity", "schedulerName", "runtimeClassName", "priorityClassName"):
        default = "default-scheduler" if key == "schedulerName" else None
        if actual.get(key, default) != expected.get(key, default):
            raise AdmissionError("Pod differs from reviewed execution template")
    container = actual["containers"][0]
    trusted = expected["containers"][0]
    for key in ("name", "command", "args", "env", "envFrom", "volumeMounts", "securityContext", "workingDir",
                "lifecycle", "startupProbe", "livenessProbe", "readinessProbe", "volumeDevices", "resources"):
        observed_value, trusted_value = container.get(key), trusted.get(key)
        if key in {"startupProbe", "livenessProbe", "readinessProbe"} and trusted_value is not None:
            defaults = {"initialDelaySeconds": 0, "timeoutSeconds": 1, "periodSeconds": 10,
                        "successThreshold": 1, "failureThreshold": 3}
            trusted_value = {**defaults, **trusted_value}
            observed_value = {**defaults, **observed_value} if observed_value is not None else None
        if observed_value != trusted_value:
            raise AdmissionError("Container differs from reviewed execution template")
    if container["image"] != definition["image"] or trusted["image"] != definition["image"]:
        raise AdmissionError("Unapproved container image")
    statuses = pod["status"].get("containerStatuses", [])
    if len(statuses) != 1 or statuses[0].get("name") != container["name"] or not statuses[0].get("ready"):
        raise AdmissionError("Container runtime identity is unavailable")
    status = statuses[0]
    image_id = status.get("imageID", "")
    if image_id.startswith("docker-pullable://"):
        image_id = image_id.removeprefix("docker-pullable://")
    info = node["status"]["nodeInfo"]
    if actual.get("nodeName") != node["metadata"]["name"]:
        raise AdmissionError("Node evidence does not match Pod")
    if any(node["metadata"].get("labels", {}).get(k) != v
           for k, v in expected.get("nodeSelector", {}).items()):
        raise AdmissionError("Node does not match reviewed placement")
    evidence = {"namespace": pod["metadata"]["namespace"], "pod_name": pod["metadata"]["name"],
                "pod_uid": pod["metadata"]["uid"], "container": container["name"],
                "container_id": status.get("containerID", ""), "image": container["image"],
                "image_id": image_id, "restart_count": status.get("restartCount"),
                "platform": info["operatingSystem"] + "/" + info["architecture"],
                "node_name": node["metadata"]["name"],
                "observed_at": datetime.now(timezone.utc).isoformat()}
    return verify_evidence(definition, evidence)


class Client:
    def __init__(self, args, definition, template):
        self.args, self.definition, self.template = args, definition, template

    def kubectl(self, *args, payload=None):
        result = subprocess.run(
            ["kubectl", "--context", self.args.context, "-n", "weppcloud", *args],
            input=None if payload is None else json.dumps(payload), text=True,
            capture_output=True, timeout=120, check=False,
        )
        if result.returncode:
            raise AdmissionError("Kubernetes/adapter command failed; inspect protected operator logs")
        # Image startup may emit operational log lines; only the final JSON line is protocol output.
        if args[0] == "exec":
            lines = result.stdout.strip().splitlines()
            if not lines:
                raise AdmissionError("Adapter returned no protocol response")
            return loads(lines[-1])
        return loads(result.stdout)

    def evidence(self):
        pod = self.kubectl("get", "pod", self.args.pod, "-o", "json")
        node = self.kubectl("get", "node", pod["spec"]["nodeName"], "-o", "json")
        return observe(pod, node, self.template, self.definition)

    def adapter(self, command, **payload):
        return self.kubectl("exec", "-i", self.args.pod, "-c",
                            self.template["spec"]["containers"][0]["name"], "--",
                            "/opt/venv/bin/python", "-m", "wepppy.declarative.adapter", command,
                            payload=payload)

    def run(self):
        submission = self.definition["submission_id"]
        if self.args.command == "status":
            return self.adapter("status", submission_id=submission)
        initial = self.evidence()
        if self.args.command == "cancel":
            result = self.adapter("cancel", submission_id=submission)
        else:
            result = self.adapter("submit", definition=self.definition,
                                  owner_id=self.args.owner_id, evidence=initial)
        deadline = time.monotonic() + self.args.wait_seconds
        while time.monotonic() < deadline:
            current = self.evidence()
            verify_evidence(self.definition, current, initial)
            result = self.adapter("status", submission_id=submission)
            science = result["jobs"]["attempt_id"]
            finalizer = result["jobs"]["finalizer_id"]
            if result.get("verified") or result["protection"] == "failed":
                return result
            if science in {"finished", "failed", "stopped", "canceled"} or result.get("science_not_dispatched"):
                if finalizer == "missing" and not result.get("finalization_intent"):
                    result = self.adapter("finalize", submission_id=submission, evidence=current)
                elif finalizer == "finished":
                    return self.adapter("complete", submission_id=submission, evidence=current)
                elif finalizer in {"failed", "stopped", "canceled"}:
                    return result
            elif science == "missing":
                raise AdmissionError("Dispatch is uncertain; scientific replay is prohibited")
            time.sleep(2)
        result["error"] = {"code": "observation_timeout", "message": "Build remains incomplete; observe existing work"}
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("validate", "submit", "status", "cancel"))
    parser.add_argument("--definition", required=True, type=Path)
    parser.add_argument("--approvals", required=True, type=Path)
    parser.add_argument("--template", type=Path, help="Reviewed rendered Pod JSON")
    parser.add_argument("--context")
    parser.add_argument("--pod")
    parser.add_argument("--owner-id", type=int)
    parser.add_argument("--wait-seconds", type=int, default=900)
    args = parser.parse_args()
    try:
        definition = loads(args.definition.read_text())
        if args.command in {"status", "cancel"}:
            validate_definition(definition)
        else:
            validate(definition, loads(args.approvals.read_text()))
        if args.command == "validate":
            result = {"protocol": PROTOCOL, "command": "validate", "valid": True,
                      "runid": None, "submission_id": definition["submission_id"], "verified": False}
        else:
            if not args.context or not args.pod or args.template is None:
                raise AdmissionError("Explicit target context, Pod and reviewed template are required")
            if args.command == "submit" and (args.owner_id is None or args.owner_id <= 0):
                raise AdmissionError("Existing owner ID is required")
            result = Client(args, definition, loads(args.template.read_text())).run()
        print(json.dumps(result, sort_keys=True))
        canceled = (args.command == "cancel" and result.get("processing") == "canceled"
                    and result.get("protection") == "readonly" and not result.get("error"))
        return 0 if args.command in {"validate", "status"} or result.get("verified") or canceled else 1
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
        # Operator CLI boundary: subprocess/configuration diagnostics may contain credentials.
        print(json.dumps({"protocol": PROTOCOL, "command": args.command, "verified": False,
                          "error": {"code": "admission_failed", "message": "Definition, target or runtime evidence is unavailable or invalid"}}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
