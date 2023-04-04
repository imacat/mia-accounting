# The Mia! Accounting Project.
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
"""The named shortcut periods.

"""
from datetime import date, timedelta

from accounting.locale import gettext
from .month_end import month_end
from .period import Period


class ThisMonth(Period):
    """The period of this month."""
    def __init__(self):
        today: date = date.today()
        this_month_start: date = date(today.year, today.month, 1)
        super().__init__(this_month_start, month_end(today))
        self.is_default = True
        self.is_this_month = True

    def _set_properties(self) -> None:
        self.spec = "this-month"
        self.desc = gettext("This Month")
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
        super().__init__(start, month_end(start))
        self.is_last_month = True

    def _set_properties(self) -> None:
        self.spec = "last-month"
        self.desc = gettext("Last Month")
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
        self.desc = gettext("Since Last Month")
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
        self.desc = gettext("This Year")
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
        self.desc = gettext("Last Year")
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
