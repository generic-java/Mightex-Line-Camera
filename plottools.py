import re

import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QLabel, QWidget, QVBoxLayout, QHBoxLayout
from matplotlib.artist import Artist
from matplotlib.axes import Axes
from matplotlib.backend_bases import FigureCanvasBase
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from scipy.optimize import curve_fit

from app_widgets import ArrowImmuneRadioButton, LabeledLineEdit
from camera_engine.mtsse import Frame, LineCamera, PIXELS


class BlitManager:
    """
    :source: https://matplotlib.org/stable/users/explain/animations/blitting.html
    """
    def __init__(self, canvas, animated_artists=()):
        """
        Parameters
        ----------
        canvas : FigureCanvasAgg
            The canvas to work with, this only works for subclasses of the Agg
            canvas which have the `~FigureCanvasAgg.copy_from_bbox` and
            `~FigureCanvasAgg.restore_region` methods.

        animated_artists : Iterable[Artist]
            List of the artists to manage
        """
        self.canvas = canvas
        self._background = None
        self._artists = []

        for artist in animated_artists:
            self.add_artist(artist)
        # grab the background on every draw
        canvas.mpl_connect("draw_event", self.on_draw)

    def on_draw(self, event):
        """Callback to register with 'draw_event'."""
        if event is not None:
            if event.canvas != self.canvas:
                raise RuntimeError
        self._background = self.canvas.copy_from_bbox(self.canvas.figure.bbox)
        self._draw_animated()

    def force_refresh(self):
        self.canvas.draw()

    def add_artist(self, artist):
        """
        Add an artist to be managed.

        Parameters
        ----------
        artist : Artist

            The artist to be added.  Will be set to 'animated' (just
            to be safe).  *artist* must be in the figure associated with
            the canvas this class is managing.

        """
        if artist.figure != self.canvas.figure:
            raise RuntimeError
        artist.set_animated(True)
        self._artists.append(artist)

    def _draw_animated(self):
        """Draw all the animated artists."""
        for a in self._artists:
            self.canvas.figure.draw_artist(a)

    def update(self):
        """Update the screen with animated artists."""
        # paranoia in case we missed the draw event
        if self._background is None:
            self.on_draw(None)
        else:
            # restore the background
            self.canvas.restore_region(self._background)
            # draw all the animated artists
            self._draw_animated()
            # update the GUI state
            self.canvas.blit(self.canvas.figure.bbox)
        # let the GUI event loop process anything it has to do
        self.canvas.flush_events()

def clamp(min_value, max_value, num):
    return min(max(min_value, num), max_value)


class DataHandler(QObject):
    _signal = pyqtSignal(Frame)

    def __init__(self, camera: LineCamera):
        super().__init__()
        camera.add_frame_callback(self._received_data)

    # noinspection PyUnresolvedReferences
    def _received_data(self, input_frame: Frame):
        self._signal.emit(input_frame)

    def get_signal(self):
        return self._signal

primary_fitting_params = (0, 1, 0, 0)
reference_fitting_params = (0, 1, 0, 0)

class AxisUnitType:
    PIXEL = 0
    WAVELENGTH = 1

    def __init__(self, unit_type):
        self.unit_type = unit_type

_primary_unit = AxisUnitType(AxisUnitType.PIXEL)
_reference_unit = AxisUnitType(AxisUnitType.WAVELENGTH)

class CrosshairReadout(QLabel):

    pixel_x = 0
    wl_x = 0
    y = 0

    def __init__(self, pixel_x: int, wl_x: float, y: int, unit: AxisUnitType):
        super().__init__()
        self.unit = unit
        self.update_values(pixel_x, wl_x, y)

    def update_values(self, pixel_x, wl_x, y: int):
        self.pixel_x = pixel_x
        self.wl_x = wl_x
        self.y = y
        self.display_values()

    def set_value_wl(self):
        pass

    def display_values(self):
        if self.unit.unit_type == AxisUnitType.PIXEL:
            self.set_text(self.pixel_x, self.y)
        else:
            self.set_text(f"{self.wl_x:.3f}", self.y)

    def set_text(self, x, y):
        self.setText(f"x: {x}\ny: {y}")


