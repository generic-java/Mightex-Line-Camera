import matplotlib
import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtWidgets import QLabel, QWidget, QVBoxLayout, QHBoxLayout, QApplication, QSizePolicy
from matplotlib.axes import Axes
from matplotlib.backend_bases import FigureCanvasBase
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from scipy.optimize import curve_fit

from app_widgets import ArrowImmuneRadioButton, Entry, FixedSizeSpacer
from camera_engine.mtsse import Frame, LineCamera, PIXELS
from utils import format_number


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
        self.visible_artists = []

        self.add_artists(*animated_artists)
        # Grab the background on every draw
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

    def add_artists(self, *artists):
        """
        Adds artists to be managed.

        Parameters
        ----------
        artists : Artists

            Artists to be added.  Will be set to 'animated' (just
            to be safe).  *artist* must be in the figure associated with
            the canvas this class is managing.

        """
        for artist in artists:
            if artist.figure != self.canvas.figure:
                raise RuntimeError
            artist.set_animated(True)
            self._artists.append(artist)
            self.visible_artists.append(True)

    def hide_artist(self, index):
        self.visible_artists[index] = False

    def show_artist(self, index):
        self.visible_artists[index] = True

    def _draw_animated(self):
        """Draw all the animated artists."""
        for i in range(len(self._artists)):
            if self.visible_artists[i]:
                self.canvas.figure.draw_artist(self._artists[i])

    def update(self): # not the bottleneck
        #self.timer.reset()
        """Update the screen with animated artists."""
        # Paranoia in case we missed the draw event
        if self._background is None:
            self.on_draw(None)
        else:
            # Restore the background
            self.canvas.restore_region(self._background)

            # Draw all the animated artists
            self._draw_animated()

            # Update the GUI state
            self.canvas.blit(self.canvas.figure.bbox)

        # Let the GUI event loop process anything it has to do
        self.canvas.flush_events()



def clamp(min_value, max_value, num):
    return min(max(min_value, num), max_value)


class DataHandler(QObject):
    _signal = pyqtSignal(Frame)
    FPS = 30
    awaiting_plot = False

    def __init__(self, camera: LineCamera):
        super().__init__()
        self.camera = camera

        def frame_callback(_):
            self.awaiting_plot = True

        self.camera.set_frame_callback(frame_callback)
        self.timer = QTimer()
        self.timer.setInterval(int(1000 / self.FPS))
        self.timer.timeout.connect(self._plot_data)
        self.timer.start()

    def _plot_data(self):
        if self.awaiting_plot:
            frame = self.camera.last_received_frame()
            if frame:
                self._signal.emit(frame)
            self.awaiting_plot = False

    def get_signal(self):
        return self._signal


class CrosshairReadout(QLabel):
    def set_text(self, x, y):
        self.setText(f"Crosshair x: {format_number(x)}\nCrosshair y: {format_number(y)}")


class Crosshair:
    index = 0
    index_y = 0
    x_line = None
    y_line = None
    x_multiplier = 1
    y_multiplier = 1

    def __init__(self, blit_manager: BlitManager, crosshair_readout: CrosshairReadout, canvas: FigureCanvasBase,
                 axes: Axes, line: Line2D, size=50, color="white"):
        super().__init__()
        self.blit_manager = blit_manager
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
        self.line = line

        canvas.mpl_connect("draw_event", self.on_resize)

    def increment_index(self, increment: int):
        self.set_position_index(self.index + increment)

    def set_position_index(self, index: int):
        line_x, line_y = self.line.get_data()
        if len(line_x) == 0:
            return
        index = int(clamp(0, len(line_x) - 1, index))
        self.index = index

        x_min, x_max = self.axes.get_xlim()
        y_min, y_max = self.axes.get_ylim()

        display_x = clamp(x_min, x_max, line_x[index])
        display_y = clamp(y_min, y_max, line_y[index])
        extent_x = self.size / 2 * self.x_multiplier
        extent_y = self.size / 2 * self.y_multiplier
        vertical_y = np.array([display_y - extent_y, display_y + extent_y])
        self.vertical.set_data(display_x * np.ones_like(vertical_y), vertical_y)
        horizontal_x = np.array([display_x - extent_x, display_x + extent_x])
        self.horizontal.set_data(horizontal_x, display_y * np.ones_like(horizontal_x))

        self.crosshair_readout.set_text(display_x, display_y)
        self.blit_manager.update()

    def refresh(self):
        self.on_resize()
        self.set_position_index(self.index)

    def reset(self):
        self.set_position_index(self.index)

    def get_position_indices(self):
        return self.index, self.index_y

    def on_resize(self, event=None):
        x_left, x_right = self.axes.get_xlim()
        y_bottom, y_top = self.axes.get_ylim()

        bbox = self.axes.get_window_extent()
        width_pixels, height_pixels = bbox.size
        self.x_multiplier = (x_right - x_left) / width_pixels
        self.y_multiplier = (y_top - y_bottom) / height_pixels
        self.set_position_index(self.index)

    def get_artists(self):
        return self.vertical, self.horizontal


