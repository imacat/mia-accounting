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
"""The income statement.

"""
from decimal import Decimal

import sqlalchemy as sa
from flask import render_template, Response

from accounting import db
from accounting.locale import gettext
from accounting.models import Currency, BaseAccount, Account, JournalEntry, \
    JournalEntryLineItem
from accounting.report.period import Period, PeriodChooser
from accounting.report.utils.base_page_params import BasePageParams
from accounting.report.utils.base_report import BaseReport
from accounting.report.utils.csv_export import BaseCSVRow, csv_download, \
    period_spec
from accounting.report.utils.option_link import OptionLink
from accounting.report.utils.report_chooser import ReportChooser
from accounting.report.utils.report_type import ReportType
from accounting.report.utils.urls import ledger_url, income_statement_url


class ReportAccount:
    """An account in the report."""

    def __init__(self, account: Account, amount: Decimal, url: str):
        """Constructs an account in the report.

        :param account: The account.
        :param amount: The amount.
        :param url: The URL to the ledger of the account.
        """
        self.account: Account = account
        """The account."""
        self.amount: Decimal = amount
        """The amount of the account."""
        self.url: str = url
        """The URL to the ledger of the account."""


class AccumulatedTotal:
    """An accumulated total."""

    def __init__(self, title: str):
        """Constructs an accumulated total.

        :param title: The title.
        """
        self.title: str = title
        """The account."""
        self.amount: Decimal = Decimal("0")
        """The amount of the account."""


class Subsection:
    """A subsection."""

    def __init__(self, title: BaseAccount):
        """Constructs a subsection.

        :param title: The title account.
        """
        self.title: BaseAccount = title
        """The title account."""
        self.accounts: list[ReportAccount] = []
        """The accounts in the subsection."""

    @property
    def total(self) -> Decimal:
        """Returns the total of the subsection.

        :return: The total of the subsection.
        """
        return sum([x.amount for x in self.accounts])


class Section:
    """A section."""

    def __init__(self, title: BaseAccount, accumulated_title: str):
        """Constructs a section.

        :param title: The title account.
        :param accumulated_title: The title for the accumulated total.
        """
        self.title: BaseAccount = title
        """The title account."""
        self.subsections: list[Subsection] = []
        """The subsections in the section."""
        self.accumulated: AccumulatedTotal \
            = AccumulatedTotal(accumulated_title)

    @property
    def total(self) -> Decimal:
        """Returns the total of the section.

        :return: The total of the section.
        """
        return sum([x.total for x in self.subsections])


class CSVRow(BaseCSVRow):
    """A row in the CSV."""

    def __init__(self, text: str | None, amount: str | Decimal | None):
        """Constructs a row in the CSV.

        :param text: The text.
        :param amount: The amount.
        """
        self.text: str | None = text
        """The text."""
        self.amount: str | Decimal | None = amount
        """The amount."""

    @property
    def values(self) -> list[str | Decimal | None]:
        """Returns the values of the row.

        :return: The values of the row.
        """
        return [self.text, self.amount]


class PageParams(BasePageParams):
    """The HTML page parameters."""

    def __init__(self, currency: Currency,
                 period: Period,
                 has_data: bool,
                 sections: list[Section], ):
        """Constructs the HTML page parameters.

        :param currency: The currency.
        :param period: The period.
        :param has_data: True if there is any data, or False otherwise.
        """
        self.currency: Currency = currency
        """The currency."""
        self.period: Period = period
        """The period."""
        self.__has_data: bool = has_data
        """True if there is any data, or False otherwise."""
        self.sections: list[Section] = sections
        """The sections in the income statement."""
        self.period_chooser: PeriodChooser = PeriodChooser(
            lambda x: income_statement_url(currency, x))
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
        return ReportChooser(ReportType.INCOME_STATEMENT,
                             currency=self.currency,
                             period=self.period)

    @property
    def currency_options(self) -> list[OptionLink]:
        """Returns the currency options.

        :return: The currency options.
        """
        return self._get_currency_options(
            lambda x: income_statement_url(x, self.period), self.currency)


