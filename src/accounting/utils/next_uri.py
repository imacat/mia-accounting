# The Mia! Accounting Project.
# Author: imacat@mail.imacat.idv.tw (imacat), 2023/2/1

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
"""The utilities to handle the next URI.

This module should not import any other module from the application.

"""
from urllib.parse import urlparse, parse_qsl, ParseResult, urlencode, \
    urlunparse

from flask import request, Blueprint


def append_next(uri: str) -> str:
    """Appends the current URI as the next URI to the query argument.

    :param uri: The URI.
    :return: The URI with the current URI appended as the next URI.
    """
    next_uri: str = request.full_path if request.query_string else request.path
    return __set_next(uri, next_uri)


def inherit_next(uri: str) -> str:
    """Inherits the current next URI to the query argument, if exists.

    :param uri: The URI.
    :return: The URI with the current next URI added at the query argument.
    """
    next_uri: str | None = request.form.get("next") \
        if request.method == "POST" else request.args.get("next")
    if next_uri is None:
        return uri
    return __set_next(uri, next_uri)


def or_next(uri: str) -> str:
    """Returns the next URI, if exists, or the supplied URI.

    :param uri: The URI.
    :return: The next URI or the supplied URI.
    """
    next_uri: str | None = request.form.get("next") \
        if request.method == "POST" else request.args.get("next")
    return uri if next_uri is None else next_uri


def __set_next(uri: str, next_uri: str) -> str:
    """Sets the next URI to the query arguments.

    :param uri: The URI.
    :param next_uri: The next URI.
    :return: The URI with the next URI set.
    """
    uri_p: ParseResult = urlparse(uri)
    params: list[tuple[str, str]] = parse_qsl(uri_p.query)
    params = [x for x in params if x[0] != "next"]
    params.append(("next", next_uri))
    parts: list[str] = list(uri_p)
    parts[4] = urlencode(params)
    return urlunparse(parts)


def init_app(bp: Blueprint) -> None:
    """Initializes the application.

    :param bp: The blueprint of the accounting application.
    :return: None.
    """
    bp.add_app_template_filter(append_next, "accounting_append_next")
    bp.add_app_template_filter(inherit_next, "accounting_inherit_next")
    bp.add_app_template_filter(or_next, "accounting_or_next")
