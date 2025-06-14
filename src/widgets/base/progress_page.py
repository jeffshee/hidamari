from gi.repository import Gtk, GLib, Adw


class ProgressPage(Gtk.Box):
    def __init__(self, pulse_period=500, duration=10000):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.set_halign(Gtk.Align.CENTER)
        self.set_valign(Gtk.Align.CENTER)

        self.bar = Gtk.ProgressBar()
        self.append(self.bar)

        self._pulse_period = pulse_period
        self._duration = duration
        self._increment = self._pulse_period / self._duration

        self._counter = 0.0
        self._timeout_id = None

        self.start()

    def _on_pulse(self):
        self.bar.pulse()
        return True  # keep pulsing forever until stopped

    def start(self):
        if self._timeout_id is None:
            self._timeout_id = GLib.timeout_add(self._pulse_period, self._on_pulse)

    def stop(self):
        if self._timeout_id is not None:
            GLib.source_remove(self._timeout_id)
            self._timeout_id = None
        self.bar.set_fraction(0.0)
