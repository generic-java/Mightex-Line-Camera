import os
import traceback

import numpy as np
from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import *

from app_widgets import FileInput, LabeledLineEdit, SimpleButton, ErrorDialog, IconButton, FixedSizeSpacer, \
    PlayStopButton, ToolbarButton, ClearFocusFilter, WindowHandleButton, MenuButton, MoveWindowSpacer, \
    FullscreenToggleButton, Dialog, TeXWidget, CopyableCoefficient
from camera_engine.mtsse import LineCamera
from camera_engine.wrapper import PIXELS
from loadwaves import load_waves, fetch_nist_data, read_nist_data, save_waves
from plottools import DataHandler, RealTimePlot
from utils import format_number


class Window(QMainWindow):
    def __init__(self, camera: LineCamera):
        super().__init__()

        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.camera = camera
        self.setWindowTitle("Mightex Manager")

        # All things plotting
        self.plot = RealTimePlot(DataHandler(camera))
        self.setCentralWidget(PlotContainer(self.plot, self.camera))

        # Create shared dialogs
        self.save_dialog = SaveFileDialog(self)
        self.csv_save_dialog = SaveFileDialog(self, ask_for_delimiter=False, dialog_filter="CSV Files (*.csv)")
        self.txt_save_dialog = SaveFileDialog(self, dialog_filter="Text Documents (*.txt)")

        # Menu
        self.create_menu()

        self.toolbar = QToolBar("My main toolbar")
        self.create_toolbar()

        self.resize(1100, 700)
        self.event_filter = ClearFocusFilter()
        self.installEventFilter(self.event_filter)

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
            trace = traceback.format_exc()
            print("Caught an exception:\n", trace)

    def resizeEvent(self, event):
        self.plot.redraw()

    def create_menu(self):
        menu_widget = QWidget()
        menu_widget.setObjectName("menubar")
        menu_container = QHBoxLayout()
        menu_container.setContentsMargins(0, 0, 0, 0)

        menu_button_container_outer = QVBoxLayout()
        menu_button_container_inner = QHBoxLayout()

        # File menu
        file_menu = MenuButton("File")
        new_action = QAction("New", self)
        file_menu.addAction(new_action)

        # Save as submenu
        save_as = file_menu.add_menu("Save as")
        save_as_csv = QAction("CSV", self)
        save_as_csv.triggered.connect(self.csv_save_dialog.open)
        save_as_txt = QAction("TXT", self)
        save_as_txt.triggered.connect(self.txt_save_dialog.open)
        save_as_other = QAction("Other", self)
        save_as_other.triggered.connect(self.save_dialog.open)
        save_as.addAction(save_as_csv)
        save_as.addAction(save_as_txt)
        save_as.addAction(save_as_other)

        # Load spectra submenu
        load_spectra = file_menu.add_menu("Load spectra")
        load_spectra.setFixedWidth(200)

        # Primary loader
        load_first = load_spectra.addAction("Load primary spectrum")
        primary_spectrum_dialog = LoadSpectrumDialog(self, RealTimePlot.PRIMARY)
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

        secondary_spectrum_dialog = LoadSpectrumDialog(self, RealTimePlot.REFERENCE)
        load_file_normal.triggered.connect(secondary_spectrum_dialog.open)

        # View menu
        view_menu = MenuButton("View")

        toggle_toolbar = QAction("Toggle toolbar", self)
        toggle_toolbar.triggered.connect(self.toggle_toolbar)
        view_menu.add_action(toggle_toolbar)

        # Toggle primary plot
        toggle_primary_plot = QAction("Toggle primary plot", self)
        toggle_primary_plot.triggered.connect(self.plot.toggle_primary_plot)
        view_menu.add_action(toggle_primary_plot)

        # Toggle reference plot
        toggle_reference_plot = QAction("Toggle reference plot", self)
        toggle_reference_plot.triggered.connect(self.plot.toggle_reference_plot)
        view_menu.add_action(toggle_reference_plot)

        # Tools menu
        tools_menu = MenuButton("Tools")
        tools_menu.get_menu().setMinimumWidth(225)

        # Region calibrated primary spectrum
        # Calibrate primary wavelength submenu
        calibrate_primary_wavelength = tools_menu.add_menu("Calibrate primary x axis")
        calibrate_primary_wavelength.setMinimumWidth(225)

        map_pixels_primary_dialog = MaxPixelsDialog(self, RealTimePlot.PRIMARY)
        calibrate_wavelength_map = calibrate_primary_wavelength.addAction("Map pixels to wavelengths")
        calibrate_wavelength_map.triggered.connect(map_pixels_primary_dialog.show)

        enter_coeff_dialog_primary = EnterCoeffDialog(self, RealTimePlot.PRIMARY)
        calibrate_wavelength_coeff = calibrate_primary_wavelength.addAction("Enter coefficients")
        calibrate_wavelength_coeff.triggered.connect(enter_coeff_dialog_primary.open)
        # End region

        # Region calibrate reference spectrum
        # Calibrate reference wavelength submenu
        calibrate_reference_wavelength = tools_menu.add_menu("Calibrate reference x axis")
        calibrate_reference_wavelength.setMinimumWidth(225)

        map_pixels_reference_dialog = MaxPixelsDialog(self, RealTimePlot.REFERENCE)
        calibrate_reference_wavelength_map = calibrate_reference_wavelength.addAction("Map pixels to wavelengths")
        calibrate_reference_wavelength_map.triggered.connect(map_pixels_reference_dialog.show)

        enter_coeff_dialog_reference = EnterCoeffDialog(self, RealTimePlot.REFERENCE)
        calibrate_reference_wavelength_coeff = calibrate_reference_wavelength.addAction("Enter coefficients")
        calibrate_reference_wavelength_coeff.triggered.connect(enter_coeff_dialog_reference.open)
        # End region

        # Help menu
        help_menu = MenuButton("Help")

        # Window button container
        button_container = QHBoxLayout()

        # Minimize button
        minimize_button = WindowHandleButton(QIcon("./res/icons/minimize.png"), QIcon("./res/icons/minimize_hover.png"), QSize(46, 40))
        minimize_button.clicked.connect(self.showMinimized)
        button_container.addWidget(minimize_button)

        # Fullscreen button

        fullscreen_toggle = FullscreenToggleButton(
            self,
            QIcon("./res/icons/fullscreen.png"),
            QIcon("./res/icons/fullscreen_hover.png"),
            QIcon("./res/icons/restore_down.png"),
            QIcon("./res/icons/restore_down_hover.png"),
            QSize(46, 40)
        )
        button_container.addWidget(fullscreen_toggle)

        # Close button
        close_button = WindowHandleButton(QIcon("./res/icons/close.png"), QIcon("./res/icons/close_hover.png"), QSize(46, 40))
        close_button.clicked.connect(self.close)
        button_container.addWidget(close_button)

        # Add menu items
        menu_button_container_inner.addWidget(file_menu)
        menu_button_container_inner.addWidget(view_menu)
        menu_button_container_inner.addWidget(tools_menu)
        menu_button_container_inner.addWidget(help_menu)

        menu_button_container_outer.addLayout(menu_button_container_inner)
        menu_button_container_outer.addStretch()

        menu_container.addLayout(menu_button_container_outer)
        menu_container.addWidget(MoveWindowSpacer(self))
        menu_container.addLayout(button_container)
        menu_widget.setLayout(menu_container)

        self.setMenuWidget(menu_widget)


    def toggle_toolbar(self):
        _ = self.toolbar.show() if self.toolbar.isHidden() else self.toolbar.hide()

    def create_toolbar(self):
        self.toolbar.setMovable(False)
        self.toolbar.setIconSize(QSize(20, 20))
        self.addToolBar(self.toolbar)

        self.toolbar.addWidget(FixedSizeSpacer(width=10))

        self.toolbar.addAction(ToolbarButton(QIcon("./res/icons/save.png"), "Save spectrum", self, callback=self.save_dialog.open))
        self.toolbar.addAction(ToolbarButton(QIcon("./res/icons/notepad.png"), "Save as CSV", self, callback=self.csv_save_dialog.open))
        self.toolbar.addAction(ToolbarButton(QIcon("./res/icons/txtpad.png"), "Save as TXT", self, callback=self.txt_save_dialog.open))

        self.toolbar.addSeparator()

        def grab_frames_continuous():
            self.camera.stop_spectrum_grab()
            self.camera.grab_spectrum_frames()

        play_stop_button = PlayStopButton("Acquire continuous spectrum", self, grab_frames_continuous, self.camera.stop_spectrum_grab)
        self.toolbar.addAction(play_stop_button)

        def grab_one_frame():
            play_stop_button.set_stopped()
            self.camera.stop_spectrum_grab()
            self.camera.grab_spectrum_frames(1)

        self.toolbar.addAction(ToolbarButton(QIcon("./res/icons/camera.png"),"Acquire frame", self, callback=grab_one_frame))
        self.toolbar.addAction(ToolbarButton(QIcon("./res/icons/background.png"), "Take background", self, callback=grab_one_frame))

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

    def load_spectrum(self, wavelengths, intensities, graph_selector: int):
        self.plot.set_raw_data(wavelengths, intensities, graph_selector)

    def save_settings(self):
        pass


