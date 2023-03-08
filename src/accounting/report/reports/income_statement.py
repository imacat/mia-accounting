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
"""The income statement.

"""
from decimal import Decimal

import sqlalchemy as sa
from flask import url_for, render_template, Response

from accounting import db
from accounting.locale import gettext
from accounting.models import Currency, BaseAccount, Account, Transaction, \
    JournalEntry
from accounting.report.period import Period
from .utils.base_report import BaseReport
from .utils.csv_export import BaseCSVRow, csv_download
from .utils.option_link import OptionLink
from .utils.page_params import PageParams
from .utils.period_choosers import IncomeStatementPeriodChooser
from .utils.report_chooser import ReportChooser
from .utils.report_type import ReportType


class IncomeStatementAccount:
    """An account in the income statement."""

    def __init__(self, account: Account, amount: Decimal, url: str):
        """Constructs an account in the income statement.

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


class IncomeStatementAccumulatedTotal:
    """An accumulated total in the income statement."""

    def __init__(self, title: str):
        """Constructs an accumulated total in the income statement.

        :param title: The title.
        """
        self.title: str = title
        """The account."""
        self.amount: Decimal = Decimal("0")
        """The amount of the account."""


class IncomeStatementSubsection:
    """A subsection in the income statement."""

    def __init__(self, title: BaseAccount):
        """Constructs a subsection in the income statement.

        :param title: The title account.
        """
        self.title: BaseAccount = title
        """The title account."""
        self.accounts: list[IncomeStatementAccount] = []
        """The accounts in the subsection."""

    @property
    def total(self) -> Decimal:
        """Returns the total of the subsection.

        :return: The total of the subsection.
        """
        return sum([x.amount for x in self.accounts])


class IncomeStatementSection:
    """A section in the income statement."""

    def __init__(self, title: BaseAccount, accumulated_title: str):
        """Constructs a section in the income statement.

        :param title: The title account.
        :param accumulated_title: The title for the accumulated total.
        """
        self.title: BaseAccount = title
        """The title account."""
        self.subsections: list[IncomeStatementSubsection] = []
        """The subsections in the section."""
        self.accumulated: IncomeStatementAccumulatedTotal \
            = IncomeStatementAccumulatedTotal(accumulated_title)

    @property
    def total(self) -> Decimal:
        """Returns the total of the section.

        :return: The total of the section.
        """
        return sum([x.total for x in self.subsections])


class CSVRow(BaseCSVRow):
    """A row in the CSV income statement."""

    def __init__(self, text: str | None, amount: str | Decimal | None):
        """Constructs a row in the CSV income statement.

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


class IncomeStatementPageParams(PageParams):
    """The HTML parameters of the income statement."""

    def __init__(self, currency: Currency,
                 period: Period,
                 has_data: bool,
                 sections: list[IncomeStatementSection],):
        """Constructs the HTML parameters of the income statement.

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
        self.sections: list[IncomeStatementSection] = sections
        self.period_chooser: IncomeStatementPeriodChooser \
            = IncomeStatementPeriodChooser(currency)
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
        def get_url(currency: Currency):
            if self.period.is_default:
                return url_for("accounting.report.income-statement-default",
                               currency=currency)
            return url_for("accounting.report.income-statement",
                           currency=currency, period=self.period)

        in_use: set[str] = set(db.session.scalars(
            sa.select(JournalEntry.currency_code)
            .group_by(JournalEntry.currency_code)).all())
        return [OptionLink(str(x), get_url(x), x.code == self.currency.code)
                for x in Currency.query.filter(Currency.code.in_(in_use))
                .order_by(Currency.code).all()]


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
        self.__sections: list[IncomeStatementSection]
        """The sections."""
        self.__set_data()

    def __set_data(self) -> None:
        """Queries and sets data sections in the income statement.

        :return: None.
        """
        balances: list[IncomeStatementAccount] = self.__query_balances()

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

        sections: dict[str, IncomeStatementSection] \
            = {x.code: IncomeStatementSection(x, total_titles[x.code])
               for x in titles}
        subsections: dict[str, IncomeStatementSubsection] \
            = {x.code: IncomeStatementSubsection(x) for x in subtitles}
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

    def __query_balances(self) -> list[IncomeStatementAccount]:
        """Queries and returns the balances.

        :return: The balances.
        """
        sub_conditions: list[sa.BinaryExpression] \
            = [Account.base_code.startswith(str(x)) for x in range(4, 10)]
        conditions: list[sa.BinaryExpression] \
            = [JournalEntry.currency_code == self.__currency.code,
               sa.or_(*sub_conditions)]
        if self.__period.start is not None:
            conditions.append(Transaction.date >= self.__period.start)
        if self.__period.end is not None:
            conditions.append(Transaction.date <= self.__period.end)
        balance_func: sa.Function = sa.func.sum(sa.case(
            (JournalEntry.is_debit, -JournalEntry.amount),
            else_=JournalEntry.amount)).label("balance")
        select_balance: sa.Select \
            = sa.select(JournalEntry.account_id, balance_func)\
            .join(Transaction).join(Account)\
            .filter(*conditions)\
            .group_by(JournalEntry.account_id)\
            .order_by(Account.base_code, Account.no)
        balances: list[sa.Row] = db.session.execute(select_balance).all()
        accounts: dict[int, Account] \
            = {x.id: x for x in Account.query
               .filter(Account.id.in_([x.account_id for x in balances])).all()}

        def get_url(account: Account) -> str:
            """Returns the ledger URL of an account.

            :param account: The account.
            :return: The ledger URL of the account.
            """
            if self.__period.is_default:
                return url_for("accounting.report.ledger-default",
                               currency=self.__currency, account=account)
            return url_for("accounting.report.ledger",
                           currency=self.__currency, account=account,
                           period=self.__period)

        return [IncomeStatementAccount(account=accounts[x.account_id],
                                       amount=x.balance,
                                       url=get_url(accounts[x.account_id]))
                for x in balances]

    def csv(self) -> Response:
        """Returns the report as CSV for download.

        :return: The response of the report for download.
        """
        filename: str = "income-statement-{currency}-{period}.csv"\
            .format(currency=self.__currency.code, period=self.__period.spec)
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
        params: IncomeStatementPageParams = IncomeStatementPageParams(
            currency=self.__currency,
            period=self.__period,
            has_data=self.__has_data,
            sections=self.__sections)
        return render_template("accounting/report/income-statement.html",
                               report=params)
