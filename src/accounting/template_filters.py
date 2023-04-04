# The Mia! Accounting Project.
# Author: imacat@mail.imacat.idv.tw (imacat), 2023/2/25

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
"""The template filters.

"""
import typing as t
from datetime import date, timedelta
from decimal import Decimal

from flask_babel import get_locale

from accounting.locale import gettext


def format_amount(value: Decimal | None) -> str | None:
    """Formats an amount for readability.

    :param value: The amount.
    :return: The formatted amount text.
    """
    if value is None:
        return None
    if value == 0:
        return "-"
    whole: int = int(value)
    frac: Decimal = (value - whole).normalize()
    return "{:,}".format(whole) + str(abs(frac))[1:]


def format_date(value: date) -> str:
    """Formats a date to be human-friendly.

    :param value: The date.
    :return: The human-friendly date text.
    """
    today: date = date.today()
    if value == today:
        return gettext("Today")
    if value == today - timedelta(days=1):
        return gettext("Yesterday")
    if value == today + timedelta(days=1):
        return gettext("Tomorrow")
    locale = str(get_locale())
    if locale == "zh" or locale.startswith("zh_"):
        if value == today - timedelta(days=2):
            return gettext("The day before yesterday")
        if value == today + timedelta(days=2):
            return gettext("The day after tomorrow")
    if locale == "zh" or locale.startswith("zh_"):
        weekdays = ["一", "二", "三", "四", "五", "六", "日"]
        weekday = weekdays[value.weekday()]
    else:
        weekday = value.strftime("%a")
    if value.year != today.year:
        return "{}/{}/{}({})".format(
            value.year, value.month, value.day, weekday)
    return "{}/{}({})".format(value.month, value.day, weekday)


def default(value: t.Any, default_value: t.Any = "") -> t.Any:
    """Returns the default value if the given value is None.

    :param value: The value.
    :param default_value: The default value when the given value is None.
    :return: The value, or the default value if the given value is None.
    """
    return default_value if value is None else value