def load_stylesheet(fname: str):
    with open(os.path.join("./res/stylesheets", fname)) as file:
        return file.read()

class PlotContainer(QWidget):
    def __init__(self, plot: RealTimePlot, camera: LineCamera):
        super().__init__()
        self.plot = plot
        self.camera = camera
        plot_container_layout = QVBoxLayout()

        plot_container_layout.addWidget(self.plot)

        # Master controls container
        master_controls_container = QHBoxLayout()

        # Region primary plot controls
        # Controls container
        primary_controls_box = QWidget()
        primary_controls_box.setObjectName("primary-controls-box")
        primary_controls_container = QVBoxLayout()
        primary_label_container = QHBoxLayout()
        primary_label_container.addWidget(QLabel("Primary graph controls"))
        primary_label_container.addStretch()
        primary_controls_container.addLayout(primary_label_container)
        primary_controls_box.setLayout(primary_controls_container)

        # Crosshair readout
        primary_crosshair_readout_container = QHBoxLayout()
        primary_crosshair_readout_container.addWidget(plot.get_primary_crosshair_readout())
        primary_crosshair_readout_container.addStretch()

        primary_controls_container.addLayout(primary_crosshair_readout_container)

        # Primary x axis bounds
        primary_x_bounds_container = QHBoxLayout()
        primary_x_bounds_container.addWidget(self.plot.get_primary_x_min_readout())
        primary_x_bounds_container.addWidget(self.plot.get_primary_x_max_readout())
        primary_x_bounds_container.addStretch()
        primary_controls_container.addLayout(primary_x_bounds_container)

        # Primary y axis bounds
        primary_y_bounds_container = QHBoxLayout()
        primary_y_bounds_container.addWidget(self.plot.get_primary_y_min_control())
        primary_y_bounds_container.addWidget(self.plot.get_primary_y_max_control())
        primary_y_bounds_container.addStretch()
        primary_controls_container.addLayout(primary_y_bounds_container)

        # Unit control
        primary_unit_control_container = QHBoxLayout()
        unit_control = plot.get_primary_unit_control()
        primary_unit_control_container.addWidget(unit_control)
        primary_controls_container.addLayout(primary_unit_control_container)
        primary_unit_control_container.addStretch()

        primary_controls_box.setFixedSize(QSize(300, 200))
        # End region

        # Region reference plot controls
        # Reference controls box
        reference_controls_box = QWidget()
        reference_controls_box.setObjectName("reference-controls-box")
        reference_controls_container = QVBoxLayout()
        reference_label_container = QHBoxLayout()
        reference_label_container.addWidget(QLabel("Reference graph controls"))
        reference_label_container.addStretch()
        reference_controls_container.addLayout(reference_label_container)
        reference_controls_box.setLayout(reference_controls_container)

        # Crosshair readout
        reference_crosshair_readout_container = QHBoxLayout()
        reference_crosshair_readout_container.addWidget(plot.get_reference_crosshair_readout())
        reference_crosshair_readout_container.addStretch()

        reference_controls_container.addLayout(reference_crosshair_readout_container)

        # Reference x axis bounds
        reference_x_bounds_container = QHBoxLayout()
        reference_x_bounds_container.addWidget(self.plot.get_reference_x_min_control())
        reference_x_bounds_container.addWidget(self.plot.get_reference_x_max_control())
        reference_x_bounds_container.addStretch()
        reference_controls_container.addLayout(reference_x_bounds_container)

        # Reference y axis bounds
        reference_y_bounds_container = QHBoxLayout()
        reference_y_bounds_container.addWidget(self.plot.get_reference_y_min_control())
        reference_y_bounds_container.addWidget(self.plot.get_reference_y_max_control())
        reference_y_bounds_container.addStretch()
        reference_controls_container.addLayout(reference_y_bounds_container)

        reference_controls_container.addWidget(FixedSizeSpacer(height=5))
        constrain_reference_x_button = SimpleButton("Align x", plot.constrain_reference_x)
        reference_controls_container.addWidget(constrain_reference_x_button)

        # Unit control
        reference_unit_control_container = QHBoxLayout()
        reference_unit_control = plot.get_reference_unit_control()
        reference_unit_control_container.addWidget(reference_unit_control)
        reference_controls_container.addLayout(reference_unit_control_container)
        reference_unit_control_container.addStretch()

        reference_controls_box.setFixedSize(QSize(300, 200))
        # End region

        def set_exposure(text: str):
            try:
                exposure = int(float(text))
            except ValueError:
                return

            self.camera.set_exposure_ms(exposure)

        exposure_time_edit = LabeledLineEdit("Exposure time (ms):", on_edit=set_exposure, max_text_width=75, text=f"{camera.get_exposure_ms():.0f}")


        master_controls_container.addWidget(primary_controls_box)
        master_controls_container.addWidget(reference_controls_box)
        master_controls_container.addWidget(exposure_time_edit)
        master_controls_container.addStretch()
        plot_container_layout.addLayout(master_controls_container)
        plot_container_layout.addWidget(self.plot.get_selection_control())
        plot_container_layout.addWidget(self.plot.get_selection_control())

        self.setLayout(plot_container_layout)


