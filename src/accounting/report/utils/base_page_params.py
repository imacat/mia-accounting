# The Mia! Accounting Project.
# Author: imacat@mail.imacat.idv.tw (imacat), 2023/3/6

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
"""The page parameters of a report.

"""
import typing as t
from abc import ABC, abstractmethod
from urllib.parse import urlparse, ParseResult, parse_qsl, urlencode, \
    urlunparse

import sqlalchemy as sa
from flask import request

from accounting import db
from accounting.models import Currency, JournalEntryLineItem
from accounting.utils.journal_entry_types import JournalEntryType
from .option_link import OptionLink
from .report_chooser import ReportChooser


class BasePageParams(ABC):
    """The base HTML page parameters class."""

    @property
    @abstractmethod
    def has_data(self) -> bool:
        """Returns whether there is any data on the page.

        :return: True if there is any data, or False otherwise.
        """

    @property
    @abstractmethod
    def report_chooser(self) -> ReportChooser:
        """Returns the report chooser.

        :return: The report chooser.
        """

    @property
    def journal_entry_types(self) -> t.Type[JournalEntryType]:
        """Returns the journal entry types.

        :return: The journal entry types.
        """
        return JournalEntryType

    @property
    def csv_uri(self) -> str:
        uri: str = request.full_path if request.query_string \
            else request.path
        uri_p: ParseResult = urlparse(uri)
        params: list[tuple[str, str]] = parse_qsl(uri_p.query)
        params = [x for x in params if x[0] != "as"]
        params.append(("as", "csv"))
        parts: list[str] = list(uri_p)
        parts[4] = urlencode(params)
        return urlunparse(parts)

    @staticmethod
    def _get_currency_options(get_url: t.Callable[[Currency], str],
                              active_currency: Currency) -> list[OptionLink]:
        """Returns the currency options.

        :param get_url: The callback to return the URL of a currency.
        :param active_currency: The active currency.
        :return: The currency options.
        """
        in_use: set[str] = set(db.session.scalars(
            sa.select(JournalEntryLineItem.currency_code)
            .group_by(JournalEntryLineItem.currency_code)).all())
        return [OptionLink(str(x), get_url(x), x.code == active_currency.code)
                for x in Currency.query.filter(Currency.code.in_(in_use))
                .order_by(Currency.code).all()]
