"""Poll a real RQ tree; retain every response and require terminal success."""
import argparse
import time

from runtime_http import request


def poll(label, job_id, timeout=3600):
    started = time.monotonic()
    attempt = 0
    previous = None
    while time.monotonic() - started < timeout:
        body = request(f'{label}_poll_{attempt:04d}', 'GET',
                       f'/rq-engine/api/jobstatus/{job_id}')
        state = body['status']
        if state != previous:
            print('tree', job_id, state, body.get('progress'), flush=True)
            previous = state
        if state in {'finished', 'failed', 'stopped', 'canceled'}:
            tree = request(f'{label}_jobinfo', 'GET',
                           f'/rq-engine/api/jobinfo/{job_id}')
            if state != 'finished':
                raise RuntimeError(f'{job_id}: terminal {state}; retained jobinfo')
            return tree
        if state not in {'queued', 'started', 'deferred', 'scheduled'}:
            raise RuntimeError(f'Unexpected job state: {state}')
        attempt += 1
        time.sleep(5)
    raise TimeoutError(f'Job tree {job_id} did not finish within {timeout}s')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('label')
    parser.add_argument('job_id')
    parser.add_argument('--timeout', type=int, default=3600)
    args = parser.parse_args()
    poll(args.label, args.job_id, args.timeout)
