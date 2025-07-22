from PyQt6.QtCore import Qt, QObject, QEvent, QSize, QPoint
from PyQt6.QtGui import QIcon, QAction, QPixmap
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QLineEdit, QFileDialog, QSizePolicy, QPushButton, QMessageBox, QRadioButton, QMenu, QSplashScreen, QApplication, QToolButton, QMainWindow


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

class MenuButton(QToolButton):
    _open_menu: QMenu = None
    def __init__(self, name: str):
        super().__init__()
        self.setText(name)
        self._menu = QMenu()
        self.setMenu(self._menu)
        self.setFixedWidth(60)
        self.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)

    def add_action(self, action: QAction):
        self._menu.addAction(action)

    def add_menu(self, name: str):
        return self._menu.addMenu(name)

    def get_menu(self):
        return self._menu

    def enterEvent(self, event):
        if MenuButton._open_menu and MenuButton._open_menu is not self.menu():
            MenuButton._open_menu.close()

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


class ClearFocusFilter(QObject):
    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.MouseButtonPress:
            focused = QApplication.focusWidget()
            if focused is not None and hasattr(focused, "clearFocus"): # Check if it has the clearFocus function
                widget_under_mouse = obj.childAt(event.pos())
                if widget_under_mouse is None or widget_under_mouse != focused:
                    focused.clearFocus()
        return super().eventFilter(obj, event)


class WindowHandleButton(QPushButton):
    def __init__(self, primary_icon: QIcon, hover_icon: QIcon, size: QSize):
        super().__init__()
        self.primary_icon = primary_icon
        self.hover_icon = hover_icon
        self.setFixedSize(size)
        self.setIconSize(size)
        self.setIcon(primary_icon)

    def enterEvent(self, a0):
        self.setIcon(self.hover_icon)

    def leaveEvent(self, a0):
        self.setIcon(self.primary_icon)

class FullscreenToggleButton(QPushButton):
    in_fullscreen = False

    def __init__(self, parent: QMainWindow, fullscreen: QIcon, fullscreen_hover: QIcon, restore_down: QIcon, restore_down_hover: QIcon, size: QSize):
        super().__init__()
        self.parent = parent
        self.fullscreen = fullscreen
        self.fullscreen_hover = fullscreen_hover
        self.restore_down = restore_down
        self.restore_down_hover = restore_down_hover
        self.primary_icon = fullscreen
        self.hover_icon = fullscreen_hover
        self.setFixedSize(size)
        self.setIconSize(size)
        self.setIcon(self.primary_icon)

    def enterEvent(self, event):
        self.setIcon(self.hover_icon)

    def leaveEvent(self, event):
        self.setIcon(self.primary_icon)

    def mousePressEvent(self, event):
        self.in_fullscreen = not self.in_fullscreen
        if self.in_fullscreen:
            self.parent.showFullScreen()
            self.primary_icon = self.restore_down
            self.hover_icon = self.restore_down_hover
        else:
            self.parent.setWindowState(Qt.WindowState.WindowNoState)
            self.primary_icon = self.fullscreen
            self.hover_icon = self.fullscreen_hover


class MoveWindowSpacer(QWidget):
    dragging_window = False
    drag_offset: QPoint = QPoint()

    def __init__(self, window: QMainWindow):
        super().__init__()
        self.parent = window
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)  # Ensure it receives events
        self.setStyleSheet("background: transparent;")

    def mousePressEvent(self, event):
        self.dragging_window = True
        self.drag_offset = self.parent.frameGeometry().topLeft() - event.globalPosition().toPoint() # Window position minus mouse position
        event.accept() # Accept the event so it isn't processed by anything else

    def mouseReleaseEvent(self, event):
        self.dragging_window = False
        event.accept()

    def mouseMoveEvent(self, event):
        if self.dragging_window:
            self.parent.move(event.globalPosition().toPoint() + self.drag_offset)
            event.accept()