# import sys
# import os
#
# file_path = os.path.dirname(os.path.realpath(__file__))
# lib_path = os.path.join(file_path, "../bindings/python")
# sys.path.append(lib_path)

import logging
import time
from datetime import datetime
import threading
from dataclasses import dataclass
import random

from rgbmatrix import graphics
import requests
from PIL import Image, ImageEnhance

from samplebase import SampleBase
import ping3


log = logging.getLogger(__name__)


@dataclass
class Message:
    colour: graphics.Color
    text: str


@dataclass
class Icon:
    name: str
    text: str
    image: Image = None


FETCH_EVERY = 30
FETCH_ENDPOINT = "http://lemon.com/api/messages"
SLEEP_ENDPOINT = "https://sleep.fig14.com/am-i-sleeping"

CLOCK_COLOUR = graphics.Color(37, 37, 37)
MOTD_COLOUR = graphics.Color(12, 45, 55)
AI_MOTD_COLOUR = graphics.Color(12, 12, 80)
ALERT_COLOUR = graphics.Color(255, 0, 0)
LOADING_COLOUR = graphics.Color(0, 75, 0)
SLEEPING_COLOUR = graphics.Color(37, 0, 75)
SLEEPING_UNDERLINE_COLOUR = graphics.Color(15, 0, 30)
BTC_COLOUR = graphics.Color(10, 70, 10)
INTERNET_FAILOVER_COLOUR = graphics.Color(50, 25, 0)

CANVAS_WIDTH = 64
CANVAS_HEIGHT = 32

ICON_PROBABILITY = 0.05


last_motd = None
last_ai_motd = None
messages = []
message = None
message_index = 0

daddy_sleeping = False
internet_failover = None

alert = None
no_internet_message = None

message_pos = 0
alert_pos = 0


message_lock = threading.Lock()
alert_lock = threading.Lock()
internet_lock = threading.Lock()

icons = [
    Icon("pikachu", "Pika pika!"),
    Icon("metroid", "Metroids!"),
    Icon("toad", "Our princess is in another castle!"),
    Icon("core-x", "X Parasites!"),
    Icon("oddish", "Oddish oddish!"),
    Icon("ultros", "Yeowch! Seafood soup!"),
]

for icon in icons:
    image = Image.open(f"../icons/{icon.name}.png").convert("RGB")
    enhancer = ImageEnhance.Brightness(image)
    # to reduce brightness by 50%, use factor 0.5
    icon.image = enhancer.enhance(0.5)


icon_pos = CANVAS_WIDTH
icon = random.choice(icons)


def show_random_icon():
    global icon, icon_pos
    icon = random.choice(icons)
    log.info(icon.text)
    icon_pos = CANVAS_WIDTH


def ping_remote_server(host="8.8.8.8"):
    try:
        response = ping3.ping(host, timeout=5)
        if response is not None:
            return True
        else:
            log.info(f"{host} is not reachable.")
            return False
    except exceptions.PingError as e:
        log.info(f"Ping error for {host}: {e}")
        return False


def check_internet(num_attempts=2):
    for i in range(num_attempts):
        if i != 0:
            log.info(f"Retrying (attempt {i+1})")

        if ping_remote_server():
            return True

    return False


def get_messages():
    """
    Continuously poll for messages - run this in a thread!
    """
    global alert, messages, last_motd, last_ai_motd, daddy_sleeping, \
        no_internet_message, internet_failover

    log.info("Starting message fetch loop")

    while True:
        try:
            new_messages = []

            connected_to_internet = check_internet()
            with internet_lock:
                if connected_to_internet:
                    no_internet_message = None
                else:
                    no_internet_message = "Internet is Down!"

            # Fetch MOTD
            r = requests.get(FETCH_ENDPOINT)
            if r.status_code != 200:
                with message_lock:
                    error = f"ERROR: received {r.status_code} from {FETCH_ENDPOINT}"
                    log.error(error)
                    messages.append(error)
                    continue
            else:
                response = r.json()

                motd = response["motd"].replace("\r", "").replace("\n", "  ")
                if motd != last_motd:
                    log.info(f"MOTD: {motd}")
                    last_motd = motd

                new_messages.append(Message(MOTD_COLOUR, motd))

                ai_motd = response["ai_motd"].replace("\r", "").replace("\n", "  ")
                if ai_motd != last_ai_motd:
                    log.info(f"AI MOTD: {ai_motd}")
                    last_ai_motd = ai_motd

                new_messages.append(Message(AI_MOTD_COLOUR, ai_motd))

                btc = response["btc"]
                new_messages.append(Message(BTC_COLOUR, btc))

                with alert_lock:
                    if alert != response["alert"]:
                        alert = response["alert"]
                        if alert is None:
                            log.info("Alert over")
                        else:
                            log.info(f"ALERT: {alert}")

                # Connection status
                connection_status = response["connection-status"]
                new_internet_failover = connection_status != "normal"
                if new_internet_failover != internet_failover:
                    log.info(f"Failover status changed to {new_internet_failover}")
                    internet_failover = new_internet_failover

            # Fetch sleep status
            if connected_to_internet:
                sleep_response = requests.get(SLEEP_ENDPOINT)

                if sleep_response.status_code != 200:
                    error = f"ERROR: received {r.status_code} from {SLEEP_ENDPOINT}"
                    log.error(error)
                    new_messages.append(Message(ALERT_COLOUR, error))

                else:
                    sleep_str = sleep_response.text
                    new_sleeping = "asleep" in sleep_str
                    if new_sleeping != daddy_sleeping:
                        log.info(f"Sleep status: {sleep_str}")

                    daddy_sleeping = new_sleeping

                    if daddy_sleeping:
                        new_messages.append(Message(SLEEPING_COLOUR, "Daddy is sleeping zzZzZzZZzZZzz..."))

            with message_lock:
                messages = new_messages

        except Exception as e:
            log.exception(f"Exception in main loop: {e}")

        time.sleep(30)


