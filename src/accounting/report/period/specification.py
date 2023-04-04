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
"""The period specification composer.

"""
from datetime import date, timedelta


def get_spec(start: date | None, end: date | None) -> str:
    """Returns the period specification.

    :param start: The start of the period.
    :param end: The end of the period.
    :return: The period specification.
    """
    if start is None and end is None:
        return "-"
    if end is None:
        return __get_since_spec(start)
    if start is None:
        return __get_until_spec(end)
    try:
        return __get_year_spec(start, end)
    except ValueError:
        pass
    try:
        return __get_month_spec(start, end)
    except ValueError:
        pass
    return __get_day_spec(start, end)


def __get_since_spec(start: date) -> str:
    """Returns the period specification without the end day.

    :param start: The start of the period.
    :return: The period specification without the end day
    """
    if start.month == 1 and start.day == 1:
        return start.strftime("%Y-")
    if start.day == 1:
        return start.strftime("%Y-%m-")
    return start.strftime("%Y-%m-%d-")


def __get_until_spec(end: date) -> str:
    """Returns the period specification without the start day.

    :param end: The end of the period.
    :return: The period specification without the start day
    """
    if end.month == 12 and end.day == 31:
        return end.strftime("-%Y")
    if (end + timedelta(days=1)).day == 1:
        return end.strftime("-%Y-%m")
    return end.strftime("-%Y-%m-%d")


def __get_year_spec(start: date, end: date) -> str:
    """Returns the period specification as a year range.

    :param start: The start of the period.
    :param end: The end of the period.
    :return: The period specification as a year range.
    :raise ValueError: The period is not a year range.
    """
    if start.month != 1 or start.day != 1 \
            or end.month != 12 or end.day != 31:
        raise ValueError
    start_spec: str = start.strftime("%Y")
    if start.year == end.year:
        return start_spec
    end_spec: str = end.strftime("%Y")
    return f"{start_spec}-{end_spec}"


def __get_month_spec(start: date, end: date) -> str:
    """Returns the period specification as a month range.

    :param start: The start of the period.
    :param end: The end of the period.
    :return: The period specification as a month range.
    :raise ValueError: The period is not a month range.
    """
    if start.day != 1 or (end + timedelta(days=1)).day != 1:
        raise ValueError
    start_spec: str = start.strftime("%Y-%m")
    if start.year == end.year and start.month == end.month:
        return start_spec
    end_spec: str = end.strftime("%Y-%m")
    return f"{start_spec}-{end_spec}"


def __get_day_spec(start: date, end: date) -> str:
    """Returns the period specification as a day range.

    :param start: The start of the period.
    :param end: The end of the period.
    :return: The period specification as a day range.
    :raise ValueError: The period is a month or year range.
    """
    start_spec: str = start.strftime("%Y-%m-%d")
    if start == end:
        return start_spec
    end_spec: str = end.strftime("%Y-%m-%d")
    return f"{start_spec}-{end_spec}"
