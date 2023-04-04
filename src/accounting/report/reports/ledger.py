# The Mia! Accounting Project.
# Author: imacat@mail.imacat.idv.tw (imacat), 2023/3/7

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
"""The ledger.

"""
from datetime import date
from decimal import Decimal

import sqlalchemy as sa
from flask import url_for, render_template, Response
from sqlalchemy.orm import selectinload

from accounting import db
from accounting.locale import gettext
from accounting.models import Currency, Account, JournalEntry, \
    JournalEntryLineItem
from accounting.report.period import Period, PeriodChooser
from accounting.report.utils.base_page_params import BasePageParams
from accounting.report.utils.base_report import BaseReport
from accounting.report.utils.csv_export import BaseCSVRow, csv_download, \
    period_spec
from accounting.report.utils.option_link import OptionLink
from accounting.report.utils.report_chooser import ReportChooser
from accounting.report.utils.report_type import ReportType
from accounting.report.utils.urls import ledger_url
from accounting.utils.cast import be
from accounting.utils.pagination import Pagination


class ReportLineItem:
    """A line item in the report."""

    def __init__(self, line_item: JournalEntryLineItem | None = None):
        """Constructs the line item in the report.

        :param line_item: The journal entry line item.
        """
        self.is_brought_forward: bool = False
        """Whether this is the brought-forward line item."""
        self.is_total: bool = False
        """Whether this is the total line item."""
        self.date: date | None = None
        """The date."""
        self.description: str | None = None
        """The description."""
        self.debit: Decimal | None = None
        """The debit amount."""
        self.credit: Decimal | None = None
        """The credit amount."""
        self.balance: Decimal | None = None
        """The balance."""
        self.note: str | None = None
        """The note."""
        self.url: str | None = None
        """The URL to the journal entry line item."""
        if line_item is not None:
            self.date = line_item.journal_entry.date
            self.description = line_item.description
            self.debit = line_item.amount if line_item.is_debit else None
            self.credit = None if line_item.is_debit else line_item.amount
            self.note = line_item.journal_entry.note
            self.url = url_for("accounting.journal-entry.detail",
                               journal_entry=line_item.journal_entry)


class LineItemCollector:
    """The line item collector."""

    def __init__(self, currency: Currency, account: Account, period: Period):
        """Constructs the line item collector.

        :param currency: The currency.
        :param account: The account.
        :param period: The period.
        """
        self.__currency: Currency = currency
        """The currency."""
        self.__account: Account = account
        """The account."""
        self.__period: Period = period
        """The period"""
        self.brought_forward: ReportLineItem | None
        """The brought-forward line item."""
        self.line_items: list[ReportLineItem]
        """The line items."""
        self.total: ReportLineItem | None
        """The total line item."""
        self.brought_forward = self.__get_brought_forward()
        self.line_items = self.__query_line_items()
        self.total = self.__get_total()
        self.__populate_balance()

    def __get_brought_forward(self) -> ReportLineItem | None:
        """Queries, composes and returns the brought-forward line item.

        :return: The brought-forward line item, or None if the report starts
            from the beginning.
        """
        if self.__period.start is None:
            return None
        if self.__account.is_nominal:
            return None
        balance_func: sa.Function = sa.func.sum(sa.case(
            (JournalEntryLineItem.is_debit, JournalEntryLineItem.amount),
            else_=-JournalEntryLineItem.amount))
        select: sa.Select = sa.Select(balance_func).join(JournalEntry)\
            .filter(be(JournalEntryLineItem.currency_code
                       == self.__currency.code),
                    be(JournalEntryLineItem.account_id
                       == self.__account.id),
                    JournalEntry.date < self.__period.start)
        balance: int | None = db.session.scalar(select)
        if balance is None:
            return None
        line_item: ReportLineItem = ReportLineItem()
        line_item.is_brought_forward = True
        line_item.date = self.__period.start
        line_item.description = gettext("Brought forward")
        if balance > 0:
            line_item.debit = balance
        elif balance < 0:
            line_item.credit = -balance
        line_item.balance = balance
        return line_item

    def __query_line_items(self) -> list[ReportLineItem]:
        """Queries and returns the line items.

        :return: The line items.
        """
        conditions: list[sa.BinaryExpression] \
            = [JournalEntryLineItem.currency_code == self.__currency.code,
               JournalEntryLineItem.account_id == self.__account.id]
        if self.__period.start is not None:
            conditions.append(JournalEntry.date >= self.__period.start)
        if self.__period.end is not None:
            conditions.append(JournalEntry.date <= self.__period.end)
        return [ReportLineItem(x) for x in JournalEntryLineItem.query
                .join(JournalEntry)
                .filter(*conditions)
                .order_by(JournalEntry.date,
                          JournalEntry.no,
                          JournalEntryLineItem.is_debit.desc(),
                          JournalEntryLineItem.no)
                .options(selectinload(JournalEntryLineItem.journal_entry))
                .all()]

    def __get_total(self) -> ReportLineItem | None:
        """Composes the total line item.

        :return: The total line item, or None if there is no data.
        """
        if self.brought_forward is None and len(self.line_items) == 0:
            return None
        line_item: ReportLineItem = ReportLineItem()
        line_item.is_total = True
        line_item.description = gettext("Total")
        line_item.debit = sum([x.debit for x in self.line_items
                               if x.debit is not None])
        line_item.credit = sum([x.credit for x in self.line_items
                                if x.credit is not None])
        line_item.balance = line_item.debit - line_item.credit
        if self.brought_forward is not None:
            line_item.balance \
                = self.brought_forward.balance + line_item.balance
        return line_item

    def __populate_balance(self) -> None:
        """Populates the balance of the line items.

        :return: None.
        """
        if self.__account.is_nominal:
            return None
        balance: Decimal = 0 if self.brought_forward is None \
            else self.brought_forward.balance
        for line_item in self.line_items:
            if line_item.debit is not None:
                balance = balance + line_item.debit
            if line_item.credit is not None:
                balance = balance - line_item.credit
            line_item.balance = balance