class Graph:
    PIXEL = 0
    WAVELENGTH = 1
    _subtract_bg = False

    def __init__(self, unit_type: int, blit_manager: BlitManager, axes: Axes, raw_data, line: Line2D, crosshair: Crosshair, fitting_params):
        self._unit_type = unit_type
        self._blit_manager = blit_manager
        self._axes = axes
        self._raw_x, self._raw_y = raw_data
        self._calibrated_x = self._raw_x
        self._bg_subtracted = self._raw_y
        self._background = np.zeros_like(self._raw_y)
        self._line = line
        self._crosshair = crosshair
        self._fitting_params = fitting_params

    def set_unit_type(self, unit_type: int):
        self._unit_type = unit_type
        self.update_x_bounds()

    def get_unit_type(self):
        return self._unit_type

    def get_axes(self) -> Axes:
        return self._axes

    def get_raw_data(self):
        return self._raw_x, self._raw_y

    def set_raw_data(self, x, y):
        self._raw_x, self._raw_y = (x, y)
        if len(y) != len(self._background):
            self._background = np.zeros_like(y)
        self._bg_subtracted = y - self._background

        display_y = self._bg_subtracted if self._subtract_bg else self._raw_y
        if self._unit_type == Graph.WAVELENGTH:
            self._calibrated_x = cubic(x, *self._fitting_params)
            self._line.set_data(self._calibrated_x, display_y)
        else:
            self._calibrated_x = x
            self._line.set_data(x, display_y)

        x_min, x_max = self.get_x_bounds()
        display_x, display_y = self._line.get_data()
        tol = 1e-3
        if abs(np.min(display_x) - x_min) > tol or abs(np.max(display_x) - x_max) > tol: # If the x bounds of the new dataset are different
            self.update_x_bounds()
        else:
            self._crosshair.reset()
            self._blit_manager.update()

    def get_calibrated_data(self):
        return self._calibrated_x

    def get_data(self):
        return self._raw_x, self._calibrated_x, self._raw_y, self._bg_subtracted

    def get_line(self) -> Line2D:
        return self._line

    def set_background(self, background):
        self._background = background
        self._bg_subtracted = self._raw_y - background
        self._line.set_ydata(self._bg_subtracted)
        self._blit_manager.update()

    def configure_bg_subtraction(self, subtract_background: bool):
        self._subtract_bg = subtract_background
        self._line.set_ydata(self._bg_subtracted if self._subtract_bg else self._raw_y)
        self._blit_manager.update()

    def get_crosshair(self) -> Crosshair:
        return self._crosshair

    def get_fitting_params(self) -> tuple:
        return self._fitting_params

    def set_fitting_params(self, params: tuple):
        self._fitting_params = params

    def get_x_bounds(self):
        return self._axes.get_xlim()

    def get_y_bounds(self):
        return self._axes.get_ylim()

    def update_x_bounds(self, refresh=True):
        if len(self._raw_x) == 0:
            return
        if self._unit_type == Graph.WAVELENGTH:
            self._axes.set_xlim(cubic(np.min(self._raw_x), *self._fitting_params), cubic(np.max(self._raw_x), *self._fitting_params))
            self._line.set_xdata(cubic(self._raw_x, *self._fitting_params))
        elif self._unit_type == Graph.PIXEL:
            self._axes.set_xlim(np.min(self._raw_x), np.max(self._raw_x))
            self._line.set_xdata(self._raw_x)
        if refresh:
            self.refresh()

    def refresh(self):
        self._crosshair.refresh()
        self._blit_manager.force_refresh()
        self._blit_manager.update()

    def get_artists(self):
        return self._line, *self._crosshair.get_artists()