class MapInput(QWidget):
    def __init__(self, parent_layout: QLayout, removable=True):
        super().__init__()
        self.parent_layout = parent_layout
        self.removable = removable
        layout = QHBoxLayout()
        self.pixel_input = LabeledLineEdit("Pixel:")
        layout.addWidget(self.pixel_input)

        layout.addWidget(FixedSizeSpacer(width=20))

        self.wl_input = LabeledLineEdit("Wavelength:", max_text_width=90)
        layout.addWidget(self.wl_input)

        if removable:
            layout.addWidget(FixedSizeSpacer(width=20))

            delete_button = IconButton(QIcon("./res/icons/trash.png"), self.clear)
            delete_button.setFixedSize(QSize(20, 20))
            layout.addWidget(delete_button)

        layout.addStretch()
        self.setLayout(layout)

    def get_pixel(self):
        return self.pixel_input.get_int()

    def get_wavelength(self):
        return self.wl_input.get_float()

    def clear(self):
        if self.removable:
            self.hide()
            self.parent_layout.removeWidget(self)
        else:
            self.pixel_input.set_text("")
            self.wl_input.set_text("")


# noinspection PyShadowingNames
class MaxPixelsDialog(Dialog):
    def __init__(self, parent: Window, graph_type: int = RealTimePlot.PRIMARY):
        super().__init__(parent, "Map pixels to wavelengths")

        self.graph_type = graph_type
        self.parent = parent

        layout = QVBoxLayout()

        map_container = QScrollArea()
        map_container.setWidgetResizable(True)
        map_container.setFixedSize(QSize(400, 175))
        self.container_widget = QWidget()
        self.container_widget.setObjectName("map-pixels-container")
        map_container_layout = QVBoxLayout()
        self.container_widget.setLayout(map_container_layout)
        map_container.setWidget(self.container_widget)
        layout.addWidget(map_container)

        def load_map():
            fname, _ = QFileDialog.getOpenFileName(filter="CSV Files (*.csv)")
            if not fname:
                return
            try:
                pixels, wavelengths = load_waves(fname)
                map_widgets = self.get_map_inputs()

                i = 0
                while i < len(pixels):
                    if i < len(map_widgets):
                        map_widget = map_widgets[i]
                    else:
                        map_widget = MapInput(map_container_layout, removable=True)
                        map_container_layout.addWidget(map_widget)

                    map_widget.pixel_input.set_text(f"{pixels[i]:.0f}")
                    map_widget.wl_input.set_text(str(wavelengths[i]))
                    i += 1
                while i < len(map_widgets): # If there are still map widgets beyond amount needed to load the map, delete them
                    map_widgets[i].clear()
                    i += 1

            except IOError:
                ErrorDialog("Could not read the file.  Check that it exists and is in the correct format.", width=400)
                return
            except Exception as e:
                ErrorDialog(e, width=400)
                return

        def save_map():
            fname, _ = QFileDialog.getSaveFileName(filter="CSV Files (*.csv)")
            if not fname:
                return
            try:
                map_widgets = self.get_map_inputs()
                pixels, wavelengths = np.zeros(len(map_widgets)), np.zeros(len(map_widgets))
                for i in range(len(map_widgets)):
                    pixels[i] = map_widgets[i].get_pixel()
                    wavelengths[i] = map_widgets[i].get_wavelength()

                save_waves(fname, pixels, wavelengths)

            except IOError:
                ErrorDialog("Could not save file.  Check that it is not already open in another program.", width=400)
                return
            except ValueError:
                return
            except RuntimeError as e:
                ErrorDialog(e, width=400)

        load_map_button = SimpleButton("Load map", load_map)
        save_map_button = SimpleButton("Save map", save_map)

        load_save_container = QHBoxLayout()
        load_save_container.addWidget(load_map_button)
        load_save_container.addWidget(save_map_button)
        load_save_container.addStretch()

        def add_map_item():
            map_container_layout.addWidget(MapInput(map_container_layout, removable=True))

        def clear_map():
            for map_widget in self.get_map_inputs():
                map_widget.clear()

        add_map_button = SimpleButton("Add map item", add_map_item)
        clear_map_button = SimpleButton("Clear", clear_map)

        button_container = QHBoxLayout()
        button_container.addWidget(add_map_button)
        button_container.addWidget(clear_map_button)
        button_container.addStretch()
        layout.addStretch()
        layout.addLayout(button_container)
        layout.addLayout(load_save_container)
        layout.addStretch()

        math_container = QVBoxLayout()

        equation_widget = TeXWidget(text = "$y = a_0 + a_1 x + a_2 x^2 + a_3 x^3$", width=250, height=40)
        math_container.addWidget(equation_widget)

        coeff_container_outer = QHBoxLayout()
        coeff_container = QVBoxLayout()
        self.coeff_widgets = [CopyableCoefficient(f"a_{i}", 0, TeXWidget(width=250, height=40)) for i in range(4)]
        [coeff_container.addWidget(coeff_label) for coeff_label in self.coeff_widgets]
        coeff_container_outer.addLayout(coeff_container)
        coeff_container_outer.addStretch()

        math_container.addLayout(coeff_container_outer)

        map_button = SimpleButton("Calculate fit", self.calculate_fit)
        map_button_container = QHBoxLayout()
        map_button_container.addWidget(map_button)
        map_button_container.addStretch()
        layout.addLayout(map_button_container)

        layout.addLayout(math_container)

        close_button = SimpleButton("Close", self.close)
        close_button_container = QHBoxLayout()
        close_button_container.addStretch()
        close_button_container.addWidget(close_button)
        layout.addLayout(close_button_container)

        layout.setContentsMargins(10, 10, 10, 10)

        for i in range(2):
            map_container_layout.addWidget(MapInput(map_container_layout, removable=False))

        self.set_main_layout(layout)

    def show(self):
        super().show()
        self.setFixedSize(self.size())
        self.display_coefficients()

    def display_coefficients(self):
        coefficients = self.parent.plot.get_primary_graph().get_fitting_params()
        for i in range(len(coefficients)):
            self.coeff_widgets[i].set_value(coefficients[i])

    def get_map_inputs(self) -> list:
        map_inputs = []
        for map_input in self.container_widget.findChildren(MapInput):
            if not map_input.isHidden():
                map_inputs.append(map_input)

        return map_inputs

    def calculate_fit(self):
        try:
            x_data = []
            y_data = []
            for widget in self.get_map_inputs():
                x_data.append(widget.get_pixel())
                y_data.append(widget.get_wavelength())

            self.parent.plot.fit(x_data, y_data, self.graph_type)
            self.display_coefficients()
        except ValueError:
            return
        except Exception as e:
            ErrorDialog(str(e), width=400)

