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
"""The date period.

This file is largely taken from the NanoParma ERP project, first written in
2021/9/16 by imacat (imacat@nanoparma.com).

"""
import typing as t
from datetime import date, timedelta

from .description import get_desc
from .month_end import month_end
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
            and self.end == month_end(self.start)
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
