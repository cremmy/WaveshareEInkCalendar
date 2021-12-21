import datetime
import logging
import os
from dateutil import tz
from suntime import Sun
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
from .DrawUtils import *

from .IEventProvider import IEventProvider


class Config:
    def __init__(self):
        resources_dir = os.path.join(os.getcwd(), 'resource')

        self.size = (880, 528)
        self.colors = [(0, 0, 0), (255, 0, 0)]
        self.monochrome = False

        self.calendar_size = (self.size[0]*3//4, self.size[1])
        self.calendar_position = (0, 0)
        self.calendar_padding = (1, 1, 4, 1)  # CSS-like: top, right, bottom, left
        self.calendar_font_date_bold = os.path.join(resources_dir, 'DejaVuSans.ttf')
        self.calendar_font_date_thin = os.path.join(resources_dir, 'DejaVuSans-ExtraLight.ttf')
        self.calendar_font_event_count = os.path.join(resources_dir, 'DejaVuSans-ExtraLight.ttf')
        self.calendar_event_icon = os.path.join(resources_dir, 'event.png')
        self.calendar_event_allday_icon = os.path.join(resources_dir, 'event_all_day.png')
        self.calendar_font_size = 24
        self.calendar_date_position = (6, 4)
        self.calendar_events_margin_left = 24
        self.calendar_weeks_past = 2      # How many weeks in the past should be drawn
        self.calendar_weeks_future = 4    # How many weeks in the future should be drawn
        self.calendar_day_margin = 1
        self.calendar_weekend_margin = 7  # Distance between week and weekend columns

        self.today_size = (self.size[0]*1//4, self.size[1]*1//3)
        self.today_position = (self.size[0]*3//4, 0)
        self.today_padding = (16, 16, 8, 8)
        self.today_font = os.path.join(resources_dir, 'DejaVuSans.ttf')
        self.today_date_font_size = 50
        self.today_sunrise_icon = os.path.join(resources_dir, 'sun.png')
        self.today_sunrise_font_size = 24
        self.today_sunrise_coordinates = (50.05432853424836, 19.93845258591673)

        self.tasklist_size = (self.size[0]*1//4, self.size[1]*2//3)
        self.tasklist_position = (self.size[0]*3//4, self.size[1]*1//3)
        self.tasklist_padding = (4, 0, 0, 8)
        self.tasklist_font_header = os.path.join(resources_dir, 'DejaVuSans.ttf')
        self.tasklist_font_event = os.path.join(resources_dir, 'DejaVuSans-ExtraLight.ttf')
        self.tasklist_font_size_header = 20
        self.tasklist_font_size_event = 16
        self.tasklist_task_offset = 8          # Move tasks X pixels to the right
        self.tasklist_task_days = 7            # Get tasks from the next X days
        self.tasklist_highlight_next_days = 3  # Highlight tasks for the next X days
        self.tasklist_highlight_icon_today = os.path.join(resources_dir, 'event_today.png')
        self.tasklist_highlight_icon_upcoming = os.path.join(resources_dir, 'event_upcoming.png')
        self.tasklist_event_long_icon_from = os.path.join(resources_dir, 'event_long_from.png')
        self.tasklist_event_long_icon_through = os.path.join(resources_dir, 'event_long_through.png')
        self.tasklist_event_long_icon_to = os.path.join(resources_dir, 'event_long_to.png')


class EventProviderAggregate(IEventProvider):
    def __init__(self, event_providers):
        IEventProvider.__init__(self)
        self._event_providers = event_providers

    def preload(self, date_from, date_to):
        for ep in self._event_providers:
            ep.preload(date_from, date_to)

    def get_events(self, date):
        events = []

        for ep in self._event_providers:
            events = events + ep.get_events(date)

        return events

    def get_all_day_events(self, date):
        events = []

        for ep in self._event_providers:
            events = events + ep.get_all_day_events(date)

        return events

    def is_holiday(self, date):
        for ep in self._event_providers:
            if ep.is_holiday(date):
                return True

        return False


class EInkDraw:
    def __init__(self, size, supported_colors=None, multiimage_monochrome=True):
        """
        Creates buffers for each defined color, either [color count] monochrome, or one 24-bit.

        :param size: Size of created image
        :param supported_colors: List of supported colors.
               If drawing multiple monochrome images, only number of colors is important
        :param multiimage_monochrome: Generat [color count] 1-bit image that can be passed to EInk driver
        """
        if len(size) != 2 or size[0] < 1 or size[1] < 1:
            raise ValueError("Invalid image size, expected two-value tuple of positive integers")
        if len(supported_colors) < 1:
            raise ValueError("Invalid color list, define at least one color")

        logger = logging.getLogger("EInkDraw")

        self._colors = supported_colors
        self._monochrome = multiimage_monochrome
        if multiimage_monochrome:
            # For monochrome images every color is "black", with "white" background
            for i in range(len(supported_colors)):
                self._colors[i] = 0

        logger.debug("Creating images...".format(len(supported_colors)))
        self._canvas = []
        self._draw = []
        if multiimage_monochrome:
            self._bgcolor = 255
            for i in range(len(supported_colors)):
                logger.debug("Creating monochrome image: {}".format(size))
                canvas = Image.new("1", size, self._bgcolor)
                draw = ImageDraw.Draw(canvas)
                draw.fontmode = "1"

                self._canvas.append(canvas)
                self._draw.append(draw)
        else:
            self._bgcolor = (255, 255, 255)
            logger.debug("Creating RGB image: {}".format(size))
            canvas = Image.new("RGB", size, self._bgcolor)

            self._canvas.append(canvas)
            self._draw.append(ImageDraw.Draw(canvas))

    def get_canvas(self, color_id):
        if not self._monochrome:
            return self._canvas[0]
        return self._canvas[min(color_id, len(self._canvas)-1)]

    def get_image_draw(self, color_id):
        if not self._monochrome:
            return self._draw[0]
        return self._draw[min(color_id, len(self._draw)-1)]

    def get_color(self, color_id):
        return self._colors[min(color_id, len(self._colors)-1)]

    def get_images(self):
        return self._canvas

    def get_size(self):
        return self._canvas[0].width, self._canvas[0].height

    def get_background_color(self):
        return self._bgcolor

    def merge(self, other, position):
        if not isinstance(other, EInkDraw):
            raise ValueError("\"other\" should be an instance of EInkDraw")
        if len(position) != 2:
            raise ValueError("Invalid position, expected two-value tuple")
        if len(self._canvas) != len(other._canvas):
            raise ValueError("Other EInkDraw does not have the same number of images")

        for i in range(0, len(self._canvas)):
            self._canvas[i].paste(other._canvas[i], position)


class CalendarFrameDraw:
    def __init__(self, event_providers, config: Config = None, reference=None):
        if config is None:
            self._config = Config()
        else:
            self._config = config

        if reference is None:
            reference = datetime.datetime.now(tz=tz.tzlocal())
        self._reference = reference

        self._event_provider = EventProviderAggregate(event_providers)
        self._logger = logging.getLogger("CalendarFrameDraw")

        # Check configuration
        if len(config.colors) != 2:
            raise ValueError("Current implementation supports only displays with at least two colors")
        if config.calendar_weeks_past < 0:
            raise ValueError("Number of previous weeks shouldn't be negative")
        if config.calendar_weeks_future < 0:
            raise ValueError("Number of next weeks shouldn't be negative")
        if config.tasklist_task_days < 0:
            raise ValueError("Number of days for tasklist souldn't be negative")
        if config.tasklist_highlight_next_days < 0:
            raise ValueError("Number of highlighted days for tasklist souldn't be negative")
        # Should we check if all parts fit in the specified size...?
        # Nah, it's Python, shouldn't crash.

        self._logger.debug("Creating buffer: {}".format(self._config.size))
        self._draw = EInkDraw(self._config.size, self._config.colors, self._config.monochrome)

    def draw(self):
        # Calculate time span and preload events
        self._logger.info("Calculating calendar event range...")
        today = self._reference.date()
        monday = today - datetime.timedelta(days=today.weekday())  # Monday, the true first day of the week
        date_from = monday - datetime.timedelta(weeks=self._config.calendar_weeks_past)
        date_to = max(
            monday + datetime.timedelta(weeks=self._config.calendar_weeks_future),
            today + datetime.timedelta(days=self._config.tasklist_task_days))
        self._logger.debug("  Today: {}; Monday: {}".format(today, monday))
        self._logger.debug("  From:  {}; To:     {}".format(date_from, date_to))

        self._logger.info("Preloading events...")
        self._event_provider.preload(date_from, date_to)

        # Draw calendar
        self._logger.info("Drawing calendar...")
        draw = EInkDraw(self._config.calendar_size, self._config.colors, self._config.monochrome)
        self._draw_calendar(draw)
        self._draw.merge(draw, self._config.calendar_position)

        # Draw today's information
        self._logger.info("Drawing today's information...")
        draw = EInkDraw(self._config.today_size, self._config.colors, self._config.monochrome)
        self._draw_today(draw)
        self._draw.merge(draw, self._config.today_position)

        # Draw tasklist
        self._logger.info("Drawing tasklist...")
        draw = EInkDraw(self._config.tasklist_size, self._config.colors, self._config.monochrome)
        self._draw_tasklist(draw)
        self._draw.merge(draw, self._config.tasklist_position)

        self._logger.info("Drawing finished")
        return self._draw.get_images()

    def _draw_calendar(self, draw: EInkDraw):
        self._logger.info("Calculating calendar range...")

        today = self._reference.date()
        monday = today - datetime.timedelta(days=today.weekday())
        date_from = monday - datetime.timedelta(weeks=self._config.calendar_weeks_past)
        date_to = monday + datetime.timedelta(weeks=self._config.calendar_weeks_future)
        week_span = self._config.calendar_weeks_future + self._config.calendar_weeks_past

        self._logger.debug("  Today: {}; Monday: {}".format(today, monday))
        self._logger.debug("  From:  {}; To:     {}".format(date_from, date_to))
        self._logger.debug("  Weeks: {}".format(week_span))

        day_size =\
            (
                (
                    draw.get_size()[0] -
                    (self._config.calendar_padding[1]+self._config.calendar_padding[3])
                )//7 -
                self._config.calendar_day_margin,

                (
                    draw.get_size()[1] -
                    (self._config.calendar_padding[0]+self._config.calendar_padding[2])
                )//week_span -
                self._config.calendar_day_margin
            )
        # Draw each grid item on separate image to make sure there is no overflow
        draw_day = EInkDraw(day_size, self._config.colors, self._config.monochrome)

        font_date_bold = ImageFont.truetype(self._config.calendar_font_date_bold, self._config.calendar_font_size)
        font_date_thin = ImageFont.truetype(self._config.calendar_font_date_thin, self._config.calendar_font_size)
        font_event_count = ImageFont.truetype(self._config.calendar_font_event_count, self._config.calendar_font_size)
        icon_event = Image.open(self._config.calendar_event_icon).convert("1")
        icon_event_all_day = Image.open(self._config.calendar_event_allday_icon).convert("1")

        date = date_from
        while date < date_to:
            for i in range(len(draw_day.get_images())):
                draw_day.get_image_draw(i).rectangle([(0, 0), draw_day.get_size()], fill=draw.get_background_color())

            self._draw_calendar_day(
                draw_day,
                date,
                font_date_bold,
                font_date_thin,
                font_event_count,
                icon_event,
                icon_event_all_day
            )
            draw.merge(
                draw_day,
                (
                    self._config.calendar_padding[3] +
                    date.weekday()*(day_size[0]-1+self._config.calendar_day_margin) +
                    (self._config.calendar_weekend_margin if date.weekday() >= 5 else 0),

                    self._config.calendar_padding[0] +
                    (date - date_from).days // 7 * (day_size[1]+self._config.calendar_day_margin)
                )
            )
            date = date + datetime.timedelta(days=1)

    def _draw_calendar_day(
            self,
            draw: EInkDraw,
            date,
            font_date_bold,
            font_date_thin,
            font_event_count,
            icon_event,
            icon_event_all_day):
        #
        # Preparation
        #
        border_width = 1
        font = font_date_thin
        if date == self._reference.date():
            border_width = 4
            font = font_date_bold
        elif date > self._reference.date() and date.month == self._reference.month:
            border_width = 2
            font = font_date_bold
        else:
            pass

        is_holiday = 1 if self._event_provider.is_holiday(date) else 0
        #
        # Border
        #
        if date < self._reference.date():
            draw_rectangle_dashed(
                draw.get_image_draw(is_holiday),
                [
                    0,
                    0,
                    draw.get_size()[0] - 2,
                    draw.get_size()[1] - 1
                ],
                width=border_width,
                outline=draw.get_color(is_holiday),
                dash=3,
                space=6)
        else:
            draw.get_image_draw(is_holiday).rectangle(
                [
                    0,
                    0,
                    draw.get_size()[0] - 2,
                    draw.get_size()[1] - 1
                ],
                width=border_width,
                outline=draw.get_color(is_holiday))

        #
        # Number
        #
        message = "{}".format(date.day)
        size = font.getsize(message)
        draw.get_image_draw(is_holiday).text(
            (self._config.calendar_date_position[0]+border_width, self._config.calendar_date_position[1]),
            message,
            font=font,
            fill=draw.get_color(is_holiday))

        #
        # Number of events
        #
        events = self._event_provider.get_events(date)
        events_all_day = self._event_provider.get_all_day_events(date)

        y = self._config.calendar_date_position[1] + size[1]+2

        if len(events_all_day) > 0:
            message = "{}".format(len(events_all_day))
            size = font.getsize(message)

            draw.get_image_draw(is_holiday).bitmap(
                (self._config.calendar_events_margin_left, y+size[1]-icon_event_all_day.height),
                icon_event_all_day,
                fill=draw.get_color(is_holiday)
            )
            draw.get_image_draw(is_holiday).text(
                (self._config.calendar_events_margin_left + icon_event_all_day.width, y),
                message,
                font=font_event_count,
                fill=draw.get_color(is_holiday)
            )

            y += size[1]

        if len(events) > 0:
            message = "{}".format(len(events))
            size = font.getsize(message)

            draw.get_image_draw(is_holiday).bitmap(
                (self._config.calendar_events_margin_left, y+size[1]-icon_event.height),
                icon_event,
                fill=draw.get_color(is_holiday)
            )
            draw.get_image_draw(is_holiday).text(
                (self._config.calendar_events_margin_left + icon_event.width, y),
                message,
                font=font_event_count,
                fill=draw.get_color(is_holiday)
            )

    def _draw_today(self, draw: EInkDraw):
        self._draw_today_date(draw)
        self._draw_today_sunrise(draw)

        draw.get_image_draw(0).line(
            [
                (0, 0),
                (0, draw.get_size()[1]-1),
                (draw.get_size()[0], draw.get_size()[1]-1)
            ],
            fill=draw.get_color(0))

    def _draw_today_date(self, draw: EInkDraw):
        subframe_size = draw.get_size()
        font_date = ImageFont.truetype(self._config.today_font, self._config.today_date_font_size)

        today = self._reference.date()
        date_string = today.strftime("%b. %d\n%a")
        date_size = font_date.getsize_multiline(date_string)
        self._logger.debug("Date string size: {}x{}px".format(date_size[0], date_size[1]))

        if self._event_provider.is_holiday(today):
            draw.get_image_draw(1).text(
                (subframe_size[0]-self._config.today_padding[1]-date_size[0], self._config.today_padding[0]),
                date_string,
                align="right",
                fill=draw.get_color(1),
                font=font_date)
        else:
            draw.get_image_draw(0).text(
                (subframe_size[0]-self._config.today_padding[1]-date_size[0], self._config.today_padding[0]),
                date_string,
                align="right",
                fill=draw.get_color(0),
                font=font_date)

    def _draw_today_sunrise(self, draw: EInkDraw):
        subframe_size = draw.get_size()
        font_sunrise = ImageFont.truetype(self._config.today_font, self._config.today_sunrise_font_size)
        icon_sun = Image.open(self._config.today_sunrise_icon).convert("1")

        # Calculate sunrise and sunset
        sun = Sun(*self._config.today_sunrise_coordinates)

        now = self._reference
        today = now.date()
        # Support for drawing calendars on any date
        next_sr = sun.get_local_sunrise_time(today)

        order = 0
        if next_sr < now:
            sun.get_local_sunrise_time(today+datetime.timedelta(days=1))
            order += 1
        next_ss = sun.get_local_sunset_time(today)
        if next_ss < now:
            sun.get_local_sunset_time(today+datetime.timedelta(days=1))
            order += 1
        if order > 1:
            order = 0

        # Check if sunrise/set time is going up or down
        trend_days = 5
        sr_direction = 0
        for i in range(trend_days):
            sr_test = sun.get_local_sunrise_time(next_sr + datetime.timedelta(days=i)) - datetime.timedelta(days=i)
            if sr_test < next_sr:
                sr_direction += -1
                break
            elif sr_test > next_sr:
                sr_direction += 1
                break
        sr_direction = (sr_direction/trend_days)

        ss_direction = 0
        for i in range(trend_days):
            ss_test = sun.get_local_sunset_time(next_ss + datetime.timedelta(days=i)) - datetime.timedelta(days=i)
            if ss_test < next_ss:
                ss_direction += -1
                break
            elif ss_test > next_ss:
                ss_direction += 1
                break
        ss_direction /= trend_days

        self._logger.debug("Next sunrise: {} (~{:.1f} min/day)".format(next_sr, sr_direction))
        self._logger.debug("Next sunset: {} (~{:.1f} min/day)".format(next_ss, ss_direction))

        # Draw sunrise/set information
        sunrise_string = next_sr.strftime("%H:%M")
        sunrise_size = font_sunrise.getsize_multiline(sunrise_string)
        sunset_string = next_ss.strftime("%H:%M")
        # We assume both strings have the same size, because of HH:MM format.

        x = self._config.today_padding[3]
        y = subframe_size[1] - sunrise_size[1] - self._config.today_padding[2]

        if order == 0:
            order = (0, 1)
        else:
            order = (1, 0)

        for i in order:
            if i == 0:
                # Draw sunrise icon
                draw.get_image_draw(1).bitmap(
                    (x, y+sunrise_size[1]-icon_sun.height - int(sr_direction*4)),
                    icon_sun,
                    fill=draw.get_color(1))
                x += icon_sun.width

                # Draw sunrise time
                draw.get_image_draw(0).text(
                    (x, y),
                    sunrise_string,
                    align="left",
                    fill=draw.get_color(0),
                    font=font_sunrise)
                # x += sunrise_size[0]

                # Second part will be aligned to the right
                x = subframe_size[0] - icon_sun.width - sunrise_size[0] - self._config.today_padding[1]
            else:
                # Draw sunset icon
                draw.get_image_draw(0).bitmap(
                    (x, y+sunrise_size[1]-icon_sun.height - int(ss_direction*4)),
                    icon_sun,
                    fill=draw.get_color(0))
                x += icon_sun.width

                # Draw sunset time
                draw.get_image_draw(0).text(
                    (x, y),
                    sunset_string,
                    align="left",
                    fill=draw.get_color(0),
                    font=font_sunrise)
                # x += sunrise_size[0]

                # Second part will be aligned to the right
                x = subframe_size[0] - icon_sun.width - sunrise_size[0] - self._config.today_padding[1]

    def _draw_tasklist(self, draw):
        font_header = ImageFont.truetype(self._config.tasklist_font_header, self._config.tasklist_font_size_header)
        font_event = ImageFont.truetype(self._config.tasklist_font_event, self._config.tasklist_font_size_event)
        icon_highlight_today = Image.open(self._config.tasklist_highlight_icon_today).convert("1")
        icon_highlight_upcoming = Image.open(self._config.tasklist_highlight_icon_upcoming).convert("1")
        icon_event_long_from = Image.open(self._config.tasklist_event_long_icon_from).convert("1")
        icon_event_long_through = Image.open(self._config.tasklist_event_long_icon_through).convert("1")
        icon_event_long_to = Image.open(self._config.tasklist_event_long_icon_to).convert("1")

        date = self._reference.date()
        date_to = datetime.date.today() + datetime.timedelta(days=self._config.tasklist_task_days)

        y = self._config.tasklist_padding[0]
        while date < date_to:
            y = self._draw_tasklist_day(draw,
                                        date,
                                        y,
                                        font_header,
                                        font_event,
                                        icon_highlight_today,
                                        icon_highlight_upcoming,
                                        icon_event_long_from,
                                        icon_event_long_through,
                                        icon_event_long_to)
            date = date + datetime.timedelta(days=1)

        draw.get_image_draw(0).line(
            [
                (0, 0),
                (0, draw.get_size()[1]-1),
            ],
            fill=draw.get_color(0))

    def _draw_tasklist_day(
            self,
            draw,
            date,
            y,
            font_header,
            font_event,
            icon_highlight_today,
            icon_highlight_upcoming,
            icon_event_long_from,
            icon_event_long_through,
            icon_event_long_to):
        events = self._event_provider.get_events(date)
        events_all_day = self._event_provider.get_all_day_events(date)
        if len(events) + len(events_all_day) < 1:
            return y

        is_upcoming = 1 if (date - self._reference.date()).days < self._config.tasklist_highlight_next_days else 0
        is_holiday = 1 if self._event_provider.is_holiday(date) else 0

        # Draw header
        message = "{:2d}-{:02d}".format(date.month, date.day)
        size = font_header.getsize(message)
        draw.get_image_draw(is_holiday).text(
            (self._config.tasklist_padding[3], y),
            message,
            font=font_header,
            fill=draw.get_color(is_holiday)
            )
        if is_upcoming:
            icon = icon_highlight_upcoming
            if date == self._reference.date():
                icon = icon_highlight_today

            draw.get_image_draw(0).bitmap(
                (
                    self._config.tasklist_padding[3]+4+size[0],
                    y+size[1]-icon.height
                ),
                icon,
                fill=draw.get_color(0)
            )
        y += size[1]+8

        for event in events_all_day + events:
            x = self._config.tasklist_padding[3]+self._config.tasklist_task_offset
            if event.all_day:
                message = event.summary
            elif event.start.date() == event.end.date():
                message = "{:2d}:{:02d} {}".format(event.start.hour, event.start.minute, event.summary)
            elif event.start.date() == date:
                draw.get_image_draw(0).bitmap(
                    (x, y),
                    icon_event_long_from,
                    fill=draw.get_color(0)
                )
                x += icon_event_long_from.width + 2
                message = "{:2d}:{:02d} {}".format(event.start.hour, event.start.minute, event.summary)
            elif event.end.date() == date:
                draw.get_image_draw(0).bitmap(
                    (x, y),
                    icon_event_long_to,
                    fill=draw.get_color(0)
                )
                x += icon_event_long_to.width + 2
                message = "{:2d}:{:02d} {}".format(event.end.hour, event.end.minute, event.summary)
            else:
                draw.get_image_draw(0).bitmap(
                    (x, y),
                    icon_event_long_through,
                    fill=draw.get_color(0)
                )
                x += icon_event_long_through.width + 4
                message = "{}".format(event.summary)

            size = font_header.getsize(message)
            draw.get_image_draw(0).text(
                (x, y),
                message,
                font=font_event,
                fill=draw.get_color(0))
            y += size[1]+4

        return y
