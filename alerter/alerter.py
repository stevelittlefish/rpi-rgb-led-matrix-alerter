import time
from datetime import datetime

from rgbmatrix import graphics

from samplebase import SampleBase


motd = "Loading..."
alert = None


class RunText(SampleBase):
    def __init__(self, *args, **kwargs):
        super(RunText, self).__init__(*args, **kwargs)
        self.parser.add_argument("-t", "--text", help="The text to scroll on the RGB LED panel", default="Hello world!")

    def run(self):
        offscreen_canvas = self.matrix.CreateFrameCanvas()

        time_font = graphics.Font()
        time_font.LoadFont("../fonts/6x10.bdf")

        font = graphics.Font()
        font.LoadFont("../fonts/8x13.bdf")
        textColor = graphics.Color(0, 0, 100)
        pos = offscreen_canvas.width
        my_text = self.args.text

        while True:
            offscreen_canvas.Clear()
            now = datetime.now()

            time_str = now.strftime("%H:%M:%S")

            graphics.DrawText(offscreen_canvas, time_font, 9, 8, textColor, time_str)

            len = graphics.DrawText(offscreen_canvas, font, pos, 27, textColor, motd) + 50
            pos -= 1
            if (pos + len < 0):
                pos = offscreen_canvas.width

            time.sleep(0.05)
            offscreen_canvas = self.matrix.SwapOnVSync(offscreen_canvas)


# Main function
if __name__ == "__main__":
    run_text = RunText()
    if (not run_text.process()):
        run_text.print_help()
