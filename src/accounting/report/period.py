# The Mia! Accounting Flask Project.
# Author: imacat@mail.imacat.idv.tw (imacat), 2023/3/4

#  Copyright (c) 2023 imacat.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
"""The date period.

This file is largely taken from the NanoParma ERP project, first written in
2021/9/16 by imacat (imacat@nanoparma.com).

"""
import calendar
import datetime
import re
import typing as t

from accounting.locale import gettext


class Period:
    """A date period."""

    def __init__(self, start: datetime.date | None, end: datetime.date | None):
        """Constructs a new date period.

        :param start: The start date, or None from the very beginning.
        :param end: The end date, or None till no end.
        """
        self.start: datetime.date | None = start
        """The start of the period."""
        self.end: datetime.date | None = end
        """The end of the period."""
        self.is_default: bool = False
        """Whether the is the default period."""
        self.is_this_month: bool = False
        """Whether the period is this month."""
        self.is_last_month: bool = False
        """Whether the period is last month."""
        self.is_since_last_month: bool = False
        """Whether the period is since last month."""
        self.is_this_year: bool = False
        """Whether the period is this year."""
        self.is_last_year: bool = False
        """Whether the period is last year."""
        self.is_today: bool = False
        """Whether the period is today."""
        self.is_yesterday: bool = False
        """Whether the period is yesterday."""
        self.is_all: bool = start is None and end is None
        """Whether the period is all time."""
        self.spec: str = ""
        """The period specification."""
        self.desc: str = ""
        """The text description."""
        self.is_type_month: bool = False
        """Whether the period is for the month chooser."""
        self.is_a_year: bool = False
        """Whether the period is a whole year."""
        self.is_a_day: bool = False
        """Whether the period is a single day."""
        self._set_properties()

    def _set_properties(self) -> None:
        """Sets the following properties.

        * self.spec
        * self.desc
        * self.is_a_month
        * self.is_type_month
        * self.is_a_year
        * self.is_a_day

        Override this method to set the properties in the subclasses.

        :return: None.
        """
        self.spec = self.__get_spec()
        self.desc = self.__get_desc()
        if self.start is None or self.end is None:
            return
        self.is_type_month \
            = self.start.day == 1 and self.end == _month_end(self.start)
        self.is_a_year = self.start == datetime.date(self.start.year, 1, 1) \
            and self.end == datetime.date(self.start.year, 12, 31)
        self.is_a_day = self.start == self.end

    @classmethod
    def get_instance(cls, spec: str | None = None) -> t.Self:
        """Returns a period instance.

        :param spec: The period specification, or omit for the default.
        :return: The period instance.
        :raise ValueError: When the period is invalid.
        """
        if spec is None:
            return ThisMonth()
        named_periods: dict[str, t.Type[t.Callable[[], Period]]] = {
            "this-month": lambda: ThisMonth(),
            "last-month": lambda: LastMonth(),
            "since-last-month": lambda: SinceLastMonth(),
            "this-year": lambda: ThisYear(),
            "last-year": lambda: LastYear(),
            "today": lambda: Today(),
            "yesterday": lambda: Yesterday(),
        }
        if spec in named_periods:
            return named_periods[spec]()
        start: datetime.date
        end: datetime.date
        start, end = _parse_period_spec(spec)
        if start is not None and end is not None and start > end:
            raise ValueError
        return cls(start, end)

    def __get_spec(self) -> str:
        """Returns the period specification.

        :return: The period specification.
        """
        if self.start is None:
            if self.end is None:
                return "-"
            else:
                if self.end.day != _month_end(self.end).day:
                    return "-%04d-%02d-%02d" % (
                        self.end.year, self.end.month, self.end.day)
                if self.end.month != 12:
                    return "-%04d-%02d" % (self.end.year, self.end.month)
                return "-%04d" % self.end.year
        else:
            if self.end is None:
                if self.start.day != 1:
                    return "%04d-%02d-%02d-" % (
                        self.start.year, self.start.month, self.start.day)
                if self.start.month != 1:
                    return "%04d-%02d-" % (self.start.year, self.start.month)
                return "%04d-" % self.start.year
            else:
                try:
                    return self.__get_year_spec()
                except ValueError:
                    pass
                try:
                    return self.__get_month_spec()
                except ValueError:
                    pass
                return self.__get_day_spec()

    def __get_year_spec(self) -> str:
        """Returns the period specification as a year range.

        :return: The period specification as a year range.
        :raise ValueError: The period is not a year range.
        """
        if self.start.month != 1 or self.start.day != 1 \
                or self.end.month != 12 or self.end.day != 31:
            raise ValueError
        if self.start.year == self.end.year:
            return "%04d" % self.start.year
        return "%04d-%04d" % (self.start.year, self.end.year)

    def __get_month_spec(self) -> str:
        """Returns the period specification as a month range.

        :return: The period specification as a month range.
        :raise ValueError: The period is not a month range.
        """
        if self.start.day != 1 or self.end != _month_end(self.end):
            raise ValueError
        if self.start.year == self.end.year \
                and self.start.month == self.end.month:
            return "%04d-%02d" % (self.start.year, self.start.month)
        return "%04d-%02d-%04d-%02d" % (
            self.start.year, self.start.month,
            self.end.year, self.end.month)

    def __get_day_spec(self) -> str:
        """Returns the period specification as a day range.

        :return: The period specification as a day range.
        :raise ValueError: The period is a month or year range.
        """
        if self.start == self.end:
            return "%04d-%02d-%02d" % (
                self.start.year, self.start.month, self.start.day)
        return "%04d-%02d-%02d-%04d-%02d-%02d" % (
            self.start.year, self.start.month, self.start.day,
            self.end.year, self.end.month, self.end.day)

    def __get_desc(self) -> str:
        """Returns the period description.

        :return: The period description.
        """
        cls: t.Type[t.Self] = self.__class__
        if self.start is None:
            if self.end is None:
                return gettext("for all time")
            else:
                if self.end != _month_end(self.end):
                    return gettext("until %(end)s",
                                   end=cls.__format_date(self.end))
                if self.end.month != 12:
                    return gettext("until %(end)s",
                                   end=cls.__format_month(self.end))
                return gettext("until %(end)s", end=str(self.end.year))
        else:
            if self.end is None:
                if self.start.day != 1:
                    return gettext("since %(start)s",
                                   start=cls.__format_date(self.start))
                if self.start.month != 1:
                    return gettext("since %(start)s",
                                   start=cls.__format_month(self.start))
                return gettext("since %(start)s", start=str(self.start.year))
            else:
                try:
                    return self.__get_year_desc()
                except ValueError:
                    pass
                try:
                    return self.__get_month_desc()
                except ValueError:
                    pass
                return self.__get_day_desc()

    @staticmethod
    def __format_date(date: datetime.date) -> str:
        """Formats a date.

        :param date: The date.
        :return: The formatted date.
        """
        return F"{date.year}/{date.month}/{date.day}"

    @staticmethod
    def __format_month(month: datetime.date) -> str:
        """Formats a month.

        :param month: The month.
        :return: The formatted month.
        """
        return F"{month.year}/{month.month}"

    def __get_year_desc(self) -> str:
        """Returns the description as a year range.

        :return: The description as a year range.
        :raise ValueError: The period is not a year range.
        """
        if self.start.month != 1 or self.start.day != 1 \
                or self.end.month != 12 or self.end.day != 31:
            raise ValueError
        start: str = str(self.start.year)
        if self.start.year == self.end.year:
            return gettext("in %(period)s", period=start)
        end: str = str(self.end.year)
        return gettext("in %(start)s-%(end)s", start=start, end=end)

    def __get_month_desc(self) -> str:
        """Returns the description as a month range.

        :return: The description as a month range.
        :raise ValueError: The period is not a month range.
        """
        if self.start.day != 1 or self.end != _month_end(self.end):
            raise ValueError
        start: str = F"{self.start.year}/{self.start.month}"
        if self.start.year == self.end.year \
                and self.start.month == self.end.month:
            return gettext("in %(period)s", period=start)
        if self.start.year == self.end.year:
            end_month: str = str(self.end.month)
            return gettext("in %(start)s-%(end)s", start=start, end=end_month)
        end: str = F"{self.end.year}/{self.end.month}"
        return gettext("in %(start)s-%(end)s", start=start, end=end)

    def __get_day_desc(self) -> str:
        """Returns the description as a day range.

        :return: The description as a day range.
        :raise ValueError: The period is a month or year range.
        """
        start: str = F"{self.start.year}/{self.start.month}/{self.start.day}"
        if self.start == self.end:
            return gettext("in %(period)s", period=start)
        if self.start.year == self.end.year \
                and self.start.month == self.end.month:
            end_day: str = str(self.end.day)
            return gettext("in %(start)s-%(end)s", start=start, end=end_day)
        if self.start.year == self.end.year:
            end_month_day: str = F"{self.end.month}/{self.end.day}"
            return gettext("in %(start)s-%(end)s",
                           start=start, end=end_month_day)
        end: str = F"{self.end.year}/{self.end.month}/{self.end.day}"
        return gettext("in %(start)s-%(end)s", start=start, end=end)

    def is_year(self, year: int) -> bool:
        """Returns whether the period is the specific year period.

        :param year: The year.
        :return: True if the period is the year period, or False otherwise.
        """
        if not self.is_a_year:
            return False
        return self.start.year == year

    @property
    def is_type_arbitrary(self) -> bool:
        """Returns whether this period is an arbitrary period.

        :return: True if this is an arbitrary period, or False otherwise.
        """
        return not self.is_type_month and not self.is_a_year \
            and not self.is_a_day

    @property
    def before(self) -> t.Self | None:
        """Returns the period before this period.

        :return: The period before this period.
        """
        if self.start is None:
            return None
        return self.__class__(None, self.start - datetime.timedelta(days=1))


