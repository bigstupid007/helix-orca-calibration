#!/usr/bin/env python3
"""App-owned compiler concurrency gate for the unchanged Orca dependency build."""
import fcntl
import os
from pathlib import Path
import re
import sys
import time


def make_arguments(arguments):
    output = []
    index = 0
    while index < len(arguments):
        argument = arguments[index]
        if argument in ('-j', '--jobs'):
            jobs = 4
            if index + 1 < len(arguments) and arguments[index+1].isdigit():
                index += 1
                jobs = min(4, max(1, int(arguments[index])))
            output.append('-j'+str(jobs))
        elif re.fullmatch(r'-j\d+', argument):
            output.append('-j'+str(min(4, max(1, int(argument[2:])))))
        elif argument.startswith('--jobs='):
            jobs = argument.split('=',1)[1]
            if not jobs.isdigit(): raise ValueError('Invalid build job count')
            output.append('-j'+str(min(4, max(1, int(jobs)))))
        else:
            output.append(argument)
        index += 1
    return output


def main():
    tool = Path(sys.argv[0]).name
    # FFmpeg's unmodified configure defaults to the name gcc, ignoring CC.
    # Forward that driver alias to the actual pinned Clang-backed compiler;
    # FFmpeg still detects its real version and selects Clang semantics.
    tool = {'gcc':'cc','g++':'c++'}.get(tool,tool)
    if tool == 'make':
        os.execv('/usr/bin/make', ['make', *make_arguments(sys.argv[1:])])
    if tool not in ('cc','c++'):
        raise SystemExit('Build gate must be invoked as make, cc or c++')
    directory = Path('/build/compiler-slots')
    directory.mkdir(mode=0o700,exist_ok=True)
    descriptors = [os.open(directory/str(i), os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600) for i in range(4)]
    while True:
        for descriptor in descriptors:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:
                continue
            for other in descriptors:
                if other != descriptor: os.close(other)
            os.set_inheritable(descriptor,True)
            os.execv('/usr/bin/'+tool,[tool,*sys.argv[1:]])
        time.sleep(0.05)


if __name__=='__main__':main()
