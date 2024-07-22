import gi
gi.require_version('Gdk', '3.0')
from gi.repository import Gdk


class Monitor:
    def __init__(self, name, width=0, height=0, x=0, y=0, is_primary=False, wallpaper=None):
        self.width = width
        self.height = height
        self.wallpaper = wallpaper
        self.primary = is_primary
        self.x = x
        self.y = y
        self.name = name

    def set_wallpaper(self, wallpaper):
        self.wallpaper = wallpaper

    def __str__(self):
        return f"Monitor(name={self.name}, x={self.x}, y={self.y}, width={self.width}, height={self.height}, primary={self.primary}, wallpaper={self.wallpaper})"


class MonitorInfo:
    @staticmethod
    def get_unique_monitor_count():
        display = Gdk.Display.get_default()
        return display.get_n_monitors()

    @staticmethod
    def monitors():
        display = Gdk.Display.get_default()
        n_monitors = display.get_n_monitors()
        monitors = []
        
        for i in range(n_monitors):
            monitor = display.get_monitor(i)
            geometry = monitor.get_geometry()
            width_mm = monitor.get_width_mm()
            height_mm = monitor.get_height_mm()
            name = monitor.get_model()
            is_primary = monitor.is_primary()

            monitors.append({
                'x': geometry.x,
                'y': geometry.y,
                'width': geometry.width,
                'height': geometry.height,
                'width_mm': width_mm,
                'height_mm': height_mm,
                'name': name,
                'is_primary': is_primary,
            })
        
        return monitors

class Monitors:
    def __init__(self):
        self.monitors = {}
        for monitor in MonitorInfo.monitors():
            self.monitors[monitor['name']] = Monitor(
                name=monitor['name'],
                width=monitor['width'],
                height=monitor['height'],
                x=monitor['x'],
                y=monitor['y'],
                is_primary=monitor['is_primary']
            )
        # we should create default monitor
        self.monitors['default'] = Monitor(name='default',width=0)

    def get_monitor(self, key):
        return self.monitors[key]

    def get_primary_monitor(self):
        for monitor in self.monitors:
            if monitor.primary:
                return monitor

        return self.monitors.items[0]

    def get_primary_monitor_index(self):
        for i, monitor in enumerate(self.monitors):
            if monitor.primary:
                return i

        return 0

    def get_monitors(self):
        return self.monitors

    def __str__(self):
        return "\n".join(str(monitor) for monitor in self.monitors)

"""def testCount():
    info = MonitorInfo()
    print(f"Unique Monitor Count = {info.get_unique_monitor_count()}")
    
def testMonitors():
    monitors = Monitors()
    for i, monitor in enumerate(monitors.get_monitors()):
        print(f"Monitor {i} : {monitor}")
"""