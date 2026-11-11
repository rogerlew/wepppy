"""Process logging adapter; stored state is source metadata only, never values."""
from __future__ import annotations

import copy
from collections.abc import Mapping
import logging
import sys
import threading
from multiprocessing.process import BaseProcess

from .safe_traceback import (
    SecretSourceProfile, UNAVAILABLE, _snapshot, sanitize_text, _exception_text,
    render_exception, safe_text, unavailable,
)

_PROFILE: SecretSourceProfile | None = None
_INSTALLED = False


def current_profile(fallback: SecretSourceProfile) -> SecretSourceProfile:
    """Shared helpers retain the calling process's explicitly selected profile."""
    return _PROFILE if _PROFILE is not None else fallback


def is_exception_record(record: logging.LogRecord) -> bool:
    arguments = record.args.values() if isinstance(record.args, Mapping) else record.args
    object_argument = isinstance(record.args, (tuple, Mapping)) and any(isinstance(arg, BaseException) for arg in arguments)
    return bool(record.exc_info or record.exc_text or record.stack_info
                or getattr(record, '_safe_exception_record', False)
                or isinstance(record.msg, BaseException) or object_argument)


class SafeFormatter(logging.Formatter):
    """Wrap an existing formatter, retaining ordinary record formatting exactly."""

    def __init__(self, formatter: logging.Formatter | None, source_profile: SecretSourceProfile):
        super().__init__()
        self.delegate = formatter or logging.Formatter()
        self.source_profile = source_profile

    def format(self, record: logging.LogRecord) -> str:
        if not is_exception_record(record):
            return self.delegate.format(record)
        try:
            snapshot = _snapshot(self.source_profile)
            copied = copy.copy(record)
            if copied.exc_info and copied.exc_info[1] is not None:
                copied.exc_text = _exception_text(copied.exc_info[1])
                copied.exc_info = None
            return sanitize_text(self.delegate.format(copied), snapshot)
        except Exception:  # broad-except: final logging output boundary cannot emit raw diagnostics
            return unavailable(getattr(record, "error_id", None))


def safe_record_message(record: logging.LogRecord, profile: SecretSourceProfile) -> str:
    """For handlers deliberately publishing only message rather than a traceback."""
    if not is_exception_record(record):
        return record.getMessage()
    try:
        return safe_text(record.getMessage(), source_profile=profile)
    except Exception:  # broad-except: publication boundary, including broken interpolation
        return UNAVAILABLE


def _wrap(handler: logging.Handler, profile: SecretSourceProfile) -> None:
    if not isinstance(handler.formatter, SafeFormatter):
        handler.setFormatter(SafeFormatter(handler.formatter, profile))


def install(profile: SecretSourceProfile) -> None:
    """Install once at the owning entrypoint, before secret-consuming imports.

    Later lazy imports must not replace the process owner. Existing and future
    handlers receive a formatter; queue handlers sanitize before prepare clears
    exception provenance. No file is opened during installation/normal logging.
    """
    global _PROFILE, _INSTALLED
    if _INSTALLED:
        return
    _PROFILE = profile
    previous_factory = logging.getLogRecordFactory()
    previous_add_handler = logging.Logger.addHandler
    previous_set_formatter = logging.Handler.setFormatter
    previous_process_run = BaseProcess.run

    def factory(*args, **kwargs):
        record = previous_factory(*args, **kwargs)
        record._safe_exception_record = sys.exception() is not None
        if isinstance(record.msg, BaseException):
            record._safe_exception_record = True
        arguments = record.args.values() if isinstance(record.args, Mapping) else record.args
        if isinstance(record.args, (tuple, Mapping)) and any(isinstance(arg, BaseException) for arg in arguments):
            record._safe_exception_record = True
        return record

    def set_formatter(handler, formatter):
        if not isinstance(formatter, SafeFormatter):
            formatter = SafeFormatter(formatter, profile)
        previous_set_formatter(handler, formatter)

    def add_handler(logger, handler):
        _wrap(handler, profile)
        previous_add_handler(logger, handler)

    def handle_error(handler, record):
        # stdlib handleError prints raw record.msg/args on I/O failure. Never
        # re-emit those values while reporting a failed diagnostic sink.
        try:
            sys.stderr.write(UNAVAILABLE + '\n')
        except (OSError, ValueError):
            pass  # stderr itself is unavailable; no further output boundary exists

    logging.setLogRecordFactory(factory)
    logging.Handler.setFormatter = set_formatter
    logging.Logger.addHandler = add_handler
    logging.Handler.handleError = handle_error
    for logger in [logging.getLogger(), *logging.Logger.manager.loggerDict.values()]:
        if isinstance(logger, logging.Logger):
            for handler in logger.handlers:
                _wrap(handler, profile)
    # lastResort is not attached to a logger.
    if logging.lastResort is not None:
        _wrap(logging.lastResort, profile)

    def uncaught(exc_type, exc, tb):
        # Any escaping hook failure makes CPython print the raw original error.
        # This final output boundary must also contain interrupted/failed sinks.
        try:
            sys.stderr.write(render_exception(exc, source_profile=profile) + '\n')
        except BaseException:  # broad-except: hook failure would expose the raw original exception
            pass  # no functioning diagnostic sink remains; never retry raw output

    def thread_uncaught(args):
        if args.exc_type is SystemExit:
            return  # Preserve threading default: ordinary thread exits are silent.
        uncaught(args.exc_type, args.exc_value, args.exc_traceback)

    def unraisable(args):
        uncaught(args.exc_type, args.exc_value, args.exc_traceback)

    def process_run(process):
        # multiprocessing prints target failures itself, bypassing sys.excepthook.
        # Preserve success and numeric exit semantics at that existing boundary.
        try:
            return previous_process_run(process)
        except SystemExit as exc:
            if exc.code is None or isinstance(exc.code, int):
                raise
            uncaught(type(exc), exc, exc.__traceback__)
            raise SystemExit(1) from None
        except BaseException as exc:  # broad-except: existing multiprocessing terminal output boundary
            uncaught(type(exc), exc, exc.__traceback__)
            raise SystemExit(1) from None

    BaseProcess.run = process_run
    sys.excepthook = uncaught
    threading.excepthook = thread_uncaught
    sys.unraisablehook = unraisable
    _INSTALLED = True