class EnterCoeffDialog(Dialog):
    def __init__(self, parent: Window, graph_type: int):
        super().__init__(parent, title="Enter calibration coefficients")
        self.parent = parent
        self.graph_type = graph_type
        layout = QVBoxLayout()

        equation_widget = TeXWidget(text = "$y = a_0 + a_1 x + a_2 x^2 + a_3 x^3$", width=250, height=40)
        layout.addWidget(equation_widget)

        self.entries = []
        for i in range(4):
            container = QHBoxLayout()
            container.addWidget(TeXWidget(f"$a_{i}:$", width=30, height = 40))
            entry = QLineEdit()
            entry.setFixedWidth(150)
            self.entries.append(entry)
            container.addWidget(entry)
            container.addStretch()
            layout.addLayout(container)

        close_button = SimpleButton("Calculate fit", self.calculate_fit)
        bottom_hbox = QHBoxLayout()
        bottom_hbox.addStretch()
        bottom_hbox.addWidget(close_button)
        layout.addStretch()
        layout.addLayout(bottom_hbox)

        layout.setContentsMargins(10, 10, 10, 10)
        self.set_main_layout(layout)

    def open(self):
        super().open()
        current_coefficients = self.parent.plot.get_graph(self.graph_type).get_fitting_params()
        for i in range(len(self.entries)):
            value = current_coefficients[i]
            self.entries[i].setText(format_number(value, decimal_places=12))

    def calculate_fit(self):
        try:
            coefficients = []
            for entry in self.entries:
                coeff = float(entry.text())
                coefficients.append(coeff)
            self.parent.plot.set_coefficients(tuple(coefficients), self.graph_type)
            self.close()
        except ValueError:
            ErrorDialog("Please enter valid numbers for each entry.")
        except Exception as e:
            ErrorDialog(str(e), width=400)


