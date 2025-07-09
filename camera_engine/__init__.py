from threading import Thread

from wrapper import init_device


def start_engine():
    init_device()

Thread(target=start_engine).start()