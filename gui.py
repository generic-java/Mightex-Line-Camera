import os

import numpy as np
from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QPixmap, QAction, QIcon
from PyQt6.QtWidgets import *

from app_widgets import FileInput, LabeledLineEdit, SimpleButton, ErrorDialog, IconButton, MenuSelectorButton, FixedSizeSpacer
from camera_engine.mtsse import LineCamera
from camera_engine.wrapper import PIXELS
from loadwaves import load_waves, fetch_waves, read_nist_data, save_waves
from plottools import DataHandler, RealTimePlot


class Window(QMainWindow):
    def __init__(self, camera: LineCamera):
        super().__init__()

        #self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.camera = camera
        self.setWindowTitle("Mightex Manager")

        # All things plotting
        plot_container = QWidget()
        plot_container_layout = QVBoxLayout()

        self.plot = RealTimePlot(DataHandler(camera))
        plot_container_layout.addWidget(self.plot)

        # Crosshair readout
        plot_container_layout.addWidget(self.plot.get_crosshair_readout())

        # Unit control
        plot_container_layout.addWidget(self.plot.get_unit_control())

        plot_container.setLayout(plot_container_layout)
        self.setCentralWidget(plot_container)

        # Menu
        self.menubar = self.menuBar()
        self.create_menu()

        self.toolbar = QToolBar("My main toolbar")
        self.create_toolbar()

        self.resize(1200, 800)

    # noinspection PyUnboundLocalVariable
    def keyPressEvent(self, event):
        try:
            super().keyPressEvent(event)
            key = event.key()
            if key == Qt.Key.Key_Right or key == Qt.Key.Key_Left:
                if event.key() == Qt.Key.Key_Right:
                    increment = 1
                elif key == Qt.Key.Key_Left:
                    increment = -1
                self.plot.move_crosshair(increment)

        except Exception as e:
            print(e)

    def resizeEvent(self, event):
        self.plot.redraw()

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
        load_spectra.setFixedWidth(200)

        # Primary loader
        load_first = load_spectra.addAction("Load primary spectrum")
        primary_spectrum_dialog = LoadSpectrumDialog(self, 1)
        load_first.triggered.connect(primary_spectrum_dialog.open)
        load_spectra.addAction(load_first)

        # Secondary menu
        load_second_menu = load_spectra.addMenu("Load reference spectrum")
        load_file_normal = load_second_menu.addAction("Load from file")

        nist_download_dialog = DownloadFromNISTDialog(self)
        download_from_nist = load_second_menu.addAction("Download from NIST")
        download_from_nist.triggered.connect(nist_download_dialog.open)

        nist_open_dialog = OpenFromNISTDialog(self)
        open_from_nist = load_second_menu.addAction("Open from NIST file")
        open_from_nist.triggered.connect(nist_open_dialog.open)

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

        map_pixels_dialog = MaxPixelsDialog(self)
        calibrate_wavelength_map = calibrate_wavelength.addAction("Map pixels to wavelengths")
        calibrate_wavelength_map.triggered.connect(map_pixels_dialog.show)

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

        save_dialog = SaveFileDialog(self)

        self.toolbar.addAction(ToolbarButton(QIcon("./res/icons/save.png"), "Save spectrum", self, callback=save_dialog.open))

        self.toolbar.addAction(ToolbarButton(QIcon("./res/icons/notepad.png"), "Save as CSV", self, callback=self.save_file))
        self.toolbar.addAction(ToolbarButton(QIcon("./res/icons/txtpad.png"), "Save as TXT", self, callback=self.save_file))

        self.toolbar.addAction(PlayStopButton("Acquire continuous spectrum", self, self.camera.grab_spectrum_frames, self.camera.stop_spectrum_grab))

        #self.toolbar.addAction()

    def save_file(self, dialog_filter=""):
        fname, _ = QFileDialog.getSaveFileName(filter=dialog_filter)
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

    def save_txt(self):
        pass

    def load_primary_spectrum(self, wavelengths, intensities):
        self.plot.set_primary_line(wavelengths, intensities)

    def load_secondary_spectrum(self, wavelengths, intensities):
        self.plot.set_secondary_line(wavelengths, intensities)

    def save_settings(self):
        pass


