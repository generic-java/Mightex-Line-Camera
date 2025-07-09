import matplotlib.pyplot as plt
import numpy as np

class RealTimePlot:

    def __init__(self, x_data=None, y_data=None):
        plt.ion()
        self.x_data = x_data if x_data is not None else np.array([])
        self.y_data = y_data if y_data is not None else np.array([])
        self.figure, self.axes = plt.subplots()
        (self.line,) = self.axes.plot(self.x_data, self.y_data, animated=True) # Because animated=True, this will not show until we request the artist to be drawn
        plt.show()

        plt.pause(0.1) # I'm unsure if this is necessary

        self.background = self.figure.canvas.copy_from_bbox(self.figure.bbox)
        self.axes.draw_artist(self.line)
        self.figure.canvas.blit(self.figure.bbox)

    def update_data(self, x_data, y_data):
        self.update_x_data(x_data)
        self.update_y_data(y_data)

    def update_x_data(self, x_data):
        self.x_data = x_data

    def update_y_data(self, y_data):
        self.y_data = y_data

    def redraw(self):
        self.figure.canvas.restore_region(self.background)
        self.line.set_xdata(self.x_data)
        self.line.set_ydata(self.y_data)
        self.axes.draw_artist(self.line)
        self.figure.canvas.blit(self.figure.bbox) # blit updates a specified part of the figure (in this case everything within the figure's bounding box by pushing the RGBA buffer to the GUI and displaying it)
        self.figure.canvas.flush_events()
