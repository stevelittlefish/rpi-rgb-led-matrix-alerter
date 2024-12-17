import time
from datetime import datetime
import threading
from dataclasses import dataclass

from rgbmatrix import graphics
import requests

from samplebase import SampleBase


@dataclass
class Message:
    colour: graphics.Color
    text: str


FETCH_EVERY = 30
FETCH_ENDPOINT = "http://lemon.com/api/messages"

CLOCK_COLOUR = graphics.Color(25, 25, 25)
MOTD_COLOUR = graphics.Color(0, 0, 50)
ALERT_COLOUR = graphics.Color(255, 0, 0)
LOADING_COLOUR = graphics.Color(0, 12, 25)


last_motd = None
messages = [Message(LOADING_COLOUR, "Loading...")]
message = messages[0]
message_index = 0

alert = None

message_pos = 0
alert_pos = 0


message_lock = threading.Lock()
alert_lock = threading.Lock()


def get_messages():
    """
    Continuously poll for messages - run this in a thread!
    """
    global alert, messages, last_motd
    
    print("Starting message fetch loop")

    while True:
        try:
            # print("Fetching messages")

            r = requests.get(FETCH_ENDPOINT)
            if r.status_code != 200:
                with message_lock:
                    messages = [Message(ALERT_COLOUR, f"ERROR {r.status_code}")]
            else:
                response = r.json()

                motd = response["motd"]
                if motd != last_motd:
                    print(f"MOTD: {motd}")
                    last_motd = motd

                with message_lock:
                    messages = [Message(MOTD_COLOUR, motd)]

                with alert_lock:
                    if alert != response["alert"]:
                        alert = response["alert"]
                        if alert is None:
                            print("Alert over")
                        else:
                            print(f"ALERT: {alert}")

        except Exception as e:
            print(f"Error: {e}")

        time.sleep(30)


class RunText(SampleBase):
    def __init__(self, *args, **kwargs):
        super(RunText, self).__init__(*args, **kwargs)
        self.parser.add_argument("-t", "--text", help="The text to scroll on the RGB LED panel", default="Hello world!")

    def run(self):
        global message_pos, messages, message, alert_pos, message_index

        offscreen_canvas = self.matrix.CreateFrameCanvas()

        time_font = graphics.Font()
        time_font.LoadFont("../fonts/7x13.bdf")

        font = graphics.Font()
        # font.LoadFont("../fonts/clR6x12.bdf")
        font.LoadFont("../fonts/7x13.bdf")
        message_pos = offscreen_canvas.width
        
        alert_font = graphics.Font()
        alert_font.LoadFont("../fonts/7x13B.bdf")
        alert_pos = offscreen_canvas.width

        message_thread = threading.Thread(target=get_messages, daemon=True)
        message_thread.start()

        while True:
            offscreen_canvas.Clear()
            now = datetime.now()

            unix_time = now.timestamp()
            
            alert_to_render = None
            with alert_lock:
                alert_to_render = alert

            if alert_to_render:
                if (int(unix_time) % 2) == 0:
                    graphics.DrawLine(offscreen_canvas, 0, 0, offscreen_canvas.width, 0, ALERT_COLOUR)
                    graphics.DrawLine(offscreen_canvas, 0, 1, offscreen_canvas.width, 1, ALERT_COLOUR)
                    graphics.DrawLine(offscreen_canvas, 0, offscreen_canvas.height - 2, offscreen_canvas.width, offscreen_canvas.height - 2, ALERT_COLOUR)
                    graphics.DrawLine(offscreen_canvas, 0, offscreen_canvas.height - 1, offscreen_canvas.width, offscreen_canvas.height - 1, ALERT_COLOUR)

                length = graphics.DrawText(offscreen_canvas, alert_font, alert_pos, 20, ALERT_COLOUR, alert_to_render)
                alert_pos -= 1
                if (alert_pos + length < 0):
                    alert_pos = offscreen_canvas.width

            else:
                time_str = now.strftime("%H:%M:%S")

                graphics.DrawText(offscreen_canvas, time_font, 4, 11, CLOCK_COLOUR, time_str)

                length = graphics.DrawText(offscreen_canvas, font, message_pos, 27, message.colour, message.text)
                message_pos -= 1
                if (message_pos + length + 10 < 0):
                    message_pos = offscreen_canvas.width
                    message_index += 1
                    with message_lock:
                        if message_index >= len(messages):
                            message_index = 0
                        message = messages[message_index]

            time.sleep(0.05)
            offscreen_canvas = self.matrix.SwapOnVSync(offscreen_canvas)


# Main function
if __name__ == "__main__":
    run_text = RunText()
    if (not run_text.process()):
        run_text.print_help()
