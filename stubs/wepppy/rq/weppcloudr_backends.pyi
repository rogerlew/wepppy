from __future__ import annotations

from pathlib import Path
from dataclasses import dataclass
from typing import Callable, Mapping, Protocol

REQUEST_SCHEMA_VERSION: int
MAX_REQUEST_BYTES: int
MAX_CONTROL_PLANE_RESPONSE_BYTES: int
TERMINAL_STATES: frozenset[str]
KNOWN_STATES: frozenset[str]
K8S_ERROR_CODES: frozenset[str]

class BackendError(RuntimeError): ...
class BackendExecutionError(BackendError):
    stdout: str
    stderr: str
    def __init__(self, detail: str, *, stdout: str = ..., stderr: str = ...) -> None: ...
class BackendConfigurationError(BackendError): ...
class KubernetesRenderError(BackendError):
    code: str
    def __init__(self, code: str, detail: str) -> None: ...

@dataclass(frozen=True)
class RenderRequest:
    schema_version: int
    rq_job_id: str
    runid: str
    config: str
    run_root: str
    active_root: str
    skip_cache: bool
    correlation_id: str
    deployment_revision: str
    renderer_image_digest: str
    def __init__(
        self,
        schema_version: int,
        rq_job_id: str,
        runid: str,
        config: str,
        run_root: str,
        active_root: str,
        skip_cache: bool,
        correlation_id: str,
        deployment_revision: str,
        renderer_image_digest: str,
    ) -> None: ...
    def to_json(self) -> str: ...
    @property
    def digest(self) -> str: ...

@dataclass(frozen=True)
class BackendResult:
    stdout: str
    stderr: str
    receipt: Mapping[str, object] | None = ...

class RenderBackend(Protocol):
    def render(self, request: RenderRequest, *, timeout: int) -> BackendResult: ...

def validate_request(request: RenderRequest) -> None: ...
def deterministic_job_name(rq_job_id: str) -> str: ...

class DockerExecBackend:
    def __init__(self, container_name: str, fencing_generation: int) -> None: ...
    def render(self, request: RenderRequest, *, timeout: int) -> BackendResult: ...

class RenderControlPlaneClient(Protocol):
    def submit(self, request: RenderRequest) -> Mapping[str, object]: ...
    def observe(self, rq_job_id: str, request_digest: str) -> Mapping[str, object]: ...
    def cancel(self, rq_job_id: str, request_digest: str) -> Mapping[str, object]: ...

class HttpRenderControlPlaneClient:
    def __init__(
        self, endpoint: str, token_file: Path, *, request_timeout: float = ...
    ) -> None: ...
    def submit(self, request: RenderRequest) -> Mapping[str, object]: ...
    def observe(self, rq_job_id: str, request_digest: str) -> Mapping[str, object]: ...
    def cancel(self, rq_job_id: str, request_digest: str) -> Mapping[str, object]: ...

class KubernetesJobBackend:
    def __init__(
        self,
        client: RenderControlPlaneClient,
        *,
        expected_namespace: str,
        poll_interval: float = ...,
        monotonic: Callable[[], float] = ...,
        sleeper: Callable[[float], None] = ...,
    ) -> None: ...
    def render(self, request: RenderRequest, *, timeout: int) -> BackendResult: ...
    def cancel(self, request: RenderRequest) -> Mapping[str, object]: ...
