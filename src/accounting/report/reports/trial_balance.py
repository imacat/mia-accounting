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
"""The trial balance.

"""
from decimal import Decimal

import sqlalchemy as sa
from flask import url_for, Response, render_template

from accounting import db
from accounting.locale import gettext
from accounting.models import Currency, Account, Transaction, JournalEntry
from accounting.report.period import Period
from .utils.csv_export import BaseCSVRow, csv_download
from .utils.option_link import OptionLink
from .utils.page_params import PageParams
from .utils.period_choosers import TrialBalancePeriodChooser
from .utils.report_chooser import ReportChooser
from .utils.report_type import ReportType


class TrialBalanceAccount:
    """An account in the trial balance."""

    def __init__(self, account: Account, amount: Decimal, url: str):
        """Constructs an account in the trial balance.

        :param account: The account.
        :param amount: The amount.
        :param url: The URL to the ledger of the account.
        """
        self.account: Account = account
        """The account."""
        self.debit: Decimal | None = amount if amount > 0 else None
        """The debit amount."""
        self.credit: Decimal | None = -amount if amount < 0 else None
        """The credit amount."""
        self.url: str = url
        """The URL to the ledger of the account."""


class TrialBalanceTotal:
    """The total in the trial balance."""

    def __init__(self, debit: Decimal, credit: Decimal):
        """Constructs the total in the trial balance.

        :param debit: The debit amount.
        :param credit: The credit amount.
        """
        self.debit: Decimal | None = debit
        """The debit amount."""
        self.credit: Decimal | None = credit
        """The credit amount."""


class CSVRow(BaseCSVRow):
    """A row in the CSV trial balance."""

    def __init__(self, text: str | None,
                 debit: str | Decimal | None,
                 credit: str | Decimal | None):
        """Constructs a row in the CSV trial balance.

        :param text: The text.
        :param debit: The debit amount.
        :param credit: The credit amount.
        """
        self.text: str | None = text
        """The text."""
        self.debit: str | Decimal | None = debit
        """The debit amount."""
        self.credit: str | Decimal | None = credit
        """The credit amount."""

    @property
    def values(self) -> list[str | Decimal | None]:
        """Returns the values of the row.

        :return: The values of the row.
        """
        return [self.text, self.debit, self.credit]


class TrialBalancePageParams(PageParams):
    """The HTML parameters of the trial balance."""

    def __init__(self, currency: Currency,
                 period: Period,
                 accounts: list[TrialBalanceAccount],
                 total: TrialBalanceTotal):
        """Constructs the HTML parameters of the trial balance.

        :param currency: The currency.
        :param period: The period.
        :param accounts: The accounts in the trial balance.
        :param total: The total of the trial balance.
        """
        self.currency: Currency = currency
        """The currency."""
        self.period: Period = period
        """The period."""
        self.accounts: list[TrialBalanceAccount] = accounts
        """The accounts in the trial balance."""
        self.total: TrialBalanceTotal = total
        """The total of the trial balance."""
        self.period_chooser: TrialBalancePeriodChooser \
            = TrialBalancePeriodChooser(currency)
        """The period chooser."""

    @property
    def has_data(self) -> bool:
        """Returns whether there is any data on the page.

        :return: True if there is any data, or False otherwise.
        """
        return len(self.accounts) > 0

    @property
    def report_chooser(self) -> ReportChooser:
        """Returns the report chooser.

        :return: The report chooser.
        """
        return ReportChooser(ReportType.TRIAL_BALANCE,
                             currency=self.currency,
                             period=self.period)

    @property
    def currency_options(self) -> list[OptionLink]:
        """Returns the currency options.

        :return: The currency options.
        """
        def get_url(currency: Currency):
            if self.period.is_default:
                return url_for("accounting.report.trial-balance-default",
                               currency=currency)
            return url_for("accounting.report.trial-balance",
                           currency=currency, period=self.period)

        in_use: set[str] = set(db.session.scalars(
            sa.select(JournalEntry.currency_code)
            .group_by(JournalEntry.currency_code)).all())
        return [OptionLink(str(x), get_url(x), x.code == self.currency.code)
                for x in Currency.query.filter(Currency.code.in_(in_use))
                .order_by(Currency.code).all()]


class TrialBalance:
    """The trial balance."""

    def __init__(self, currency: Currency, period: Period):
        """Constructs a trial balance.

        :param currency: The currency.
        :param period: The period.
        """
        self.__currency: Currency = currency
        """The currency."""
        self.__period: Period = period
        """The period."""
        self.__accounts: list[TrialBalanceAccount]
        """The accounts in the trial balance."""
        self.__total: TrialBalanceTotal
        """The total of the trial balance."""
        self.__set_data()

    def __set_data(self) -> None:
        """Queries and sets data sections in the trial balance.

        :return: None.
        """
        conditions: list[sa.BinaryExpression] \
            = [JournalEntry.currency_code == self.__currency.code]
        if self.__period.start is not None:
            conditions.append(Transaction.date >= self.__period.start)
        if self.__period.end is not None:
            conditions.append(Transaction.date <= self.__period.end)
        balance_func: sa.Function = sa.func.sum(sa.case(
            (JournalEntry.is_debit, JournalEntry.amount),
            else_=-JournalEntry.amount)).label("balance")
        select_balances: sa.Select \
            = sa.select(Account.id, balance_func)\
            .join(Transaction).join(Account)\
            .filter(*conditions)\
            .group_by(JournalEntry.account_id)\
            .order_by(Account.base_code, Account.no)
        balances: list[sa.Row] = db.session.execute(select_balances).all()
        accounts: dict[int, Account] \
            = {x.id: x for x in Account.query
               .filter(Account.id.in_([x.id for x in balances])).all()}

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

        self.__accounts = [TrialBalanceAccount(account=accounts[x.id],
                                               amount=x.balance,
                                               url=get_url(accounts[x.id]))
                           for x in balances]
        self.__total = TrialBalanceTotal(
            sum([x.debit for x in self.__accounts if x.debit is not None]),
            sum([x.credit for x in self.__accounts if x.credit is not None]))

    def csv(self) -> Response:
        """Returns the report as CSV for download.

        :return: The response of the report for download.
        """
        filename: str = "trial-balance-{currency}-{period}.csv"\
            .format(currency=self.__currency.code, period=self.__period.spec)
        return csv_download(filename, self.__get_csv_rows())

    def __get_csv_rows(self) -> list[CSVRow]:
        """Composes and returns the CSV rows.

        :return: The CSV rows.
        """
        rows: list[CSVRow] = [CSVRow(gettext("Account"), gettext("Debit"),
                                     gettext("Credit"))]
        rows.extend([CSVRow(str(x.account).title(), x.debit, x.credit)
                     for x in self.__accounts])
        rows.append(CSVRow(gettext("Total"), self.__total.debit,
                           self.__total.credit))
        return rows

    def html(self) -> str:
        """Composes and returns the report as HTML.

        :return: The report as HTML.
        """
        params: TrialBalancePageParams = TrialBalancePageParams(
            currency=self.__currency,
            period=self.__period,
            accounts=self.__accounts,
            total=self.__total)
        return render_template("accounting/report/trial-balance.html",
                               report=params)
