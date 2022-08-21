import argparse
import logging
import sys

try:
    from commons import *
    from utils import is_gnome, is_wayland, is_nvidia_proprietary, is_vdpau_ok
    import server
except ModuleNotFoundError:
    from hidamari.commons import *
    from hidamari.utils import is_gnome, is_wayland, is_nvidia_proprietary, is_vdpau_ok
    from hidamari import server

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
    parser.add_argument("-r", "--reset", action="store_true", help="Reset user configuration.")
    args = parser.parse_args()

    # Setup logger
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)

    # Log system information
    logger.debug(f"[Desktop Env] {os.environ.get('XDG_CURRENT_DESKTOP', 'Not found')} | is_gnome = {is_gnome()}")
    logger.debug(f"[Windowing Sys] {os.environ.get('XDG_SESSION_TYPE', 'Not found')} | is_wayland = {is_wayland()}")
    logger.debug(f"[GPU] is_nvidia_proprietary = {is_nvidia_proprietary()} | is_vdpau_ok = {is_vdpau_ok()}")
    logger.debug(f"[Args] {vars(args)}")

    # Make Hidamari folder if not exist
    os.makedirs(VIDEO_WALLPAPER_DIR, exist_ok=True)

    # Clear sys.argv as it has influence to the Gtk.Application
    sys.argv = [sys.argv[0]]
    server.main(args)


if __name__ == "__main__":
    main()
