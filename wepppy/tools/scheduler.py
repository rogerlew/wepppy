import argparse
import importlib
import json
import logging
import os
import random
import signal
import time
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Mapping, Optional

import redis
from rq import Queue

from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs

try:
    import yaml
except ImportError as exc:  # pragma: no cover - fail fast if YAML config is used.
    yaml = None
    YAML_IMPORT_ERROR = exc
else:
    YAML_IMPORT_ERROR = None


@dataclass
class TaskSpec:
    name: str
    func_path: str
    interval_seconds: int
    queue: str
    args: list[Any]
    kwargs: dict[str, Any]
    enabled: bool
    initial_delay_seconds: int
    jitter_seconds: int
    job_timeout: Optional[int]
    result_ttl: Optional[int]
    job_id: Optional[str]
    description: Optional[str]


@dataclass
class TaskState:
    spec: TaskSpec
    func: Callable[..., Any]
    next_run: float


def _load_config(path: str) -> dict[str, Any]:
    if not path:
        raise ValueError("Scheduler config path is required")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Scheduler config not found: {path}")
    with open(path, "r", encoding="utf-8") as handle:
        if path.endswith(('.yaml', '.yml')):
            if yaml is None:
                raise ImportError(
                    "PyYAML is required for YAML configs"
                ) from YAML_IMPORT_ERROR
            return yaml.safe_load(handle) or {}
        return json.load(handle)


def _resolve_callable(dotted_path: str) -> Callable[..., Any]:
    module_name, attr = dotted_path.rsplit('.', 1)
    module = importlib.import_module(module_name)
    target = getattr(module, attr)
    if not callable(target):
        raise TypeError(f"Resolved target is not callable: {dotted_path}")
    return target


def _as_int(value: Any, *, name: str) -> int:
    if isinstance(value, bool) or value is None:
        raise ValueError(f"{name} must be an integer")
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be an integer") from exc


def _normalize_tasks(raw: Iterable[Mapping[str, Any]], defaults: Mapping[str, Any]) -> list[TaskSpec]:
    specs: list[TaskSpec] = []
    for entry in raw:
        if not isinstance(entry, Mapping):
            raise ValueError("Each task must be a mapping")
        name = entry.get("name")
        func_path = entry.get("func")
        if not name or not func_path:
            raise ValueError("Tasks require name and func fields")
        interval_seconds = _as_int(entry.get("interval_seconds"), name=f"{name}.interval_seconds")
        if interval_seconds <= 0:
            raise ValueError(f"{name}.interval_seconds must be > 0")
        queue = entry.get("queue") or defaults.get("default_queue", "default")
        args = list(entry.get("args") or [])
        kwargs = dict(entry.get("kwargs") or {})
        enabled = bool(entry.get("enabled", True))
        initial_delay_seconds = _as_int(
            entry.get("initial_delay_seconds", defaults.get("initial_delay_seconds", 0)),
            name=f"{name}.initial_delay_seconds",
        )
        if initial_delay_seconds < 0:
            raise ValueError(f"{name}.initial_delay_seconds must be >= 0")
        jitter_seconds = _as_int(
            entry.get("jitter_seconds", defaults.get("jitter_seconds", 0)),
            name=f"{name}.jitter_seconds",
        )
        if jitter_seconds < 0:
            raise ValueError(f"{name}.jitter_seconds must be >= 0")
        job_timeout = entry.get("job_timeout")
        if job_timeout is not None:
            job_timeout = _as_int(job_timeout, name=f"{name}.job_timeout")
            if job_timeout <= 0:
                raise ValueError(f"{name}.job_timeout must be > 0")
        result_ttl = entry.get("result_ttl")
        if result_ttl is not None:
            result_ttl = _as_int(result_ttl, name=f"{name}.result_ttl")
            if result_ttl <= 0:
                raise ValueError(f"{name}.result_ttl must be > 0")
        job_id = entry.get("job_id")
        description = entry.get("description")
        specs.append(
            TaskSpec(
                name=str(name),
                func_path=str(func_path),
                interval_seconds=interval_seconds,
                queue=str(queue),
                args=args,
                kwargs=kwargs,
                enabled=enabled,
                initial_delay_seconds=initial_delay_seconds,
                jitter_seconds=jitter_seconds,
                job_timeout=job_timeout,
                result_ttl=result_ttl,
                job_id=job_id,
                description=description,
            )
        )
    return specs


