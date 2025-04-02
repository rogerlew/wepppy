import traceback

import os
import csv

from os.path import join as _join
from os.path import split as _split
from os.path import exists as _exists

from flask import jsonify, make_response

from datetime import datetime



def get_wd(runid):
    legacy = _join('/geodata/weppcloud_runs', runid)
    if _exists(legacy):
        return legacy
        
    prefix = runid[:2]
    return _join('/wc1/runs', prefix, runid)
    

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

