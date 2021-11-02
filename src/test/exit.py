# import atexit

# @atexit.register
# def last_word():
#     with open("last_word.txt", "w") as f:
#         print("I'm dead...", file=f)
#
#
# while True:
#     pass


import pydbus
from gi.repository import GLib

loop = GLib.MainLoop()


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
        # session_bus = pydbus.SessionBus()
        # proxy = session_bus.get("org.gnome.Shell", "/org/gnome/SessionManager/EndSessionDialog")
        # proxy.ConfirmedLogout.connect(on_active_changed)
        # proxy.Confirmed.connect(on_active_changed)
        # proxy.ConfirmedLogout.connect(on_active_changed)

        # system_bus = pydbus.SystemBus()
        # proxy = system_bus.get(".login1")
        # proxy.PrepareForShutdown.connect(on_active_changed)

        self.on_end_session = on_end_session

        session_bus = pydbus.SessionBus()
        proxy = session_bus.get("org.gnome.SessionManager")
        client_id = proxy.RegisterClient("", "")
        self.session_client = session_bus.get("org.gnome.SessionManager", client_id)
        self.session_client.QueryEndSession.connect(self.__query_end_session_handler)
        self.session_client.EndSession.connect(self.__end_session_handler)

    def __end_session_response(self, ok=True):
        if ok:
            self.session_client.EndSessionResponse(True, "")
        else:
            self.session_client.EndSessionResponse(False, "Not ready")

    def __query_end_session_handler(self, flags):
        # ignore flags, always agree on the QueryEndSesion
        self.__end_session_response(True)

    def __end_session_handler(self, flags):
        self.on_end_session()
        self.__end_session_response(True)


def last_word():
    with open("last_word.txt", "w") as f:
        print("I'm dead...")
        print("I'm dead...", file=f)
        loop.quit()


handler = EndSessionHandler(last_word)
loop.run()
