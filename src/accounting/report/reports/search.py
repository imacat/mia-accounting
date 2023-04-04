# The Mia! Accounting Project.
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
    JournalEntry, JournalEntryLineItem
from accounting.report.utils.base_page_params import BasePageParams
from accounting.report.utils.base_report import BaseReport
from accounting.report.utils.csv_export import csv_download
from accounting.report.utils.report_chooser import ReportChooser
from accounting.report.utils.report_type import ReportType
from accounting.utils.cast import be
from accounting.utils.pagination import Pagination
from accounting.utils.query import parse_query_keywords
from .journal import get_csv_rows


class LineItemCollector:
    """The line item collector."""

    def __init__(self):
        """Constructs the line item collector."""
        self.line_items: list[JournalEntryLineItem] = self.__query_line_items()
        """The line items."""

    def __query_line_items(self) -> list[JournalEntryLineItem]:
        """Queries and returns the line items.

        :return: The line items.
        """
        keywords: list[str] = parse_query_keywords(request.args.get("q"))
        if len(keywords) == 0:
            return []
        conditions: list[sa.BinaryExpression] = []
        for k in keywords:
            sub_conditions: list[sa.BinaryExpression] \
                = [JournalEntryLineItem.description.icontains(k),
                   JournalEntryLineItem.account_id.in_(
                       self.__get_account_condition(k)),
                   JournalEntryLineItem.currency_code.in_(
                       self.__get_currency_condition(k)),
                   JournalEntryLineItem.journal_entry_id.in_(
                       self.__get_journal_entry_condition(k))]
            try:
                sub_conditions.append(
                    JournalEntryLineItem.amount == Decimal(k))
            except ArithmeticError:
                pass
            conditions.append(sa.or_(*sub_conditions))
        return JournalEntryLineItem.query.join(JournalEntry)\
            .filter(*conditions)\
            .order_by(JournalEntry.date,
                      JournalEntry.no,
                      JournalEntryLineItem.is_debit,
                      JournalEntryLineItem.no)\
            .options(selectinload(JournalEntryLineItem.account),
                     selectinload(JournalEntryLineItem.currency),
                     selectinload(JournalEntryLineItem.journal_entry)).all()

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
            .filter(AccountL10n.title.icontains(k))
        conditions: list[sa.BinaryExpression] \
            = [Account.base_code.contains(k),
               Account.title_l10n.icontains(k),
               code.contains(k),
               Account.id.in_(select_l10n)]
        if k in gettext("Needs Offset"):
            conditions.append(Account.is_need_offset)
        return sa.select(Account.id).filter(sa.or_(*conditions))

    @staticmethod
    def __get_currency_condition(k: str) -> sa.Select:
        """Composes and returns the condition to filter the currency.

        :param k: The keyword.
        :return: The condition to filter the currency.
        """
        select_l10n: sa.Select = sa.select(CurrencyL10n.currency_code)\
            .filter(CurrencyL10n.name.icontains(k))
        return sa.select(Currency.code).filter(
            sa.or_(Currency.code.icontains(k),
                   Currency.name_l10n.icontains(k),
                   Currency.code.in_(select_l10n)))

    @staticmethod
    def __get_journal_entry_condition(k: str) -> sa.Select:
        """Composes and returns the condition to filter the journal entry.

        :param k: The keyword.
        :return: The condition to filter the journal entry.
        """
        conditions: list[sa.BinaryExpression] \
            = [JournalEntry.note.icontains(k)]
        journal_entry_date: datetime
        try:
            journal_entry_date = datetime.strptime(k, "%Y")
            conditions.append(
                be(sa.extract("year", JournalEntry.date)
                   == journal_entry_date.year))
        except ValueError:
            pass
        try:
            journal_entry_date = datetime.strptime(k, "%Y/%m")
            conditions.append(sa.and_(
                sa.extract("year", JournalEntry.date)
                == journal_entry_date.year,
                sa.extract("month", JournalEntry.date)
                == journal_entry_date.month))
        except ValueError:
            pass
        try:
            journal_entry_date = datetime.strptime(f"2000/{k}", "%Y/%m/%d")
            conditions.append(sa.and_(
                sa.extract("month", JournalEntry.date)
                == journal_entry_date.month,
                sa.extract("day", JournalEntry.date)
                == journal_entry_date.day))
        except ValueError:
            pass
        return sa.select(JournalEntry.id).filter(sa.or_(*conditions))


class PageParams(BasePageParams):
    """The HTML page parameters."""

    def __init__(self, pagination: Pagination[JournalEntryLineItem],
                 line_items: list[JournalEntryLineItem]):
        """Constructs the HTML page parameters.

        :param line_items: The search result line items.
        """
        self.pagination: Pagination[JournalEntryLineItem] = pagination
        """The pagination."""
        self.line_items: list[JournalEntryLineItem] = line_items
        """The line items."""

    @property
    def has_data(self) -> bool:
        """Returns whether there is any data on the page.

        :return: True if there is any data, or False otherwise.
        """
        return len(self.line_items) > 0

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
        self.__line_items: list[JournalEntryLineItem] \
            = LineItemCollector().line_items
        """The line items."""

    def csv(self) -> Response:
        """Returns the report as CSV for download.

        :return: The response of the report for download.
        """
        filename: str = "search-{q}.csv".format(q=request.args["q"])
        return csv_download(filename, get_csv_rows(self.__line_items))

    def html(self) -> str:
        """Composes and returns the report as HTML.

        :return: The report as HTML.
        """
        pagination: Pagination[JournalEntryLineItem] \
            = Pagination[JournalEntryLineItem](self.__line_items,
                                               is_reversed=True)
        params: PageParams = PageParams(pagination=pagination,
                                        line_items=pagination.list)
        return render_template("accounting/report/search.html",
                               report=params)
