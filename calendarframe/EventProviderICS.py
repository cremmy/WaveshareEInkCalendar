import logging
from dateutil import tz
import icalevents.icalevents as icalevents
from .IEventProvider import IEventProvider


class EventProviderICS(IEventProvider):
    def __init__(self, address=None, file=None, is_holiday_calendar=None, week_holidays=None):
        IEventProvider.__init__(self, is_holiday_calendar, week_holidays)

        self._address = address
        self._file = file

    def preload(self, date_from, date_to):
        logger = logging.getLogger("EventProviderICS")

        logger.info("Downloading ICS...")
        self._events = icalevents.events(url=self._address, file=self._file, start=date_from, end=date_to)
        for event in self._events:
            event.start = event.start.replace(tzinfo=tz.tzlocal())
            event.end = event.end.replace(tzinfo=tz.tzlocal())
        self._events.sort()

        for event in self._events:
            logger.debug("{}-{}: {}; {}".format(
                event.start,
                event.end,
                event.summary,
                "(all day)" if event.all_day else ""
            ))

        logger.info("Retrieved events from ICS file")