class ThisMonth(Period):
    """The period of this month."""
    def __init__(self):
        today: datetime.date = datetime.date.today()
        this_month_start: datetime.date \
            = datetime.date(today.year, today.month, 1)
        super(ThisMonth, self).__init__(this_month_start, _month_end(today))
        self.is_default = True
        self.is_this_month = True

    def _set_properties(self) -> None:
        self.spec = "this-month"
        self.desc = gettext("This month")
        self.is_a_month = True
        self.is_type_month = True


class LastMonth(Period):
    """The period of this month."""
    def __init__(self):
        today: datetime.date = datetime.date.today()
        year: int = today.year
        month: int = today.month - 1
        if month < 1:
            year = year - 1
            month = 12
        start: datetime.date = datetime.date(year, month, 1)
        super(LastMonth, self).__init__(start, _month_end(start))
        self.is_last_month = True

    def _set_properties(self) -> None:
        self.spec = "last-month"
        self.desc = gettext("Last month")
        self.is_a_month = True
        self.is_type_month = True


class SinceLastMonth(Period):
    """The period of this month."""
    def __init__(self):
        today: datetime.date = datetime.date.today()
        year: int = today.year
        month: int = today.month - 1
        if month < 1:
            year = year - 1
            month = 12
        start: datetime.date = datetime.date(year, month, 1)
        super(SinceLastMonth, self).__init__(start, None)
        self.is_since_last_month = True

    def _set_properties(self) -> None:
        self.spec = "since-last-month"
        self.desc = gettext("Since last month")
        self.is_type_month = True


