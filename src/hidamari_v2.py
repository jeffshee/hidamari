import os
import time
from pydbus import SessionBus
from gi.repository import GLib

DBUS_NAME = "io.github.jeffshee.hidamari"
SERVER = "server_v2.py"

# Make sure that X11 is the backend. This makes sure Wayland reverts to XWayland.
os.environ['GDK_BACKEND'] = "x11"
# Suppress VLC Log
os.environ["VLC_VERBOSE"] = "-1"

loop = GLib.MainLoop()


def create_server():
    print("Creating server...")
    import subprocess
    import sys
    subprocess.Popen([sys.executable, SERVER])


bus = SessionBus()
server = None
for i in range(2):
    try:
        server = bus.get(DBUS_NAME)
    except Exception as e:
        if e.code == 2 and i == 0:
            create_server()
        time.sleep(1)

if server is None:
    raise RuntimeError("Couldn't connect to server")

server.PropertiesChanged.connect(print)

reply = server.Hello()
print(reply)
#
# reply = server.EchoString("test 123")
# print(reply)
#
# server.SomeProperty = "hello!"
# server.Quit()
#
# # Must use GLib.MainLoop() to receive signal

# server.video("ddd")
# loop.run()
