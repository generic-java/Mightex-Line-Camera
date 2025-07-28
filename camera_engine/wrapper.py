import os
import time
from ctypes import *

mtsse_dll = WinDLL(os.path.join(str(__file__).replace("wrapper.py", ""), "lib64/MT_Spectrometer_SDK.dll"))

PIXELS = 3648
received_data_callback = lambda _, __, ___, ____: None

class FrameRecord(Structure):
    _fields_ = [
        ("RawData", POINTER(c_double)),
        ("CalibData", POINTER(c_double)),
        ("AbsInten", POINTER(c_double)),
    ]

class FrameDataProperty(Structure):
    _fields_ = [
        ("CameraID", c_int),
        ("ExposureTime", c_int),
        ("TimeStamp", c_int),
        ("TriggerOccurred", c_int),
        ("TriggerEventCount", c_int),
        ("OverSaturated", c_int),
        ("LightShieldValue", c_int)
    ]

callback_pointer = CFUNCTYPE(None, c_int, c_int, POINTER(FrameDataProperty), POINTER(c_void_p))

mtsse_dll.MTSSE_GetDeviceSpectrometerFrameData.argtypes = [
    c_int, c_int, c_int, POINTER(POINTER(FrameRecord))
]

class WorkMode:
    NORMAL = 0
    TRIGGER = 1

class FrameGrab:
    SINGLE = 1
    CONTINUOUS = 0x8888

# noinspection PyArgumentList
@callback_pointer
def receive_frame(row, col, attrs, frame_ptr_ptr):
    frame_ptr = cast(frame_ptr_ptr.contents, POINTER(FrameRecord))
    raw_data = frame_ptr.contents.RawData[:PIXELS]
    calibrated_data = frame_ptr.contents.CalibData[:PIXELS]
    absolute_intensity = frame_ptr.contents.AbsInten[:PIXELS]
    attributes = {
        "camera_id": attrs.contents.CameraID,
        "exposure_time": attrs.contents.ExposureTime,
        "timestamp": attrs.contents.TimeStamp,
        "trigger_occurred": attrs.contents.TriggerOccurred,
        "trigger_event_count": attrs.contents.TriggerEventCount,
        "oversaturated": attrs.contents.OverSaturated,
        "light_shield_value": attrs.contents.LightShieldValue
    }
    received_data_callback(row, col, attributes, (raw_data, calibrated_data, absolute_intensity))

def install_callback(callback):
    global received_data_callback
    received_data_callback = callback

def init_device():
    return mtsse_dll.MTSSE_InitDevice(None)

def set_device_work_mode(device_id: int, work_mode: int):
    return mtsse_dll.MTSSE_SetDeviceWorkMode(device_id, work_mode)

def start_frame_grab(grab_type: int):
    return mtsse_dll.MTSSE_StartFrameGrab(grab_type)

def stop_frame_grab():
    return mtsse_dll.MTSSE_StopFrameGrab()

def set_device_active_status(device_id: int, active_flag: bool):
    return mtsse_dll.MTSSE_SetDeviceActiveStatus(device_id, int(active_flag))

def install_device_frame_hooker(device_id: int, callback):
    return mtsse_dll.MTSSE_InstallDeviceFrameHooker(device_id, callback)

def get_device_spectrometer_frame_data(device_id: int, spectrometer_id: int, wait_until_done: bool):
    return mtsse_dll.MTSSE_GetDeviceSpectrometerFrameData(device_id, spectrometer_id, int(wait_until_done), byref(POINTER(FrameRecord)()))

def set_device_soft_trigger(device_id: int):
    mtsse_dll.MTSSE_SetDeviceSoftTrigger(device_id)

def set_device_exposure_time(device_id: int, exposure_time: int):
    mtsse_dll.MTSSE_SetDeviceExposureTime(device_id, exposure_time)

def uninit_device():
    mtsse_dll.MTSSE_UnInitDevice()

def cleanup():
    stop_frame_grab()
    time.sleep(1)
    uninit_device()