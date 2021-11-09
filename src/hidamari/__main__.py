from . import server

from hidamari.commons import *

import argparse
import logging
import sys

logger = logging.getLogger(LOGGER_NAME)

def main():
    # Make sure that X11 is the backend. This makes sure Wayland reverts to XWayland.
    os.environ["GDK_BACKEND"] = "x11"
    # Suppress VLC Log
    os.environ["VLC_VERBOSE"] = "-1"

    parser = argparse.ArgumentParser(description="Hidamari launcher")
    parser.add_argument("-p", "--pause", dest="p", type=int, default=0,
                        help="Add pause before launching Hidamari. [sec]")
    parser.add_argument("-b", "--background", action="store_true", help="Launch only the live wallpaper.")
    parser.add_argument("-d", "--debug", action="store_true", help="Print debug messages.")
    args = parser.parse_args()

    # Setup logger
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)

    # Log system information
    logger.debug(f"[Desktop] {os.environ.get('XDG_CURRENT_DESKTOP', 'Not found')}")
    logger.debug(f"[Display Server] {os.environ.get('XDG_SESSION_TYPE', 'Not found')}")
    logger.debug(f"[Args] {vars(args)}")

    # Clear sys.argv as it has influence to the Gtk.Application
    sys.argv = [sys.argv[0]]
    server.main(args)

if __name__ == "__main__":
    main()
