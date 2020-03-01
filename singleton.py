import os
import sys
import tempfile
import fcntl


class SingleInstance(object):

    def __init__(self, flavor_id='', lockfile=''):
        self.initialized = False
        if lockfile:
            self.lockfile = lockfile
        else:
            basename = os.path.splitext(os.path.abspath(sys.argv[0]))[0].replace(
                '/', '-').replace(':', '').replace('\\', '-') + '-%s' % flavor_id + '.lock'
            self.lockfile = os.path.normpath(
                tempfile.gettempdir() + '/' + basename)

        self.fp = open(self.lockfile, 'w')
        self.fp.flush()
        try:
            fcntl.lockf(self.fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except IOError:
            print('Another instance is already running, quitting.')
            sys.exit(0)
        self.initialized = True

    def __del__(self):
        if not self.initialized:
            return
        try:
            fcntl.lockf(self.fp, fcntl.LOCK_UN)
            # os.close(self.fp)
            if os.path.isfile(self.lockfile):
                os.unlink(self.lockfile)
        except Exception as e:
            print(e)
            sys.exit(-1)
