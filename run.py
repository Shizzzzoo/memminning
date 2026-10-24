#!/usr/bin/python3
"""Stable entrypoint also used by the independent restoration timer."""
import argparse
import dataclasses
import json
import sys

from memminning import __version__
from memminning.core import Engine, OperationError, log, scan, setup_logging


def main():
    parser = argparse.ArgumentParser(description='Memminning — reviewed temporary desktop resource control')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--scan', action='store_true', help='Print a read-only JSON system inventory')
    group.add_argument('--restore', action='store_true', help='Restore the current session')
    group.add_argument('--recover', action='store_true', help='Login recovery: restore any incomplete session')
    group.add_argument('--restore-session', metavar='ID', help='Timer recovery; ignores stale session IDs')
    parser.add_argument('--version', action='version', version=__version__)
    args = parser.parse_args()
    setup_logging()
    # GTK signal callback exceptions go through sys.excepthook rather than main().
    def record_unhandled(kind, value, traceback):
        log.critical('Unhandled callback error', exc_info=(kind, value, traceback))
        sys.__excepthook__(kind, value, traceback)
    sys.excepthook = record_unhandled
    if args.scan:
        print(json.dumps(dataclasses.asdict(scan()), indent=2))
        return 0
    if args.restore or args.recover or args.restore_session:
        errors = Engine().restore(args.restore_session)
        for error in errors:
            print(error, file=sys.stderr)
        return 1 if errors else 0
    from memminning.gui import main as gui_main
    return gui_main()


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as exc:
        log.exception('Unhandled application error')
        print(f'Memminning: {exc}', file=sys.stderr)
        sys.exit(1)
