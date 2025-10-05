import json
import logging
import subprocess
from pprint import pformat

import gi
gi.require_version("Wnck", "3.0")
from gi.repository import Gio, GLib, Wnck  # , Gdk

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
    return "gnome" in str(os.environ.get("XDG_CURRENT_DESKTOP") or '').lower()


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
    try:
        output = subprocess.check_output(
            "glxinfo -B", shell=True, encoding='UTF-8')
    except FileNotFoundError:
        logger.error("[Utils] glxinfo not found, unable to check GPU")
        return False
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
        logger.error("[Utils] vdpauinfo not found, unable to check VDPAU")
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
    if is_flatpak():
        """
        Use portal to autostart for Flatpak
        Documentation:
        https://libportal.org/method.Portal.request_background.html
        https://libportal.org/method.Portal.request_background_finish.html 
        """

        gi.require_version("Xdp", "1.0")
        from gi.repository import Xdp
        xdp = Xdp.Portal.new()

        # Request Autostart
        xdp.request_background(
            None,  # parent
            "Autostart Hidamari in background",  # reason
            ['hidamari', '-b'],  # commandline
            Xdp.BackgroundFlags.AUTOSTART if autostart else Xdp.BackgroundFlags.NONE,  # flags
            None,  # cancellable
            lambda portal, result, user_data: logger.debug(
                f"[Utils] autostart={autostart}, request_background sucess={portal.request_background_finish(result)}"),  # callback
            None,  # user_data
        )
        
    os.makedirs(AUTOSTART_DIR, exist_ok=True)
    logger.debug(
        f"[Utils] autostart={autostart}, path={AUTOSTART_DESKTOP_PATH}")
    if autostart:
        with open(AUTOSTART_DESKTOP_PATH, mode='w') as f:
            if is_flatpak():
                # Write files to the sandbox as well, for the following reasons:
                # (1) So that we know if autostart is enabled by looking the file in sandbox
                # (2) Acts as a fallback in case the portal doesn't work
                f.write(AUTOSTART_DESKTOP_CONTENT_FLATPAK)
            else:
                f.write(AUTOSTART_DESKTOP_CONTENT)
    else:
        if os.path.isfile(AUTOSTART_DESKTOP_PATH):
            os.remove(AUTOSTART_DESKTOP_PATH)


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
    if not is_gnome():
        return
    extension_list = ["ding@rastersoft.com",
                      "desktopicons-neo@darkdemon", 
                      "gtk4-ding@smedius.gitlab.com",
                      "zorin-desktop-icons@zorinos.com"
                      ]
    for ext in extension_list:
        # Check if installed and enabled
        if gnome_extension_is_installed(ext) and gnome_extension_is_enabled(ext):
            # Reload the extension
            logger.info(f"[Utils] Apply workaround for {ext}")
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
        self.session_bus = pydbus.SessionBus()
        self.proxies = []
        self.signal_subscriptions = []
        
        screensaver_list = ["org.gnome.ScreenSaver",
                            "org.cinnamon.ScreenSaver",
                            "org.freedesktop.ScreenSaver"]
        for s in screensaver_list:
            try:
                proxy = self.session_bus.get(s)
                # Store proxy reference to prevent garbage collection
                self.proxies.append(proxy)
                subscription = proxy.ActiveChanged.connect(on_active_changed)
                self.signal_subscriptions.append((proxy, subscription))
            except GLib.Error:
                pass

    def cleanup(self):
        """Cleanup signal subscriptions"""
        for proxy, subscription in self.signal_subscriptions:
            try:
                # Note: pydbus doesn't have a direct disconnect method
                # The connection will be cleaned up when the proxy is garbage collected
                pass
            except Exception as e:
                logger.warning(f"[ActiveHandler] Error during cleanup: {e}")
        self.signal_subscriptions.clear()
        self.proxies.clear()


