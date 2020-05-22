from gi.repository import GLib
import pydbus

loop = GLib.MainLoop()
session_bus = pydbus.SessionBus()
proxy = session_bus.get('org.gnome.ScreenSaver')
proxy.ActiveChanged.connect(print)
loop.run()
