import sys
import traceback

from PyQt6.QtGui import QFontDatabase
from PyQt6.QtWidgets import QApplication

from app_widgets import SplashScreen, ErrorDialog
from camera_engine.mtsse import *
from gui_main import Window, load_stylesheet


class CustomApplication(QApplication):
    def notify(self, receiver, event):
        try:
            return super().notify(receiver, event)
        except Exception:
            traceback.print_exc()
            return False


def excepthook(exc_type, exc_value, exc_tb):
    traceback.print_exception(exc_type, exc_value, exc_tb)

sys.excepthook = excepthook

def main():
    app = CustomApplication(sys.argv)
    app.setStyleSheet(load_stylesheet("style.qss"))
    splash = SplashScreen()
    splash.show()
    QFontDatabase.addApplicationFont("./res/fonts/aharoni/ahronbd.ttf")
    QFontDatabase.addApplicationFont("./res/fonts/roboto/static/Roboto.ttf")

    no_camera = False

    try:
        start_engine()
    except ConnectionError:
        no_camera = True

    print("Camera engine initialized.")
    splash.close()

    camera = LineCamera()

    window = Window(camera)
    window.show()

    if no_camera:
        ErrorDialog("No camera was detected.  Restart the app to try again.", "Connection error", parent=window)
    app.exec()
    teardown_engine()


if __name__ == "__main__":
    main()