class Crosshair:
    index_x = 0
    index_y = 0
    x_line = None
    y_line = None
    x_multiplier = 1
    y_multiplier = 1

    def __init__(self, crosshair_readout: CrosshairReadout, canvas: FigureCanvasBase, axes: Axes, unit: AxisUnitType, size=50, color="white"):
        super().__init__()
        self.unit = unit
        self.crosshair_readout = crosshair_readout
        self.axes = axes
        self.size = size
        self.color = color
        self.vertical = Line2D([], [])
        axes.add_line(self.vertical)
        self.vertical.set_animated(True)
        self.vertical.set_color(color)
        self.horizontal = Line2D([], [])
        axes.add_line(self.horizontal)
        self.horizontal.set_animated(True)
        self.horizontal.set_color(color)
        self.set_position_indices(0, 0)

        canvas.mpl_connect("draw_event", self.on_resize)

    def set_position_indices(self, index_x, index_y):
        x_min, x_max = self.axes.get_xlim()
        y_min, y_max = self.axes.get_ylim()
        self.index_x = clamp(0, PIXELS, index_x)
        self.index_y = index_y
        self.crosshair_readout.update_values(self.index_x, cubic(self.index_x, *primary_fitting_params), self.index_y)
        display_x = clamp(x_min, x_max, cubic(index_x, *primary_fitting_params) if self.unit.unit_type == AxisUnitType.WAVELENGTH else index_x)
        display_y = clamp(y_min, y_max, index_y)
        extent_x = self.size / 2 * self.x_multiplier
        extent_y = self.size / 2 * self.y_multiplier
        vertical_y = np.arange(display_y - extent_y, display_y + extent_y, 0.1)
        self.vertical.set_data(display_x * np.ones_like(vertical_y), vertical_y)
        horizontal_x = np.arange(display_x - extent_x, display_x + extent_x, 0.1)
        self.horizontal.set_data(horizontal_x, display_y * np.ones_like(horizontal_x))

    def refresh(self):
        self.on_resize()
        self.set_position_indices(self.index_x, self.index_y)

    def get_position_indices(self):
        return self.index_x, self.index_y

    def on_resize(self, event=None):
        x_left, x_right = self.axes.get_xlim()
        y_bottom, y_top = self.axes.get_ylim()

        bbox = self.axes.get_window_extent()
        width_pixels, height_pixels = bbox.size
        self.x_multiplier = (x_right - x_left) / width_pixels
        self.y_multiplier = (y_top - y_bottom) / height_pixels
        self.set_position_indices(self.index_x, self.index_y)

    def get_artists(self):
        return self.vertical, self.horizontal

    def set_unit_type(self, unit_type: int):
        self.unit.unit_type = unit_type


