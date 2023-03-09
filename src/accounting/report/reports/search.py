# The Mia! Accounting Flask Project.
# Author: imacat@mail.imacat.idv.tw (imacat), 2023/3/8

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
"""The search.

"""
from datetime import datetime
from decimal import Decimal

import sqlalchemy as sa
from flask import Response, render_template, request
from sqlalchemy.orm import selectinload

from accounting.locale import gettext
from accounting.models import Currency, CurrencyL10n, Account, AccountL10n, \
    Transaction, JournalEntry
from accounting.utils.pagination import Pagination
from accounting.utils.query import parse_query_keywords
from .journal import get_csv_rows
from .utils.base_page_params import BasePageParams
from .utils.base_report import BaseReport
from .utils.csv_export import csv_download
from .utils.report_chooser import ReportChooser
from .utils.report_type import ReportType


class EntryCollector:
    """The report entry collector."""

    def __init__(self):
        """Constructs the report entry collector."""
        self.entries: list[JournalEntry] = self.__query_entries()
        """The report entries."""

    def __query_entries(self) -> list[JournalEntry]:
        """Queries and returns the journal entries.

        :return: The journal entries.
        """
        keywords: list[str] = parse_query_keywords(request.args.get("q"))
        if len(keywords) == 0:
            return []
        conditions: list[sa.BinaryExpression] = []
        for k in keywords:
            sub_conditions: list[sa.BinaryExpression] \
                = [JournalEntry.summary.contains(k),
                   JournalEntry.account_id.in_(
                       self.__get_account_condition(k)),
                   JournalEntry.currency_code.in_(
                       self.__get_currency_condition(k)),
                   JournalEntry.transaction_id.in_(
                       self.__get_transaction_condition(k))]
            try:
                sub_conditions.append(JournalEntry.amount == Decimal(k))
            except ArithmeticError:
                pass
            conditions.append(sa.or_(*sub_conditions))
        return JournalEntry.query.filter(*conditions)\
            .options(selectinload(JournalEntry.account),
                     selectinload(JournalEntry.currency),
                     selectinload(JournalEntry.transaction)).all()

    @staticmethod
    def __get_account_condition(k: str) -> sa.Select:
        """Composes and returns the condition to filter the account.

        :param k: The keyword.
        :return: The condition to filter the account.
        """
        code: sa.BinaryExpression = Account.base_code + "-" \
            + sa.func.substr("000" + sa.cast(Account.no, sa.String),
                             sa.func.char_length(sa.cast(Account.no,
                                                         sa.String)) + 1)
        select_l10n: sa.Select = sa.select(AccountL10n.account_id)\
            .filter(AccountL10n.title.contains(k))
        conditions: list[sa.BinaryExpression] \
            = [Account.base_code.contains(k),
               Account.title_l10n.contains(k),
               code.contains(k),
               Account.id.in_(select_l10n)]
        if k in gettext("Need offset"):
            conditions.append(Account.is_offset_needed)
        return sa.select(Account.id).filter(sa.or_(*conditions))

    @staticmethod
    def __get_currency_condition(k: str) -> sa.Select:
        """Composes and returns the condition to filter the currency.

        :param k: The keyword.
        :return: The condition to filter the currency.
        """
        select_l10n: sa.Select = sa.select(CurrencyL10n.currency_code)\
            .filter(CurrencyL10n.name.contains(k))
        return sa.select(Currency.code).filter(
            sa.or_(Currency.code.contains(k),
                   Currency.name_l10n.contains(k),
                   Currency.code.in_(select_l10n)))

    @staticmethod
    def __get_transaction_condition(k: str) -> sa.Select:
        """Composes and returns the condition to filter the transaction.

        :param k: The keyword.
        :return: The condition to filter the transaction.
        """
        conditions: list[sa.BinaryExpression] = [Transaction.note.contains(k)]
        txn_date: datetime
        try:
            txn_date = datetime.strptime(k, "%Y")
            conditions.append(
                sa.extract("year", Transaction.date) == txn_date.year)
        except ValueError:
            pass
        try:
            txn_date = datetime.strptime(k, "%Y/%m")
            conditions.append(sa.and_(
                sa.extract("year", Transaction.date) == txn_date.year,
                sa.extract("month", Transaction.date) == txn_date.month))
        except ValueError:
            pass
        try:
            txn_date = datetime.strptime(f"2000/{k}", "%Y/%m/%d")
            conditions.append(sa.and_(
                sa.extract("month", Transaction.date) == txn_date.month,
                sa.extract("day", Transaction.date) == txn_date.day))
        except ValueError:
            pass
        return sa.select(Transaction.id).filter(sa.or_(*conditions))


class PageParams(BasePageParams):
    """The HTML page parameters."""

    def __init__(self, pagination: Pagination[JournalEntry],
                 entries: list[JournalEntry]):
        """Constructs the HTML page parameters.

        :param entries: The search result entries.
        """
        self.pagination: Pagination[JournalEntry] = pagination
        """The pagination."""
        self.entries: list[JournalEntry] = entries
        """The entries."""

    @property
    def has_data(self) -> bool:
        """Returns whether there is any data on the page.

        :return: True if there is any data, or False otherwise.
        """
        return len(self.entries) > 0

    @property
    def report_chooser(self) -> ReportChooser:
        """Returns the report chooser.

        :return: The report chooser.
        """
        return ReportChooser(ReportType.SEARCH)


class Search(BaseReport):
    """The search."""

    def __init__(self):
        """Constructs a search."""
        self.__entries: list[JournalEntry] = EntryCollector().entries
        """The journal entries."""

    def csv(self) -> Response:
        """Returns the report as CSV for download.

        :return: The response of the report for download.
        """
        filename: str = "search-{q}.csv".format(q=request.args["q"])
        return csv_download(filename, get_csv_rows(self.__entries))

    def html(self) -> str:
        """Composes and returns the report as HTML.

        :return: The report as HTML.
        """
        pagination: Pagination[JournalEntry] \
            = Pagination[JournalEntry](self.__entries)
        params: PageParams = PageParams(pagination=pagination,
                                        entries=pagination.list)
        return render_template("accounting/report/search.html",
                               report=params)