class ReferenceGraph(Graph):
    def __init__(self, unit_type: int, blit_manager: BlitManager, axes: Axes, raw_data, line: Line2D,
                 crosshair: Crosshair, fitting_params):
        super().__init__(unit_type, blit_manager, axes, raw_data, line, crosshair, fitting_params)

    def set_raw_data(self, x, y):
        super().set_raw_data(x, y)
        x_min = np.min(x)
        x_max = np.max(x)
        y_min = np.min(y) * 1.005
        y_max = np.max(y) * 1.2
        self._axes.set_xlim(x_min, x_max)
        self._axes.set_ylim(y_min, y_max)
        self._blit_manager.force_refresh()
        self._blit_manager.update()


class RealTimePlot(QWidget):
    style = {
        "background": "#343434",
        "color": "#e44cc3"
    }

    PRIMARY = 0
    REFERENCE = 1

    primary_hidden = False
    reference_hidden = False

    def __init__(self, data_handler: DataHandler, **kwargs):
        super().__init__()
        self._subtract_background = False
        self._background = np.zeros(PIXELS)
        matplotlib.rcParams["path.simplify"] = True
        matplotlib.rcParams["path.simplify_threshold"] = 1.0
        self.selected_graph = RealTimePlot.PRIMARY
        self.style.update(kwargs)
        self.pixel_array = np.arange(0, PIXELS, 1)
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self._blit_manager = BlitManager(self.canvas)
        self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        container = QVBoxLayout()
        container.addWidget(self.canvas)
        self.setLayout(container)
        self.data_handler = data_handler
        # noinspection PyUnresolvedReferences
        self.data_handler.get_signal().connect(self.refresh)

        color = self.style["color"]

        primary_axes = self.figure.add_subplot()
        primary_axes.set_xlim(0, PIXELS)
        primary_axes.set_ylim(0, 65535)
        primary_axes.grid(True, color="#4b6b71")
        primary_line = Line2D([], [], linewidth=1)
        primary_axes.add_line(primary_line)

        # Primary crosshair readout
        self.primary_crosshair_readout = CrosshairReadout()

        # Primary crosshair
        self.primary_crosshair = Crosshair(self._blit_manager, self.primary_crosshair_readout, self.canvas, primary_axes, primary_line)

        self.primary_graph = Graph(
            Graph.PIXEL,
            self._blit_manager,
            primary_axes,
            (np.array([]), np.array([])),
            primary_line,
            self.primary_crosshair,
            (0, 1, 0, 0)
        )

        reference_axes = self.figure.add_subplot()
        reference_axes.set_ylim(0, 1.2)
        reference_line = Line2D([], [], linewidth=1)
        reference_axes.add_line(reference_line)

        # Reference crosshair readout
        self.reference_crosshair_readout = CrosshairReadout()

        # Reference crosshair
        self.reference_crosshair = Crosshair(self._blit_manager, self.reference_crosshair_readout, self.canvas,
                                             reference_axes, reference_line)

        self.reference_graph = ReferenceGraph(
            Graph.WAVELENGTH,
            self._blit_manager,
            reference_axes,
            (np.array([]), np.array([])),
            reference_line,
            self.reference_crosshair,
            (0, 1, 0, 0)
        )

        # noinspection PyTypeChecker
        self.canvas.mpl_connect("button_press_event", self.onclick)

        # Primary unit control
        self.primary_unit_control = WavelengthPixelButton(self.primary_graph, lambda _: self.refresh_primary_x_bounds_readout())

        # Reference unit control
        self.reference_unit_control = WavelengthPixelButton(self.reference_graph, lambda _: self.refresh_reference_x_bounds_control())

        # Primary x limits
        self.primary_x_min = Entry("Min x:", max_text_width=75)
        self.primary_x_min.disable_editing()
        self.primary_x_max = Entry("Max x:", max_text_width=75)
        self.primary_x_max.disable_editing()
        self.refresh_primary_x_bounds_readout()

        # Primary y limits
        self.primary_y_min = Entry("Min y:", on_edit=self.relim_primary_y, max_text_width=75)
        self.primary_y_max = Entry("Max y:", on_edit=self.relim_primary_y, max_text_width=75)
        self.refresh_primary_y_bounds_control()

        # Reference x limits
        self.reference_x_min = Entry("Min x:", on_edit=self.relim_reference_x, max_text_width=75)
        self.reference_x_max = Entry("Max x:", on_edit=self.relim_reference_x, max_text_width=75)
        self.refresh_reference_x_bounds_control()

        # Reference y limits
        self.reference_y_min = Entry("Min y:", on_edit=self.relim_reference_y, max_text_width=75)
        self.reference_y_max = Entry("Max y:", on_edit=self.relim_reference_y, max_text_width=75)
        self.refresh_reference_y_bounds_control()

        # Selection control
        self.selection_control = PlotSelector(self)

        # Blit manager
        self._blit_manager.add_artists(*self.primary_graph.get_artists(), *self.reference_graph.get_artists())
        self.primary_indices = (0, 1, 2)
        self.reference_indices = (3, 4, 5)

        # style
        primary_axes.patch.set_facecolor(self.style["background"])
        reference_axes.patch.set_facecolor("#00000000")
        reference_axes.yaxis.tick_right()
        reference_axes.xaxis.tick_top()
        self.figure.patch.set_facecolor(self.style["background"])

        primary_axes.spines["bottom"].set_color(color)
        primary_axes.spines["top"].set_color("#00000000")
        primary_axes.spines["left"].set_color(color)
        primary_axes.spines["right"].set_color("#00000000")
        primary_axes.xaxis.label.set_color(color)
        primary_axes.tick_params(axis="x", colors=color)
        primary_axes.tick_params(axis="y", colors=color)

        reference_axes.tick_params(axis="x", colors="orange")
        reference_axes.tick_params(axis="y", colors="orange")

        reference_axes.spines["bottom"].set_color(color)
        reference_axes.spines["top"].set_color("orange")
        reference_axes.spines["left"].set_color(color)
        reference_axes.spines["right"].set_color("orange")
        reference_axes.xaxis.label.set_color("orange")

        primary_line.set_color("#e44cc3")
        reference_line.set_color("orange")

    def get_primary_graph(self):
        return self.primary_graph

    def get_reference_graph(self):
        return self.reference_graph

    def select_graph(self, selected_graph: int):
        self.selected_graph = selected_graph

    def set_raw_data(self, x, y, graph_selector: int):
        self.get_graph(graph_selector).set_raw_data(x, y)
        if graph_selector == RealTimePlot.REFERENCE:
            self.refresh_reference_x_bounds_control()
            self.refresh_reference_y_bounds_control()

    def get_primary_raw_data(self):
        return self.primary_graph.get_raw_data()

    def get_primary_calibrated_data(self):
        return self.primary_graph.get_calibrated_data()

    def get_primary_data(self):
        return self.primary_graph.get_data()

    def get_background_subtracted(self):
        return self.primary_graph.get_data()[2]

    def get_reference_data(self):
        return self.reference_graph.get_raw_data()

    def refresh(self, frame: Frame | None):
        if frame:
            self.set_raw_data(self.pixel_array, frame.raw_data, RealTimePlot.PRIMARY)

    def move_crosshair(self, increment: int):
        graph = self.get_graph(self.selected_graph)
        graph.get_crosshair().increment_index(increment)

    # noinspection PyTypeChecker
    def onclick(self, event):
        focused = QApplication.focusWidget()
        if focused:
            focused.clearFocus()

        graph = self.get_graph(self.selected_graph)

        transform = graph.get_axes().transData.inverted()  # This makes a transform that converts display coordinates to data coordinates
        data_x, data_y = transform.transform((event.x, event.y))  # Transforms display coordinates to data coordinates

        line_x, line_y = graph.get_line().get_data()
        if len(line_x) == 0:
            return
        index = np.abs(data_x - line_x).argmin()
        graph.get_crosshair().set_position_index(index)

    def redraw(self):
        self._blit_manager.force_refresh()
        self._blit_manager.update()

    def get_graph(self, graph_selector: int) -> Graph:
        if graph_selector != 0 and graph_selector != 1:
            raise ValueError(f"Expected 0 or 1 but received {graph_selector}")
        return self.primary_graph if graph_selector == RealTimePlot.PRIMARY else self.reference_graph

    def _refresh_graph(self, graph_selector):
        graph = self.get_graph(graph_selector)
        graph.get_crosshair().refresh()
        self._blit_manager.force_refresh()
        self._blit_manager.update()

    def _refresh_primary(self):
        self._refresh_graph(RealTimePlot.PRIMARY)

    def _refresh_reference(self):
        self._refresh_graph(RealTimePlot.REFERENCE)

    def define_axes_bounds(self, line_edit_min: Entry, line_edit_max: Entry, set_lim, refresh_plot):
        try:
            min_val = float(line_edit_min.get_text())
            max_val = float(line_edit_max.get_text())
        except ValueError:
            return

        if min_val < max_val:
            set_lim(min_val, max_val)
            refresh_plot()

    def relim_primary_y(self):
        axes = self.primary_graph.get_axes()
        self.define_axes_bounds(self.primary_y_min, self.primary_y_max, axes.set_ylim, self._refresh_primary)

    def relim_reference_x(self):
        axes = self.reference_graph.get_axes()
        self.define_axes_bounds(self.reference_x_min, self.reference_x_max, axes.set_xlim, self._refresh_reference)

    def relim_reference_y(self):
        axes = self.reference_graph.get_axes()
        self.define_axes_bounds(self.reference_y_min, self.reference_y_max, axes.set_ylim, self._refresh_reference)

    # noinspection PyTupleAssignmentBalance
    def fit(self, pixels, wavelengths, graph_selector: int):
        graph = self.get_graph(graph_selector)
        graph.set_unit_type(Graph.WAVELENGTH)
        if len(pixels) == 2:
            (a0, a1), _ = curve_fit(linear, pixels, wavelengths)
            graph.set_fitting_params((a0, a1, 0, 0))
        elif len(pixels) == 3:
            (a0, a1, a2), _ = curve_fit(quadratic, pixels, wavelengths)
            graph.set_fitting_params((a0, a1, a2, 0))
        else:
            fitting_params, _ = curve_fit(cubic, pixels, wavelengths)
            graph.set_fitting_params(fitting_params)

        self._after_fit(graph, graph_selector)

    def set_coefficients(self, fitting_params: tuple, graph_selector: int):
        if len(fitting_params) != 4:
            raise ValueError(f"Expected 4 coefficients and got {len(fitting_params):.0f}")

        graph = self.get_graph(graph_selector)
        graph.set_unit_type(Graph.WAVELENGTH)
        graph.set_fitting_params(fitting_params)
        self._after_fit(graph, graph_selector)

    def constrain_reference_x(self):
        x_min, x_max = self.primary_graph.get_x_bounds()
        self.reference_graph.get_axes().set_xlim(x_min, x_max)
        self.refresh_reference_x_bounds_control()
        self.reference_graph.refresh()

    def _after_fit(self, graph, graph_selector):
        graph.update_x_bounds(refresh=False)
        if graph_selector == RealTimePlot.PRIMARY:
            self.refresh_primary_x_bounds_readout()
            self.primary_unit_control.check_wavelength()
            self.constrain_reference_x()
        else:
            self.refresh_reference_x_bounds_control()
            self.reference_unit_control.check_wavelength()


        self._blit_manager.force_refresh()  # Redraw the entire plot, including the background
        self._blit_manager.update()

    def set_unit(self, graph_selector: int, to_set: Graph, unit_type: int):
        if not 0 <= unit_type <= 1 or type(unit_type) != int:
            raise ValueError(f"Expected 0 or 1 but got {unit_type}")

        if unit_type != to_set.unit_type:
            to_set.unit_type = unit_type
            self.get_graph(graph_selector).update_x_bounds()

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

    def get_primary_x_min_readout(self):
        return self.primary_x_min

    def get_primary_x_max_readout(self):
        return self.primary_x_max

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

    def refresh_primary_x_bounds_readout(self):
        x_min, x_max = self.primary_graph.get_x_bounds()
        self.primary_x_min.set_text(f"{x_min:.2f}")
        self.primary_x_max.set_text(f"{x_max:.2f}")

    def refresh_primary_y_bounds_control(self):
        y_min, y_max = self.primary_graph.get_y_bounds()
        self.primary_y_min.set_text(f"{y_min:.2f}")
        self.primary_y_max.set_text(f"{y_max:.2f}")

    def refresh_reference_x_bounds_control(self):
        x_min, x_max = self.reference_graph.get_x_bounds()
        self.reference_x_min.set_text(f"{x_min:.2f}")
        self.reference_x_max.set_text(f"{x_max:.2f}")


    def refresh_reference_y_bounds_control(self):
        y_min, y_max = self.reference_graph.get_y_bounds()
        self.reference_y_min.set_text(f"{y_min:.2f}")
        self.reference_y_max.set_text(f"{y_max:.2f}")

    def toggle_primary_plot(self):
        self.primary_hidden = not self.primary_hidden
        if self.primary_hidden:
            [self._blit_manager.hide_artist(index) for index in self.primary_indices]
        else:
            [self._blit_manager.show_artist(index) for index in self.primary_indices]
        self._blit_manager.update()

    def toggle_reference_plot(self):
        self.reference_hidden = not self.reference_hidden
        if self.reference_hidden:
            [self._blit_manager.hide_artist(index) for index in self.reference_indices]
        else:
            [self._blit_manager.show_artist(index) for index in self.reference_indices]
        self._blit_manager.update()

    def set_background(self, background: Frame):
        self._background = background