def load_stylesheet(fname: str):
    with open(os.path.join("./res/stylesheets", fname)) as file:
        return file.read()


class PixelMapInput(QWidget):
    def __init__(self, removable=True):
        super().__init__()
        layout = QHBoxLayout()
        self.pixel_input = LabeledLineEdit("Pixel:")
        layout.addWidget(self.pixel_input)

        layout.addWidget(FixedSizeSpacer(width=20))

        self.wl_input = LabeledLineEdit("Wavelength:")
        layout.addWidget(self.wl_input)

        if removable:
            layout.addWidget(FixedSizeSpacer(width=20))

            delete_button = IconButton(QIcon("./res/icons/trash.png"), self.hide)
            delete_button.setFixedSize(QSize(20, 20))
            layout.addWidget(delete_button)

        layout.addStretch()
        self.setLayout(layout)

    def get_pixel(self):
        return self.pixel_input.get_int()

    def get_wavelength(self):
        return self.wl_input.get_float()


class MaxPixelsDialog(QDialog):
    def __init__(self, parent: Window):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("Map pixels to wavelengths")

        vbox = QVBoxLayout()

        map_container = QScrollArea()
        map_container.setWidgetResizable(True)
        map_container.setFixedSize(QSize(400, 175))
        self.container_widget = QWidget()
        self.container_widget.setObjectName("map-pixels-container")
        container_layout = QVBoxLayout()
        self.container_widget.setLayout(container_layout)
        map_container.setWidget(self.container_widget)
        vbox.addWidget(map_container)

        def add_map_item():
            container_layout.addWidget(PixelMapInput(removable=True))

        add_map_button = SimpleButton("Add map item", add_map_item)
        button_container = QHBoxLayout()
        button_container.addStretch()
        button_container.addWidget(add_map_button)
        vbox.addStretch()
        vbox.addLayout(button_container)

        map_button = SimpleButton("Map", self.on_close)
        bottom_hbox = QHBoxLayout()
        bottom_hbox.addStretch()
        bottom_hbox.addWidget(map_button)
        vbox.addStretch()
        vbox.addLayout(bottom_hbox)

        vbox.setContentsMargins(10, 10, 10, 10)

        for i in range(2):
            container_layout.addWidget(PixelMapInput(removable=False))

        self.setLayout(vbox)

    def show(self):
        super().show()
        self.setFixedSize(self.size())

    def on_close(self):
        try:
            x_data = []
            y_data = []
            for widget in self.container_widget.findChildren(PixelMapInput):
                if not widget.isHidden():
                    x_data.append(widget.get_pixel())
                    y_data.append(widget.get_wavelength())

            self.parent.plot.fit(x_data, y_data)
            self.close()
        except Exception as e:
            print(e)