def _schedule_time(base: float, interval_seconds: int, jitter_seconds: int) -> float:
    if jitter_seconds > 0:
        return base + interval_seconds + random.uniform(0, jitter_seconds)
    return base + interval_seconds


def _build_states(specs: list[TaskSpec]) -> list[TaskState]:
    now = time.monotonic()
    states: list[TaskState] = []
    for spec in specs:
        func = _resolve_callable(spec.func_path)
        delay = float(spec.initial_delay_seconds)
        next_run = now + delay
        if spec.jitter_seconds > 0:
            next_run += random.uniform(0, spec.jitter_seconds)
        states.append(TaskState(spec=spec, func=func, next_run=next_run))
    return states


def _enqueue_task(queue: Queue, task: TaskState) -> None:
    spec = task.spec
    enqueue_kwargs: dict[str, Any] = {}
    if spec.job_timeout is not None:
        enqueue_kwargs["job_timeout"] = spec.job_timeout
    if spec.result_ttl is not None:
        enqueue_kwargs["result_ttl"] = spec.result_ttl
    if spec.job_id:
        enqueue_kwargs["job_id"] = spec.job_id
    if spec.description:
        enqueue_kwargs["description"] = spec.description
    queue.enqueue(task.func, *spec.args, **spec.kwargs, **enqueue_kwargs)


def run_scheduler(
    config_path: str,
    *,
    sleep_seconds: int,
    dry_run: bool,
    run_once: bool,
) -> None:
    config = _load_config(config_path)
    tasks = config.get("tasks")
    if not isinstance(tasks, list):
        raise ValueError("Scheduler config must define a tasks list")

    defaults = {
        "default_queue": config.get("default_queue", "default"),
        "initial_delay_seconds": config.get("initial_delay_seconds", 0),
        "jitter_seconds": config.get("jitter_seconds", 0),
    }
    specs = _normalize_tasks(tasks, defaults)
    states = _build_states(specs)

    conn_kwargs = redis_connection_kwargs(RedisDB.RQ)
    redis_conn = redis.Redis(**conn_kwargs)
    queues: dict[str, Queue] = {}

    def get_queue(name: str) -> Queue:
        queue = queues.get(name)
        if queue is None:
            queue = Queue(name, connection=redis_conn)
            queues[name] = queue
        return queue

    stop = False

    def _handle_stop(signum: int, frame: Optional[Any]) -> None:
        nonlocal stop
        stop = True
        logging.info("Scheduler received signal %s, shutting down", signum)

    signal.signal(signal.SIGTERM, _handle_stop)
    signal.signal(signal.SIGINT, _handle_stop)

    logging.info("Scheduler loaded %d task(s) from %s", len(states), config_path)

    while not stop:
        now = time.monotonic()
        for task in states:
            spec = task.spec
            if not spec.enabled:
                continue
            if now < task.next_run:
                continue
            logging.info("Scheduling task %s", spec.name)
            if not dry_run:
                queue = get_queue(spec.queue)
                _enqueue_task(queue, task)
            else:
                logging.info("Dry run enabled, skipping enqueue for %s", spec.name)
            task.next_run = _schedule_time(now, spec.interval_seconds, spec.jitter_seconds)
        if run_once:
            break
        time.sleep(sleep_seconds)


def main() -> None:
    parser = argparse.ArgumentParser(description="Enqueue scheduled RQ tasks.")
    parser.add_argument(
        "--config",
        default=os.getenv("SCHEDULE_CONFIG", "docker/scheduled-tasks.yml"),
        help="Path to scheduler config file",
    )
    parser.add_argument(
        "--sleep-seconds",
        type=int,
        default=int(os.getenv("SCHEDULE_SLEEP_SECONDS", "30")),
        help="Loop sleep duration between scheduler ticks",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=os.getenv("SCHEDULE_DRY_RUN", "false").lower() == "true",
        help="Log actions without enqueueing",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        default=False,
        help="Run one scheduler tick and exit",
    )
    parser.add_argument(
        "--log-level",
        default=os.getenv("SCHEDULE_LOG_LEVEL", "INFO"),
        help="Logging level",
    )

    args = parser.parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO), format="%(asctime)s %(levelname)s %(message)s")

    run_scheduler(
        args.config,
        sleep_seconds=args.sleep_seconds,
        dry_run=args.dry_run,
        run_once=args.once,
    )


if __name__ == "__main__":
    main()