class SaveFileDialog(Dialog):
    # noinspection PyUnresolvedReferences
    def __init__(self, parent: Window, ask_for_delimiter=True, title="Save spectrum", dialog_filter="All Files (*.*)"):
        super().__init__(parent, title)
        self.parent = parent

        layout = QVBoxLayout()

        if ask_for_delimiter:
            self.delimiter_input = LabeledLineEdit("Delimiter:", max_text_width=25, text=",")
            layout.addWidget(self.delimiter_input)
        else:
            self.delimiter_input = None

        prefix = "\n" if ask_for_delimiter else ""
        label = QLabel(prefix + "Column 0: Pixel value\n\nColumn 1: Calibrated wavelength value\n\nColumn 2: Intensity\n")
        layout.addWidget(label)

        self.file_input = FileInput(dialog_filter=dialog_filter, is_save_file=True)

        layout.addWidget(self.file_input)

        save_button = SimpleButton("Save", self.on_close)

        bottom_hbox = QHBoxLayout()
        bottom_hbox.addStretch()
        bottom_hbox.addWidget(save_button)
        layout.addStretch()
        layout.addLayout(bottom_hbox)

        layout.setContentsMargins(10, 10, 10, 10)
        self.set_main_layout(layout)

    def open(self):
        super().open()
        self.setFixedSize(self.size())

    def on_close(self):
        try:
            pixels, wavelengths, intensities = self.parent.plot.get_primary_data()
            if self.delimiter_input:
                delimiter = self.delimiter_input.get_text()
                if not delimiter:
                    delimiter = ","
            else:
                delimiter = ","

            save_waves(self.file_input.get_chosen_fname(), pixels, wavelengths, intensities, delimiter=delimiter)
            self.close()

        except ValueError:
            return


