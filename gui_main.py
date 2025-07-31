import traceback

import numpy as np
from PyQt6.QtCore import QPropertyAnimation, QEasingCurve
from PyQt6.QtWidgets import *
from sympy import SympifyError
from sympy.core.backend import sympify

from app_widgets import *
from camera_engine.mtsse import LineCamera, Frame
from loadwaves import load_waves, fetch_nist_data, read_nist_data, save_waves
from plottools import DataHandler, RealTimePlot, IncompatibleSpectrumSizeError
from settings_manager import Settings
from utils import AnimationSequence, Animation, size_to_point

settings = Settings()

class Window(QMainWindow):
    _spectrometer_wl = 350
    _position = QPoint(0, 0)
    _size = QSize(1100, 700)
    _in_fullscreen = False
    _on_unminimize = None
    _enter_fullscreen_sequence = None
    _restore_down_sequence = None
    _minimize_sequence = None
    _unminimize_sequence = None
    _close_sequence = None

    def __init__(self, camera: LineCamera):
        super().__init__()
        self.animation_active = False

        self.setWindowFlag(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setWindowTitle("Mightex Manager")

        # Camera control
        self.camera = camera
        self.calibration_checkbox = CheckBox(initially_checked=True)

        # All things plotting
        self.plot = RealTimePlot(DataHandler(camera))
        self.coeff_calibrator = AutomaticCalibrator(self.plot)

        # Main layout
        self.central_widget = QWidget()
        self.central_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        transparent_bg(self.central_widget)

        self.main_widget = self.make_central_widget()
        self.main_widget.setParent(self.central_widget)

        #self.central_widget.setLayout(None)
        self.setCentralWidget(self.central_widget)
        self.main_widget.move(0, 0)

        self.cover = QWidget(self.central_widget)
        self.cover.hide()
        self.cover.setObjectName("cover")
        self.cover.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Create shared dialogs
        self.save_dialog = SaveFileDialog(self)
        self.csv_save_dialog = SaveFileDialog(self, ask_for_delimiter=False, dialog_filter="CSV Files (*.csv)")
        self.txt_save_dialog = SaveFileDialog(self, dialog_filter="Text Documents (*.txt)")

        # Menu
        self.create_menu()

        self.toolbar = QToolBar()
        self.create_toolbar()

        self.resize(self._size)
        self.resize_central_widgets()
        self.event_filter = ClearFocusFilter()
        self.installEventFilter(self.event_filter)

    def changeEvent(self, event):
        if event.type() == QEvent.Type.WindowStateChange:
            if event.oldState() & Qt.WindowState.WindowMinimized:
                if self._on_unminimize:
                    self._on_unminimize()
        super().changeEvent(event)

    def resizeEvent(self, event):
        self.resize_central_widgets()
        self.plot.redraw()

    def resize_central_widgets(self):
        size = self.central_widget.size()
        self.main_widget.resize(size)
        self.cover.resize(size)

    def show(self):
        super().show()
        self._position = self.pos()
        self.resize_central_widgets()

    def move(self, position: QPoint):
        if self._in_fullscreen:
            return
        super().move(position)
        if not self._in_fullscreen:
            self._position = position


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
        primary_spectrum_dialog = LoadDisplayableSpectrumDialog(self, RealTimePlot.PRIMARY)
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

        secondary_spectrum_dialog = LoadDisplayableSpectrumDialog(self, RealTimePlot.REFERENCE)
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

        coeff_equation_dialog = CoeffEquationDialog(self)
        coeff_equation = calibrate_primary_wavelength.addAction("Enter coefficient equations")
        coeff_equation.triggered.connect(coeff_equation_dialog.open)
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

        # Region load background
        load_background_dialog = LoadBackgroundDialog(self)
        load_background = tools_menu.add_action(QAction("Load background"))
        load_background.triggered.connect(load_background_dialog.open)
        # End region

        # Help menu
        help_menu = MenuButton("Help")

        # Window button container
        button_container = self.create_window_handle_buttons()

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

    # noinspection PyUnresolvedReferences
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

        def take_background():
            def receive_background(frame: Frame):
                self.plot.set_background(frame.raw_data[1])
                self.camera.remove_callback(receive_background)
            self.camera.add_frame_callback(receive_background)
            grab_one_frame()

        self.toolbar.addAction(ToolbarButton(QIcon("./res/icons/background.png"), "Take background", self, callback=take_background))

    def make_central_widget(self):
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
        primary_label_container.addWidget(TitleLabel("Primary graph controls"))
        primary_label_container.addStretch()
        primary_controls_container.addLayout(primary_label_container)
        primary_controls_container.addStretch()
        primary_controls_box.setLayout(primary_controls_container)

        # Crosshair readout
        primary_crosshair_readout_container = QHBoxLayout()
        primary_crosshair_readout_container.addWidget(self.plot.get_primary_crosshair_readout())
        primary_crosshair_readout_container.addStretch()
        primary_controls_container.addLayout(primary_crosshair_readout_container)
        primary_controls_container.addWidget(FixedSizeSpacer(height=3))

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

        # Autoscale button
        primary_controls_container.addWidget(FixedSizeSpacer(height=5))
        primary_autoscale_y = SimpleButton("Autoscale y", lambda: self.plot.autoscale_graph(RealTimePlot.PRIMARY))
        primary_controls_container.addWidget(primary_autoscale_y)

        # Unit control
        primary_unit_control_container = QHBoxLayout()
        unit_control = self.plot.get_primary_unit_control()
        primary_unit_control_container.addWidget(unit_control)
        primary_controls_container.addLayout(primary_unit_control_container)
        primary_unit_control_container.addStretch()

        primary_controls_box.setFixedSize(QSize(300, 250))

        # End region

        # Region reference plot controls
        # Reference controls box
        reference_controls_box = QWidget()
        reference_controls_box.setObjectName("reference-controls-box")
        reference_controls_container = QVBoxLayout()
        reference_label_container = QHBoxLayout()
        reference_label_container.addWidget(TitleLabel("Reference graph controls"))
        reference_label_container.addStretch()
        reference_controls_container.addLayout(reference_label_container)
        reference_controls_container.addStretch()
        reference_controls_box.setLayout(reference_controls_container)

        # Crosshair readout
        reference_crosshair_readout_container = QHBoxLayout()
        reference_crosshair_readout_container.addWidget(self.plot.get_reference_crosshair_readout())
        reference_crosshair_readout_container.addStretch()
        reference_controls_container.addLayout(reference_crosshair_readout_container)
        reference_controls_container.addWidget(FixedSizeSpacer(height=3))

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

        reference_axes_control_container = QHBoxLayout()
        reference_autoscale_y = SimpleButton("Align x", self.plot.constrain_reference_x)
        reference_axes_control_container.addWidget(reference_autoscale_y)

        reference_autoscale_x = SimpleButton("Autoscale x", lambda: self.plot.get_graph(RealTimePlot.REFERENCE).update_x_bounds())
        reference_axes_control_container.addWidget(reference_autoscale_x)

        reference_autoscale_y = SimpleButton("Autoscale y", lambda: self.plot.autoscale_graph(RealTimePlot.REFERENCE))
        reference_axes_control_container.addWidget(reference_autoscale_y)

        reference_controls_container.addLayout(reference_axes_control_container)

        # Unit control
        reference_unit_control_container = QHBoxLayout()
        reference_unit_control = self.plot.get_reference_unit_control()
        reference_unit_control_container.addWidget(reference_unit_control)
        reference_controls_container.addLayout(reference_unit_control_container)
        reference_unit_control_container.addStretch()

        reference_controls_box.setFixedSize(QSize(300, 250))
        # End region

        # Region camera controls

        right_box_container = QVBoxLayout()

        # Reference controls box
        camera_controls_box = QWidget()
        camera_controls_box.setObjectName("camera-controls-box")
        camera_controls_container = QVBoxLayout()
        camera_label_container = QHBoxLayout()
        camera_label_container.addWidget(TitleLabel("Data acquisition"))
        camera_label_container.addStretch()
        camera_controls_container.addLayout(camera_label_container)
        camera_controls_container.addStretch()
        camera_controls_box.setLayout(camera_controls_container)



        # Region calibration
        center_wl_input_container = QHBoxLayout()

        def wavelength_edited(text: str):
            try:
                wavelength = float(text)
                self._spectrometer_wl = wavelength
                self.coeff_calibrator.calibrate(wavelength)
            except ValueError:
                pass

        center_wl_input = Entry("Spectrometer wavelength (nm)", on_edit=wavelength_edited)
        center_wl_input_container.addWidget(center_wl_input)
        center_wl_input_container.addStretch()
        camera_controls_container.addLayout(center_wl_input_container)

        automatic_calibration_container = QHBoxLayout()
        calibration_label = QLabel("Automatic calibration")
        automatic_calibration_container.addWidget(calibration_label)
        automatic_calibration_container.addWidget(self.calibration_checkbox)
        automatic_calibration_container.addStretch()
        camera_controls_container.addLayout(automatic_calibration_container)
        # End region

        background_subtraction_container = QHBoxLayout()
        bg_label = QLabel("Subtract background")
        background_subtraction_container.addWidget(bg_label)
        bg_subtract_checkbox = CheckBox(initially_checked=False, callback=lambda subtract: self.plot.get_primary_graph().configure_bg_subtraction(subtract))
        background_subtraction_container.addWidget(bg_subtract_checkbox)
        background_subtraction_container.addStretch()
        camera_controls_container.addLayout(background_subtraction_container)


        def set_exposure(text: str):
            try:
                exposure = int(float(text))
            except ValueError:
                return

            self.camera.set_exposure_ms(exposure)


        exposure_time_edit = Entry("Exposure time (ms):", on_edit=set_exposure, max_text_width=75, text=f"{self.camera.get_exposure_ms():.0f}")
        camera_controls_container.addWidget(exposure_time_edit)

        camera_controls_box.setFixedSize(QSize(300, 174))

        selection_box = QWidget()
        selection_box.setObjectName("selection-box")
        selection_container = QVBoxLayout()
        selection_label_container = QHBoxLayout()
        selection_label_container.addWidget(TitleLabel("Selected graph"))
        selection_container.addLayout(selection_label_container)
        selection_control = self.plot.get_selection_control()
        selection_control.setFixedHeight(35)
        selection_container.addWidget(selection_control)
        selection_box.setLayout(selection_container)
        selection_box.setFixedSize(QSize(300, 70))

        right_box_container.addWidget(camera_controls_box)
        right_box_container.addWidget(selection_box)
        # End region

        master_controls_container.addWidget(primary_controls_box)
        master_controls_container.addWidget(reference_controls_box)
        master_controls_container.addLayout(right_box_container)
        master_controls_container.addStretch()
        plot_container_layout.addLayout(master_controls_container)

        central_widget = QWidget()
        central_widget.setLayout(plot_container_layout)
        return central_widget

    def create_window_handle_buttons(self):

        button_container = QHBoxLayout()

        # Region property animations

        # Opacity
        content_opacity_effect = QGraphicsOpacityEffect(self)
        content_opacity_effect.setOpacity(1)
        self.cover.setGraphicsEffect(content_opacity_effect)

        # Position
        position_animation = QPropertyAnimation(self, b"pos")  # A string literal preceded by 'b' creates a byte array representing the ASCII string
        position_animation.setDuration(100)
        position_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        size_animation = QPropertyAnimation(self, b"size")
        size_animation.setDuration(100)
        size_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        # Enter fullscreen animation
        fade_content_animation = QPropertyAnimation(content_opacity_effect, b"opacity")
        fade_content_animation.setDuration(50)
        fade_content_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        fade_window_animation = QPropertyAnimation(self, b"windowOpacity")
        fade_window_animation.setDuration(50)
        fade_window_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        # End region


        # Region universal prep functions
        def prep_content_fadeout():
            content_opacity_effect.setOpacity(0)
            fade_content_animation.setStartValue(0)
            fade_content_animation.setEndValue(1)
            self.cover.show()

        def prep_content_fadein():
            fade_content_animation.setStartValue(1)
            fade_content_animation.setEndValue(0)
            self.cover.show()
            self.plot.enable_redrawing()
            self.main_widget.show()

        def finish_fadein():
            self.cover.hide()
        # End region

        # Region minimize button
        def prep_minimize_resize():
            self.main_widget.hide()
            self.cover.hide()
            self.plot.suppress_redrawing()
            position_animation.setDuration(200)
            size_animation.setDuration(200)
            start_size = self.size()
            end_size = QSize(640, 400)
            start_position = self.pos()
            position_animation.setStartValue(start_position)
            screen_geometry = self.screen().availableGeometry()
            position_animation.setEndValue(QPoint(
                screen_geometry.x() + int(screen_geometry.width() / 2) - int(end_size.width() / 2),
                screen_geometry.y() + screen_geometry.height() - end_size.height())
            )
            size_animation.setStartValue(start_size)
            size_animation.setEndValue(end_size)
            fade_window_animation.setStartValue(1)
            fade_window_animation.setEndValue(0)
            fade_window_animation.setDuration(300)

        def prep_unminimize_fadein():
            self.main_widget.hide()
            self.cover.hide()
            self.plot.suppress_redrawing()
            position_animation.setDuration(200)
            size_animation.setDuration(200)

            start_size = self.size()
            start_position = self.pos()
            if self._in_fullscreen:
                screen_geometry = self.screen().availableGeometry()
                end_position = screen_geometry.topLeft()
                end_size = screen_geometry.size()
            else:
                end_position = self._position
                end_size = self._size

            position_animation.setStartValue(start_position)
            position_animation.setEndValue(end_position)
            size_animation.setStartValue(start_size)
            size_animation.setEndValue(end_size)
            fade_window_animation.setStartValue(0)
            fade_window_animation.setEndValue(1)
            fade_window_animation.setDuration(200)

        def finish_unminimize():
            self.cover.hide()
            self.plot.enable_redrawing()

        self._minimize_sequence = AnimationSequence(
            Animation((fade_content_animation,), before_start=prep_content_fadeout),
            Animation((size_animation, position_animation, fade_window_animation), before_start=prep_minimize_resize, on_finished=self.showMinimized)
        )

        self._unminimize_sequence = AnimationSequence(
            Animation((size_animation, position_animation, fade_window_animation), before_start=prep_unminimize_fadein),
            Animation((fade_content_animation, ), before_start=prep_content_fadein, on_finished=finish_unminimize)
        )
        self._on_unminimize = self._unminimize_sequence.start

        minimize_button = WindowHandleButton(QIcon("./res/icons/minimize.png"), QIcon("./res/icons/minimize_hover.png"), QSize(46, 40))
        minimize_button.clicked.connect(self._minimize_sequence.start)
        button_container.addWidget(minimize_button)
        # End region

        # Region fullscreen button
        def prep_fullscreen_resize():
            self.main_widget.hide()
            self.cover.hide()
            self.plot.suppress_redrawing()
            screen_geometry = self.screen().availableGeometry()
            position_animation.setStartValue(self.pos())
            position_animation.setEndValue(screen_geometry.topLeft())
            size_animation.setStartValue(self.size())
            size_animation.setEndValue(screen_geometry.size())

        def prep_restore_down_resize():
            self.main_widget.hide()
            self.cover.hide()
            self.plot.suppress_redrawing()
            position_animation.setStartValue(self.pos())
            position_animation.setEndValue(self._position)
            size_animation.setStartValue(self.size())
            size_animation.setEndValue(self._size)

        self._enter_fullscreen_sequence = AnimationSequence(
            Animation((fade_content_animation, ), before_start=prep_content_fadeout),
            Animation((size_animation, position_animation), before_start=prep_fullscreen_resize),
            Animation((fade_content_animation, ), before_start=prep_content_fadein, on_finished=finish_fadein)
        )

        self._restore_down_sequence = AnimationSequence(
            Animation((fade_content_animation,), before_start=prep_content_fadeout),
            Animation((size_animation, position_animation), before_start=prep_restore_down_resize),
            Animation((fade_content_animation,), before_start=prep_content_fadein, on_finished=finish_fadein)
        )

        def enter_fullscreen():
            self._in_fullscreen = True
            self._enter_fullscreen_sequence.start()

        def restore_down():
            self._in_fullscreen = False
            self._restore_down_sequence.start()

        fullscreen_toggle = FullscreenToggleButton(
            self,
            QSize(46, 40),
            enter_fullscreen,
            restore_down
        )
        button_container.addWidget(fullscreen_toggle)
        # End region

        # Region close button
        def prep_close_resize():
            self.main_widget.hide()
            self.cover.hide()
            self.plot.suppress_redrawing()
            position_animation.setDuration(200)
            size_animation.setDuration(200)
            start_size = self.size()
            end_size = QSize(320, 200)
            start_position = self.pos()
            position_animation.setStartValue(start_position)
            position_animation.setEndValue(start_position + 0.5 * size_to_point(start_size) - 0.5 * size_to_point(end_size))
            size_animation.setStartValue(start_size)
            size_animation.setEndValue(end_size)
            fade_window_animation.setStartValue(1)
            fade_window_animation.setEndValue(0)
            fade_window_animation.setDuration(300)

        self._close_sequence = AnimationSequence(
            Animation((fade_content_animation,), before_start=prep_content_fadeout),
            Animation((size_animation, position_animation, fade_window_animation), before_start=prep_close_resize, on_finished=self.close)
        )

        close_button = WindowHandleButton(QIcon("./res/icons/close.png"), QIcon("./res/icons/close_hover.png"), QSize(46, 40))
        close_button.clicked.connect(self._close_sequence.start)
        button_container.addWidget(close_button)
        # End region

        return button_container


    def load_spectrum(self, wavelengths, intensities, graph_selector: int):
        self.plot.set_raw_data(wavelengths, intensities, graph_selector)

    def get_spectrometer_wl(self):
        return self._spectrometer_wl


def load_stylesheet(fname: str):
    with open(os.path.join("./res/stylesheets", fname)) as file:
        return file.read()


class MapInput(QWidget):
    def __init__(self, parent_layout: QLayout, removable=True):
        super().__init__()
        self.parent_layout = parent_layout
        self.removable = removable
        layout = QHBoxLayout()
        self.pixel_input = Entry("Pixel:")
        layout.addWidget(self.pixel_input)

        layout.addWidget(FixedSizeSpacer(width=20))

        self.wl_input = Entry("Wavelength:", max_text_width=90)
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

        map_container = QScrollArea(self)
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

                save_waves(fname, (pixels, wavelengths))

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

class CoeffEquationDialog(Dialog):
    def __init__(self, parent: Window):
        super().__init__(parent, title="Enter equations")
        self.parent = parent
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Enter expressions for each calibration coefficient as a function of wavelength.\n'w' represents the spectrometer wavelength in nm."))

        equation_widget = TeXWidget(text="$y = a_0 + a_1 x + a_2 x^2 + a_3 x^3$", width=250, height=40)
        layout.addWidget(equation_widget)

        self.entries = []
        for i in range(4):
            container = QHBoxLayout()
            container.addWidget(TeXWidget(f"$a_{i} = $", width=30, height=40))
            entry = QLineEdit()
            entry.setFixedWidth(400)
            self.entries.append(entry)
            container.addWidget(entry)
            container.addStretch()
            layout.addLayout(container)

        close_button = SimpleButton("Apply", self.apply)
        bottom_hbox = QHBoxLayout()
        bottom_hbox.addStretch()
        bottom_hbox.addWidget(close_button)
        layout.addStretch()
        layout.addLayout(bottom_hbox)

        layout.setContentsMargins(10, 10, 10, 10)
        self.set_main_layout(layout)

    def apply(self):
        try:
            expressions = []
            for entry in self.entries:
                coeff_equation = entry.text()
                expressions.append(sympify(coeff_equation))

            self.parent.coeff_calibrator.set_expressions(expressions)
            self.parent.coeff_calibrator.calibrate(self.parent.get_spectrometer_wl())
            self.close()

        except SympifyError:
            ErrorDialog("Enter a valid equation.")
        except Exception as e:
            ErrorDialog(str(e), width=400)


class SaveFileDialog(Dialog):
    # noinspection PyUnresolvedReferences
    def __init__(self, parent: Window, ask_for_delimiter=True, title="Save spectrum", dialog_filter="All Files (*.*)"):
        super().__init__(parent, title)
        self.parent = parent

        layout = QVBoxLayout()

        if ask_for_delimiter:
            self.delimiter_input = Entry("Delimiter:", max_text_width=25, text=",")
            layout.addWidget(self.delimiter_input)
        else:
            self.delimiter_input = None

        prefix = "\n" if ask_for_delimiter else ""
        label = QLabel(prefix + "Column 0: Pixel values\n\nColumn 1: Calibrated wavelength values\n\nColumn 2: Intensities\n\nColumn 3: Background-subtracted intensities\n")
        layout.addWidget(label)

        self.file_input = FileInput(dialog_filter=dialog_filter, is_save_file=True)

        layout.addWidget(self.file_input)

        save_button = SimpleButton("Save", self.save)

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

    def save(self):
        try:
            pixels, wavelengths, intensities, bg_subtracted = self.parent.plot.get_primary_data()
            if self.delimiter_input:
                delimiter = self.delimiter_input.get_text()
                if not delimiter:
                    delimiter = ","
            else:
                delimiter = ","

            save_waves(self.file_input.get_chosen_fname(), (pixels, wavelengths, intensities, bg_subtracted), delimiter=delimiter)
            self.close()

        except ValueError as e:
            ErrorDialog(parent=self.parent, text=e)


class LoadSpectrumDialog(Dialog):
    def __init__(self, parent: Window, title: str):
        super().__init__(parent, title)
        self.parent = parent

        layout = QVBoxLayout()

        self.delimiter_input = Entry("Delimiter:", max_text_width=25, text=",")
        layout.addWidget(self.delimiter_input)
        self.row_start_input = Entry("Start at row:", max_text_width=35, text="21")
        layout.addWidget(self.row_start_input)
        self.wavelength_column_input = Entry("Wavelength column:", max_text_width=35, text="0")
        layout.addWidget(self.wavelength_column_input)
        self.intensity_column_input = Entry("Intensity column:", max_text_width=35, text="2")
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
        fname = self.file_input.get_chosen_fname()

        row_start = self.row_start_input.get_int()
        wavelength_col = self.wavelength_column_input.get_int()
        intensity_col = self.intensity_column_input.get_int()

        wavelengths, intensities = load_waves(fname, row_start=row_start, x_col=wavelength_col, y_col=intensity_col, delimiter=self.delimiter_input.get_text())

        return wavelengths, intensities

class LoadDisplayableSpectrumDialog(LoadSpectrumDialog):
    def __init__(self, parent: Window, graph_selector: int):
        super().__init__(parent, title="Load primary spectrum" if graph_selector == RealTimePlot.PRIMARY else "Load reference spectrum")
        self.graph_selector = graph_selector

    def on_close(self):
        # noinspection PyBroadException
        try:
            wavelengths, intensities = super().on_close()
            self.parent.load_spectrum(wavelengths, intensities, self.graph_selector)
            if self.graph_selector == RealTimePlot.PRIMARY:
                self.parent.plot.get_selection_control().check_primary()
            else:
                self.parent.plot.get_selection_control().check_reference()
            self.close()
        except ValueError:
            return
        except:
            ErrorDialog("An error occurred.  Check your inputs.")


class LoadBackgroundDialog(LoadSpectrumDialog):
    def __init__(self, parent: Window):
        super().__init__(parent, title="Load background")

    def on_close(self):
        # noinspection PyBroadException
        try:
            _, intensities = super().on_close()
            self.parent.plot.set_background(intensities)
            self.parent.plot.set_background_enabled(True)
            self.close()
        except IncompatibleSpectrumSizeError as e:
            ErrorDialog(e)
        except ValueError:
            return
        except:
            traceback.print_exc()
            ErrorDialog("An error occurred.  Check your inputs.")


class DownloadFromNISTDialog(Dialog):
    def __init__(self, parent: Window):
        super().__init__(parent, "Download from NIST")
        self.parent = parent
        self.setObjectName("load-spectrum-dialog")

        layout = QVBoxLayout()

        self.element_input = Entry("Element:", max_text_width=30)
        layout.addWidget(self.element_input)

        self.start_wl_input = Entry("Start wavelength:", max_text_width=35)
        layout.addWidget(self.start_wl_input)

        self.end_wl_input = Entry("End wavelength:", max_text_width=35)
        layout.addWidget(self.end_wl_input)

        self.fwhm_input = Entry("Full width half max:", max_text_width=35)
        layout.addWidget(self.fwhm_input)

        self.intensity_fraction_input = Entry("Intensity fraction:", max_text_width=35)
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
            self.parent.plot.get_selection_control().check_reference()

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

        self.start_wl_input = Entry("Start wavelength:", max_text_width=35, text="400")
        layout.addWidget(self.start_wl_input)

        self.end_wl_input = Entry("End wavelength:", max_text_width=35, text="700")
        layout.addWidget(self.end_wl_input)

        self.fwhm_input = Entry("Full width half max:", max_text_width=35, text="1")
        layout.addWidget(self.fwhm_input)

        self.intensity_fraction_input = Entry("Intensity fraction:", max_text_width=35, text="0.3")
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
            self.parent.plot.get_selection_control().check_reference()

            self.close()
        except ValueError:
            return
        except AttributeError:
            ErrorDialog("NIST could not generate a spectrum based on your inputs")

class AutomaticCalibrator:
    def __init__(self, plot: RealTimePlot):
        self.plot = plot
        self.coeff_expressions = []
        for i in range(4):
            self.coeff_expressions.append(sympify("1") if i == 1 else sympify("0"))

    def set_expressions(self, expressions: tuple | list):
        if len(expressions) != 4:
            raise ValueError
        self.coeff_expressions = expressions

    def evaluate(self, wavelength):
        coefficients = []
        for expression in self.coeff_expressions:
            coefficients.append(float(expression.subs("w", wavelength).evalf()))
        return tuple(coefficients)

    def calibrate(self, wavelength):
        self.plot.set_coefficients(self.evaluate(wavelength), RealTimePlot.PRIMARY)

class FullscreenAnimation:
    def __init__(self, parent: Window, on_start=None, on_finished=None, duration=125):
        self.parent = parent
        self.on_start = on_start

        self.position_animation = QPropertyAnimation(self.parent, b"pos")  # A string literal preceded by 'b' creates a byte array representing the ASCII string
        self.position_animation.setDuration(duration)
        self.position_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        self.size_animation = QPropertyAnimation(self.parent, b"size")  # A string literal preceded by 'b' creates a byte array representing the ASCII string
        self.size_animation.setDuration(duration)
        self.size_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        if on_finished:
            self.size_animation.finished.connect(on_finished)

    def play(self, start_pos: QPoint, end_pos: QPoint, start_size: QSize, end_size: QSize):
        self.position_animation.setStartValue(start_pos)
        self.position_animation.setEndValue(end_pos)

        self.size_animation.setStartValue(start_size)
        self.size_animation.setEndValue(end_size)

        if self.on_start:
            self.on_start()

        self.size_animation.start()
        self.position_animation.start()