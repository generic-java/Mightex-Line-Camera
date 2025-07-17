from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QAction, QPixmap
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QLineEdit, QFileDialog, QSizePolicy, QPushButton, QMessageBox, QRadioButton, QMenu, QSplashScreen


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

        self.load_file_button = SimpleButton("Choose file", pick_file)

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
    def __init__(self, label_text="", parent=None, max_text_width=50, text="", on_edit=lambda text: None):
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.label = QLabel(label_text)
        self._line_edit = QLineEdit()
        # noinspection PyUnresolvedReferences
        self._line_edit.textEdited.connect(on_edit)
        self._line_edit.setText(text)

        layout.addWidget(self.label)
        layout.addWidget(self._line_edit)
        self._line_edit.setFixedWidth(max_text_width)
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Maximum)

    def set_text(self, text: str):
        self._line_edit.setText(text)

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


class SimpleButton(QPushButton):
    def __init__(self, name: str, callback):
        super().__init__(name)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Maximum)
        self.clicked.connect(callback)

class IconButton(QPushButton):
    def __init__(self, icon: QIcon, callback):
        super().__init__()
        self.setIcon(icon)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Maximum)
        self.clicked.connect(callback)

class ArrowImmuneRadioButton(QRadioButton):
    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Up, Qt.Key.Key_Down):
            event.ignore()
        else:
            super().keyPressEvent(event)

class MenuSelectorButton(QPushButton):
    _selected: str = None
    def __init__(self, name: str, *actions):
        super().__init__(name)
        menu = QMenu()

        def make_select(option_name=""):
            def select_option():
                self._selected = option_name
                self.setText(option_name)
            return select_option

        for action in actions:
            action.triggered.connect(make_select(option_name=action.text()))

        menu.addActions(actions)
        self.setMenu(menu)

    def get_selected(self):
        return self._selected

class Action(QAction):
    def __init__(self, name, callback):
        super().__init__(name)
        self.triggered.connect(callback)


class FixedSizeSpacer(QWidget):
    def __init__(self, width=None, height=None):
        super().__init__()
        if width:
            self.setFixedWidth(width)
        if height:
            self.setFixedHeight(height)


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
