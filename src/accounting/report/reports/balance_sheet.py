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
"""The balance sheet.

"""
import csv
from decimal import Decimal
from io import StringIO

import sqlalchemy as sa
from flask import url_for, render_template, Response

from accounting import db
from accounting.locale import gettext
from accounting.models import Currency, BaseAccount, Account, Transaction, \
    JournalEntry
from accounting.report.period import Period
from .utils.option_link import OptionLink
from .utils.page_params import PageParams
from .utils.period_choosers import BalanceSheetPeriodChooser
from .utils.report_chooser import ReportChooser
from .utils.report_type import ReportType


class BalanceSheetAccount:
    """An account in the balance sheet."""

    def __init__(self, account: Account, amount: Decimal, url: str):
        """Constructs an account in the balance sheet.

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


class BalanceSheetSubsection:
    """A subsection in the balance sheet."""

    def __init__(self, title: BaseAccount):
        """Constructs a subsection in the balance sheet.

        :param title: The title account.
        """
        self.title: BaseAccount = title
        """The title account."""
        self.accounts: list[BalanceSheetAccount] = []
        """The accounts in the subsection."""

    @property
    def total(self) -> Decimal:
        """Returns the total of the subsection.

        :return: The total of the subsection.
        """
        return sum([x.amount for x in self.accounts])


class BalanceSheetSection:
    """A section in the balance sheet."""

    def __init__(self, title: BaseAccount):
        """Constructs a section in the balance sheet.

        :param title: The title account.
        """
        self.title: BaseAccount = title
        """The title account."""
        self.subsections: list[BalanceSheetSubsection] = []
        """The subsections in the section."""

    @property
    def total(self) -> Decimal:
        """Returns the total of the section.

        :return: The total of the section.
        """
        return sum([x.total for x in self.subsections])


class AccountCollector:
    """The balance sheet account collector."""

    def __init__(self, currency: Currency, period: Period):
        """Constructs the balance sheet account collector.

        :param currency: The currency.
        :param period: The period.
        """
        self.__currency: Currency = currency
        """The currency."""
        self.__period: Period = period
        """The period."""
        self.accounts: list[BalanceSheetAccount] = self.__query_balances()
        """The balance sheet accounts."""

    def __query_balances(self) -> list[BalanceSheetAccount]:
        """Queries and returns the balances.

        :return: The balances.
        """
        sub_conditions: list[sa.BinaryExpression] \
            = [Account.base_code.startswith(x) for x in {"1", "2", "3"}]
        conditions: list[sa.BinaryExpression] \
            = [JournalEntry.currency_code == self.__currency.code,
               sa.or_(*sub_conditions)]
        if self.__period.end is not None:
            conditions.append(Transaction.date <= self.__period.end)
        balance_func: sa.Function = sa.func.sum(sa.case(
            (JournalEntry.is_debit, JournalEntry.amount),
            else_=-JournalEntry.amount)).label("balance")
        select_balance: sa.Select \
            = sa.select(Account.id, Account.base_code, Account.no,
                        balance_func)\
            .join(Transaction).join(Account)\
            .filter(*conditions)\
            .group_by(Account.id, Account.base_code, Account.no)\
            .order_by(Account.base_code, Account.no)
        account_balances: list[sa.Row] \
            = db.session.execute(select_balance).all()
        self.__all_accounts: list[Account] = Account.query\
            .filter(sa.or_(Account.id.in_({x.id for x in account_balances}),
                           Account.base_code == "3351",
                           Account.base_code == "3353")).all()
        account_by_id: dict[int, Account] \
            = {x.id: x for x in self.__all_accounts}

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

        self.accounts: list[BalanceSheetAccount] \
            = [BalanceSheetAccount(account=account_by_id[x.id],
                                   amount=x.balance,
                                   url=get_url(account_by_id[x.id]))
               for x in account_balances]
        self.__add_accumulated()
        self.__add_current_period()
        self.accounts.sort(key=lambda x: (x.account.base_code, x.account.no))
        for balance in self.accounts:
            if not balance.account.base_code.startswith("1"):
                balance.amount = -balance.amount
        return self.accounts

    def __add_accumulated(self) -> None:
        """Adds the accumulated profit or loss to the balances.

        :return: None.
        """
        code: str = "3351-001"
        amount: Decimal | None = self.__query_accumulated()
        url: str = url_for("accounting.report.income-statement",
                           currency=self.__currency,
                           period=self.__period.before)
        self.__add_owner_s_equity(code, amount, url)

    def __query_accumulated(self) -> Decimal | None:
        """Queries and returns the accumulated profit or loss.

        :return: The accumulated profit or loss.
        """
        if self.__period.start is None:
            return None
        conditions: list[sa.BinaryExpression] \
            = [JournalEntry.currency_code == self.__currency.code,
               Transaction.date < self.__period.start]
        conditions.extend([sa.not_(Account.base_code.startswith(x))
                           for x in {"1", "2"}])
        balance_func: sa.Function = sa.func.sum(sa.case(
            (JournalEntry.is_debit, JournalEntry.amount),
            else_=-JournalEntry.amount)).label("balance")
        select_balance: sa.Select = sa.select(balance_func)\
            .join(Transaction).join(Account).filter(*conditions)
        return db.session.scalar(select_balance)

    def __add_current_period(self) -> None:
        """Adds the accumulated profit or loss to the balances.

        :return: None.
        """
        code: str = "3353-001"
        amount: Decimal | None = self.__query_currency_period()
        url: str = url_for("accounting.report.income-statement",
                           currency=self.__currency, period=self.__period)
        self.__add_owner_s_equity(code, amount, url)

    def __query_currency_period(self) -> Decimal | None:
        """Queries and returns the net income or loss for current period.

        :return: The net income or loss for current period.
        """
        conditions: list[sa.BinaryExpression] \
            = [JournalEntry.currency_code == self.__currency.code]
        if self.__period.start is not None:
            conditions.append(Transaction.date >= self.__period.start)
        if self.__period.end is not None:
            conditions.append(Transaction.date <= self.__period.end)
        conditions.extend([sa.not_(Account.base_code.startswith(x))
                           for x in {"1", "2"}])
        balance_func: sa.Function = sa.func.sum(sa.case(
            (JournalEntry.is_debit, JournalEntry.amount),
            else_=-JournalEntry.amount)).label("balance")
        select_balance: sa.Select = sa.select(balance_func)\
            .join(Transaction).join(Account).filter(*conditions)
        return db.session.scalar(select_balance)

    def __add_owner_s_equity(self, code: str, amount: Decimal | None,
                             url: str) -> None:
        """Adds an owner's equity balance.

        :param code: The code of the account to add.
        :param amount: The amount.
        :return: None.
        """
        # There is an existing balance.
        account_balance_by_code: dict[str, BalanceSheetAccount] \
            = {x.account.code: x for x in self.accounts}
        if code in account_balance_by_code:
            balance: BalanceSheetAccount = account_balance_by_code[code]
            balance.url = url
            if amount is not None:
                balance.amount = balance.amount + amount
            return
        # Add a new balance
        if amount is None:
            return
        account_by_code: dict[str, Account] \
            = {x.code: x for x in self.__all_accounts}
        self.accounts.append(BalanceSheetAccount(account=account_by_code[code],
                                                 amount=amount,
                                                 url=url))


class CSVHalfRow:
    """A half row in the CSV balance sheet."""

    def __init__(self, title: str | None, amount: Decimal | None):
        """The constructs a half row in the CSV balance sheet.

        :param title: The title.
        :param amount: The amount.
        """
        self.title: str | None = title
        """The title."""
        self.amount: Decimal | None = amount
        """The amount."""


class CSVRow:
    """A row in the CSV balance sheet."""

    def __init__(self):
        """Constructs a row in the CSV balance sheet."""
        self.asset_title: str | None = None
        """The title of the asset."""
        self.asset_amount: Decimal | None = None
        """The amount of the asset."""
        self.liability_title: str | None = None
        """The title of the liability."""
        self.liability_amount: Decimal | None = None
        """The amount of the liability."""

    @property
    def values(self) -> list[str | Decimal | None]:
        """Returns the values of the row.

        :return: The values of the row.
        """
        return [self.asset_title, self.asset_amount,
                self.liability_title, self.liability_amount]


class BalanceSheetPageParams(PageParams):
    """The HTML parameters of the balance sheet."""

    def __init__(self, currency: Currency,
                 period: Period,
                 has_data: bool,
                 assets: BalanceSheetSection,
                 liabilities: BalanceSheetSection,
                 owner_s_equity: BalanceSheetSection):
        """Constructs the HTML parameters of the balance sheet.

        :param currency: The currency.
        :param period: The period.
        :param has_data: True if there is any data, or False otherwise.
        :param assets: The assets.
        :param liabilities: The liabilities.
        :param owner_s_equity: The owner's equity.
        """
        self.currency: Currency = currency
        """The currency."""
        self.period: Period = period
        """The period."""
        self.__has_data: bool = has_data
        """True if there is any data, or False otherwise."""
        self.assets: BalanceSheetSection = assets
        """The assets."""
        self.liabilities: BalanceSheetSection = liabilities
        """The liabilities."""
        self.owner_s_equity: BalanceSheetSection = owner_s_equity
        """The owner's equity."""
        self.period_chooser: BalanceSheetPeriodChooser \
            = BalanceSheetPeriodChooser(currency)
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
        return ReportChooser(ReportType.BALANCE_SHEET,
                             currency=self.currency,
                             period=self.period)

    @property
    def currency_options(self) -> list[OptionLink]:
        """Returns the currency options.

        :return: The currency options.
        """
        def get_url(currency: Currency):
            if self.period.is_default:
                return url_for("accounting.report.balance-sheet-default",
                               currency=currency)
            return url_for("accounting.report.balance-sheet",
                           currency=currency, period=self.period)

        in_use: set[str] = set(db.session.scalars(
            sa.select(JournalEntry.currency_code)
            .group_by(JournalEntry.currency_code)).all())
        return [OptionLink(str(x), get_url(x), x.code == self.currency.code)
                for x in Currency.query.filter(Currency.code.in_(in_use))
                .order_by(Currency.code).all()]


