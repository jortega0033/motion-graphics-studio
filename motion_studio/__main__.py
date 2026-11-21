"""Command line entry: python -m motion_studio --data-dir DIR [--port N]"""

import argparse
import signal
import sys

from .server import create_server
from .store import StoreError


def _port(text):
    try:
        value = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError("port must be an integer")
    if not 0 <= value <= 65535:
        raise argparse.ArgumentTypeError("port must be between 0 and 65535")
    return value


def main(argv=None):
    parser = argparse.ArgumentParser(prog="motion_studio")
    parser.add_argument("--data-dir", required=True,
                        help="directory for the SQLite database")
    parser.add_argument("--port", type=_port, default=8765,
                        help="loopback port (default 8765, 0 = any free port)")
    args = parser.parse_args(argv)

    try:
        server = create_server(args.data_dir, args.port)
    except StoreError as exc:
        print("Motion Studio: %s" % exc.message, file=sys.stderr)
        return 2
    except OSError as exc:
        print("Motion Studio: cannot start: %s" % exc, file=sys.stderr)
        return 2

    def _stop(signum, frame):
        raise KeyboardInterrupt

    for name in ("SIGTERM", "SIGBREAK"):
        sig = getattr(signal, name, None)
        if sig is not None:
            try:
                signal.signal(sig, _stop)
            except (ValueError, OSError):
                pass

    print("Motion Studio listening on http://127.0.0.1:%d/" % server.server_port,
          flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
