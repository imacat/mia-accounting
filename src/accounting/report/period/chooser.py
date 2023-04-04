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
"""The period chooser.

This file is largely taken from the NanoParma ERP project, first written in
2021/9/16 by imacat (imacat@nanoparma.com).

"""
import typing as t
from datetime import date

from accounting.models import JournalEntry
from .period import Period
from .shortcuts import ThisMonth, LastMonth, SinceLastMonth, ThisYear, \
    LastYear, Today, Yesterday, AllTime, TemplatePeriod, YearPeriod


class PeriodChooser:
    """The period chooser."""

    def __init__(self, get_url: t.Callable[[Period], str]):
        """Constructs a period chooser.

        :param get_url: The callback to return the URL of the current report in
            a period.
        """
        self.__get_url: t.Callable[[Period], str] = get_url
        """The callback to return the URL of the current report in a period."""

        # Shortcut periods
        self.this_month_url: str = get_url(ThisMonth())
        """The URL for this month."""
        self.last_month_url: str = get_url(LastMonth())
        """The URL for last month."""
        self.since_last_month_url: str = get_url(SinceLastMonth())
        """The URL since last mint."""
        self.this_year_url: str = get_url(ThisYear())
        """The URL for this year."""
        self.last_year_url: str = get_url(LastYear())
        """The URL for last year."""
        self.today_url: str = get_url(Today())
        """The URL for today."""
        self.yesterday_url: str = get_url(Yesterday())
        """The URL for yesterday."""
        self.all_url: str = get_url(AllTime())
        """The URL for all period."""
        self.url_template: str = get_url(TemplatePeriod())
        """The URL template."""

        first: JournalEntry | None \
            = JournalEntry.query.order_by(JournalEntry.date).first()
        start: date | None = None if first is None else first.date

        # Attributes
        self.data_start: date | None = start
        """The start of the data."""
        self.has_data: bool = start is not None
        """Whether there is any data."""
        self.has_last_month: bool = False
        """Where there is data in last month."""
        self.has_last_year: bool = False
        """Whether there is data in last year."""
        self.has_yesterday: bool = False
        """Whether there is data in yesterday."""
        self.available_years: list[int] = []
        """The available years."""

        if self.has_data:
            today: date = date.today()
            self.has_last_month = start < date(today.year, today.month, 1)
            self.has_last_year = start.year < today.year
            self.has_yesterday = start < today
            if start.year < today.year - 1:
                self.available_years \
                    = reversed(range(start.year, today.year - 1))

    def year_url(self, year: int) -> str:
        """Returns the period URL of a year.

        :param year: The year
        :return: The period URL of the year.
        """
        return self.__get_url(YearPeriod(year))