class CSVRow(BaseCSVRow):
    """A row in the CSV."""

    def __init__(self, journal_entry_date: date | str | None,
                 description: str | None,
                 debit: str | Decimal | None,
                 credit: str | Decimal | None,
                 balance: str | Decimal | None,
                 note: str | None):
        """Constructs a row in the CSV.

        :param journal_entry_date: The journal entry date.
        :param description: The description.
        :param debit: The debit amount.
        :param credit: The credit amount.
        :param balance: The balance.
        :param note: The note.
        """
        self.date: date | str | None = journal_entry_date
        """The date."""
        self.description: str | None = description
        """The description."""
        self.debit: str | Decimal | None = debit
        """The debit amount."""
        self.credit: str | Decimal | None = credit
        """The credit amount."""
        self.balance: str | Decimal | None = balance
        """The balance."""
        self.note: str | None = note
        """The note."""

    @property
    def values(self) -> list[str | Decimal | None]:
        """Returns the values of the row.

        :return: The values of the row.
        """
        return [self.date, self.description,
                self.debit, self.credit, self.balance, self.note]


class PageParams(BasePageParams):
    """The HTML page parameters."""

    def __init__(self, currency: Currency,
                 account: Account,
                 period: Period,
                 has_data: bool,
                 pagination: Pagination[ReportLineItem],
                 brought_forward: ReportLineItem | None,
                 line_items: list[ReportLineItem],
                 total: ReportLineItem | None):
        """Constructs the HTML page parameters.

        :param currency: The currency.
        :param account: The account.
        :param period: The period.
        :param has_data: True if there is any data, or False otherwise.
        :param brought_forward: The brought-forward line item.
        :param line_items: The line items.
        :param total: The total line item.
        """
        self.currency: Currency = currency
        """The currency."""
        self.account: Account = account
        """The account."""
        self.period: Period = period
        """The period."""
        self.__has_data: bool = has_data
        """True if there is any data, or False otherwise."""
        self.pagination: Pagination[ReportLineItem] = pagination
        """The pagination."""
        self.brought_forward: ReportLineItem | None = brought_forward
        """The brought-forward line item."""
        self.line_items: list[ReportLineItem] = line_items
        """The line items."""
        self.total: ReportLineItem | None = total
        """The total line item."""
        self.period_chooser: PeriodChooser = PeriodChooser(
            lambda x: ledger_url(currency, account, x))
        """The period chooser."""

    @property
    def has_data(self) -> bool:
        """Returns whether there is any data on the page.

        :return: True if there is any data, or False otherwise.
        """
        return self.__has_data

    @property
    def report_chooser(self) -> ReportChooser:
        """Returns the report chooser.

        :return: The report chooser.
        """
        return ReportChooser(ReportType.LEDGER,
                             currency=self.currency,
                             account=self.account,
                             period=self.period)

    @property
    def currency_options(self) -> list[OptionLink]:
        """Returns the currency options.

        :return: The currency options.
        """
        return self._get_currency_options(
            lambda x: ledger_url(x, self.account, self.period), self.currency)

    @property
    def account_options(self) -> list[OptionLink]:
        """Returns the account options.

        :return: The account options.
        """
        in_use: sa.Select = sa.Select(JournalEntryLineItem.account_id)\
            .filter(be(JournalEntryLineItem.currency_code
                       == self.currency.code))\
            .group_by(JournalEntryLineItem.account_id)
        return [OptionLink(str(x), ledger_url(self.currency, x, self.period),
                           x.id == self.account.id)
                for x in Account.query.filter(Account.id.in_(in_use))
                .order_by(Account.base_code, Account.no).all()]


