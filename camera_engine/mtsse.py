from threading import Thread

import numpy as np

from .wrapper import *

PIXELS = 3648

class _FrameGrabber(Thread):
    active = True
    run_forever = False
    def __init__(self, device_id, frames, interval_ms, callback):
        super().__init__()
        self.device_id = device_id
        self.frames = frames
        self.run_forever = (frames == -1)
        self.interval = interval_ms / 1000
        self.callback = callback
        self.start()

    def run(self):
        if self.run_forever:
            start_frame_grab(0x8888)
            get_device_spectrometer_frame_data(self.device_id, 1, True)
        else:
            i = 0
            while self.active and i < self.frames:
                start_frame_grab(1)
                get_device_spectrometer_frame_data(self.device_id, 1, True)
                time.sleep(self.interval)
                i+=1
            self.active = False

    def kill(self):
        self.active = False
        stop_frame_grab()

class WorkMode:
    NORMAL = 0
    TRIGGER = 1

class Frame:
    def __init__(self, row: int, col: int, attributes: dict, data_tuple: tuple):
        for key, val in attributes.items():
            setattr(self, key, val)
        self.row = row
        self.col = col
        self.raw_data = np.array(data_tuple[0])
        self.calibrated_data = np.array(data_tuple[1])
        self.absolute_intensities = np.array(data_tuple[2])

    def __eq__(self, other):
        return isinstance(other, Frame) and self.raw_data == other.raw_data and self.calibrated_data == other.calibrated_data and self.absolute_intensities == other.absolute_intensities

def _handle_new_frame(row, col, attributes, data_tuple):
    frame = Frame(row, col, attributes, data_tuple)
    _camera_registry[attributes["camera_id"]].add_frame(frame)

install_callback(_handle_new_frame)

_camera_registry = {}

def start_engine():
    if init_device() == 0:
        raise ConnectionError("Failed to connect to the camera")

def teardown_engine():
    uninit_device()


class LineCamera:

    _default_exposure_time: int = 50
    _frame_grabber: _FrameGrabber = None
    _last_received_frame: Frame = None
    _frame_callbacks = []
    _exposure_microseconds = 50000

    def __init__(self, activate=True, device_id=1):
        self.device_id = device_id
        self.set_work_mode(WorkMode.NORMAL)
        install_device_frame_hooker(device_id, receive_frame)
        _camera_registry[device_id] = self
        if activate:
            self.activate()

    def add_frame_callback(self, callback):
        self._frame_callbacks.append(callback)

    def remove_callback(self, callback):
        self._frame_callbacks.remove(callback)

    def activate(self):
        set_device_active_status(self.device_id, True)
        self.set_exposure_ms(LineCamera._default_exposure_time)

    def shutdown(self):
        set_device_active_status(self.device_id, False)

    def grab_spectrum_frames(self, frames:int =-1, interval_ms=0, callback=None):
        if self._frame_grabber and self._frame_grabber.active:
            raise Exception("User attempted to grab frames before stopping an existing frame grab process")

        self._frame_grabber = _FrameGrabber(self.device_id, frames, interval_ms, callback)

    def stop_spectrum_grab(self):
        if self._frame_grabber:
            self._frame_grabber.kill()

    def is_grabbing_frames(self):
        return self._frame_grabber and self._frame_grabber.active

    def set_exposure_microseconds(self, exposure_time_microseconds):
        self._exposure_microseconds = self._exposure_microseconds
        set_device_exposure_time(self.device_id, exposure_time_microseconds)

    def get_exposure_microseconds(self):
        return self._exposure_microseconds

    def set_exposure_ms(self, exposure_time_ms):
        self._exposure_microseconds = exposure_time_ms * 1000
        self.set_exposure_microseconds(exposure_time_ms * 1000)

    def get_exposure_ms(self):
        return self._exposure_microseconds / 1000

    def set_work_mode(self, work_mode: int):
        if work_mode != 0 and work_mode != 1:
            raise ValueError(f"Expected a value of 0 or 1 and got {work_mode}")
        set_device_work_mode(self.device_id, work_mode)

    def has_frame(self):
        return self._last_received_frame

    def last_received_frame(self) -> Frame | None:
        return self._last_received_frame

    def add_frame(self, frame: Frame):
        self._last_received_frame = frame
        for frame_callback in self._frame_callbacks:
            frame_callback(frame)