class SaveFileDialog(QDialog):
    # noinspection PyUnresolvedReferences
    def __init__(self, parent: Window, ask_for_delimiter=True, title="Save spectrum", dialog_filter="All Files (*.*)"):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle(title)

        vbox = QVBoxLayout()

        if ask_for_delimiter:
            self.delimiter_input = LabeledLineEdit("Delimiter:", max_text_width=25, text=",")
            vbox.addWidget(self.delimiter_input)

        wl_column_container = QHBoxLayout()
        wl_column_label = QLabel("Wavelength column:")
        wl_column_readout = QLabel("N/A")

        wl_column_readout.setObjectName("wl-column-readout")

        wl_column_container.addWidget(wl_column_label)
        wl_column_container.addWidget(wl_column_readout)
        wl_column_container.addStretch()

        intensity_column_container = QHBoxLayout()
        intensity_label = QLabel("Intensity column:")
        intensity_column_container.addWidget(intensity_label)
        first_column_action = QAction("Column 0", self)
        first_column_action.triggered.connect(lambda: wl_column_readout.setText("Column 1"))
        second_column_action = QAction("Column 1", self)
        second_column_action.triggered.connect(lambda: wl_column_readout.setText("Column 0"))
        self.intensity_column_button = MenuSelectorButton("Choose intensity column", first_column_action, second_column_action)
        intensity_column_container.addWidget(self.intensity_column_button)
        intensity_column_container.addStretch()
        vbox.addLayout(intensity_column_container)
        vbox.addLayout(wl_column_container)
        first_column_action.trigger()

        self.file_input = FileInput(dialog_filter=dialog_filter)

        vbox.addWidget(self.file_input)

        save_button = SimpleButton("Save", self.on_close)

        bottom_hbox = QHBoxLayout()
        bottom_hbox.addStretch()
        bottom_hbox.addWidget(save_button)
        vbox.addStretch()
        vbox.addLayout(bottom_hbox)

        vbox.setContentsMargins(10, 10, 10, 10)
        self.setLayout(vbox)

    def open(self):
        super().open()
        self.setFixedSize(self.size())

    def on_close(self):
        try:
            wavelengths, intensities = self.parent.plot.get_primary_data()
            if self.intensity_column_button.get_selected() == "Column 1":
                save_waves(self.file_input.get_chosen_fname(), wavelengths, intensities, delimiter=self.delimiter_input.get_text())
            else:
                save_waves(self.file_input.get_chosen_fname(), wavelengths, intensities, delimiter=self.delimiter_input.get_text())

            self.close()
        except Exception as e:
            print(e)
            return

class LoadSpectrumDialog(QDialog):
    def __init__(self, parent: Window, spectrum_num):
        super().__init__(parent)
        self.parent = parent
        self.spectrum_num = spectrum_num
        self.setObjectName("load-spectrum-dialog")
        if spectrum_num == 1:
            self.setWindowTitle("Load primary spectrum")
        else:
            self.setWindowTitle("Load reference spectrum")

        vbox = QVBoxLayout()

        self.delimiter_input = LabeledLineEdit("Delimiter:", max_text_width=25, text=",")
        vbox.addWidget(self.delimiter_input)
        self.row_start_input = LabeledLineEdit("Start at row:", max_text_width=35, text="22")
        vbox.addWidget(self.row_start_input)
        self.wavelength_column_input = LabeledLineEdit("Wavelength column:", max_text_width=35, text="0")
        vbox.addWidget(self.wavelength_column_input)
        self.intensity_column_input = LabeledLineEdit("Intensity column:", max_text_width=35, text="2")
        vbox.addWidget(self.intensity_column_input)
        self.file_input = FileInput()
        vbox.addWidget(self.file_input)

        load_button = SimpleButton("Load", self.on_close)

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

        load_button = SimpleButton("Load", self.on_close)

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


class OpenFromNISTDialog(QDialog):
    def __init__(self, parent: Window):
        super().__init__(parent)
        self.parent = parent
        self.setObjectName("load-spectrum-dialog")
        self.setWindowTitle("Load spectrum")

        vbox = QVBoxLayout()

        self.start_wl_input = LabeledLineEdit("Start wavelength:", max_text_width=35, text="400")
        vbox.addWidget(self.start_wl_input)

        self.end_wl_input = LabeledLineEdit("End wavelength:", max_text_width=35, text="700")
        vbox.addWidget(self.end_wl_input)

        self.fwhm_input = LabeledLineEdit("Full width half max:", max_text_width=35, text="1")
        vbox.addWidget(self.fwhm_input)

        self.intensity_fraction_input = LabeledLineEdit("Intensity fraction:", max_text_width=35, text="0.3")
        vbox.addWidget(self.intensity_fraction_input)

        self.file_input = FileInput(label_text="File:", dialog_filter="TXT File (*.txt)")
        vbox.addWidget(self.file_input)

        load_button = SimpleButton("Load", self.on_close)

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
            start_wavelength = self.start_wl_input.get_float()
            end_wavelength = self.end_wl_input.get_float()
            full_width_half_max = self.fwhm_input.get_float()
            intensity_fraction = self.intensity_fraction_input.get_float()
            fpath = self.file_input.get_chosen_fname()

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
    fpath: str = "./res/splash/splash screen.png"
    def __init__(self):
        super().__init__(QPixmap(self.fpath))
