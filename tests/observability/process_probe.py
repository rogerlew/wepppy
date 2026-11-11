"""Synthetic subprocess fixture: never loads deployment credentials."""
import logging
from collections import UserDict
import multiprocessing
import os
import sys

from wepppy.observability.safe_logging import install
from wepppy.observability.safe_traceback import SecretSourceProfile, SecretSourceSpec

PROFILE = SecretSourceProfile('probe', (SecretSourceSpec('F5_CHILD', 'F5_CHILD_FILE'),))


def fail():
    raise RuntimeError('child-context ' + os.environ['F5_CHILD'])


def leave(code):
    raise SystemExit(code)


if __name__ == '__main__':
    mode = sys.argv[1]
    if mode == 'playback':
        from wepppy.observability.secret_profiles import PLAYBACK
        install(PLAYBACK)
    else:
        install(PROFILE)
    canary = os.environ['F5_CHILD']
    logging.basicConfig(level=logging.INFO)
    if mode in ('logging', 'playback'):
        for mapping in (dict, UserDict):
            logging.warning('mapping %(why)s', mapping(why=ValueError(canary)))
        try:
            raise ValueError('log-context ' + canary)
        except ValueError:
            logging.exception('dependency error %s', canary)
    elif mode == 'multiprocessing':
        for target, args, expected in ((fail, (), 1), (leave, (7,), 7), (leave, (None,), 0), (leave, (canary,), 1)):
            process = multiprocessing.get_context('fork').Process(target=target, args=args)
            process.start()
            process.join(10)
            assert process.exitcode == expected
        print('exit-semantics-preserved')
    elif mode == 'stderr-failure':
        original = sys.stderr
        class FailOnce:
            def __init__(self):
                self.first = True
            def write(self, text):
                if self.first:
                    self.first = False
                    raise OSError('synthetic broken sink')
                return original.write(text)
            def flush(self):
                original.flush()
        sys.stderr = FailOnce()
        fail()
    else:
        fail()
