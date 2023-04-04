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
"""The template filters for the journal entry management.

"""
from decimal import Decimal
from html import escape
from urllib.parse import ParseResult, urlparse, parse_qsl, urlencode, \
    urlunparse

from flask import request


def with_type(uri: str) -> str:
    """Adds the journal entry type to the URI, if it is specified.

    :param uri: The URI.
    :return: The result URL, optionally with the journal entry type added.
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
    """Adds the transfer journal entry type to the URI.

    :param uri: The URI.
    :return: The result URL, with the transfer journal entry type added.
    """
    uri_p: ParseResult = urlparse(uri)
    params: list[tuple[str, str]] = parse_qsl(uri_p.query)
    params = [x for x in params if x[0] != "as"]
    params.append(("as", "transfer"))
    parts: list[str] = list(uri_p)
    parts[4] = urlencode(params)
    return urlunparse(parts)


def format_amount_input(value: Decimal | None) -> str:
    """Format an amount for an input value.

    :param value: The amount.
    :return: The formatted amount text for an input value.
    """
    if value is None:
        return ""
    whole: int = int(value)
    frac: Decimal = (value - whole).normalize()
    return str(whole) + str(frac)[1:]


def text2html(value: str) -> str:
    """Converts plain text into HTML.

    :param value: The plain text.
    :return: The HTML.
    """
    s: str = escape(value)
    s = s.replace("\n", "<br>")
    s = s.replace("  ", " &nbsp;")
    return s
