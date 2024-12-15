import time
from datetime import datetime

from rgbmatrix import graphics
import requests

from samplebase import SampleBase


FETCH_EVERY = 30
FETCH_ENDPOINT = "http://lemon.com/api/messages"

CLOCK_COLOUR = graphics.Color(25, 25, 25)
MOTD_COLOUR = graphics.Color(0, 0, 50)
ALERT_COLOUR = graphics.Color(255, 0, 0)


motd = "Loading..."
alert = None

motd_pos = 0


def get_messages():
    global alert, motd

    print("Fetching messages")

    r = requests.get(FETCH_ENDPOINT)
    if r.status_code != 200:
        motd = f"ERROR {r.status_code}"
    else:
        response = r.json()
        motd = response["motd"]
        alert = response["alert"]


class RunText(SampleBase):
    def __init__(self, *args, **kwargs):
        super(RunText, self).__init__(*args, **kwargs)
        self.parser.add_argument("-t", "--text", help="The text to scroll on the RGB LED panel", default="Hello world!")

    def run(self):
        global motd_pos

        offscreen_canvas = self.matrix.CreateFrameCanvas()

        time_font = graphics.Font()
        time_font.LoadFont("../fonts/6x10.bdf")

        font = graphics.Font()
        font.LoadFont("../fonts/8x13.bdf")
        motd_pos = offscreen_canvas.width
        my_text = self.args.text

        next_fetch = 0

        while True:
            offscreen_canvas.Clear()
            now = datetime.now()

            unix_time = now.timestamp()

            if unix_time > next_fetch:
                next_fetch = unix_time + FETCH_EVERY

                get_messages()

            time_str = now.strftime("%H:%M:%S")

            graphics.DrawText(offscreen_canvas, time_font, 9, 8, CLOCK_COLOUR, time_str)

            len = graphics.DrawText(offscreen_canvas, font, motd_pos, 27, MOTD_COLOUR, motd) + 50
            motd_pos -= 1
            if (motd_pos + len < 0):
                motd_pos = offscreen_canvas.width

            time.sleep(0.05)
            offscreen_canvas = self.matrix.SwapOnVSync(offscreen_canvas)


# Main function
if __name__ == "__main__":
    run_text = RunText()
    if (not run_text.process()):
        run_text.print_help()
