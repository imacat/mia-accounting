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
import typing as t
from datetime import date, timedelta

from accounting.locale import gettext
from .description import get_desc
from .specification import get_spec


class Period:
    """A date period."""

    def __init__(self, start: date | None, end: date | None):
        """Constructs a new date period.

        :param start: The start date, or None from the very beginning.
        :param end: The end date, or None till no end.
        """
        self.start: date | None = start
        """The start of the period."""
        self.end: date | None = end
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
        self.is_a_month: bool = False
        """Whether the period is a whole month."""
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

        Override this method to set the properties in the subclasses, to skip
        the calculation.

        :return: None.
        """
        self.spec = get_spec(self.start, self.end)
        self.desc = get_desc(self.start, self.end)
        if self.start is None or self.end is None:
            return
        self.is_a_month = self.start.day == 1 \
            and self.end == _month_end(self.start)
        self.is_type_month = self.is_a_month
        self.is_a_year = self.start == date(self.start.year, 1, 1) \
            and self.end == date(self.start.year, 12, 31)
        self.is_a_day = self.start == self.end

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
        return Period(None, self.start - timedelta(days=1))


class ThisMonth(Period):
    """The period of this month."""
    def __init__(self):
        today: date = date.today()
        this_month_start: date = date(today.year, today.month, 1)
        super().__init__(this_month_start, _month_end(today))
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
        today: date = date.today()
        year: int = today.year
        month: int = today.month - 1
        if month < 1:
            year = year - 1
            month = 12
        start: date = date(year, month, 1)
        super().__init__(start, _month_end(start))
        self.is_last_month = True

    def _set_properties(self) -> None:
        self.spec = "last-month"
        self.desc = gettext("Last month")
        self.is_a_month = True
        self.is_type_month = True


class SinceLastMonth(Period):
    """The period of this month."""
    def __init__(self):
        today: date = date.today()
        year: int = today.year
        month: int = today.month - 1
        if month < 1:
            year = year - 1
            month = 12
        start: date = date(year, month, 1)
        super().__init__(start, None)
        self.is_since_last_month = True

    def _set_properties(self) -> None:
        self.spec = "since-last-month"
        self.desc = gettext("Since last month")
        self.is_type_month = True


class ThisYear(Period):
    """The period of this year."""
    def __init__(self):
        year: int = date.today().year
        start: date = date(year, 1, 1)
        end: date = date(year, 12, 31)
        super().__init__(start, end)
        self.is_this_year = True

    def _set_properties(self) -> None:
        self.spec = "this-year"
        self.desc = gettext("This year")
        self.is_a_year = True


class LastYear(Period):
    """The period of last year."""
    def __init__(self):
        year: int = date.today().year
        start: date = date(year - 1, 1, 1)
        end: date = date(year - 1, 12, 31)
        super().__init__(start, end)
        self.is_last_year = True

    def _set_properties(self) -> None:
        self.spec = "last-year"
        self.desc = gettext("Last year")
        self.is_a_year = True


class Today(Period):
    """The period of today."""
    def __init__(self):
        today: date = date.today()
        super().__init__(today, today)
        self.is_today = True

    def _set_properties(self) -> None:
        self.spec = "today"
        self.desc = gettext("Today")
        self.is_a_day = True


class Yesterday(Period):
    """The period of yesterday."""
    def __init__(self):
        yesterday: date = date.today() - timedelta(days=1)
        super().__init__(yesterday, yesterday)
        self.is_yesterday = True

    def _set_properties(self) -> None:
        self.spec = "yesterday"
        self.desc = gettext("Yesterday")
        self.is_a_day = True


class AllTime(Period):
    """The period of all time."""
    def __init__(self):
        super().__init__(None, None)
        self.is_all = True

    def _set_properties(self) -> None:
        self.spec = "all-time"
        self.desc = gettext("All")


class TemplatePeriod(Period):
    """The period template."""
    def __init__(self):
        super().__init__(None, None)

    def _set_properties(self) -> None:
        self.spec = "PERIOD"


class YearPeriod(Period):
    """A year period."""

    def __init__(self, year: int):
        """Constructs a year period.

        :param year: The year.
        """
        start: date = date(year, 1, 1)
        end: date = date(year, 12, 31)
        super().__init__(start, end)


def _month_end(day: date) -> date:
    """Returns the end day of month for a date.

    :param day: The date.
    :return: The end day of the month of that day.
    """
    last_day: int = calendar.monthrange(day.year, day.month)[1]
    return date(day.year, day.month, last_day)
