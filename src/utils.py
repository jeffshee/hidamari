import sys
import json
import logging
import subprocess
from pprint import pformat

import gi
gi.require_version("Wnck", "3.0")
from gi.repository import Gio, GLib, Wnck, Gdk

import pydbus

try:
    from commons import *
except ModuleNotFoundError:
    from hidamari.commons import *

logger = logging.getLogger(LOGGER_NAME)


def is_gnome():
    """
    Check if current DE is GNOME or not.
    On Ubuntu 20.04, $XDG_CURRENT_DESKTOP = ubuntu:GNOME
    On Fedora 34, $XDG_CURRENT_DESKTOP = GNOME
    Hence we do the detection by looking for the word "gnome"
    """
    return "gnome" in os.environ.get("XDG_CURRENT_DESKTOP").lower()


def is_wayland():
    """
    Check if current session is Wayland or not.
    $XDG_SESSION_TYPE = x11 | wayland
    """
    return os.environ.get("XDG_SESSION_TYPE") == "wayland"


def is_nvidia_proprietary():
    """
    Check if the GPU is nvidia and the driver is proprietary
    """
    # glxinfo | grep "client glx vendor string"
    output = subprocess.check_output(
        "glxinfo -B", shell=True, encoding='UTF-8')
    return "OpenGL vendor string: NVIDIA Corporation" in output


def is_vdpau_ok():
    """
    Check if the VDPAU works fine
    """
    # vdpauinfo
    try:
        ret = subprocess.run("vdpauinfo",
                             stdout=subprocess.DEVNULL,
                             stderr=subprocess.STDOUT)
    except FileNotFoundError:
        logger.error("vdpauinfo not found, unable to check VDPAU")
        return False
    return ret.returncode == 0


def is_flatpak():
    """
    Check if Hidamari is a Flatpak
    Reference:
    https://gitlab.gnome.org/jrb/crosswords/-/blob/master/src/crosswords-init.c#L179
    """
    return os.path.isfile('/.flatpak-info')


def setup_autostart(autostart):
    if autostart:
        with open(AUTOSTART_DESKTOP_PATH, mode='w') as f:
            if is_flatpak():
                f.write(AUTOSTART_DESKTOP_CONTENT_FLATPAK)
            else:
                f.write(AUTOSTART_DESKTOP_CONTENT)
    else:
        try:
            os.remove(AUTOSTART_DESKTOP_PATH)
        except OSError:
            pass


def get_video_paths():
    file_list = []
    for filename in os.listdir(VIDEO_WALLPAPER_DIR):
        filepath = os.path.join(VIDEO_WALLPAPER_DIR, filename)
        file = Gio.file_new_for_path(filepath)
        info = file.query_info('standard::content-type',
                               Gio.FileQueryInfoFlags.NONE, None)
        mime_type = info.get_content_type()
        if "video" in mime_type:
            file_list.append(filepath)
    return sorted(file_list)


"""
GNOME extension utils
"""


def gnome_extension_is_enabled(extension_name: str):
    gnome_ext = pydbus.SessionBus().get("org.gnome.Shell.Extensions")
    info: dict = gnome_ext.GetExtensionInfo(extension_name)
    return info["state"] == 1  # ENABLE = 1


def gnome_extension_set_enable(extension_name: str):
    gnome_ext = pydbus.SessionBus().get("org.gnome.Shell.Extensions")
    success: bool = gnome_ext.EnableExtension(extension_name)
    return success


def gnome_extension_set_disable(extension_name: str):
    gnome_ext = pydbus.SessionBus().get("org.gnome.Shell.Extensions")
    success: bool = gnome_ext.DisableExtension(extension_name)
    return success


def gnome_extension_is_installed(extension_name: str):
    gnome_ext = pydbus.SessionBus().get("org.gnome.Shell.Extensions")
    installed: dict = gnome_ext.ListExtensions()
    return extension_name in installed.keys()


def gnome_desktop_icon_workaround():
    """
    Workaround for GNOME desktop icon extensions not displaying the icons on top of Hidamari.
    Call this right after the wallpaper is shown.
    """
    assert is_gnome()
    extension_list = ["ding@rastersoft.com", "desktopicons-neo@darkdemon"]
    for ext in extension_list:
        # Check if installed and enabled
        if gnome_extension_is_installed(ext) and gnome_extension_is_enabled(ext):
            # Reload the extension
            logger.info("[GNOME] Applying desktop icon workaround")
            gnome_extension_set_disable(ext)
            gnome_extension_set_enable(ext)


"""
Handlers
"""


