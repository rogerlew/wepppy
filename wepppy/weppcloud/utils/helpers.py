import traceback

import os
import csv

from os.path import join as _join
from os.path import split as _split
from os.path import exists as _exists

from flask import jsonify, make_response

from datetime import datetime

import socket
_hostname = socket.gethostname()

import redis

redis_wd_cache_client = None
REDIS_HOST = os.environ.get('REDIS_HOST', None)
REDIS_WD_CACHE_DB = 11
if REDIS_HOST is not None:
    try:
        redis_wd_cache_client = redis.StrictRedis(
            host=REDIS_HOST, port=6379, db=REDIS_WD_CACHE_DB, decode_responses=True)
        redis_wd_cache_client.ping()
    except Exception as e:
        print(f'Error connecting to Redis: {e}')
        redis_wd_cache_client = None
    

def get_wd(runid: str) -> str:
    """
    Gets the working directory path for a given run ID, using a Redis cache
    to speed up lookups.
    """
    global redis_wd_cache_client

    # 1. Attempt to fetch the working directory from the cache
    if redis_wd_cache_client:
        try:
            cached_wd = redis_wd_cache_client.get(runid)
            if cached_wd:
                return cached_wd
        except redis.exceptions.ConnectionError as e:
            print(f"Warning: Redis connection error during GET. Falling back to filesystem. Error: {e}")

    # 2. If not in cache or Redis is down, determine path from the filesystem
    # Check the primary, non-prefixed location first
    path = _join('/geodata/weppcloud_runs', runid)

    # If not found, fall back to the prefixed, partitioned locations
    if not _exists(path):
        prefix = runid[:2]
        if _hostname.startswith('forest'):
            path = _join('/wc1/runs', prefix, runid)
        else:
            path = _join('/geodata/wc1/runs', prefix, runid)

    # 3. Store the determined path in the cache for future requests
    if redis_wd_cache_client:
        try:
            # Cache the result with a 72-hour (259200 seconds) expiration
            redis_wd_cache_client.set(runid, path, ex=72 * 3600)
        except redis.exceptions.ConnectionError as e:
            # If caching fails, the function still succeeds. Just log the issue.
            print(f"Warning: Redis connection error during SET. Error: {e}")

    return path
    

def error_factory(msg='Error Handling Request'):
    return jsonify({'Success': False,
                    'Error': msg})


def exception_factory(msg='Error Handling Request',
                      stacktrace=None,
                      runid=None):
    if stacktrace is None:
        stacktrace = traceback.format_exc()

    if runid is not None:
        wd = get_wd(runid)
        if _exists(wd):
            with open(_join(wd, 'exceptions.log'), 'a') as fp:
                fp.write(f'[{datetime.now()}]\n')
                fp.write(stacktrace)
                fp.write('\n\n')

    with open('/var/log/exceptions.log', 'a') as fp:
        fp.write(f'[{datetime.now()}] ')
        if runid is not None:
            fp.write(f'{runid}\n')
        fp.write(stacktrace)
        fp.write('\n\n')

    return make_response(jsonify({'Success': False,
                         'Error': msg,
                         'StackTrace': stacktrace.split('\n')}), 500)


def success_factory(kwds=None):
    if kwds is None:
        return jsonify({'Success': True})
    else:
        return jsonify({'Success': True,
                        'Content': kwds})


def htmltree(_dir='.', padding='', print_files=True, recurse=False):
    def _tree(__dir, _padding, _print_files, recurse=False):
        # Original from Written by Doug Dahms
        # http://code.activestate.com/recipes/217212/
        #
        # Adapted to return string instead of printing to stdout

        from os import listdir, sep
        from os.path import abspath, basename, isdir

        s = [_padding[:-1] + '+-' + basename(abspath(__dir)) + '\n']
        f = []
        _padding += ' '
        if _print_files:
            files = listdir(__dir)
        else:
            files = [x for x in listdir(__dir) if isdir(__dir + sep + x)]
        count = 0
        for file in sorted(files):
            count += 1
            path = __dir + sep + file
            if isdir(path) and recurse:
                if count == len(files):
                    s.extend(htmltree(path, _padding + ' ', _print_files) + '\n')
                else:
                    s.extend(htmltree(path, _padding + '|', _print_files) + '\n')
            else:
                if isdir(path):
                    s.append(_padding + '+-<a href="{file}/\">{file}</a>\n'.format(file=file))
                else:
                    if os.path.islink(path):
                        target = ' -> {}'.format('/'.join(os.readlink(path).split('/')[-2:]))
                    else:
                        target = ''

                    f.append(_padding + '>-<a href="{file}">{file}</a>{target}\n'
                             .format(file=file, target=target))

        s.extend(f)
        return s

    return ''.join(_tree(_dir, padding, print_files))


def matplotlib_vis(path):
    import matplotlib.pyplot as plt

    data, transform, proj = read_raster(path)

    plt.imshow(data)
    img_bytes = BytesIO()
    plt.savefig(img_bytes)
    img_bytes.seek(0)
    return send_file(img_bytes, mimetype='image/png')

