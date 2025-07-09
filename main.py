import queue

import matplotlib.pyplot as plt

from camera_engine.mtsse import *
from plottools import BlitManager

x = np.arange(0, PIXELS, 1)
queue = queue.Queue(maxsize=10)

for i in range(10):
    queue.put(np.zeros_like(x))

def main():
    print("Camera engine initialized.")

    figure, axes = plt.subplots()
    axes.set_xlim(-182.35, 3829.25)
    axes.set_ylim(800, 65535)
    figure.set_size_inches(12, 6)
    line, = axes.plot([], [])

    plt.show(block=False)
    plt.pause(0.1)

    blit_manager = BlitManager(figure.canvas, (line,))

    camera = LineCamera()
    camera.grab_spectrum_frames()

    while True:
        frame = camera.get_frame()
        if frame:
            line.set_data(x, frame.raw_data)
        blit_manager.update()
        plt.pause(0.01)


if __name__ == "__main__":
    main()
