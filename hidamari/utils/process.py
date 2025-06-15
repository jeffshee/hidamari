from gi.repository import Gio, GLib
from hidamari.config.paths_config import CLAMAV_EXECUTABLES
from hidamari.messages.messages import ERROR, NO_COMMAND_PROVIDED, ACTION_NOT_PERMITTED, OUTPUT_IS_BINARY


def report_result(callback: callable, success: bool, message: str) -> None:
    try:
        GLib.idle_add(callback, success, message)
    except Exception as e:
        print(f"{ERROR}: {e}")


def run_async_process(command_args: list[str], callback: callable):
    if not command_args:
        report_result(callback, False, NO_COMMAND_PROVIDED)
        return

    command = command_args[0]
    if command not in CLAMAV_EXECUTABLES:
        report_result(callback, False, ACTION_NOT_PERMITTED)
        return

    try:
        proc = Gio.Subprocess.new(
            command_args,
            Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_PIPE,
        )
    except GLib.Error as e:
        report_result(callback, False, e.message)
        return

    def on_communicate(proc, res):
        try:
            success, out_bytes, err_bytes = proc.communicate_finish(res)
            try:
                if success:
                    message = out_bytes.get_data().decode().strip() if out_bytes else ""
                else:
                    message = err_bytes.get_data().decode().strip() if err_bytes else ""
            except UnicodeDecodeError:
                message = OUTPUT_IS_BINARY

            report_result(callback, success, message)
        except GLib.Error as e:
            report_result(callback, False, e.message)

    def on_wait(proc, res):
        try:
            proc.wait_finish(res)
            proc.communicate_async(None, None, on_communicate)
        except GLib.Error as e:
            report_result(callback, False, e.message)

    proc.wait_async(None, on_wait)
