import queue
from threading import Thread

import matplotlib.pyplot as plt
import numpy as np

from camera_engine.wrapper import *
from utils import Timer

x = np.arange(0, PIXELS, 1)
queue = queue.Queue(maxsize=10)

for i in range(10):
    queue.put(np.zeros_like(x))


def main():
    figure, axes = plt.subplots()
    axes.set_xlim(-182.35, 3829.25)
    axes.set_ylim(800, 65535)
    figure.set_size_inches(12, 6)
    line, = axes.plot([], [])

    plt.show(block=False)
    plt.pause(0.1)

    background = figure.canvas.copy_from_bbox(figure.bbox)


    def on_receive_frame(row, col, attributes, data_tuple):
        y = np.array(data_tuple[0])
        queue.put(y, block=True)

    def create_visualization():
        if not queue.empty():
            figure.canvas.restore_region(background)
            y = queue.get(block=False)
            line.set_data(x, y)
            axes.draw_artist(line)
            figure.canvas.blit(figure.bbox)
            figure.canvas.flush_events()
            plt.pause(0.01)

    timer = Timer()
    print("Connecting to device...")

    Thread(target=init_device).start()
    plt.pause(20)

    print("Device initialization successful")
    set_device_work_mode(1, WorkMode.NORMAL)
    set_device_active_status(1, True)
    install_device_frame_hooker(1, receive_frame)
    install_callback(on_receive_frame)

    timer.reset()

    def get_data():
        start_frame_grab(FrameGrab.CONTINUOUS)
        get_device_spectrometer_frame_data(1, 1, True) # If this is False and not called in a separate thread, the program is much slower.  I would guess that this is because it creates a thread in C that runs much faster than the python thread



    Thread(target=get_data).start()

    while True:
        create_visualization()

    timer.run_at(30, stop_frame_grab)




if __name__ == "__main__":
    main()
