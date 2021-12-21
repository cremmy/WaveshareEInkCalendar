import getopt
import logging
import os
import sys
import time
from calendarframe import EventProviderCalDAV, EventProviderICS, CalendarFrameDraw, Config


def usage():
    print("main.py [mode=draw-test]")


def main(argv):
    log_format = "[%(levelname)-8s][%(asctime)s.%(msecs)03d][%(name)s]: %(message)s"
    log_date = "%Y-%m-%d %H:%M:%S"

    logging.basicConfig(level=logging.DEBUG, format=log_format, datefmt=log_date)
    logger = logging.getLogger("main")

    sys.path.insert(1, os.path.join(os.getcwd(), 'libs'))

    mode_drawtest = False
    try:
        opts, args = getopt.getopt(argv, "hv", ["mode="])
    except getopt.GetoptError:
        usage()
        sys.exit()
    for opt, arg in opts:
        if opt == "v":
            logger.debug("Enabled verbose output")
        if opt in ["--mode"]:
            if arg == "draw-test":
                mode_drawtest = True
                logger.debug("Mode set to draw test")

    logger.info("Start")

    event_providers = [
        EventProviderICS(file="resource/test.ics"),
        EventProviderICS(address="https://www.mozilla.org/media/caldata/PolishHolidays.ics", is_holiday_calendar=True),
        # EventProviderCalDAV("https://user:password@some.server.com/calendar/default.ics"),
    ]

    config = Config()
    config.monochrome = not mode_drawtest

    calendar_draw = CalendarFrameDraw(
        event_providers,
        config)
    images = calendar_draw.draw()

    if mode_drawtest:
        logger.info("Draw test using Tk")
        import tkinter
        from PIL import ImageTk
        root = tkinter.Tk()

        widgets = []
        for image in images:
            tkimage = ImageTk.PhotoImage(image)
            tklabel = tkinter.Label(root, image=tkimage)
            tklabel.pack()
            widgets.append(tkimage)
            widgets.append(tklabel)
        root.mainloop()
    else:
        logger.info("Drawing calendar to eInk display...")
        from libs.waveshare_epd import epd7in5b_HD

        epd = epd7in5b_HD.EPD()
        epd.init()
        # epd.Clear()
        epd.display(epd.getbuffer(images[0]), epd.getbuffer(images[1]))
        time.sleep(1)
        epd.Dev_exit()
        logger.info("Finished drawing to eInk display")

    logger.info("Stop")


if __name__ == "__main__":
    main(sys.argv[1:])
    exit(0)
