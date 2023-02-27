# The Mia! Accounting Flask Project.
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
"""The template filters and globals for the transaction management.

"""
from datetime import date, timedelta
from decimal import Decimal
from html import escape
from urllib.parse import ParseResult, urlparse, parse_qsl, urlencode, \
    urlunparse

from flask import request, current_app
from flask_babel import get_locale

from accounting.locale import gettext
from accounting.models import Currency


def with_type(uri: str) -> str:
    """Adds the transaction type to the URI, if it is specified.

    :param uri: The URI.
    :return: The result URL, optionally with the transaction type added.
    """
    if "as" not in request.args:
        return uri
    uri_p: ParseResult = urlparse(uri)
    params: list[tuple[str, str]] = parse_qsl(uri_p.query)
    params = [x for x in params if x[0] != "as"]
    params.append(("as", request.args["as"]))
    parts: list[str] = list(uri_p)
    parts[4] = urlencode(params)
    return urlunparse(parts)


def to_transfer(uri: str) -> str:
    """Adds the transfer transaction type to the URI.

    :param uri: The URI.
    :return: The result URL, with the transfer transaction type added.
    """
    uri_p: ParseResult = urlparse(uri)
    params: list[tuple[str, str]] = parse_qsl(uri_p.query)
    params = [x for x in params if x[0] != "as"]
    params.append(("as", "transfer"))
    parts: list[str] = list(uri_p)
    parts[4] = urlencode(params)
    return urlunparse(parts)


def format_amount(value: Decimal | None) -> str:
    """Formats an amount for readability.

    :param value: The amount.
    :return: The formatted amount text.
    """
    if value is None or value == 0:
        return "-"
    whole: int = int(value)
    frac: Decimal = (value - whole).normalize()
    return "{:,}".format(whole) + str(frac)[1:]


def format_amount_input(value: Decimal) -> str:
    """Format an amount for an input value.

    :param value: The amount.
    :return: The formatted amount text for an input value.
    """
    whole: int = int(value)
    frac: Decimal = (value - whole).normalize()
    return str(whole) + str(frac)[1:]


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


def text2html(value: str) -> str:
    """Converts plain text into HTML.

    :param value: The plain text.
    :return: The HTML.
    """
    s: str = escape(value)
    s = s.replace("\n", "<br>")
    s = s.replace("  ", " &nbsp;")
    return s


def currency_options() -> str:
    """Returns the currency options.

    :return: The currency options.
    """
    return Currency.query.order_by(Currency.code).all()


def default_currency_code() -> str:
    """Returns the default currency code.

    :return: The default currency code.
    """
    with current_app.app_context():
        return current_app.config.get("DEFAULT_CURRENCY", "USD")
