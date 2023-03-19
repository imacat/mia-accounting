# The Mia! Accounting Flask Project.
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
from accounting.models import Currency, Account, Voucher, JournalEntry
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


class ReportEntry:
    """An entry in the report."""

    def __init__(self, entry: JournalEntry | None = None):
        """Constructs the entry in the report.

        :param entry: The journal entry.
        """
        self.is_brought_forward: bool = False
        """Whether this is the brought-forward entry."""
        self.is_total: bool = False
        """Whether this is the total entry."""
        self.date: date | None = None
        """The date."""
        self.summary: str | None = None
        """The summary."""
        self.debit: Decimal | None = None
        """The debit amount."""
        self.credit: Decimal | None = None
        """The credit amount."""
        self.balance: Decimal | None = None
        """The balance."""
        self.note: str | None = None
        """The note."""
        self.url: str | None = None
        """The URL to the journal entry."""
        if entry is not None:
            self.date = entry.voucher.date
            self.summary = entry.summary
            self.debit = entry.amount if entry.is_debit else None
            self.credit = None if entry.is_debit else entry.amount
            self.note = entry.voucher.note
            self.url = url_for("accounting.voucher.detail",
                               voucher=entry.voucher)


class EntryCollector:
    """The report entry collector."""

    def __init__(self, currency: Currency, account: Account, period: Period):
        """Constructs the report entry collector.

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
        self.brought_forward: ReportEntry | None
        """The brought-forward entry."""
        self.entries: list[ReportEntry]
        """The report entries."""
        self.total: ReportEntry | None
        """The total entry."""
        self.brought_forward = self.__get_brought_forward_entry()
        self.entries = self.__query_entries()
        self.total = self.__get_total_entry()
        self.__populate_balance()

    def __get_brought_forward_entry(self) -> ReportEntry | None:
        """Queries, composes and returns the brought-forward entry.

        :return: The brought-forward entry, or None if the report starts from
            the beginning.
        """
        if self.__period.start is None:
            return None
        if self.__account.is_nominal:
            return None
        balance_func: sa.Function = sa.func.sum(sa.case(
            (JournalEntry.is_debit, JournalEntry.amount),
            else_=-JournalEntry.amount))
        select: sa.Select = sa.Select(balance_func).join(Voucher)\
            .filter(be(JournalEntry.currency_code == self.__currency.code),
                    be(JournalEntry.account_id == self.__account.id),
                    Voucher.date < self.__period.start)
        balance: int | None = db.session.scalar(select)
        if balance is None:
            return None
        entry: ReportEntry = ReportEntry()
        entry.is_brought_forward = True
        entry.date = self.__period.start
        entry.summary = gettext("Brought forward")
        if balance > 0:
            entry.debit = balance
        elif balance < 0:
            entry.credit = -balance
        entry.balance = balance
        return entry

    def __query_entries(self) -> list[ReportEntry]:
        """Queries and returns the report entries.

        :return: The report entries.
        """
        conditions: list[sa.BinaryExpression] \
            = [JournalEntry.currency_code == self.__currency.code,
               JournalEntry.account_id == self.__account.id]
        if self.__period.start is not None:
            conditions.append(Voucher.date >= self.__period.start)
        if self.__period.end is not None:
            conditions.append(Voucher.date <= self.__period.end)
        return [ReportEntry(x) for x in JournalEntry.query.join(Voucher)
                .filter(*conditions)
                .order_by(Voucher.date,
                          Voucher.no,
                          JournalEntry.is_debit.desc(),
                          JournalEntry.no)
                .options(selectinload(JournalEntry.voucher)).all()]

    def __get_total_entry(self) -> ReportEntry | None:
        """Composes the total entry.

        :return: The total entry, or None if there is no data.
        """
        if self.brought_forward is None and len(self.entries) == 0:
            return None
        entry: ReportEntry = ReportEntry()
        entry.is_total = True
        entry.summary = gettext("Total")
        entry.debit = sum([x.debit for x in self.entries
                           if x.debit is not None])
        entry.credit = sum([x.credit for x in self.entries
                            if x.credit is not None])
        entry.balance = entry.debit - entry.credit
        if self.brought_forward is not None:
            entry.balance = self.brought_forward.balance + entry.balance
        return entry

    def __populate_balance(self) -> None:
        """Populates the balance of the entries.

        :return: None.
        """
        if self.__account.is_nominal:
            return None
        balance: Decimal = 0 if self.brought_forward is None \
            else self.brought_forward.balance
        for entry in self.entries:
            if entry.debit is not None:
                balance = balance + entry.debit
            if entry.credit is not None:
                balance = balance - entry.credit
            entry.balance = balance


class CSVRow(BaseCSVRow):
    """A row in the CSV."""

    def __init__(self, voucher_date: date | str | None,
                 summary: str | None,
                 debit: str | Decimal | None,
                 credit: str | Decimal | None,
                 balance: str | Decimal | None,
                 note: str | None):
        """Constructs a row in the CSV.

        :param voucher_date: The voucher date.
        :param summary: The summary.
        :param debit: The debit amount.
        :param credit: The credit amount.
        :param balance: The balance.
        :param note: The note.
        """
        self.date: date | str | None = voucher_date
        """The date."""
        self.summary: str | None = summary
        """The summary."""
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
        return [self.date, self.summary,
                self.debit, self.credit, self.balance, self.note]


class PageParams(BasePageParams):
    """The HTML page parameters."""

    def __init__(self, currency: Currency,
                 account: Account,
                 period: Period,
                 has_data: bool,
                 pagination: Pagination[ReportEntry],
                 brought_forward: ReportEntry | None,
                 entries: list[ReportEntry],
                 total: ReportEntry | None):
        """Constructs the HTML page parameters.

        :param currency: The currency.
        :param account: The account.
        :param period: The period.
        :param has_data: True if there is any data, or False otherwise.
        :param brought_forward: The brought-forward entry.
        :param entries: The report entries.
        :param total: The total entry.
        """
        self.currency: Currency = currency
        """The currency."""
        self.account: Account = account
        """The account."""
        self.period: Period = period
        """The period."""
        self.__has_data: bool = has_data
        """True if there is any data, or False otherwise."""
        self.pagination: Pagination[ReportEntry] = pagination
        """The pagination."""
        self.brought_forward: ReportEntry | None = brought_forward
        """The brought-forward entry."""
        self.entries: list[ReportEntry] = entries
        """The entries."""
        self.total: ReportEntry | None = total
        """The total entry."""
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
        in_use: sa.Select = sa.Select(JournalEntry.account_id)\
            .filter(be(JournalEntry.currency_code == self.currency.code))\
            .group_by(JournalEntry.account_id)
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
        collector: EntryCollector = EntryCollector(
            self.__currency, self.__account, self.__period)
        self.__brought_forward: ReportEntry | None = collector.brought_forward
        """The brought-forward entry."""
        self.__entries: list[ReportEntry] = collector.entries
        """The report entries."""
        self.__total: ReportEntry | None = collector.total
        """The total entry."""

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
        rows: list[CSVRow] = [CSVRow(gettext("Date"), gettext("Summary"),
                                     gettext("Debit"), gettext("Credit"),
                                     gettext("Balance"), gettext("Note"))]
        if self.__brought_forward is not None:
            rows.append(CSVRow(self.__brought_forward.date,
                               self.__brought_forward.summary,
                               self.__brought_forward.debit,
                               self.__brought_forward.credit,
                               self.__brought_forward.balance,
                               None))
        rows.extend([CSVRow(x.date, x.summary,
                            x.debit, x.credit, x.balance, x.note)
                     for x in self.__entries])
        if self.__total is not None:
            rows.append(CSVRow(gettext("Total"), None,
                               self.__total.debit, self.__total.credit,
                               self.__total.balance, None))
        return rows

    def html(self) -> str:
        """Composes and returns the report as HTML.

        :return: The report as HTML.
        """
        all_entries: list[ReportEntry] = []
        if self.__brought_forward is not None:
            all_entries.append(self.__brought_forward)
        all_entries.extend(self.__entries)
        if self.__total is not None:
            all_entries.append(self.__total)
        pagination: Pagination[ReportEntry] \
            = Pagination[ReportEntry](all_entries, is_reversed=True)
        page_entries: list[ReportEntry] = pagination.list
        has_data: bool = len(page_entries) > 0
        brought_forward: ReportEntry | None = None
        if len(page_entries) > 0 and page_entries[0].is_brought_forward:
            brought_forward = page_entries[0]
            page_entries = page_entries[1:]
        total: ReportEntry | None = None
        if len(page_entries) > 0 and page_entries[-1].is_total:
            total = page_entries[-1]
            page_entries = page_entries[:-1]
        params: PageParams = PageParams(currency=self.__currency,
                                        account=self.__account,
                                        period=self.__period,
                                        has_data=has_data,
                                        pagination=pagination,
                                        brought_forward=brought_forward,
                                        entries=page_entries,
                                        total=total)
        return render_template("accounting/report/ledger.html",
                               report=params)