class RealTimePlot(QWidget):

    style = {
        "background": "#343434",
        "color": "#6aee35"
    }

    PRIMARY = 0
    REFERENCE = 1

    def __init__(self, data_handler: DataHandler, **kwargs):
        super().__init__()
        self.selected_plot = RealTimePlot.PRIMARY
        self.primary_unit = _primary_unit
        self.reference_unit = _reference_unit
        self.style.update(kwargs)
        self.x = np.arange(0, PIXELS, 1)
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        vbox = QVBoxLayout()
        vbox.addWidget(self.canvas)
        self.setLayout(vbox)
        self.data_handler = data_handler
        # noinspection PyUnresolvedReferences
        self.data_handler.get_signal().connect(self.refresh)

        color = self.style["color"]

        self.primary_axes = self.figure.add_subplot()
        self.primary_axes.set_xlim(0, PIXELS)
        self.primary_axes.set_ylim(0, 65535)
        self.primary_axes.grid(True, color=color)

        self.reference_axes = self.figure.add_subplot()
        self.reference_axes.set_ylim(0, 1.2)

        self.figure.set_size_inches(12, 6)
        self.primary_line, = self.primary_axes.plot([], [])
        self.primary_data_raw = (np.array([]), np.array([]))
        self.reference_line, = self.reference_axes.plot([], [])
        self.reference_data = (np.array([]), np.array([]))

        # Primary crosshair readout
        self.primary_crosshair_readout = CrosshairReadout(0, 0, 0, self.primary_unit)

        # Primary crosshair
        self.primary_crosshair = Crosshair(self.primary_crosshair_readout, self.canvas, self.primary_axes, self.primary_unit)

        # Reference crosshair readout
        self.reference_crosshair_readout = CrosshairReadout(0, 0, 0, self.reference_unit)

        # Reference crosshair
        self.reference_crosshair = Crosshair(self.primary_crosshair_readout, self.canvas, self.reference_axes, self.reference_unit)

        # noinspection PyTypeChecker
        self.canvas.mpl_connect("button_press_event", self.onclick)

        # Primary unit control
        self.primary_unit_control = WavelengthPixelButton(self)

        # Reference unit control
        self.reference_unit_control = WavelengthPixelButton(self)

        # Primary y limits
        self.primary_y_min = LabeledLineEdit("Min y:", on_edit=self.relim_primary_y, max_text_width=75)
        self.primary_y_max = LabeledLineEdit("Max y:", on_edit=self.relim_primary_y, max_text_width=75)
        self.refresh_primary_y_bounds_control()

        # Reference x limits
        self.reference_x_min = LabeledLineEdit("Min x:", on_edit=self.relim_reference_x, max_text_width=75)
        self.reference_x_max = LabeledLineEdit("Max x:", on_edit=self.relim_reference_x, max_text_width=75)
        self.refresh_reference_x_bounds_control()

        # Reference y limits
        self.reference_y_min = LabeledLineEdit("Min y:", on_edit=self.relim_reference_y, max_text_width=75)
        self.reference_y_max = LabeledLineEdit("Max y:", on_edit=self.relim_reference_y, max_text_width=75)
        self.refresh_reference_y_bounds_control()

        # Selection control
        self.selection_control = PlotSelector(self)

        # Blit manager
        self._blit_manager = BlitManager(self.canvas, (self.primary_line, self.reference_line, *self.primary_crosshair.get_artists(), *self.reference_crosshair.get_artists()))

        # style
        self.primary_axes.patch.set_facecolor(self.style["background"])
        self.reference_axes.patch.set_facecolor("#00000000")
        self.reference_axes.yaxis.tick_right()
        self.reference_axes.xaxis.tick_top()
        self.figure.patch.set_facecolor(self.style["background"])

        self.primary_axes.spines["bottom"].set_color(color)
        self.primary_axes.spines["top"].set_color("#00000000")
        self.primary_axes.spines["left"].set_color(color)
        self.primary_axes.spines["right"].set_color("#00000000")
        self.primary_axes.xaxis.label.set_color(color)
        self.primary_axes.tick_params(axis="x", colors=color)
        self.primary_axes.tick_params(axis="y", colors=color)

        self.reference_axes.tick_params(axis="x", colors="orange")
        self.reference_axes.tick_params(axis="y", colors="orange")

        self.reference_axes.spines["bottom"].set_color(color)
        self.reference_axes.spines["top"].set_color("orange")
        self.reference_axes.spines["left"].set_color(color)
        self.reference_axes.spines["right"].set_color("orange")
        self.reference_axes.xaxis.label.set_color("orange")

        self.primary_line.set_color("#e44cc3")
        self.reference_line.set_color("orange")

        # render everything once
        self.refresh(None)

    def set_primary_line(self, x, y):
        self.primary_data_raw = (x, y)
        if self.primary_unit.unit_type == AxisUnitType.WAVELENGTH:
            self.primary_line.set_data(cubic(x, *primary_fitting_params), y)
        else:
            self.primary_line.set_data(x, y)
        self._blit_manager.update()

    def get_primary_data(self):
        return self.primary_data_raw

    def set_reference_line(self, x,  y):
        self.reference_axes.set_xlim(np.min(x), np.max(x))
        self.refresh_reference_x_bounds_control()
        self.reference_line.set_data(x, y)
        self._blit_manager.force_refresh()
        self._blit_manager.update()

    def get_reference_data(self):
        return self.reference_data

    def refresh(self, frame: Frame | None):
        if frame:
            self.set_primary_line(self.x, frame.raw_data)
        self._blit_manager.update()

    def move_crosshair(self, increment: int):
        crosshair = self.primary_crosshair if self.selected_plot == RealTimePlot.PRIMARY else self.reference_crosshair
        crosshair_x, _ = crosshair.get_position_indices()
        crosshair_x = int(crosshair_x + increment)
        data_x, data_y = self.primary_data_raw
        crosshair.set_position_indices(crosshair_x, data_y[crosshair_x])
        self._blit_manager.force_refresh()
        self._blit_manager.update()

    # noinspection PyTypeChecker
    def onclick(self, event):
        crosshair = self.primary_crosshair if self.selected_plot == RealTimePlot.PRIMARY else self.reference_crosshair
        mouse_x = event.xdata # in plot units
        if mouse_x is None:
            return
        data_x, data_y = self.primary_line.get_data() if self.selected_plot == RealTimePlot.PRIMARY else self.reference_line.get_data()
        index = np.abs(mouse_x - data_x).argmin()
        crosshair.set_position_indices(index, data_y[index])
        self._blit_manager.update()

    def redraw(self):
        self._blit_manager.force_refresh()
        self._blit_manager.update()

    def relim(self):
        if self.primary_unit.unit_type == AxisUnitType.WAVELENGTH:
            self.primary_axes.set_xlim(cubic(0, *primary_fitting_params), cubic(PIXELS, *primary_fitting_params))
            self.primary_line.set_xdata(cubic(self.primary_data_raw[0], *primary_fitting_params))
        elif self.primary_unit.unit_type == AxisUnitType.PIXEL:
            self.primary_axes.set_xlim(0, PIXELS)
            self.primary_line.set_xdata(self.primary_data_raw[0])
        self._refresh_primary()

    def _refresh_primary(self):
        self.primary_crosshair.refresh()
        self.primary_crosshair_readout.display_values()
        self._blit_manager.force_refresh()
        self._blit_manager.update()

    def _refresh_reference(self):
        self.reference_crosshair.refresh()
        self.reference_crosshair_readout.display_values()
        self._blit_manager.force_refresh()
        self._blit_manager.update()

    def update_primary_height(self):
        try:
            x_min = float(self.reference_x_min.get_text())
            x_max = float(self.reference_x_max.get_text())
            self.reference_axes.set_xlim(x_min, x_max)
            self._refresh_reference()
        except Exception as e:
            print(e)

    def relim_axes(self, line_edit_min: LabeledLineEdit, line_edit_max: LabeledLineEdit, set_lim, refresh_plot):
        pattern = r"-?[0-9]*\.?[0-9]*"
        min_text = line_edit_min.get_text()
        min_val = re.search(pattern, min_text)
        if min_text and min_val and min_val.group(0) == min_text:
            min_val = float(min_val.group(0))
        else:
            return

        max_text = line_edit_max.get_text()
        max_val = re.match(pattern, max_text)
        if max_text and max_val and max_val.group(0) == max_text:
            max_val = float(max_val.group(0))
        else:
            return

        set_lim(min_val, max_val)
        refresh_plot()

    def relim_primary_y(self):
        self.relim_axes(self.primary_y_min, self.primary_y_max, self.primary_axes.set_ylim, self._refresh_primary)

    def relim_reference_x(self):
        try:
            self.relim_axes(self.reference_x_min, self.reference_x_max, self.reference_axes.set_xlim, self._refresh_reference)
        except Exception as e:
            print(e)


    def relim_reference_y(self):
        self.relim_axes(self.reference_y_min, self.reference_y_max, self.reference_axes.set_ylim, self._refresh_reference)

    # noinspection PyTupleAssignmentBalance
    def fit(self, pixels, wavelengths):
        global primary_fitting_params
        self.primary_unit.unit_type = AxisUnitType.WAVELENGTH
        if len(pixels) == 2:
            (a0, a1),_ = curve_fit(linear, pixels, wavelengths)
            primary_fitting_params = (a0, a1, 0, 0)
        elif len(pixels) == 3:
            (a0, a1, a2),_ = curve_fit(quadratic, pixels, wavelengths)
            primary_fitting_params = (a0, a1, a2, 0)
        else:
            primary_fitting_params, _ = curve_fit(cubic, pixels, wavelengths)
        self.relim()
        self.primary_unit_control.check_wavelength()
        print(primary_fitting_params) # TODO: replace with visual display

    def set_primary_unit(self, unit_type: int):
        self.set_unit(self.primary_unit, unit_type)

    def set_reference_unit(self, unit_type: int):
        self.set_unit(self.reference_unit, unit_type)

    def set_unit(self, to_set: AxisUnitType, unit_type: int):
        if not 0 <= unit_type <= 1 or type(unit_type) != int:
            raise ValueError

        if unit_type != to_set.unit_type:
            to_set.unit_type = unit_type
            self.relim()

    def get_primary_crosshair_readout(self) -> CrosshairReadout:
        return self.primary_crosshair_readout

    def get_primary_unit_control(self):
        return self.primary_unit_control

    def get_reference_crosshair_readout(self) -> CrosshairReadout:
        return self.reference_crosshair_readout

    def get_reference_unit_control(self):
        return self.reference_unit_control

    def get_selection_control(self):
        return self.selection_control

    def get_primary_y_min_control(self):
        return self.primary_y_min

    def get_primary_y_max_control(self):
        return self.primary_y_max

    def get_reference_x_min_control(self):
        return self.reference_x_min

    def get_reference_x_max_control(self):
        return self.reference_x_max

    def get_reference_y_min_control(self):
        return self.reference_y_min

    def get_reference_y_max_control(self):
        return self.reference_y_max

    def refresh_primary_y_bounds_control(self):
        y_min, y_max = self.primary_axes.get_ylim()
        self.primary_y_min.set_text(f"{y_min:.2f}")
        self.primary_y_max.set_text(f"{y_max:.2f}")

    def refresh_reference_x_bounds_control(self):
        x_min, x_max = self.reference_axes.get_xlim()
        self.reference_x_min.set_text(f"{x_min:.2f}")
        self.reference_x_max.set_text(f"{x_max:.2f}")

    def refresh_reference_y_bounds_control(self):
        y_min, y_max = self.reference_axes.get_ylim()
        self.reference_y_min.set_text(f"{y_min:.2f}")
        self.reference_y_max.set_text(f"{y_max:.2f}")



