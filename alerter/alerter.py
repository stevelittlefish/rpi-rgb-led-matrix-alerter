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


next_motd = "Loading..."
motd = next_motd
daddy_is_sleeping = False
alert = None

motd_pos = 0
alert_pos = 0


def get_messages():
    global alert, next_motd

    print("Fetching messages")

    r = requests.get(FETCH_ENDPOINT)
    if r.status_code != 200:
        next_motd = f"ERROR {r.status_code}"
    else:
        response = r.json()
        next_motd = response["motd"]
        alert = response["alert"]


class RunText(SampleBase):
    def __init__(self, *args, **kwargs):
        super(RunText, self).__init__(*args, **kwargs)
        self.parser.add_argument("-t", "--text", help="The text to scroll on the RGB LED panel", default="Hello world!")

    def run(self):
        global motd_pos, motd, alert_pos

        offscreen_canvas = self.matrix.CreateFrameCanvas()

        time_font = graphics.Font()
        time_font.LoadFont("../fonts/7x13.bdf")

        font = graphics.Font()
        # font.LoadFont("../fonts/clR6x12.bdf")
        font.LoadFont("../fonts/7x13.bdf")
        motd_pos = offscreen_canvas.width
        
        alert_font = graphics.Font()
        alert_font.LoadFont("../fonts/7x13B.bdf")
        alert_pos = offscreen_canvas.width

        next_fetch = 0

        while True:
            offscreen_canvas.Clear()
            now = datetime.now()

            unix_time = now.timestamp()

            if unix_time > next_fetch:
                next_fetch = unix_time + FETCH_EVERY

                get_messages()

            if alert:
                if (int(unix_time) % 2) == 0:
                    graphics.DrawLine(offscreen_canvas, 0, 0, offscreen_canvas.width, 0, ALERT_COLOUR)
                    graphics.DrawLine(offscreen_canvas, 0, 1, offscreen_canvas.width, 1, ALERT_COLOUR)
                    graphics.DrawLine(offscreen_canvas, 0, offscreen_canvas.height - 2, offscreen_canvas.width, offscreen_canvas.height - 2, ALERT_COLOUR)
                    graphics.DrawLine(offscreen_canvas, 0, offscreen_canvas.height - 1, offscreen_canvas.width, offscreen_canvas.height - 1, ALERT_COLOUR)

                len = graphics.DrawText(offscreen_canvas, alert_font, alert_pos, 20, ALERT_COLOUR, alert)
                alert_pos -= 1
                if (alert_pos + len < 0):
                    alert_pos = offscreen_canvas.width

            else:
                time_str = now.strftime("%H:%M:%S")

                graphics.DrawText(offscreen_canvas, time_font, 4, 11, CLOCK_COLOUR, time_str)

                len = graphics.DrawText(offscreen_canvas, font, motd_pos, 27, MOTD_COLOUR, motd)
                motd_pos -= 1
                if (motd_pos + len + 10 < 0):
                    motd_pos = offscreen_canvas.width
                    motd = next_motd

            time.sleep(0.05)
            offscreen_canvas = self.matrix.SwapOnVSync(offscreen_canvas)


# Main function
if __name__ == "__main__":
    run_text = RunText()
    if (not run_text.process()):
        run_text.print_help()