class BalanceSheet:
    """The balance sheet."""

    def __init__(self, currency: Currency, period: Period):
        """Constructs a balance sheet.

        :param currency: The currency.
        :param period: The period.
        """
        self.__currency: Currency = currency
        """The currency."""
        self.__period: Period = period
        """The period."""
        self.__has_data: bool
        """True if there is any data, or False otherwise."""
        self.__assets: BalanceSheetSection
        """The assets."""
        self.__liabilities: BalanceSheetSection
        """The liabilities."""
        self.__owner_s_equity: BalanceSheetSection
        """The owner's equity."""
        self.__set_data()

    def __set_data(self) -> None:
        """Queries and sets assets, the liabilities, and the owner's equity
        sections in the balance sheet.

        :return: None.
        """
        balances: list[BalanceSheetAccount] = AccountCollector(
            self.__currency, self.__period).accounts

        titles: list[BaseAccount] = BaseAccount.query\
            .filter(BaseAccount.code.in_({"1", "2", "3"})).all()
        subtitles: list[BaseAccount] = BaseAccount.query\
            .filter(BaseAccount.code.in_({x.account.base_code[:2]
                                          for x in balances})).all()

        sections: dict[str, BalanceSheetSection] \
            = {x.code: BalanceSheetSection(x) for x in titles}
        subsections: dict[str, BalanceSheetSubsection] \
            = {x.code: BalanceSheetSubsection(x) for x in subtitles}
        for subsection in subsections.values():
            sections[subsection.title.code[0]].subsections.append(subsection)
        for balance in balances:
            subsections[balance.account.base_code[:2]].accounts.append(balance)

        self.__has_data = len(balances) > 0
        self.__assets = sections["1"]
        self.__liabilities = sections["2"]
        self.__owner_s_equity = sections["3"]

    def csv(self) -> Response:
        """Returns the report as CSV for download.

        :return: The response of the report for download.
        """
        filename: str = "balance-sheet-{currency}-{period}.csv"\
            .format(currency=self.__currency.code, period=self.__period.spec)
        rows: list[CSVRow] = self.__get_csv_rows()
        with StringIO() as fp:
            writer = csv.writer(fp)
            writer.writerows([x.values for x in rows])
            fp.seek(0)
            response: Response = Response(fp.read(), mimetype="text/csv")
            response.headers["Content-Disposition"] \
                = f"attachment; filename={filename}"
            return response

    def __get_csv_rows(self) -> list[CSVRow]:
        """Composes and returns the CSV rows.

        :return: The CSV rows.
        """
        asset_rows: list[CSVHalfRow] = self.__section_csv_rows(self.__assets)
        liability_rows: list[CSVHalfRow] = []
        liability_rows.extend(self.__section_csv_rows(self.__liabilities))
        liability_rows.append(CSVHalfRow(gettext("Total"),
                                         self.__liabilities.total))
        liability_rows.append(CSVHalfRow(None, None))
        liability_rows.extend(self.__section_csv_rows(self.__owner_s_equity))
        liability_rows.append(CSVHalfRow(gettext("Total"),
                                         self.__owner_s_equity.total))
        rows: list[CSVRow] = [CSVRow() for _ in
                              range(max(len(asset_rows), len(liability_rows)))]
        for i in range(len(rows)):
            if i < len(asset_rows):
                rows[i].asset_title = asset_rows[i].title
                rows[i].asset_amount = asset_rows[i].amount
            if i < len(liability_rows) and liability_rows[i].title is not None:
                rows[i].liability_title = liability_rows[i].title
                rows[i].liability_amount = liability_rows[i].amount
        total: CSVRow = CSVRow()
        total.asset_title = gettext("Total")
        total.asset_amount = self.__assets.total
        total.liability_title = gettext("Total")
        total.liability_amount \
            = self.__liabilities.total + self.__owner_s_equity.total
        rows.append(total)
        return rows

    @staticmethod
    def __section_csv_rows(section: BalanceSheetSection) -> list[CSVHalfRow]:
        """Gathers the CSV rows for a section.

        :param section: The section.
        :return: The CSV rows for the section.
        """
        rows: list[CSVHalfRow] \
            = [CSVHalfRow(section.title.title.title(), None)]
        for subsection in section.subsections:
            rows.append(CSVHalfRow(f" {subsection.title.title.title()}", None))
            for account in subsection.accounts:
                rows.append(CSVHalfRow(f"  {str(account.account).title()}",
                                       account.amount))
        return rows

    def html(self) -> str:
        """Composes and returns the report as HTML.

        :return: The report as HTML.
        """
        params: BalanceSheetPageParams = BalanceSheetPageParams(
            currency=self.__currency,
            period=self.__period,
            has_data=self.__has_data,
            assets=self.__assets,
            liabilities=self.__liabilities,
            owner_s_equity=self.__owner_s_equity)
        return render_template("accounting/report/balance-sheet.html",
                               report=params)