def linear(x, a0, a1):
    return a0 + a1 * x

def quadratic(x, a0, a1, a2):
    return a0 + a1 * x + a2 * x ** 2

def cubic(x, a0, a1, a2, a3):
    return a0 + a1 * x + a2 * x ** 2 + a3 * x ** 3


class WavelengthPixelButton(QWidget):
    def __init__(self, plot: RealTimePlot):
        super().__init__()
        layout = QHBoxLayout()
        self._pixel = ArrowImmuneRadioButton("Pixel", self)
        self._pixel.setChecked(True)

        def toggle():
            if self._pixel.isChecked():
                plot.set_primary_unit(AxisUnitType.PIXEL)
            else:
                plot.set_primary_unit(AxisUnitType.WAVELENGTH)

        self._pixel.toggled.connect(toggle)
        self._wavelength = ArrowImmuneRadioButton("Wavelength", self)
        layout.addWidget(self._pixel)
        layout.addWidget(self._wavelength)
        self.setFixedWidth(200)
        self.setLayout(layout)

    def check_wavelength(self):
        self._wavelength.setChecked(True)

    def check_pixel(self):
        self._pixel.setChecked(True)


class PlotSelector(QWidget):
    def __init__(self, plot: RealTimePlot):
        super().__init__()
        layout = QHBoxLayout()
        self._primary = ArrowImmuneRadioButton("Primary spectrum", self)
        self._primary.setChecked(True)

        def toggle():
            if self._primary.isChecked():
                plot.set_primary_unit(AxisUnitType.PIXEL)
            else:
                plot.set_primary_unit(AxisUnitType.WAVELENGTH)

        self._primary.toggled.connect(toggle)
        self._reference = ArrowImmuneRadioButton("Reference spectrum", self)
        layout.addWidget(self._primary)
        layout.addWidget(self._reference)
        self.setFixedWidth(200)
        self.setLayout(layout)

    def check_primary(self):
        self._reference.setChecked(True)

    def check_reference(self):
        self._primary.setChecked(True)
