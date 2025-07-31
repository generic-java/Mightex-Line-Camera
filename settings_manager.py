import os

import json

_loadable_settings = {
    "spectrometer_wavelength": 1000,
}

_unloadable_settings = {

}

class Settings:

    settings_fpath = os.path.join(str(__file__).replace("settings_manager.py", ""), "json/settings.json")

    def __init__(self):
        with open(self.settings_fpath, "r") as file:
            _loadable_settings.update(json.load(file))

    def __setattr__(self, key, value):
        if key in _loadable_settings:
            _loadable_settings[key] = value
        else:
            raise KeyError
    def __getattribute__(self, key):
        if key in _loadable_settings:
            return _loadable_settings[key]
        elif key in _unloadable_settings:
            return _unloadable_settings[key]
        else:
            raise KeyError

    def save_settings(self):
        with open(self.settings_fpath, "w") as file:
            json.dump(_loadable_settings, file)