class LoadSpectrumDialog(Dialog):
    def __init__(self, parent: Window, graph_selector):
        super().__init__(parent, "Load primary spectrum" if graph_selector == RealTimePlot.PRIMARY else "Load reference spectrum")
        self.parent = parent
        self.graph_selector = graph_selector
        self.setObjectName("load-spectrum-dialog")

        layout = QVBoxLayout()

        self.delimiter_input = LabeledLineEdit("Delimiter:", max_text_width=25, text=",")
        layout.addWidget(self.delimiter_input)
        self.row_start_input = LabeledLineEdit("Start at row:", max_text_width=35, text="22")
        layout.addWidget(self.row_start_input)
        self.wavelength_column_input = LabeledLineEdit("Wavelength column:", max_text_width=35, text="0")
        layout.addWidget(self.wavelength_column_input)
        self.intensity_column_input = LabeledLineEdit("Intensity column:", max_text_width=35, text="2")
        layout.addWidget(self.intensity_column_input)
        self.file_input = FileInput()
        layout.addWidget(self.file_input)

        load_button = SimpleButton("Load", self.on_close)

        bottom_hbox = QHBoxLayout()
        bottom_hbox.addStretch()
        bottom_hbox.addWidget(load_button)
        layout.addStretch()
        layout.addLayout(bottom_hbox)

        layout.setContentsMargins(10, 10, 10, 10)
        self.set_main_layout(layout)

    def open(self):
        super().open()
        self.setFixedSize(self.size())

    def on_close(self):
        try:
            fname = self.file_input.get_chosen_fname()

            row_start = self.row_start_input.get_int()
            wavelength_col = self.wavelength_column_input.get_int()
            intensity_col = self.intensity_column_input.get_int()

            wavelengths, intensities = load_waves(fname, row_start=row_start, x_col=wavelength_col, y_col=intensity_col, delimiter=self.delimiter_input.get_text())
            self.parent.load_spectrum(wavelengths, intensities, self.graph_selector)
            self.close()
        except ValueError:
            return


