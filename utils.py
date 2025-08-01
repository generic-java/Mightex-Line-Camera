import os
import time
from decimal import Decimal, ROUND_HALF_UP
from threading import Thread

from PyQt6.QtCore import QSize, QPoint


class Timer:

    def __init__(self):
        self.timestamp = time.time()

    def reset(self):
        self.timestamp = time.time()

    def get_elapsed_time(self):
        return time.time() - self.timestamp

    def run_at(self, elapsed_time, callback):
        def check():
            while self.get_elapsed_time() < elapsed_time:
                time.sleep(0.01)
            print("Running callback")
            callback()

        thread = Thread(target=check, daemon=True)
        thread.start()

def format_number(number, decimal_places: int = 5) -> str:
    number = float(number)
    number_str = str(number)
    if number_str.isnumeric() or abs(round(number) - number) < (10 ** -decimal_places) / 2:
        if round(number) == 0:
            return "0"
        else:
            return f"{number:.0f}"
    else:
        try:
            precision_str = "0."
            for i in range(decimal_places):
                precision_str += "0"

            return Decimal(number_str).quantize(Decimal(precision_str), rounding=ROUND_HALF_UP).to_eng_string()

        except ValueError:
            return "0"

class Animation:
    _finished = 0
    def __init__(self, property_animations: tuple | list, before_start=None, on_finished=None):
        self._property_animations = property_animations
        self._before_start = before_start
        self._on_finished = on_finished
        self._next_up = None

    def play(self):
        self._finished = 0

        if self._before_start:
            self._before_start()

        if self._on_finished or self._next_up:
            for animation in self._property_animations:
                animation.finished.connect(self._run_on_finished)

        for animation in self._property_animations:
            animation.start()


    def play_next(self, animation):
        self._next_up = animation

    def _run_on_finished(self):
        self._finished += 1
        if self._finished == len(self._property_animations):
            self._finished = 0
            if self._on_finished:
                self._on_finished()
            for animation in self._property_animations:
                animation.finished.disconnect(self._run_on_finished)
            if self._next_up:
                self._next_up.play()

class AnimationSequence:
    def __init__(self, *animations: Animation):
        self._animations = animations
        for i in range(len(animations) - 1):
            animations[i].play_next(animations[i+1])

    def start(self):
        self._animations[0].play()

    def get_animations(self):
        return self._animations

def size_to_point(size: QSize):
    return QPoint(size.width(), size.height())

def current_dir():
    return os.path.dirname(str(__file__))
