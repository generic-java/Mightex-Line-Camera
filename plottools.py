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

from app_widgets import ArrowImmuneRadioButton
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

fitting_params = (0, 1, 0, 0)

class AxisUnitType:
    PIXEL = 0
    WAVELENGTH = 1
    unit_type = PIXEL

_primary_unit = AxisUnitType()
_reference_unit = AxisUnitType()

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
    pixel_x = 0
    pixel_y = 0
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
        self.set_position_pixels(0, 0)

        canvas.mpl_connect("draw_event", self.on_resize)

    def set_position_pixels(self, x, y):
        x_min, x_max = self.axes.get_xlim()
        y_min, y_max = self.axes.get_ylim()
        self.pixel_x = clamp(0, PIXELS, x)
        self.pixel_y = y
        self.crosshair_readout.update_values(self.pixel_x, cubic(self.pixel_x, *fitting_params), self.pixel_y)
        display_x = clamp(x_min, x_max, cubic(x, *fitting_params) if self.unit.unit_type == AxisUnitType.WAVELENGTH else x)
        display_y = clamp(y_min, y_max, y)
        extent_x = self.size / 2 * self.x_multiplier
        extent_y = self.size / 2 * self.y_multiplier
        vertical_y = np.arange(display_y - extent_y, display_y + extent_y, 0.1)
        self.vertical.set_data(display_x * np.ones_like(vertical_y), vertical_y)
        horizontal_x = np.arange(display_x - extent_x, display_x + extent_x, 0.1)
        self.horizontal.set_data(horizontal_x, display_y * np.ones_like(horizontal_x))

    def refresh(self):
        self.on_resize()
        self.set_position_pixels(self.pixel_x, self.pixel_y)

    def get_position_pixels(self):
        return self.pixel_x, self.pixel_y

    def on_resize(self, event=None):
        x_left, x_right = self.axes.get_xlim()
        y_bottom, y_top = self.axes.get_ylim()

        bbox = self.axes.get_window_extent()
        width_pixels, height_pixels = bbox.size
        self.x_multiplier = (x_right - x_left) / width_pixels
        self.y_multiplier = (y_top - y_bottom) / height_pixels
        self.set_position_pixels(self.pixel_x, self.pixel_y)

    def get_artists(self):
        return self.vertical, self.horizontal

    def set_unit_type(self, unit_type: int):
        self.unit.unit_type = unit_type


class RealTimePlot(QWidget):

    style = {
        "background": "#4b6b71",
        "color": "#6aee35"
    }

    def __init__(self, data_handler: DataHandler, **kwargs):
        super().__init__()
        self.primary_unit = _primary_unit
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
        self.primary_axes.set_ylim(800, 65535)
        self.primary_axes.grid(True, color=color)

        self.reference_axes = self.primary_axes.twinx()
        self.reference_axes.set_ylim(0, 1.2)

        self.figure.set_size_inches(12, 6)
        self.primary_line, = self.primary_axes.plot([], [])
        self.primary_data_raw = (np.array([]), np.array([]))
        self.reference_line, = self.reference_axes.plot([], [])
        self.reference_data = (np.array([]), np.array([]))

        # Crosshair readout
        self.crosshair_readout = CrosshairReadout(0, 0, 0, self.primary_unit)

        # Crosshair
        self.crosshair = Crosshair(self.crosshair_readout, self.canvas, self.primary_axes, self.primary_unit)
        # noinspection PyTypeChecker
        self.canvas.mpl_connect("button_press_event", self.onclick)

        # Unit control
        self.unit_control = WavelengthPixelButton(self)

        # Blit manager
        self._blit_manager = BlitManager(self.canvas, (self.primary_line, self.reference_line, *self.crosshair.get_artists()))

        # style
        self.primary_axes.patch.set_facecolor(self.style["background"])
        self.figure.patch.set_facecolor(self.style["background"])

        self.primary_axes.spines["bottom"].set_color(color)
        self.primary_axes.spines["top"].set_color(color)
        self.primary_axes.spines["left"].set_color(color)
        self.primary_axes.spines["right"].set_color(color)
        self.primary_axes.xaxis.label.set_color(color)
        self.primary_axes.tick_params(axis="x", colors=color)
        self.primary_axes.tick_params(axis="y", colors=color)

        self.reference_axes.tick_params(axis="x", colors="orange")
        self.reference_axes.tick_params(axis="y", colors="orange")

        self.reference_axes.spines["bottom"].set_color(color)
        self.reference_axes.spines["top"].set_color(color)
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
            self.primary_line.set_data(cubic(x, *fitting_params), y)
        else:
            self.primary_line.set_data(x, y)
        self._blit_manager.update()

    def get_primary_data(self):
        return self.primary_data_raw

    def set_reference_line(self, x,  y):
        self.reference_line.set_data(x, y)
        self._blit_manager.update()

    def get_reference_data(self):
        return self.reference_data

    def refresh(self, frame: Frame | None):
        if frame:
            self.set_primary_line(self.x, frame.raw_data)
        self._blit_manager.update()

    def move_crosshair(self, increment: int):
        crosshair_x, _ = self.crosshair.get_position_pixels()
        crosshair_x = int(crosshair_x + increment)
        data_x, data_y = self.primary_data_raw
        self.crosshair.set_position_pixels(crosshair_x, data_y[crosshair_x])
        self._blit_manager.update()

    # noinspection PyTypeChecker
    def onclick(self, event):
        mouse_x = event.xdata
        if mouse_x is None:
            return
        data_x, data_y = self.primary_line.get_data()
        index = np.abs(mouse_x - data_x).argmin()
        self.crosshair.set_position_pixels(index, data_y[index])
        self._blit_manager.update()

    def redraw(self):
        self._blit_manager.force_refresh()
        self._blit_manager.update()

    def relim(self):
        if self.primary_unit.unit_type == AxisUnitType.WAVELENGTH:
            self.primary_axes.set_xlim(cubic(0, *fitting_params), cubic(PIXELS, *fitting_params))
            self.primary_line.set_xdata(cubic(self.primary_data_raw[0], *fitting_params))
        elif self.primary_unit.unit_type == AxisUnitType.PIXEL:
            self.primary_axes.set_xlim(0, PIXELS)
            self.primary_line.set_xdata(self.primary_data_raw[0])
        self.crosshair.refresh()
        self.crosshair_readout.display_values()
        self._blit_manager.force_refresh()
        self._blit_manager.update()

    # noinspection PyTupleAssignmentBalance
    def fit(self, pixels, wavelengths):
        global fitting_params
        self.primary_unit.unit_type = AxisUnitType.WAVELENGTH
        if len(pixels) == 2:
            (a0, a1),_ = curve_fit(linear, pixels, wavelengths)
            fitting_params = (a0, a1, 0, 0)
        elif len(pixels) == 3:
            (a0, a1, a2),_ = curve_fit(quadratic, pixels, wavelengths)
            fitting_params = (a0, a1, a2, 0)
        else:
            fitting_params, _ = curve_fit(cubic, pixels, wavelengths)
        self.relim()
        self.unit_control.check_wavelength()

    def set_primary_unit(self, unit_type: int):
        if not 0 <= unit_type <= 1 or type(unit_type) != int:
            raise ValueError

        if unit_type != self.primary_unit.unit_type:
            self.primary_unit.unit_type = unit_type
            self.relim()

    def get_crosshair_readout(self) -> CrosshairReadout:
        return self.crosshair_readout

    def get_unit_control(self):
        return self.unit_control


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
