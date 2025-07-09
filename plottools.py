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
            to be safe).  *art* must be in the figure associated with
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
        cv = self.canvas
        fig = self.canvas.figure
        # paranoia in case we missed the draw event,
        if self._background is None:
            self.on_draw(None)
        else:
            # restore the background
            cv.restore_region(self._background)
            # draw all the animated artists
            self._draw_animated()
            # update the GUI state
            self.canvas.blit(fig.bbox)
        # let the GUI event loop process anything it has to do
        self.canvas.flush_events()