import time
from threading import Thread

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
