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
"""The period description composer.

"""
from datetime import date, timedelta

from accounting.locale import gettext


def get_desc(start: date | None, end: date | None) -> str:
    """Returns the period description.

    :param start: The start of the period.
    :param end: The end of the period.
    :return: The period description.
    """
    if start is None and end is None:
        return gettext("for all time")
    if start is None:
        return __get_until_desc(end)
    if end is None:
        return __get_since_desc(start)
    try:
        return __get_year_desc(start, end)
    except ValueError:
        pass
    try:
        return __get_month_desc(start, end)
    except ValueError:
        pass
    return __get_day_desc(start, end)


def __get_since_desc(start: date) -> str:
    """Returns the description without the end day.

    :param start: The start of the period.
    :return: The description without the end day.
    """

    def get_start_desc() -> str:
        """Returns the description of the start day.

        :return: The description of the start day.
        """
        if start.month == 1 and start.day == 1:
            return str(start.year)
        if start.day == 1:
            return __format_month(start)
        return __format_day(start)

    return gettext("since %(start)s", start=get_start_desc())


def __get_until_desc(end: date) -> str:
    """Returns the description without the start day.

    :param end: The end of the period.
    :return: The description without the start day.
    """

    def get_end_desc() -> str:
        """Returns the description of the end day.

        :return: The description of the end day.
        """
        if end.month == 12 and end.day == 31:
            return str(end.year)
        if (end + timedelta(days=1)).day == 1:
            return __format_month(end)
        return __format_day(end)

    return gettext("until %(end)s", end=get_end_desc())


def __get_year_desc(start: date, end: date) -> str:
    """Returns the description as a year range.

    :param start: The start of the period.
    :param end: The end of the period.
    :return: The description as a year range.
    :raise ValueError: The period is not a year range.
    """
    if start.month != 1 or start.day != 1 \
            or end.month != 12 or end.day != 31:
        raise ValueError
    start_text: str = str(start.year)
    if start.year == end.year:
        return __get_in_desc(start_text)
    return __get_from_to_desc(start_text, str(end.year))


def __get_month_desc(start: date, end: date) -> str:
    """Returns the description as a month range.

    :param start: The start of the period.
    :param end: The end of the period.
    :return: The description as a month range.
    :raise ValueError: The period is not a month range.
    """
    if start.day != 1 or (end + timedelta(days=1)).day != 1:
        raise ValueError
    start_text: str = __format_month(start)
    if start.year == end.year and start.month == end.month:
        return __get_in_desc(start_text)
    if start.year == end.year:
        return __get_from_to_desc(start_text, str(end.month))
    return __get_from_to_desc(start_text, __format_month(end))


def __get_day_desc(start: date, end: date) -> str:
    """Returns the description as a day range.

    :param start: The start of the period.
    :param end: The end of the period.
    :return: The description as a day range.
    :raise ValueError: The period is a month or year range.
    """
    start_text: str = __format_day(start)
    if start == end:
        return __get_in_desc(start_text)
    if start.year == end.year and start.month == end.month:
        return __get_from_to_desc(start_text, str(end.day))
    if start.year == end.year:
        end_month_day: str = f"{end.month}/{end.day}"
        return __get_from_to_desc(start_text, end_month_day)
    return __get_from_to_desc(start_text, __format_day(end))


def __format_month(month: date) -> str:
    """Formats a month.

    :param month: The month.
    :return: The formatted month.
    """
    return f"{month.year}/{month.month}"


def __format_day(day: date) -> str:
    """Formats a day.

    :param day: The day.
    :return: The formatted day.
    """
    return f"{day.year}/{day.month}/{day.day}"


def __get_in_desc(period: str) -> str:
    """Returns the description of a whole year, month, or day.

    :param period: The time period.
    :return: The description of a whole year, month, or day.
    """
    return gettext("in %(period)s", period=period)


def __get_from_to_desc(start: str, end: str) -> str:
    """Returns the description of a separated start and end.

    :param start: The start.
    :param end: The end.
    :return: The description of the separated start and end.
    """
    return gettext("in %(start)s-%(end)s", start=start, end=end)
