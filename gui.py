import os

import numpy as np
from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QPixmap, QAction, QIcon
from PyQt6.QtWidgets import *

from app_widgets import FileInput, LabeledLineEdit, RealTimePlot, DefaultButton, DataHandler, ErrorDialog
from camera_engine.mtsse import LineCamera
from camera_engine.wrapper import PIXELS
from loadwaves import load_waves, fetch_waves, read_nist_data


class Window(QMainWindow):
    def __init__(self, camera: LineCamera):
        super().__init__()


        #self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.camera = camera
        self.setWindowTitle("The Mighty Mightex Manager")

        self.plot = RealTimePlot(DataHandler(camera))
        self.setCentralWidget(self.plot)

        # Menu
        self.menubar = self.menuBar()
        self.create_menu()

        self.toolbar = QToolBar("My main toolbar")
        self.create_toolbar()

        self.setStyleSheet(_load_stylesheet("style.qss"))

    # noinspection PyUnboundLocalVariable
    def keyPressEvent(self, event):
        super().keyPressEvent(event)
        key = event.key()
        if key == Qt.Key.Key_Right or key == Qt.Key.Key_Left:
            if event.key() == Qt.Key.Key_Right:
                increment = 1
            elif key == Qt.Key.Key_Left:
                increment = -1
            self.plot.update_crosshair(increment)


    # noinspection PyUnresolvedReferences
    def create_menu(self):
        # File menu
        file_menu = self.menubar.addMenu("File")
        new_action = QAction("New", self)
        file_menu.addAction(new_action)

        # Save as submenu
        save_as = file_menu.addMenu("Save as")
        save_as_csv = QAction("CSV", self)
        save_as_txt = QAction("TXT", self)
        save_as_other = QAction("other", self)
        save_as.addAction(save_as_csv)
        save_as.addAction(save_as_txt)
        save_as.addAction(save_as_other)

        # Load spectra submenu
        load_spectra = file_menu.addMenu("Load spectra")

        # Primary loader
        load_first = load_spectra.addAction("Load spectrum 1")
        primary_spectrum_dialog = LoadSpectrumDialog(self, 1)
        load_first.triggered.connect(primary_spectrum_dialog.open)
        load_spectra.addAction(load_first)

        # Secondary menu
        load_second_menu = load_spectra.addMenu("Load spectrum 2")
        load_file_normal = load_second_menu.addAction("Load from file")
        nist_download_dialog = DownloadFromNISTDialog(self)
        download_from_nist = load_second_menu.addAction("Download from NIST")
        download_from_nist.triggered.connect(nist_download_dialog.open)
        open_from_nist = load_second_menu.addAction("Open from NIST file")

        secondary_spectrum_dialog = LoadSpectrumDialog(self, 2)
        load_file_normal.triggered.connect(secondary_spectrum_dialog.open)

        # View menu
        view_menu = self.menubar.addMenu("View")

        toggle_toolbar = QAction("Toggle toolbar", self)
        toggle_toolbar.triggered.connect(self.toggle_toolbar)
        view_menu.addAction(toggle_toolbar)

        # Calibrate wavelength submenu
        calibrate_wavelength = view_menu.addMenu("Calibrate x axis")
        calibrate_wavelength.setMinimumWidth(175)

        calibrate_wavelength_map = calibrate_wavelength.addAction("Map pixels to wavelengths")
        calibrate_wavelength_coeff = calibrate_wavelength.addAction("Enter coefficients")


        # Tools menu
        tools_menu = self.menubar.addMenu("Tools")

        # Help menu
        help_menu = self.menubar.addMenu("Help")

        # Close button
        close_button = QAction("Close")
        self.menubar.addAction(close_button)

    def toggle_toolbar(self):
        _  = self.toolbar.show() if self.toolbar.isHidden() else self.toolbar.hide()

    def create_toolbar(self):
        self.toolbar.setMovable(False)
        self.toolbar.setIconSize(QSize(20, 20))
        self.addToolBar(self.toolbar)
        self.toolbar.addAction(ToolbarButton(QIcon("./res/icons/save.png"), "Save spectrum", self, callback=self.save_file))

        self.toolbar.addAction(ToolbarButton(QIcon("./res/icons/notepad.png"), "Save as CSV", self))
        self.toolbar.addAction(ToolbarButton(QIcon("./res/icons/txtpad.png"), "Save as TXT", self))

        self.toolbar.addAction(PlayStopButton("Acquire continuous spectrum", self, self.camera.grab_spectrum_frames, self.camera.stop_spectrum_grab))

    def save_file(self):
        fname, _ = QFileDialog.getSaveFileName(filter="CSV File (*.csv)")
        if self.camera.has_frame():
            try:
                with open(fname, "w") as file:
                    data = np.transpose(np.column_stack((np.arange(0, PIXELS, 1), self.camera.last_received_frame().raw_data)))
                    text = ""
                    for row in data:
                        text += row[0] + "," + row[1]
                    file.write(text)

            except Exception as e:
                print(e)


    def save_csv(self):
        QFileDialog.getExistingDirectory()

    def load_primary_spectrum(self, wavelengths, intensities):
        self.plot.set_primary_line(wavelengths, intensities)

    def load_secondary_spectrum(self, wavelengths, intensities):
        self.plot.set_secondary_line(wavelengths, intensities)


def _load_stylesheet(fname: str):
    with open(os.path.join("./res/stylesheets", fname)) as file:
        return file.read()


