import numpy as np
from PyQt6.QtCore import Qt, QObject, pyqtSignal
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QLineEdit, QFileDialog, QSizePolicy, QVBoxLayout, QPushButton, QMessageBox
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from camera_engine.mtsse import Frame, LineCamera
from camera_engine.wrapper import PIXELS
from plottools import BlitManager, Crosshair


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

class FileInput(QWidget):
    _chosen_fname = None
    def __init__(self, label_text="File:", parent=None, max_width=300, is_save_file=False, dialog_filter="CSV File (*.csv);;TXT File (*.txt)"):
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.label = QLabel(label_text)
        self.line_edit = QLineEdit()

        def pick_file():
            if is_save_file:
                fname, _ = QFileDialog.getSaveFileName(filter=dialog_filter)
            else:
                fname, _ = QFileDialog.getOpenFileName(filter=dialog_filter)
            self.line_edit.setText(fname)
            self._chosen_fname = fname

        self.load_file_button = DefaultButton("Choose file", pick_file)

        layout.addWidget(self.label)
        layout.addWidget(self.line_edit)
        layout.addWidget(self.load_file_button)
        self.line_edit.setFixedWidth(max_width)
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Maximum)

    def get_chosen_fname(self):
        if self._chosen_fname:
            return self._chosen_fname
        else:
            ErrorDialog("Please choose a file")
            raise ValueError


class LabeledLineEdit(QWidget):
    def __init__(self, label_text="", parent=None, max_text_width=50):
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.label = QLabel(label_text)
        self._line_edit = QLineEdit()

        layout.addWidget(self.label)
        layout.addWidget(self._line_edit)
        self._line_edit.setFixedWidth(max_text_width)
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Maximum)

    def get_text(self):
        return self._line_edit.text()

    def get_char(self):
        text = self.get_text()
        if len(text) == 1:
            return text
        else:
            ErrorDialog("Please enter one character representing an element")
            raise ValueError

    def get_int(self):
        text = self.get_text()
        if text.isnumeric():
            return int(text)
        else:
            ErrorDialog("Please enter an integer")
            raise ValueError

    def get_float(self):
        text = self.get_text()
        try:
            return float(text)
        except ValueError as e:
            ErrorDialog("Please enter an integer")
            raise e

class ErrorDialog(QMessageBox):
    def __init__(self, text):
        super().__init__()
        self.setText(text)
        self.setIcon(QMessageBox.Icon.Critical)
        self.setWindowTitle("Error")
        self.exec()


class RealTimePlot(QWidget):

    style = {
        "background": "#4b6b71",
        "color": "#6aee35"
    }

    def __init__(self, data_handler: DataHandler, **kwargs):
        super().__init__()
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

        primary_axes = self.figure.add_subplot()
        primary_axes.set_xlim(0, PIXELS)
        primary_axes.set_ylim(800, 65535)
        primary_axes.grid(True, color=color)

        secondary_axes = primary_axes.twinx()
        secondary_axes.set_ylim(0, 65535)

        self.figure.set_size_inches(12, 6)
        self.line, = primary_axes.plot([], [])
        self.secondary_line, = secondary_axes.plot([], [])

        # Crosshair
        self.crosshair = Crosshair(self.canvas, primary_axes)
        def on_mouse_move(event):
            mouse_x = event.xdata
            data_x, data_y = self.line.get_data()
            index = np.abs(mouse_x - data_x).argmin()
            self.crosshair.set_position(data_x[index], data_y[index])
            self.blit_manager.update()

        self.figure.canvas.mpl_connect("motion_notify_event", on_mouse_move)

        self.blit_manager = BlitManager(self.canvas, (self.line, self.secondary_line, *self.crosshair.get_artists()))

        # style
        primary_axes.patch.set_facecolor(self.style["background"])
        self.figure.patch.set_facecolor(self.style["background"])

        primary_axes.spines["bottom"].set_color(color)
        primary_axes.spines["top"].set_color(color)
        primary_axes.spines["left"].set_color(color)
        primary_axes.spines["right"].set_color(color)
        primary_axes.xaxis.label.set_color(color)
        primary_axes.tick_params(axis="x", colors=color)
        primary_axes.tick_params(axis="y", colors=color)

        secondary_axes.tick_params(axis="x", colors="orange")
        secondary_axes.tick_params(axis="y", colors="orange")

        secondary_axes.spines["bottom"].set_color(color)
        secondary_axes.spines["top"].set_color(color)
        secondary_axes.spines["left"].set_color(color)
        secondary_axes.spines["right"].set_color("orange")
        secondary_axes.xaxis.label.set_color("orange")

        self.line.set_color("#e44cc3")
        self.secondary_line.set_color("orange")

        # render everything once
        self.refresh(None)

    def set_primary_line(self, x, y):
        self.line.set_data(x, y)
        self.blit_manager.update()

    def set_secondary_line(self, x,  y):
        self.secondary_line.set_data(x, y)
        self.blit_manager.update()

    def refresh(self, frame: Frame | None):
        if frame:
            self.line.set_data(self.x, frame.raw_data)
        self.blit_manager.update()

    def update_crosshair(self, increment: int):
        crosshair_x, = int(self.crosshair.get_position() + increment)
        data_x, data_y = self.line.get_data()
        self.crosshair.set_position(crosshair_x, data_y[crosshair_x])
        self.blit_manager.update()


class DefaultButton(QPushButton):
    def __init__(self, name: str, callback):
        super().__init__(name)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Maximum)
        self.clicked.connect(callback)



