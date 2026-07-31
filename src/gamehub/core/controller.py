from __future__ import annotations
import select
import time
import threading

from PySide6.QtCore import QThread, Signal

try:
    import evdev
    from evdev import ecodes
    _HAVE_EVDEV = True
except Exception:
    _HAVE_EVDEV = False

_BUTTON_MAP = {
    ecodes.BTN_SOUTH if _HAVE_EVDEV else -1: "a",
    ecodes.BTN_EAST if _HAVE_EVDEV else -1: "b",
    ecodes.BTN_NORTH if _HAVE_EVDEV else -1: "y",
    ecodes.BTN_WEST if _HAVE_EVDEV else -1: "x",
    ecodes.BTN_START if _HAVE_EVDEV else -1: "start",
    ecodes.BTN_SELECT if _HAVE_EVDEV else -1: "select",
    ecodes.BTN_TL if _HAVE_EVDEV else -1: "lb",
    ecodes.BTN_TR if _HAVE_EVDEV else -1: "rb",
    ecodes.BTN_DPAD_UP if _HAVE_EVDEV else -1: "up",
    ecodes.BTN_DPAD_DOWN if _HAVE_EVDEV else -1: "down",
    ecodes.BTN_DPAD_LEFT if _HAVE_EVDEV else -1: "left",
    ecodes.BTN_DPAD_RIGHT if _HAVE_EVDEV else -1: "right",
}

_DEADZONE = 0.35


def is_gamepad(device) -> bool:
    try:
        caps = device.capabilities(verbose=False)
        keys = set(caps.get(ecodes.EV_KEY, []))
        axes = set(caps.get(ecodes.EV_ABS, []))
        gamepad_btns = {
            ecodes.BTN_SOUTH, ecodes.BTN_EAST, ecodes.BTN_START,
            ecodes.BTN_DPAD_UP, ecodes.BTN_TR,
        }
        if keys & gamepad_btns:
            return True
        if axes and {ecodes.ABS_X, ecodes.ABS_Y}.issubset(axes):
            return True
    except Exception:
        pass
    return False


class ControllerPoller(QThread):
    connected = Signal(bool)
    button = Signal(str, bool)
    nav = Signal(str, bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = True
        self._lock = threading.Lock()

    def shutdown(self):
        with self._lock:
            self._running = False

    def stop(self):
        self.shutdown()

    def run(self):
        if not _HAVE_EVDEV:
            self.connected.emit(False)
            return

        while True:
            with self._lock:
                if not self._running:
                    return
            try:
                devices = [evdev.InputDevice(p) for p in evdev.list_devices()]
            except Exception:
                devices = []

            pads = [d for d in devices if is_gamepad(d)]
            if not pads:
                for d in devices:
                    d.close()
                self.connected.emit(False)
                time.sleep(1.5)
                continue

            self.connected.emit(True)
            self._stick = {"x": 0, "y": 0}
            try:
                self._read_pads(pads)
            except OSError:
                pass
            finally:
                for d in pads:
                    try:
                        d.close()
                    except Exception:
                        pass

    def _read_pads(self, pads):
        fds = {p.fd: p for p in pads}
        while True:
            with self._lock:
                if not self._running:
                    return
            try:
                ready, _, _ = select.select(list(fds.keys()), [], [], 0.25)
            except OSError:
                return
            for fd in ready:
                dev = fds[fd]
                try:
                    for event in dev.read():
                        self._handle_event(dev, event)
                except OSError:
                    return

    def _handle_event(self, dev, event):
        if event.type == ecodes.EV_KEY and event.code in _BUTTON_MAP:
            name = _BUTTON_MAP[event.code]
            if event.value == 1:
                self.button.emit(name, True)
            elif event.value == 0:
                self.button.emit(name, False)
        elif event.type == ecodes.EV_ABS and event.code in (ecodes.ABS_X, ecodes.ABS_Y):
            axis = "x" if event.code == ecodes.ABS_X else "y"
            try:
                info = dev.absinfo(event.code)
                span = (info.max - info.min) or 1
                value = (event.value - (info.max + info.min) / 2) / (span / 2)
            except Exception:
                value = 0
            self._handle_stick(axis, value)

    def _handle_stick(self, axis: str, value: float):
        prev = self._stick[axis]
        if value > _DEADZONE:
            new = 1
        elif value < -_DEADZONE:
            new = -1
        else:
            new = 0
        if new == prev:
            return
        self._stick[axis] = new
        if axis == "x":
            if new == 1:
                self.nav.emit("right", True)
            elif new == -1:
                self.nav.emit("left", True)
            elif prev == 1:
                self.nav.emit("right", False)
            else:
                self.nav.emit("left", False)
        else:
            if new == 1:
                self.nav.emit("down", True)
            elif new == -1:
                self.nav.emit("up", True)
            elif prev == 1:
                self.nav.emit("down", False)
            else:
                self.nav.emit("up", False)