class ActiveHandler:
    """
    Handler for monitoring screen lock
    GNOME:
    https://gitlab.gnome.org/GNOME/gnome-shell/-/blob/main/data/dbus-interfaces/org.gnome.ScreenSaver.xml
    Cinamon:
    https://github.com/linuxmint/cinnamon-screensaver/blob/master/libcscreensaver/org.cinnamon.ScreenSaver.xml
    Freedesktop:
    https://github.com/KDE/kscreenlocker/blob/master/dbus/org.freedesktop.ScreenSaver.xml
    """

    def __init__(self, on_active_changed: callable):
        session_bus = pydbus.SessionBus()
        screensaver_list = ["org.gnome.ScreenSaver",
                            "org.cinnamon.ScreenSaver",
                            "org.freedesktop.ScreenSaver"]
        for s in screensaver_list:
            try:
                proxy = session_bus.get(s)
                proxy.ActiveChanged.connect(on_active_changed)
            except GLib.Error:
                pass


class EndSessionHandler:
    """
    Handler for monitoring end session
    References:
    https://github.com/backloop/gendsession
    https://people.gnome.org/~mccann/gnome-session/docs/gnome-session.html

    PrepareForShutdown() signal from logind is not handled
    https://gitlab.gnome.org/GNOME/gnome-shell/-/issues/787
    https://bugs.launchpad.net/ubuntu/+source/gdm3/+bug/1803581

    """

    def __init__(self, on_end_session: callable):
        self.on_end_session = on_end_session

        if is_gnome():
            session_bus = pydbus.SessionBus()
            proxy = session_bus.get("org.gnome.SessionManager")
            client_id = proxy.RegisterClient("", "")
            self.session_client = session_bus.get(
                "org.gnome.SessionManager", client_id)
            self.session_client.QueryEndSession.connect(
                self.__query_end_session_handler_gnome)
            self.session_client.EndSession.connect(
                self.__end_session_handler_gnome)
        else:
            system_bus = pydbus.SystemBus()
            proxy = system_bus.get(".login1")
            proxy.PrepareForShutdown.connect(self.on_end_session)

    def __end_session_response_gnome(self, ok=True):
        if ok:
            self.session_client.EndSessionResponse(True, "")
        else:
            self.session_client.EndSessionResponse(False, "Not ready")

    def __query_end_session_handler_gnome(self, flags):
        # ignore flags, always agree on the QueryEndSesion
        self.__end_session_response_gnome(True)

    def __end_session_handler_gnome(self, flags):
        self.on_end_session()
        self.__end_session_response_gnome(True)


class WindowHandler:
    """
    Handler for monitoring window events (maximized and fullscreen mode) for X11
    """

    def __init__(self, on_window_state_changed: callable):
        self.on_window_state_changed = on_window_state_changed
        self.screen = Wnck.Screen.get_default()
        self.screen.force_update()
        self.screen.connect("window-opened", self.window_opened, None)
        self.screen.connect("window-closed", self.eval, None)
        self.screen.connect("active-workspace-changed", self.eval, None)
        for window in self.screen.get_windows():
            window.connect("state-changed", self.eval, None)

        self.prev_state = None
        # Initial check
        self.eval()

    def window_opened(self, screen, window, _):
        window.connect("state-changed", self.eval, None)

    def eval(self, *args):
        is_changed = False

        is_any_maximized, is_any_fullscreen = False, False
        for window in self.screen.get_windows():
            base_state = not Wnck.Window.is_minimized(window) and \
                Wnck.Window.is_on_workspace(
                    window, self.screen.get_active_workspace())
            window_name, is_maximized, is_fullscreen = window.get_name(), \
                Wnck.Window.is_maximized(window) and base_state, \
                Wnck.Window.is_fullscreen(window) and base_state
            if is_maximized is True:
                is_any_maximized = True
            if is_fullscreen is True:
                is_any_fullscreen = True

        cur_state = {"is_any_maximized": is_any_maximized,
                     "is_any_fullscreen": is_any_fullscreen}
        if self.prev_state is None or self.prev_state != cur_state:
            is_changed = True
            self.prev_state = cur_state

        if is_changed:
            self.on_window_state_changed(
                {"is_any_maximized": is_any_maximized, "is_any_fullscreen": is_any_fullscreen})
            logger.debug(f"[WindowHandler] {cur_state}")


# class WindowHandlerGnome:
#     """
#     Handler for monitoring window events for Gnome only
#     TODO: 
#     This is broken due to a change in GNOME. =(
#     https://gitlab.gnome.org/GNOME/gnome-shell/-/commit/7298ee23e91b756c7009b4d7687dfd8673856f8b

