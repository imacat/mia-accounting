# The Mia! Accounting Project.
# Author: imacat@mail.imacat.idv.tw (imacat), 2023/4/7

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
"""The unapplied original line items.

"""
from datetime import date
from decimal import Decimal

import sqlalchemy as sa
from flask import render_template, Response
from sqlalchemy.orm import selectinload

from accounting import db
from accounting.locale import gettext
from accounting.models import Account, JournalEntry, \
    JournalEntryLineItem
from accounting.report.utils.base_page_params import BasePageParams
from accounting.report.utils.base_report import BaseReport
from accounting.report.utils.csv_export import BaseCSVRow, csv_download
from accounting.report.utils.option_link import OptionLink
from accounting.report.utils.report_chooser import ReportChooser
from accounting.report.utils.report_type import ReportType
from accounting.report.utils.unapplied import get_accounts_with_unapplied
from accounting.report.utils.urls import unapplied_url
from accounting.utils.cast import be
from accounting.utils.offset_alias import offset_alias
from accounting.utils.pagination import Pagination


class CSVRow(BaseCSVRow):
    """A row in the CSV."""

    def __init__(self, journal_entry_date: str | date, currency: str,
                 description: str | None, amount: str | Decimal,
                 net_balance: str | Decimal):
        """Constructs a row in the CSV.

        :param journal_entry_date: The journal entry date.
        :param currency: The currency.
        :param description: The description.
        :param amount: The amount.
        :param net_balance: The net balance.
        """
        self.date: str | date = journal_entry_date
        """The date."""
        self.currency: str = currency
        """The currency."""
        self.description: str | None = description
        """The description."""
        self.amount: str | Decimal = amount
        """The amount."""
        self.net_balance: str | Decimal = net_balance
        """The net balance."""

    @property
    def values(self) -> list[str | date | Decimal | None]:
        """Returns the values of the row.

        :return: The values of the row.
        """
        return [self.date, self.currency, self.description, self.amount,
                self.net_balance]


class PageParams(BasePageParams):
    """The HTML page parameters."""

    def __init__(self, account: Account,
                 pagination: Pagination[JournalEntryLineItem],
                 line_items: list[JournalEntryLineItem]):
        """Constructs the HTML page parameters.

        :param account: The account.
        :param pagination: The pagination.
        :param line_items: The line items.
        """
        self.account: Account = account
        """The account."""
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
        return ReportChooser(ReportType.UNAPPLIED,
                             account=self.account)

    @property
    def account_options(self) -> list[OptionLink]:
        """Returns the account options.

        :return: The account options.
        """
        return [OptionLink(str(x),
                           unapplied_url(x),
                           x.id == self.account.id)
                for x in get_accounts_with_unapplied()]


def get_csv_rows(line_items: list[JournalEntryLineItem]) -> list[CSVRow]:
    """Composes and returns the CSV rows from the line items.

    :param line_items: The line items.
    :return: The CSV rows.
    """
    rows: list[CSVRow] = [CSVRow(gettext("Date"), gettext("Currency"),
                                 gettext("Description"), gettext("Amount"),
                                 gettext("Net Balance"))]
    rows.extend([CSVRow(x.journal_entry.date, x.currency.code,
                        x.description, x.amount, x.net_balance)
                 for x in line_items])
    return rows


class UnappliedOriginalLineItems(BaseReport):
    """The unapplied original line items."""

    def __init__(self, account: Account):
        """Constructs the unapplied original line items.

        :param account: The account.
        """
        self.__account: Account = account
        """The account."""
        self.__line_items: list[JournalEntryLineItem] \
            = self.__query_line_items()
        """The line items."""

    def __query_line_items(self) -> list[JournalEntryLineItem]:
        """Queries and returns the line items.

        :return: The line items.
        """
        offset: sa.Alias = offset_alias()
        net_balance: sa.Label \
            = (JournalEntryLineItem.amount
               + sa.func.sum(sa.case(
                    (be(offset.c.is_debit == JournalEntryLineItem.is_debit),
                     offset.c.amount),
                    else_=-offset.c.amount))).label("net_balance")
        select_net_balances: sa.Select \
            = sa.select(JournalEntryLineItem.id, net_balance)\
            .join(Account)\
            .join(offset, be(JournalEntryLineItem.id
                             == offset.c.original_line_item_id),
                  isouter=True)\
            .filter(be(Account.id == self.__account.id),
                    sa.or_(sa.and_(Account.base_code.startswith("2"),
                                   sa.not_(JournalEntryLineItem.is_debit)),
                           sa.and_(Account.base_code.startswith("1"),
                                   JournalEntryLineItem.is_debit)))\
            .group_by(JournalEntryLineItem.id)\
            .having(sa.or_(sa.func.count(offset.c.id) == 0, net_balance != 0))
        net_balances: dict[int, Decimal] \
            = {x.id: x.net_balance
               for x in db.session.execute(select_net_balances).all()}
        line_items: list[JournalEntryLineItem] = JournalEntryLineItem.query\
            .filter(JournalEntryLineItem.id.in_({x for x in net_balances}))\
            .join(JournalEntry)\
            .order_by(JournalEntry.date, JournalEntry.no,
                      JournalEntryLineItem.is_debit, JournalEntryLineItem.no)\
            .options(selectinload(JournalEntryLineItem.currency),
                     selectinload(JournalEntryLineItem.journal_entry)).all()
        for line_item in line_items:
            line_item.net_balance = line_item.amount \
                if net_balances[line_item.id] is None \
                else net_balances[line_item.id]
        return line_items

    def csv(self) -> Response:
        """Returns the report as CSV for download.

        :return: The response of the report for download.
        """
        filename: str = f"unapplied-{self.__account.code}.csv"
        return csv_download(filename, get_csv_rows(self.__line_items))

    def html(self) -> str:
        """Composes and returns the report as HTML.

        :return: The report as HTML.
        """
        pagination: Pagination[JournalEntryLineItem] \
            = Pagination[JournalEntryLineItem](self.__line_items,
                                               is_reversed=True)
        params: PageParams = PageParams(account=self.__account,
                                        pagination=pagination,
                                        line_items=pagination.list)
        return render_template("accounting/report/unapplied.html",
                               report=params)
