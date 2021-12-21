from abc import ABC, abstractmethod


class IEventProvider(ABC):
    def __init__(self, is_holiday_calendar=False, week_holidays=[6], holiday_description_tag="#holiday"):
        """
        Base class for event providers
        :param is_holiday_calendar: Treat days with events as holidays
        :param week_holidays: Which days of the week are holidays
        """
        if is_holiday_calendar is None:
            is_holiday_calendar = False
        if week_holidays is None:
            week_holidays = [6]

        self._is_holiday_calendar = is_holiday_calendar
        self._week_holidays = week_holidays

        self._events = None

    @abstractmethod
    def preload(self, date_from, date_to):
        pass

    def get_events(self, date):
        events = []

        for event in self._events:
            if event.all_day:
                continue
            if self._is_event_on_date(event, date):
                events.append(event)

        return events

    def get_all_day_events(self, date):
        events = []

        for event in self._events:
            if not event.all_day:
                continue
            if self._is_event_on_date(event, date):
                events.append(event)

        return events

    def is_holiday(self, date):
        if date.weekday() in self._week_holidays:
            return True

        if self._is_holiday_calendar:
            for event in self._events:
                if self._is_event_on_date(event, date):
                    return True

        # if self._holiday_description_tag is not None and self._holiday_description_tag in event.description:
        #     return True

        return False

    @staticmethod
    def _is_event_on_date(event, date):
        if event.all_day:
            if event.start.date() <= date < event.end.date():
                return True
        else:
            if event.start.date() <= date <= event.end.date():
                return True

        return False