class ThisYear(Period):
    """The period of this year."""
    def __init__(self):
        year: int = datetime.date.today().year
        start: datetime.date = datetime.date(year, 1, 1)
        end: datetime.date = datetime.date(year, 12, 31)
        super(ThisYear, self).__init__(start, end)
        self.is_this_year = True

    def _set_properties(self) -> None:
        self.spec = "this-year"
        self.desc = gettext("This year")
        self.is_a_year = True


class LastYear(Period):
    """The period of last year."""
    def __init__(self):
        year: int = datetime.date.today().year
        start: datetime.date = datetime.date(year - 1, 1, 1)
        end: datetime.date = datetime.date(year - 1, 12, 31)
        super(LastYear, self).__init__(start, end)
        self.is_last_year = True

    def _set_properties(self) -> None:
        self.spec = "last-year"
        self.desc = gettext("Last year")
        self.is_a_year = True


class Today(Period):
    """The period of today."""
    def __init__(self):
        today: datetime.date = datetime.date.today()
        super(Today, self).__init__(today, today)
        self.is_this_year = True

    def _set_properties(self) -> None:
        self.spec = "today"
        self.desc = gettext("Today")
        self.is_a_day = True
        self.is_today = True


class Yesterday(Period):
    """The period of yesterday."""
    def __init__(self):
        yesterday: datetime.date \
            = datetime.date.today() - datetime.timedelta(days=1)
        super(Yesterday, self).__init__(yesterday, yesterday)
        self.is_this_year = True

    def _set_properties(self) -> None:
        self.spec = "yesterday"
        self.desc = gettext("Yesterday")
        self.is_a_day = True
        self.is_yesterday = True