class LoadSpectrumDialog(QDialog):
    def __init__(self, parent: Window, spectrum_num):
        super().__init__(parent)
        self.parent = parent
        self.spectrum_num = spectrum_num
        self.setObjectName("load-spectrum-dialog")
        self.setWindowTitle("Load spectrum")

        vbox = QVBoxLayout()

        self.delimiter_input = LabeledLineEdit("Delimiter:", max_text_width=25)
        vbox.addWidget(self.delimiter_input)
        self.row_start_input = LabeledLineEdit("Start at row:", max_text_width=35)
        vbox.addWidget(self.row_start_input)
        self.wavelength_column_input = LabeledLineEdit("Wavelength column:", max_text_width=35)
        vbox.addWidget(self.wavelength_column_input)
        self.intensity_column_input = LabeledLineEdit("Intensity column:", max_text_width=35)
        vbox.addWidget(self.intensity_column_input)
        self.file_input = FileInput()
        vbox.addWidget(self.file_input)

        load_button = DefaultButton("Load", self.on_close)

        bottom_hbox = QHBoxLayout()
        bottom_hbox.addStretch()
        bottom_hbox.addWidget(load_button)
        vbox.addStretch()
        vbox.addLayout(bottom_hbox)

        vbox.setContentsMargins(10, 10, 10, 10)
        self.setLayout(vbox)

    def open(self):
        super().open()
        self.setFixedSize(self.size())

    def on_close(self):
        try:
            fname = self.file_input.get_chosen_fname()

            row_start = self.row_start_input.get_int()
            wavelength_col = self.wavelength_column_input.get_int()
            intensity_col = self.intensity_column_input.get_int()

            wavelengths, intensities = load_waves(fname, row_start=row_start, wavelength_col=wavelength_col, intensity_col=intensity_col, delimiter=self.delimiter_input.get_text())
            _ = self.parent.load_primary_spectrum(wavelengths, intensities) if self.spectrum_num == 1 else self.parent.load_secondary_spectrum(wavelengths, intensities)
            self.close()
        except ValueError:
            return


class DownloadFromNISTDialog(QDialog):
    def __init__(self, parent: Window):
        super().__init__(parent)
        self.parent = parent
        self.setObjectName("load-spectrum-dialog")
        self.setWindowTitle("Load spectrum")

        vbox = QVBoxLayout()

        self.element_input = LabeledLineEdit("Element:", max_text_width=20)
        vbox.addWidget(self.element_input)

        self.start_wl_input = LabeledLineEdit("Start wavelength:", max_text_width=35)
        vbox.addWidget(self.start_wl_input)

        self.end_wl_input = LabeledLineEdit("End wavelength:", max_text_width=35)
        vbox.addWidget(self.end_wl_input)

        self.fwhm_input = LabeledLineEdit("Full width half max:", max_text_width=35)
        vbox.addWidget(self.fwhm_input)

        self.intensity_fraction_input = LabeledLineEdit("Intensity fraction:", max_text_width=35)
        vbox.addWidget(self.intensity_fraction_input)

        self.file_input = FileInput(label_text="Save to:", is_save_file=True, dialog_filter="TXT File (*.txt)")
        vbox.addWidget(self.file_input)

        load_button = DefaultButton("Load", self.on_close)

        bottom_hbox = QHBoxLayout()
        bottom_hbox.addStretch()
        bottom_hbox.addWidget(load_button)
        vbox.addStretch()
        vbox.addLayout(bottom_hbox)

        vbox.setContentsMargins(10, 10, 10, 10)
        self.setLayout(vbox)

    def open(self):
        super().open()
        self.setFixedSize(self.size())

    def on_close(self):
        try:
            element = self.element_input.get_text()
            start_wavelength = self.start_wl_input.get_float()
            end_wavelength = self.end_wl_input.get_float()
            full_width_half_max = self.fwhm_input.get_float()
            intensity_fraction = self.intensity_fraction_input.get_float()
            fpath = self.file_input.get_chosen_fname()

            fetch_waves(end_wavelength, start_wavelength, element, fpath)
            wavelengths, intensities = read_nist_data(fpath, start_wavelength, end_wavelength, intensity_fraction, full_width_half_max)
            self.parent.load_secondary_spectrum(wavelengths, intensities)

            self.close()
        except ValueError:
            return
        except AttributeError:
            ErrorDialog("NIST could not generate a spectrum based on your inputs")



class ToolbarButton(QAction):

    def __init__(self, icon: QIcon, tooltip: str, window, callback=None):
        super().__init__(icon, tooltip, window)
        self.setCheckable(False)
        if callback:
            self.triggered.connect(callback)

class PlayStopButton(ToolbarButton):

    _play_icon = None
    _stop_icon = None

    def __init__(self, tooltip: str, window, play_callback, stop_callback):
        self._play_icon = QIcon("./res/icons/play.png")
        self._stop_icon = QIcon("./res/icons/stop.png")
        super().__init__(self._play_icon, tooltip, window)
        self._play_callback = play_callback
        self._stop_callback = stop_callback
        self._playing = False
        self.triggered.connect(self.set_state)

    def set_state(self):
        self._playing = not self._playing
        if self._playing:
            self._play_callback()
            self.setIcon(self._stop_icon)
            self.setToolTip("Stop acquisition")
        else:
            self._stop_callback()
            self.setIcon(self._play_icon)
            self.setToolTip("Acquire continuous spectrum")


class SplashScreen(QSplashScreen):
    fpath: str = "./res/Splash.png"
    def __init__(self):
        super().__init__(QPixmap(self.fpath))