class Ledger(BaseReport):
    """The ledger."""

    def __init__(self, currency: Currency, account: Account, period: Period):
        """Constructs a ledger.

        :param currency: The currency.
        :param account: The account.
        :param period: The period.
        """
        self.__currency: Currency = currency
        """The currency."""
        self.__account: Account = account
        """The account."""
        self.__period: Period = period
        """The period."""
        collector: LineItemCollector = LineItemCollector(
            self.__currency, self.__account, self.__period)
        self.__brought_forward: ReportLineItem | None \
            = collector.brought_forward
        """The brought-forward line item."""
        self.__line_items: list[ReportLineItem] = collector.line_items
        """The line items."""
        self.__total: ReportLineItem | None = collector.total
        """The total line item."""

    def csv(self) -> Response:
        """Returns the report as CSV for download.

        :return: The response of the report for download.
        """
        filename: str = "ledger-{currency}-{account}-{period}.csv"\
            .format(currency=self.__currency.code, account=self.__account.code,
                    period=period_spec(self.__period))
        return csv_download(filename, self.__get_csv_rows())

    def __get_csv_rows(self) -> list[CSVRow]:
        """Composes and returns the CSV rows.

        :return: The CSV rows.
        """
        rows: list[CSVRow] = [CSVRow(gettext("Date"), gettext("Description"),
                                     gettext("Debit"), gettext("Credit"),
                                     gettext("Balance"), gettext("Note"))]
        if self.__brought_forward is not None:
            rows.append(CSVRow(self.__brought_forward.date,
                               self.__brought_forward.description,
                               self.__brought_forward.debit,
                               self.__brought_forward.credit,
                               self.__brought_forward.balance,
                               None))
        rows.extend([CSVRow(x.date, x.description,
                            x.debit, x.credit, x.balance, x.note)
                     for x in self.__line_items])
        if self.__total is not None:
            rows.append(CSVRow(gettext("Total"), None,
                               self.__total.debit, self.__total.credit,
                               self.__total.balance, None))
        return rows

    def html(self) -> str:
        """Composes and returns the report as HTML.

        :return: The report as HTML.
        """
        all_line_items: list[ReportLineItem] = []
        if self.__brought_forward is not None:
            all_line_items.append(self.__brought_forward)
        all_line_items.extend(self.__line_items)
        if self.__total is not None:
            all_line_items.append(self.__total)
        pagination: Pagination[ReportLineItem] \
            = Pagination[ReportLineItem](all_line_items, is_reversed=True)
        page_line_items: list[ReportLineItem] = pagination.list
        has_data: bool = len(page_line_items) > 0
        brought_forward: ReportLineItem | None = None
        if len(page_line_items) > 0 and page_line_items[0].is_brought_forward:
            brought_forward = page_line_items[0]
            page_line_items = page_line_items[1:]
        total: ReportLineItem | None = None
        if len(page_line_items) > 0 and page_line_items[-1].is_total:
            total = page_line_items[-1]
            page_line_items = page_line_items[:-1]
        params: PageParams = PageParams(currency=self.__currency,
                                        account=self.__account,
                                        period=self.__period,
                                        has_data=has_data,
                                        pagination=pagination,
                                        brought_forward=brought_forward,
                                        line_items=page_line_items,
                                        total=total)
        return render_template("accounting/report/ledger.html",
                               report=params)