class TemplatePeriod(Period):
    """The period template."""
    def __init__(self):
        super(TemplatePeriod, self).__init__(None, None)

    def _set_properties(self) -> None:
        self.spec = "PERIOD"


class YearPeriod(Period):
    """A year period."""
    def __init__(self, year: int):
        """Constructs a year period.

        :param year: The year.
        """
        start: datetime.date = datetime.date(year, 1, 1)
        end: datetime.date = datetime.date(year, 12, 31)
        super(YearPeriod, self).__init__(start, end)
        self.spec = str(year)
        self.is_a_year = True

    def _set_properties(self) -> None:
        pass


def _parse_period_spec(text: str) \
        -> tuple[datetime.date | None, datetime.date | None]:
    """Parses the period specification.

    :param text: The period specification.
    :return: The start and end day of the period.  The start and end day
        may be None.
    :raise ValueError: When the date is invalid.
    """
    if text == "this-month":
        today: datetime.date = datetime.date.today()
        return datetime.date(today.year, today.month, 1), _month_end(today)
    if text == "-":
        return None, None
    m = re.match(r"^(\d{4})(?:-(\d{2})(?:-(\d{2}))?)?$", text)
    if m is not None:
        return __get_start(m[1], m[2], m[3]), \
               __get_end(m[1], m[2], m[3])
    m = re.match(r"^(\d{4})(?:-(\d{2})(?:-(\d{2}))?)?-$", text)
    if m is not None:
        return __get_start(m[1], m[2], m[3]), None
    m = re.match(r"-(\d{4})(?:-(\d{2})(?:-(\d{2}))?)?$", text)
    if m is not None:
        return None, __get_end(m[1], m[2], m[3])
    m = re.match(r"^(\d{4})(?:-(\d{2})(?:-(\d{2}))?)?-(\d{4})(?:-(\d{2})(?:-(\d{2}))?)?$", text)
    if m is not None:
        return __get_start(m[1], m[2], m[3]), \
               __get_end(m[4], m[5], m[6])
    raise ValueError


def __get_start(year: str, month: str | None, day: str | None)\
        -> datetime.date:
    """Returns the start of the period from the date representation.

    :param year: The year.
    :param month: The month, if any.
    :param day: The day, if any.
    :return: The start of the period.
    :raise ValueError: When the date is invalid.
    """
    if day is not None:
        return datetime.date(int(year), int(month), int(day))
    if month is not None:
        return datetime.date(int(year), int(month), 1)
    return datetime.date(int(year), 1, 1)


def __get_end(year: str, month: str | None, day: str | None)\
        -> datetime.date:
    """Returns the end of the period from the date representation.

    :param year: The year.
    :param month: The month, if any.
    :param day: The day, if any.
    :return: The end of the period.
    :raise ValueError: When the date is invalid.
    """
    if day is not None:
        return datetime.date(int(year), int(month), int(day))
    if month is not None:
        year_n: int = int(year)
        month_n: int = int(month)
        day_n: int = calendar.monthrange(year_n, month_n)[1]
        return datetime.date(year_n, month_n, day_n)
    return datetime.date(int(year), 12, 31)


def _month_end(date: datetime.date) -> datetime.date:
    """Returns the end day of month for a date.

    :param date: The date.
    :return: The end day of the month of that day.
    """
    day: int = calendar.monthrange(date.year, date.month)[1]
    return datetime.date(date.year, date.month, day)
