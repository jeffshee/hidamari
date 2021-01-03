from v2.daemon import daemon
import sys


class CLI(daemon):
    def __init__(self, args, pidfile):
        super().__init__(pidfile)
        # self.args = args
        # Sleep for defined interval
        # time.sleep(args.pause)

    def run(self):
        print("hello")
        from player import Player
        Player()


# https://www.jejik.com/articles/2007/02/a_simple_unix_linux_daemon_in_python/
if __name__ == '__main__':
    # parser = argparse.ArgumentParser()
    # parser.add_argument('-f', '--file', default=None)
    # parser.add_argument('-p', '--pause', type=int, default=0)
    # parser.add_argument('-d', '--display', type=int, default=0)
    # parser.add_argument('--volume', type=int, default=50)
    # parser.add_argument('--autostart', action='store_true')
    # parser.add_argument('--detect_maximize', action='store_true')
    # parser.add_argument('--mute', action='store_true')
    # parser.add_argument('--blur', action='store_true')
    # parser.add_argument('--blur_radius', type=int, default=5)
    # args = parser.parse_args()
    daemon = CLI(None, '/tmp/hidamari.pid')
    if len(sys.argv) == 2:
        if 'start' == sys.argv[1]:
            daemon.start()
        elif 'stop' == sys.argv[1]:
            daemon.stop()
        elif 'restart' == sys.argv[1]:
            daemon.restart()
        else:
            sys.exit(2)
        sys.exit(0)
    else:
        sys.exit(2)