def linear(x, a0, a1):
    return a0 + a1 * x


def quadratic(x, a0, a1, a2):
    return a0 + a1 * x + a2 * x ** 2


def cubic(x, a0, a1, a2, a3):
    return a0 + a1 * x + a2 * x ** 2 + a3 * x ** 3


class WavelengthPixelButton(QWidget):
    def __init__(self, graph: Graph, on_toggle=None):
        super().__init__()
        layout = QHBoxLayout()
        self._blocking_callback = False
        self._pixel = ArrowImmuneRadioButton("Pixel", self)
        self._pixel.setChecked(True)

        def toggle():
            if self._blocking_callback:
                return
            unit_type = Graph.PIXEL if self._pixel.isChecked() else Graph.WAVELENGTH
            graph.set_unit_type(unit_type)
            if on_toggle:
                on_toggle(unit_type)

        self._pixel.toggled.connect(toggle)
        self._wavelength = ArrowImmuneRadioButton("Wavelength", self)
        layout.addWidget(self._pixel)
        layout.addWidget(FixedSizeSpacer(width=10))
        layout.addWidget(self._wavelength)
        layout.addStretch()
        self.setFixedWidth(185)
        self.setLayout(layout)

    def check_wavelength(self, block_callback=True):
        self._blocking_callback = block_callback
        self._wavelength.setChecked(True)
        self._blocking_callback = False

    def check_pixel(self, block_callback=True):
        self._blocking_callback = block_callback
        self._pixel.setChecked(True)
        self._blocking_callback = False


class PlotSelector(QWidget):
    def __init__(self, plot: RealTimePlot):
        super().__init__()
        layout = QHBoxLayout()
        self._primary = ArrowImmuneRadioButton("Primary", self)
        self._primary.setChecked(True)

        def toggle():
            if self._primary.isChecked():
                plot.select_graph(RealTimePlot.PRIMARY)
            else:
                plot.select_graph(RealTimePlot.REFERENCE)

        self._primary.toggled.connect(toggle)
        self._reference = ArrowImmuneRadioButton("Reference", self)
        layout.addWidget(self._primary)
        layout.addWidget(FixedSizeSpacer(width=10))
        layout.addWidget(self._reference)
        layout.addStretch()
        self.setFixedWidth(192)
        self.setLayout(layout)

    def check_primary(self):
        self._primary.setChecked(True)

    def check_reference(self):
        self._reference.setChecked(True)