#     TLDR, there is no way to monitor window events in Wayland, unless we use an Shell extension.
#     To bypass, execute the below line in looking glass (Alt+F2 `lg`)
#     `global.context.unsafe_mode = true`
#     """

#     def __init__(self, on_window_state_changed: callable):
#         self.on_window_state_changed = on_window_state_changed
#         self.gnome_shell = pydbus.SessionBus().get("org.gnome.Shell")
#         self.prev_state = None
#         display = Gdk.Display.get_default()
#         self.num_monitor = display.get_n_monitors()
#         GLib.timeout_add(500, self.eval)

#     def eval(self):
#         is_changed = False

#         ret1, workspace = self.gnome_shell.Eval("""
#                         global.workspace_manager.get_active_workspace_index()
#                         """)
#         ret2 = False
#         maximized = []
#         for monitor in range(self.num_monitor):
#             ret2, temp = self.gnome_shell.Eval(f"""
#                             var window_list = global.get_window_actors().find(window =>
#                                 window.meta_window.maximized_horizontally &
#                                 window.meta_window.maximized_vertically &
#                                 !window.meta_window.minimized &
#                                 window.meta_window.get_workspace().workspace_index == {workspace} &
#                                 window.meta_window.get_monitor() == {monitor}
#                             );
#                             window_list
#                             """)
#             maximized.append(temp != "")
#         # Every monitors have a maximized window?
#         maximized = all(maximized)

#         ret3 = False
#         fullscreen = []
#         for monitor in range(self.num_monitor):
#             ret3, temp = self.gnome_shell.Eval(f"""
#                             var window_list = global.get_window_actors().find(window =>
#                     window.meta_window.is_fullscreen() &
#                     !window.meta_window.minimized &
#                     window.meta_window.get_workspace().workspace_index == {workspace} &
#                     window.meta_window.get_monitor() == {monitor}
#                 );
#                 window_list
#                 """)
#             fullscreen.append(temp != "")
#         # Every monitors have a fullscreen window?
#         fullscreen = all(fullscreen)

#         if not all([ret1, ret2, ret3]):
#             logging.error(
#                 "[WindowHandlerGnome] Cannot communicate with Gnome Shell!")

#         cur_state = {'is_any_maximized': maximized,
#                      'is_any_fullscreen': fullscreen}
#         if self.prev_state is None or self.prev_state != cur_state:
#             is_changed = True
#             self.prev_state = cur_state

#         if is_changed:
#             self.on_window_state_changed(
#                 {"is_any_maximized": maximized, "is_any_fullscreen": fullscreen})
#             logger.debug(f"[WindowHandlerGnome] {cur_state}")
#         return True


class ConfigUtil:
    def generate_template(self):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        self.save(CONFIG_TEMPLATE)

    @staticmethod
    def _check(config: dict):
        """Check if the config is valid"""
        is_all_keys_match = all(key in config for key in CONFIG_TEMPLATE)
        is_version_match = config.get("version") == CONFIG_VERSION
        return is_all_keys_match and is_version_match

    def _invalid(self):
        logger.debug(f"[Config] Invalid. A new config will be generated.")
        self.generate_template()
        return CONFIG_TEMPLATE

    def load(self):
        if os.path.isfile(CONFIG_PATH):
            with open(CONFIG_PATH, "r") as f:
                json_str = f.read()
                try:
                    config = json.loads(json_str)
                    if self._check(config):
                        logs = []
                        logs.append("--------- Config ---------")
                        logs.append(pformat(config, indent=3))
                        logs.append("--------------------------")
                        logs_str = "\n".join(logs)
                        logger.debug(
                            f"[Config] Loaded\n{logs_str}")
                        return config
                except json.decoder.JSONDecodeError:
                    logger.debug(f"[Config] JSONDecodeError")
        return self._invalid()

    def save(self, config):
        old_config = None
        if os.path.isfile(CONFIG_PATH):
            with open(CONFIG_PATH, "r") as f:
                json_str = f.read()
                try:
                    old_config = json.loads(json_str)
                    if not self._check(old_config):
                        old_config = None
                except json.decoder.JSONDecodeError:
                    old_config = None
        # Skip if the config is identical
        if old_config == config:
            return
        with open(CONFIG_PATH, "w") as f:
            json_str = json.dumps(config, indent=3)
            print(json_str, file=f)
            logs = []
            logs.append("--------- Config ---------")
            logs.append(pformat(config, indent=3))
            logs.append("--------------------------")
            logs_str = "\n".join(logs)
            logger.debug(f"[Config] Saved\n{logs_str}")
