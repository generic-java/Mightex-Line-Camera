import os

import json
from json import JSONDecodeError

_loadable_settings = {
    "spectrometer_wavelength": "1000",
    "subtract_bg": False,
    "auto_calibrate": True,
    "nist_element": "He I",
    "start_nist_wl": "300",
    "end_nist_wl": "800",
    "nist_fwhm": "0.1",
    "nist_intensity_fraction": "0.5",
    "nist_file": "",
    "load_row_start": "0",
    "load_wl_col": "0",
    "load_intensity_col": "2",
    "a0": "0",
    "a1": "1",
    "a2": "0",
    "a3": "0",
    "a0_eq": "0 * w",
    "a1_eq": "1",
    "a2_eq": "0 * w",
    "a3_eq": "0 * w",
}

_unloadable_settings = {
    "default_open_path": "Data",
    "default_map_path": "Mappings",
    "default_docs_path": r"res\files\Documentation.pdf",
    "github_url": "https://github.com/generic-java/Mightex-Line-Camera",
    "xkcd_url": "https://xkcd.com/273",
    "xkcd_path": r"res\images\electromagnetic_spectrum.png"
}

class Settings:

    _settings_fpath = os.path.join(str(__file__).replace("settings_manager.py", ""), "json/settings.json")
    _instance = None
    _initialized = False

    def __new__(cls, *args, **kwargs):
        if Settings._instance is None:
            Settings._instance = super().__new__(cls, *args, **kwargs)
        return Settings._instance

    def __init__(self):
        if Settings._initialized:
            return
        else:
            Settings._initialized = True
        try:
            with open(self._settings_fpath, "r") as file:
                _loadable_settings.update(json.load(file))
        except JSONDecodeError:
            with open(self._settings_fpath, "w") as file:
                file.write("{}")

    def __setattr__(self, key, value):
        if key in _loadable_settings:
            _loadable_settings[key] = value
        else:
            raise KeyError
    def __getattr__(self, key):
        if key in _loadable_settings:
            return _loadable_settings[key]
        elif key in _unloadable_settings:
            return _unloadable_settings[key]
        else:
            raise KeyError

    def save_settings(self):
        with open(self._settings_fpath, "w") as file:
            file.write(json.dumps(_loadable_settings))