class IncomeStatement(BaseReport):
    """The income statement."""

    def __init__(self, currency: Currency, period: Period):
        """Constructs an income statement.

        :param currency: The currency.
        :param period: The period.
        """
        self.__currency: Currency = currency
        """The currency."""
        self.__period: Period = period
        """The period."""
        self.__has_data: bool
        """True if there is any data, or False otherwise."""
        self.__sections: list[Section]
        """The sections."""
        self.__set_data()

    def __set_data(self) -> None:
        """Queries and sets data sections in the income statement.

        :return: None.
        """
        balances: list[ReportAccount] = self.__query_balances()

        titles: list[BaseAccount] = BaseAccount.query\
            .filter(BaseAccount.code.in_({"4", "5", "6", "7", "8", "9"})).all()
        subtitles: list[BaseAccount] = BaseAccount.query\
            .filter(BaseAccount.code.in_({x.account.base_code[:2]
                                          for x in balances})).all()

        total_titles: dict[str, str] \
            = {"4": gettext("total operating revenue"),
               "5": gettext("gross income"),
               "6": gettext("operating income"),
               "7": gettext("before tax income"),
               "8": gettext("after tax income"),
               "9": gettext("net income or loss for current period")}

        sections: dict[str, Section] \
            = {x.code: Section(x, total_titles[x.code]) for x in titles}
        subsections: dict[str, Subsection] \
            = {x.code: Subsection(x) for x in subtitles}
        for subsection in subsections.values():
            sections[subsection.title.code[0]].subsections.append(subsection)
        for balance in balances:
            subsections[balance.account.base_code[:2]].accounts.append(balance)

        self.__has_data = len(balances) > 0
        self.__sections = sorted(sections.values(), key=lambda x: x.title.code)
        total: Decimal = Decimal("0")
        for section in self.__sections:
            total = total + section.total
            section.accumulated.amount = total

    def __query_balances(self) -> list[ReportAccount]:
        """Queries and returns the balances.

        :return: The balances.
        """
        sub_conditions: list[sa.BinaryExpression] \
            = [Account.base_code.startswith(str(x)) for x in range(4, 10)]
        conditions: list[sa.BinaryExpression] \
            = [JournalEntryLineItem.currency_code == self.__currency.code,
               sa.or_(*sub_conditions)]
        if self.__period.start is not None:
            conditions.append(JournalEntry.date >= self.__period.start)
        if self.__period.end is not None:
            conditions.append(JournalEntry.date <= self.__period.end)
        balance_func: sa.Function = sa.func.sum(sa.case(
            (JournalEntryLineItem.is_debit, -JournalEntryLineItem.amount),
            else_=JournalEntryLineItem.amount)).label("balance")
        select_balances: sa.Select = sa.select(Account.id, balance_func)\
            .join(JournalEntry).join(Account)\
            .filter(*conditions)\
            .group_by(Account.id)\
            .having(balance_func != 0)\
            .order_by(Account.base_code, Account.no)
        balances: list[sa.Row] = db.session.execute(select_balances).all()
        accounts: dict[int, Account] \
            = {x.id: x for x in Account.query
               .filter(Account.id.in_([x.id for x in balances])).all()}
        return [ReportAccount(account=accounts[x.id],
                              amount=x.balance,
                              url=ledger_url(self.__currency,
                                             accounts[x.id],
                                             self.__period))
                for x in balances]

    def csv(self) -> Response:
        """Returns the report as CSV for download.

        :return: The response of the report for download.
        """
        filename: str = "income-statement-{currency}-{period}.csv"\
            .format(currency=self.__currency.code,
                    period=period_spec(self.__period))
        return csv_download(filename, self.__get_csv_rows())

    def __get_csv_rows(self) -> list[CSVRow]:
        """Composes and returns the CSV rows.

        :return: The CSV rows.
        """
        total_str: str = gettext("Total")
        rows: list[CSVRow] = [CSVRow(None, gettext("Amount"))]
        for section in self.__sections:
            rows.append(CSVRow(str(section.title).title(), None))
            for subsection in section.subsections:
                rows.append(CSVRow(f" {str(subsection.title).title()}", None))
                for account in subsection.accounts:
                    rows.append(CSVRow(f"  {str(account.account).title()}",
                                       account.amount))
                rows.append(CSVRow(f" {total_str}", subsection.total))
            rows.append(CSVRow(section.accumulated.title.title(),
                               section.accumulated.amount))
            rows.append(CSVRow(None, None))
        rows = rows[:-1]
        return rows

    def html(self) -> str:
        """Composes and returns the report as HTML.

        :return: The report as HTML.
        """
        params: PageParams = PageParams(currency=self.__currency,
                                        period=self.__period,
                                        has_data=self.__has_data,
                                        sections=self.__sections)
        return render_template("accounting/report/income-statement.html",
                               report=params)
