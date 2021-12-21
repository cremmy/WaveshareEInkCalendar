import logging
import caldav
from dateutil import tz
import icalevents.icalparser as icalparser
from .IEventProvider import IEventProvider


class EventProviderCalDAV(IEventProvider):
    def __init__(self, address, is_holiday_calendar=None, week_holidays=None):
        IEventProvider.__init__(self, is_holiday_calendar, week_holidays)

        self._address = address

    def preload(self, date_from, date_to):
        logger = logging.getLogger("EventProviderCalDAV")

        logger.info("Connecting to CalDAV server...")
        cal_client = caldav.DAVClient(self._address)
        cal_principal = cal_client.principal()
        calendars = cal_principal.calendars()

        self._events = []

        for calendar in calendars:
            results = calendar.date_search(start=date_from, end=date_to)
            for result in results:
                events = icalparser.parse_events(result.data, start=date_from, end=date_to)
                for event in events:
                    event.start = event.start.replace(tzinfo=tz.tzlocal())
                    event.end = event.end.replace(tzinfo=tz.tzlocal())
                    self._events.append(event)

        self._events.sort()
        logger.info("Retrieved events from CalDAV server")
