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
"""The period specification parser.

"""
import calendar
import re
import typing as t
from datetime import date

from .period import Period
from .shortcuts import ThisMonth, LastMonth, SinceLastMonth, ThisYear, \
    LastYear, Today, Yesterday, AllTime

DATE_SPEC_RE: str = r"(\d{4})(?:-(\d{2})(?:-(\d{2}))?)?"
"""The regular expression of a date specification."""


def get_period(spec: str | None = None) -> Period:
    """Returns a period instance.

    :param spec: The period specification, or omit for the default.
    :return: The period instance.
    :raise ValueError: When the period specification is invalid.
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
        "all-time": lambda: AllTime(),
    }
    if spec in named_periods:
        return named_periods[spec]()
    start, end = __parse_spec(spec)
    if start is not None and end is not None and start > end:
        raise ValueError
    return Period(start, end)


def __parse_spec(text: str) -> tuple[date | None, date | None]:
    """Parses the period specification.

    :param text: The period specification.
    :return: The start and end day of the period.  The start and end day
        may be None.
    :raise ValueError: When the date is invalid.
    """
    if text == "-":
        return None, None
    m = re.match(f"^{DATE_SPEC_RE}$", text)
    if m is not None:
        return __get_start(m[1], m[2], m[3]), \
               __get_end(m[1], m[2], m[3])
    m = re.match(f"^{DATE_SPEC_RE}-$", text)
    if m is not None:
        return __get_start(m[1], m[2], m[3]), None
    m = re.match(f"-{DATE_SPEC_RE}$", text)
    if m is not None:
        return None, __get_end(m[1], m[2], m[3])
    m = re.match(f"^{DATE_SPEC_RE}-{DATE_SPEC_RE}$", text)
    if m is not None:
        return __get_start(m[1], m[2], m[3]), \
               __get_end(m[4], m[5], m[6])
    raise ValueError


def __get_start(year: str, month: str | None, day: str | None) -> date:
    """Returns the start of the period from the date representation.

    :param year: The year.
    :param month: The month, if any.
    :param day: The day, if any.
    :return: The start of the period.
    :raise ValueError: When the date is invalid.
    """
    if day is not None:
        return date(int(year), int(month), int(day))
    if month is not None:
        return date(int(year), int(month), 1)
    return date(int(year), 1, 1)


def __get_end(year: str, month: str | None, day: str | None) -> date:
    """Returns the end of the period from the date representation.

    :param year: The year.
    :param month: The month, if any.
    :param day: The day, if any.
    :return: The end of the period.
    :raise ValueError: When the date is invalid.
    """
    if day is not None:
        return date(int(year), int(month), int(day))
    if month is not None:
        year_n: int = int(year)
        month_n: int = int(month)
        day_n: int = calendar.monthrange(year_n, month_n)[1]
        return date(year_n, month_n, day_n)
    return date(int(year), 12, 31)
