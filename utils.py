import time
from decimal import Decimal, ROUND_HALF_UP
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