class EndSessionHandler:
    """
    Handler for monitoring end session
    References:
    https://github.com/backloop/gendsession

    PrepareForShutdown() signal from logind is not handled
    https://gitlab.gnome.org/GNOME/gnome-shell/-/issues/787
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
            proxy.PrepareForShutdown.connect(self.__end_session_handler)

    def __end_session_response_gnome(self, ok=True):
        if ok:
            self.session_client.EndSessionResponse(True, "")
        else:
            self.session_client.EndSessionResponse(False, "Not ready")

    def __query_end_session_handler_gnome(self, flags):
        # Ignore flags, always agree on the QueryEndSesion
        self.__end_session_response_gnome(True)

    def __end_session_handler_gnome(self, flags):
        logger.debug("[EndSessionHandler] called")
        self.on_end_session()
        self.__end_session_response_gnome(True)

    def __end_session_handler(self, *_):
        logger.debug("[EndSessionHandler] called")
        self.on_end_session()


class WindowHandler:
    """
    Handler for monitoring window events (maximized and fullscreen mode) for X11
    """

    def __init__(self, on_window_state_changed: callable):
        self.on_window_state_changed = on_window_state_changed
        self.screen = Wnck.Screen.get_default()
        self.screen.force_update()
        
        # Store signal handler IDs for cleanup
        self.signal_handlers = []
        self.window_signal_handlers = {}
        
        # Connect screen signals and store handler IDs
        handler_id = self.screen.connect("window-opened", self.window_opened, None)
        self.signal_handlers.append((self.screen, handler_id))
        
        handler_id = self.screen.connect("window-closed", self.eval, None)
        self.signal_handlers.append((self.screen, handler_id))
        
        handler_id = self.screen.connect("active-workspace-changed", self.eval, None)
        self.signal_handlers.append((self.screen, handler_id))
        
        # Connect to existing windows
        for window in self.screen.get_windows():
            self._connect_window(window)

        self.prev_state = None
        # Initial check
        self.eval()

    def _connect_window(self, window):
        """Connect to a window and store the handler ID"""
        if window not in self.window_signal_handlers:
            handler_id = window.connect("state-changed", self.eval, None)
            self.window_signal_handlers[window] = handler_id

    def window_opened(self, screen, window, _):
        self._connect_window(window)

    def eval(self, *args):
        # TODO: #28 (Wallpaper stops animating on other monitor when app maximized on other)
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

    def cleanup(self):
        """Cleanup all signal handlers to prevent memory leaks"""
        # Disconnect screen signals
        for obj, handler_id in self.signal_handlers:
            try:
                obj.disconnect(handler_id)
            except Exception as e:
                logger.warning(f"[WindowHandler] Error disconnecting screen signal: {e}")
        self.signal_handlers.clear()
        
        # Disconnect window signals
        for window, handler_id in self.window_signal_handlers.items():
            try:
                window.disconnect(handler_id)
            except Exception as e:
                logger.warning(f"[WindowHandler] Error disconnecting window signal: {e}")
        self.window_signal_handlers.clear()


# class WindowHandlerGnome:
#     """
#     Handler for monitoring window events for Gnome only
#     TODO: This is broken due to a change in GNOME =(
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
        
    def _migrateV3To4(self, config: dict):
        logger.debug(f"[Config] Migration from version 3 to 4.")
        curr_data_source = config['data_source']
        config['data_source'] = CONFIG_TEMPLATE[CONFIG_KEY_DATA_SOURCE]
        config['data_source']['Default'] = curr_data_source
        config['is_pause_when_maximized'] = config["is_detect_maximized"]
        del config["is_detect_maximized"]
        config['is_mute_when_maximized'] = CONFIG_TEMPLATE[CONFIG_KEY_MUTE_WHEN_MAXIMIZED]
        config['version'] = 4
        # save config file
        self.save(config)
        
    def _checkMissingMonitors(self, old_config: dict, template: dict):
        # Extract the monitors from both configurations
        old_monitors = old_config.get("data_source", {}).keys()
        template_monitors = template.get("data_source", {}).keys()
        # Find monitors in the template that are not in the old configuration
        missing_monitors = set(template_monitors) - set(old_monitors)
        if len(missing_monitors) > 0:
            logger.warning(f"[Config] There are missing {len(missing_monitors)} monitors in config. Creating default one")
            self._createMissingMonitors(missing_monitors, old_config)
    
    def _createMissingMonitors(self, keys: set, config: dict):
        # we will set to Default new monitor sources
        for key in keys:
            config['data_source'][key] = config['data_source']['Default']
        self.save(config)
        
    def _checkDefaultSource(self, config: dict):
        # Check if the 'Default' source is empty
        default_source = config['data_source'].get('Default', '')
        mode = config.get('mode')
        if mode == MODE_VIDEO and not os.path.isfile(default_source):
            logger.warning("[Config] Default source is empty or not a valid file. Setting to the first on available.")
            
            # Get all values from the 'data_source' dictionary
            values = list(config['data_source'].values())
            # If there are no values in 'data_source', return early
            if not values:
                return
            
            # Set the 'Default' source to the first value available
            for value in values:
                if len(value) > 0 and os.path.isfile(value):
                    config['data_source']['Default'] = value
                    self.save(config)
                    break
                    
    def load(self):
        if os.path.isfile(CONFIG_PATH):
            with open(CONFIG_PATH, "r") as f:
                json_str = f.read()
                try:
                    config = json.loads(json_str)
                    # migration to version 4 for data_source type change
                    if config.get("version") <= 3 and CONFIG_VERSION >= 4:
                        self._migrateV3To4(config)
                    self._checkDefaultSource(config)
                    self._checkMissingMonitors(config, CONFIG_TEMPLATE)
                    if self._check(config):
                        logs = []
                        logs.append("--------- Config ---------")
                        logs.append(pformat(config, indent=3))
                        logs.append("--------------------------")
                        logs_str = "\n".join(logs)
                        logger.debug(
                            f"[Config] Loaded {CONFIG_PATH}\n{logs_str}")
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
            logger.debug(f"[Config] Saved {CONFIG_PATH}\n{logs_str}")
