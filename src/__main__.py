import argparse
import logging
import sys

try:
    from commons import *
    from utils import is_gnome, is_wayland, is_nvidia_proprietary, is_vdpau_ok, is_flatpak
    import server
except ModuleNotFoundError:
    from hidamari.commons import *
    from hidamari.utils import is_gnome, is_wayland, is_nvidia_proprietary, is_vdpau_ok, is_flatpak
    from hidamari import server

logger = logging.getLogger(LOGGER_NAME)


def main(version="devel", pkgdatadir="/app/share/hidamari", localedir="/app/share/locale"):
    # Make sure that X11 is the backend. This makes sure Wayland reverts to XWayland.
    os.environ["GDK_BACKEND"] = "x11"
    # Suppress VLC Log
    os.environ["VLC_VERBOSE"] = "-1"

    parser = argparse.ArgumentParser(description=f"Hidamari v{version}")
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
    logger.info(f"Hidamari v{version}")
    logger.info("--- System information ---")
    logger.info(f"is_gnome = {is_gnome()}")
    logger.info(f"is_wayland = {is_wayland()}")
    logger.info(f"is_nvidia_proprietary = {is_nvidia_proprietary()}")
    logger.info(f"is_vdpau_ok = {is_vdpau_ok()}")
    logger.info(f"is_flatpak = {is_flatpak()}")
    logger.info("--------------------------")
    logger.info(f"[Args] {vars(args)}")

    # Make Hidamari folder if not exist
    os.makedirs(VIDEO_WALLPAPER_DIR, exist_ok=True)

    # Clear sys.argv as it has influence to the Gtk.Application
    sys.argv = [sys.argv[0]]
    server.main(version, pkgdatadir, localedir, args)


if __name__ == "__main__":
    main()