class DownloadFromNISTDialog(Dialog):
    def __init__(self, parent: Window):
        super().__init__(parent, "Download from NIST")
        self.parent = parent
        self.setObjectName("load-spectrum-dialog")

        layout = QVBoxLayout()

        self.element_input = LabeledLineEdit("Element:", max_text_width=30)
        layout.addWidget(self.element_input)

        self.start_wl_input = LabeledLineEdit("Start wavelength:", max_text_width=35)
        layout.addWidget(self.start_wl_input)

        self.end_wl_input = LabeledLineEdit("End wavelength:", max_text_width=35)
        layout.addWidget(self.end_wl_input)

        self.fwhm_input = LabeledLineEdit("Full width half max:", max_text_width=35)
        layout.addWidget(self.fwhm_input)

        self.intensity_fraction_input = LabeledLineEdit("Intensity fraction:", max_text_width=35)
        layout.addWidget(self.intensity_fraction_input)

        self.file_input = FileInput(label_text="Save to:", is_save_file=True, dialog_filter="TXT File (*.txt)")
        layout.addWidget(self.file_input)

        load_button = SimpleButton("Load", self.on_close)

        bottom_hbox = QHBoxLayout()
        bottom_hbox.addStretch()
        bottom_hbox.addWidget(load_button)
        layout.addStretch()
        layout.addLayout(bottom_hbox)

        layout.setContentsMargins(10, 10, 10, 10)
        self.set_main_layout(layout)

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

            fetch_nist_data(end_wavelength, start_wavelength, element, fpath)
            wavelengths, intensities = read_nist_data(fpath, start_wavelength, end_wavelength, intensity_fraction, full_width_half_max)
            self.parent.load_spectrum(wavelengths, intensities, RealTimePlot.REFERENCE)

            self.close()
        except ValueError:
            return
        except TimeoutError:
            ErrorDialog("The connection timed out.  Check your internet connection.")
        except AttributeError as e:
            print(e)
            ErrorDialog("NIST could not generate a spectrum based on your inputs.")


class OpenFromNISTDialog(Dialog):
    def __init__(self, parent: Window):
        super().__init__(parent, "Open from NIST")
        self.parent = parent
        self.setObjectName("load-spectrum-dialog")

        layout = QVBoxLayout()

        self.start_wl_input = LabeledLineEdit("Start wavelength:", max_text_width=35, text="400")
        layout.addWidget(self.start_wl_input)

        self.end_wl_input = LabeledLineEdit("End wavelength:", max_text_width=35, text="700")
        layout.addWidget(self.end_wl_input)

        self.fwhm_input = LabeledLineEdit("Full width half max:", max_text_width=35, text="1")
        layout.addWidget(self.fwhm_input)

        self.intensity_fraction_input = LabeledLineEdit("Intensity fraction:", max_text_width=35, text="0.3")
        layout.addWidget(self.intensity_fraction_input)

        self.file_input = FileInput(label_text="File:", dialog_filter="TXT File (*.txt)")
        layout.addWidget(self.file_input)

        load_button = SimpleButton("Load", self.on_close)

        bottom_hbox = QHBoxLayout()
        bottom_hbox.addStretch()
        bottom_hbox.addWidget(load_button)
        layout.addStretch()
        layout.addLayout(bottom_hbox)

        layout.setContentsMargins(10, 10, 10, 10)
        self.set_main_layout(layout)

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
            self.parent.load_spectrum(wavelengths, intensities, RealTimePlot.REFERENCE)

            self.close()
        except ValueError:
            return
        except AttributeError:
            ErrorDialog("NIST could not generate a spectrum based on your inputs")


