import numpy as np
from matplotlib.artist import Artist
from matplotlib.axes import Axes
from matplotlib.backend_bases import FigureCanvasBase
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.lines import Line2D


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

class Crosshair:
    x = 0
    y = 0
    x_line = None
    y_line = None
    x_multiplier = 1
    y_multiplier = 1
    def __init__(self, canvas: FigureCanvasBase, axes: Axes, size=50, color="white"):
        super().__init__()
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
        self.set_position(0, 0)

        canvas.mpl_connect("draw_event", self.on_resize)

    def set_position(self, x, y):
        x_left, x_right = self.axes.get_xlim()
        y_bottom, y_top = self.axes.get_ylim()
        self.x = clamp(x_left, x_right, x)
        self.y = clamp(y_bottom, y_top, y)
        extent_x = self.size / 2 * self.x_multiplier
        extent_y = self.size / 2 * self.y_multiplier
        vertical_y = np.arange(self.y - extent_y, self.y + extent_y, 0.1)
        self.vertical.set_data(self.x * np.ones_like(vertical_y), vertical_y)
        horizontal_x = np.arange(self.x - extent_x, self.x + extent_x, 0.1)
        self.horizontal.set_data(horizontal_x, self.y * np.ones_like(horizontal_x))

    def get_position(self):
        return self.x, self.y

    def on_resize(self, event):
        x_left, x_right = self.axes.get_xlim()
        y_bottom, y_top = self.axes.get_ylim()

        bbox = self.axes.get_window_extent()
        width_pixels, height_pixels = bbox.size
        self.x_multiplier = (x_right - x_left) / width_pixels
        self.y_multiplier = (y_top - y_bottom) / height_pixels


    def get_artists(self):
        return self.vertical, self.horizontal