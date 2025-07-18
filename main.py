import sys

from PyQt6.QtGui import QFontDatabase
from PyQt6.QtWidgets import QApplication

from app_widgets import SplashScreen
from camera_engine.mtsse import *
from gui import Window, load_stylesheet


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(load_stylesheet("style.qss"))
    splash = SplashScreen()
    splash.show()
    QFontDatabase.addApplicationFont("./res/fonts/aharoni/ahronbd.ttf")
    QFontDatabase.addApplicationFont("./res/fonts/roboto/static/Roboto-SemiBold.ttf")

    start_engine()
    #time.sleep(5)
    print("Camera engine initialized.")
    splash.close()

    camera = LineCamera()
    window = Window(app, camera)

    window.show()
    app.exec()
    teardown_engine()


if __name__ == "__main__":
    main()
