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
"""The period specification parser.

"""
import calendar
import re
from datetime import date

DATE_SPEC_RE: str = r"(\d{4})(?:-(\d{2})(?:-(\d{2}))?)?"
"""The regular expression of a date specification."""


def parse_spec(text: str) -> tuple[date | None, date | None]:
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