class RunText(SampleBase):
    def __init__(self, *args, **kwargs):
        super(RunText, self).__init__(*args, **kwargs)
        self.parser.add_argument("-t", "--text", help="The text to scroll on the RGB LED panel", default="Hello world!")

    def run(self):
        global message_pos, messages, message, alert_pos, message_index, daddy_sleeping, icon_pos

        offscreen_canvas = self.matrix.CreateFrameCanvas()

        time_font = graphics.Font()
        time_font.LoadFont("../fonts/7x13.bdf")

        font = graphics.Font()
        # font.LoadFont("../fonts/clR6x12.bdf")
        font.LoadFont("../fonts/6x13.bdf")
        message_pos = CANVAS_WIDTH

        alert_font = graphics.Font()
        alert_font.LoadFont("../fonts/7x13B.bdf")
        alert_pos = CANVAS_WIDTH

        message_thread = threading.Thread(target=get_messages, daemon=True)
        message_thread.start()

        while True:
            offscreen_canvas.Clear()
            now = datetime.now()

            unix_time = now.timestamp()

            alert_to_render = None
            with alert_lock:
                alert_to_render = alert

            with internet_lock:
                if no_internet_message:
                    if alert_to_render:
                        alert_to_render = f"{alert_to_render}    {no_internet_message}"
                    else:
                        alert_to_render = no_internet_message

            if icon_pos > -32:
                offscreen_canvas.SetImage(icon.image, icon_pos)
                icon_pos -= 1

            elif alert_to_render:
                if (int(unix_time) % 2) == 0:
                    graphics.DrawLine(offscreen_canvas, 0, 0, CANVAS_WIDTH, 0, ALERT_COLOUR)
                    graphics.DrawLine(offscreen_canvas, 0, 1, CANVAS_WIDTH, 1, ALERT_COLOUR)
                    graphics.DrawLine(offscreen_canvas, 0, CANVAS_HEIGHT - 2, CANVAS_WIDTH, CANVAS_HEIGHT - 2, ALERT_COLOUR)
                    graphics.DrawLine(offscreen_canvas, 0, CANVAS_HEIGHT - 1, CANVAS_WIDTH, CANVAS_HEIGHT - 1, ALERT_COLOUR)

                length = graphics.DrawText(offscreen_canvas, alert_font, alert_pos, 20, ALERT_COLOUR, alert_to_render)
                alert_pos -= 1
                if (alert_pos + length < 0):
                    alert_pos = CANVAS_WIDTH

            else:
                time_str = now.strftime("%H:%M:%S")

                graphics.DrawText(offscreen_canvas, time_font, 4, 11, CLOCK_COLOUR, time_str)

                if daddy_sleeping:
                    graphics.DrawLine(offscreen_canvas, 0, CANVAS_HEIGHT - 2, CANVAS_WIDTH, CANVAS_HEIGHT - 2, SLEEPING_UNDERLINE_COLOUR)

                if internet_failover:
                    for i in range(3):
                        graphics.DrawLine(offscreen_canvas, CANVAS_WIDTH - 3, CANVAS_HEIGHT - 1 - i, CANVAS_WIDTH, CANVAS_HEIGHT - 1 - i, INTERNET_FAILOVER_COLOUR)

                # If no message is loaded, try to load one
                if message is None:
                    message_index = 0
                    if messages:
                        message = messages[0]

                # If we have a message
                if message:
                    length = graphics.DrawText(offscreen_canvas, font, message_pos, 26, message.colour, message.text)

                    message_pos -= 1
                    if (message_pos + length + 10 < 0):
                        message_pos = CANVAS_WIDTH
                        message_index += 1
                        with message_lock:
                            if message_index >= len(messages):
                                message_index = 0
                            message = messages[message_index]

                        # Randomly show icon
                        if random.random() < ICON_PROBABILITY:
                            show_random_icon()

            time.sleep(0.025)
            offscreen_canvas = self.matrix.SwapOnVSync(offscreen_canvas)


# Main function
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)-8s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    run_text = RunText()
    if (not run_text.process()):
        run_text.print_help()
