import multiprocessing as mp
from multiprocessing import Process

from gi.repository import GLib
from pydbus import SessionBus

from test.gui_test import main as gui_main
from test.player_test import main as player_main

DBUS_NAME = "org.example.server"
loop = GLib.MainLoop()


class Server(object):
    """
    <node>
    <interface name='org.example.server'>
        <method name='show_gui'/>
        <method name='quit'/>
    </interface>
    </node>
    """

    def __init__(self):
        mp.set_start_method("spawn")
        self.processes = []
        self.processes.append(Process(target=gui_main))
        self.processes.append(Process(target=player_main))
        # Launch all processes
        for process in self.processes:
            process.start()

    def show_gui(self):
        self.processes.append(Process(target=gui_main))
        self.processes[-1].start()

    def quit(self):
        # Quit all processes
        for process in self.processes:
            process.terminate()
        loop.quit()


def get_instance():
    bus = SessionBus()
    try:
        instance = bus.get(DBUS_NAME)
    except GLib.Error:
        return None
    return instance


def main():
    instance = get_instance()
    if instance:
        instance.show_gui()
    else:
        bus = SessionBus()
        server = Server()
        try:
            bus.publish(DBUS_NAME, server)
            loop.run()
        except RuntimeError:
            raise Exception("Failed to create server")


if __name__ == "__main__":
    main()
