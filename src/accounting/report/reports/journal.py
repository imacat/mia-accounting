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
"""The journal.

"""
from datetime import date
from decimal import Decimal

import sqlalchemy as sa
from flask import render_template, Response
from sqlalchemy.orm import selectinload

from accounting.locale import gettext
from accounting.models import Currency, Account, Voucher, VoucherLineItem
from accounting.report.period import Period, PeriodChooser
from accounting.report.utils.base_page_params import BasePageParams
from accounting.report.utils.base_report import BaseReport
from accounting.report.utils.csv_export import BaseCSVRow, csv_download, \
    period_spec
from accounting.report.utils.report_chooser import ReportChooser
from accounting.report.utils.report_type import ReportType
from accounting.report.utils.urls import journal_url
from accounting.utils.pagination import Pagination


class ReportLineItem:
    """A line item in the report."""

    def __init__(self, line_item: VoucherLineItem):
        """Constructs the line item in the report.

        :param line_item: The voucher line item.
        """
        self.line_item: VoucherLineItem = line_item
        """The voucher line item."""
        self.voucher: Voucher = line_item.voucher
        """The voucher."""
        self.currency: Currency = line_item.currency
        """The account."""
        self.account: Account = line_item.account
        """The account."""
        self.description: str | None = line_item.description
        """The description."""
        self.debit: Decimal | None = line_item.debit
        """The debit amount."""
        self.credit: Decimal | None = line_item.credit
        """The credit amount."""
        self.amount: Decimal = line_item.amount
        """The amount."""


class CSVRow(BaseCSVRow):
    """A row in the CSV."""

    def __init__(self, voucher_date: str | date,
                 currency: str,
                 account: str,
                 description: str | None,
                 debit: str | Decimal | None,
                 credit: str | Decimal | None,
                 note: str | None):
        """Constructs a row in the CSV.

        :param voucher_date: The voucher date.
        :param description: The description.
        :param debit: The debit amount.
        :param credit: The credit amount.
        :param note: The note.
        """
        self.date: str | date = voucher_date
        """The date."""
        self.currency: str = currency
        """The currency."""
        self.account: str = account
        """The account."""
        self.description: str | None = description
        """The description."""
        self.debit: str | Decimal | None = debit
        """The debit amount."""
        self.credit: str | Decimal | None = credit
        """The credit amount."""
        self.note: str | None = note
        """The note."""

    @property
    def values(self) -> list[str | Decimal | None]:
        """Returns the values of the row.

        :return: The values of the row.
        """
        return [self.date, self.currency, self.account, self.description,
                self.debit, self.credit, self.note]


class PageParams(BasePageParams):
    """The HTML page parameters."""

    def __init__(self, period: Period,
                 pagination: Pagination[VoucherLineItem],
                 line_items: list[VoucherLineItem]):
        """Constructs the HTML page parameters.

        :param period: The period.
        :param line_items: The line items.
        """
        self.period: Period = period
        """The period."""
        self.pagination: Pagination[VoucherLineItem] = pagination
        """The pagination."""
        self.line_items: list[VoucherLineItem] = line_items
        """The line items."""
        self.period_chooser: PeriodChooser = PeriodChooser(
            lambda x: journal_url(x))
        """The period chooser."""

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
        return ReportChooser(ReportType.JOURNAL,
                             period=self.period)


def get_csv_rows(line_items: list[VoucherLineItem]) -> list[CSVRow]:
    """Composes and returns the CSV rows from the line items.

    :param line_items: The line items.
    :return: The CSV rows.
    """
    rows: list[CSVRow] = [CSVRow(gettext("Date"), gettext("Currency"),
                                 gettext("Account"), gettext("Description"),
                                 gettext("Debit"), gettext("Credit"),
                                 gettext("Note"))]
    rows.extend([CSVRow(x.voucher.date, x.currency.code,
                        str(x.account).title(), x.description,
                        x.debit, x.credit, x.voucher.note)
                 for x in line_items])
    return rows


class Journal(BaseReport):
    """The journal."""

    def __init__(self, period: Period):
        """Constructs a journal.

        :param period: The period.
        """
        self.__period: Period = period
        """The period."""
        self.__line_items: list[VoucherLineItem] = self.__query_line_items()
        """The line items."""

    def __query_line_items(self) -> list[VoucherLineItem]:
        """Queries and returns the line items.

        :return: The line items.
        """
        conditions: list[sa.BinaryExpression] = []
        if self.__period.start is not None:
            conditions.append(Voucher.date >= self.__period.start)
        if self.__period.end is not None:
            conditions.append(Voucher.date <= self.__period.end)
        return VoucherLineItem.query.join(Voucher)\
            .filter(*conditions)\
            .order_by(Voucher.date,
                      Voucher.no,
                      VoucherLineItem.is_debit.desc(),
                      VoucherLineItem.no)\
            .options(selectinload(VoucherLineItem.account),
                     selectinload(VoucherLineItem.currency),
                     selectinload(VoucherLineItem.voucher)).all()

    def csv(self) -> Response:
        """Returns the report as CSV for download.

        :return: The response of the report for download.
        """
        filename: str = f"journal-{period_spec(self.__period)}.csv"
        return csv_download(filename, get_csv_rows(self.__line_items))

    def html(self) -> str:
        """Composes and returns the report as HTML.

        :return: The report as HTML.
        """
        pagination: Pagination[VoucherLineItem] \
            = Pagination[VoucherLineItem](self.__line_items, is_reversed=True)
        params: PageParams = PageParams(period=self.__period,
                                        pagination=pagination,
                                        line_items=pagination.list)
        return render_template("accounting/report/journal.html",
                               report=params)
