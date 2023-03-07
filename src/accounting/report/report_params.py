# The Mia! Accounting Flask Project.
# Author: imacat@mail.imacat.idv.tw (imacat), 2023/3/6

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
"""The page parameters of a report.

"""
import typing as t
from abc import ABC

import sqlalchemy as sa
from flask import url_for

from accounting import db
from accounting.models import Currency, Account, JournalEntry
from accounting.report.option_link import OptionLink
from accounting.report.period import Period
from accounting.report.period_choosers import PeriodChooser, \
    JournalPeriodChooser, LedgerPeriodChooser, IncomeExpensesPeriodChooser, \
    TrialBalancePeriodChooser, IncomeStatementPeriodChooser
from accounting.report.report_chooser import ReportChooser
from accounting.report.report_rows import JournalRow, LedgerRow, \
    IncomeExpensesRow, TrialBalanceRow, IncomeStatementRow
from accounting.report.report_type import ReportType
from accounting.utils.pagination import Pagination
from accounting.utils.txn_types import TransactionType

T = t.TypeVar("T")


class ReportParams(t.Generic[T], ABC):
    """The parameters of a report page."""

    def __init__(self,
                 period_chooser: PeriodChooser,
                 report_chooser: ReportChooser,
                 data_rows: list[T],
                 is_paged: bool,
                 filler: t.Callable[[list[T]], None] | None = None,
                 brought_forward: T | None = None,
                 total: T | None = None):
        """Constructs the parameters of a report page.

        :param period_chooser: The period chooser.
        :param report_chooser: The report chooser.
        :param filler: The callback to fill in the related data to the rows.
        :param data_rows: The data rows.
        :param is_paged: True to use pagination, or False otherwise.
        :param brought_forward: The brought-forward row, if any.
        :param total: The total row, if any.
        """
        self.txn_types: t.Type[TransactionType] = TransactionType
        """The transaction types."""
        self.period_chooser: PeriodChooser = period_chooser
        """The period chooser."""
        self.report_chooser: ReportChooser = report_chooser
        """The report chooser."""
        self.data_rows: list[T] = data_rows
        """The data rows"""
        self.brought_forward: T | None = brought_forward
        """The brought-forward row."""
        self.total: T | None = total
        """The total row."""
        self.pagination: Pagination[T] | None = None
        """The pagination."""
        self.has_data: bool = len(self.data_rows) > 0
        """True if there is any data in the page, or False otherwise."""
        if is_paged:
            all_rows: list[T] = []
            if brought_forward is not None:
                all_rows.append(brought_forward)
            all_rows.extend(data_rows)
            if self.total is not None:
                all_rows.append(total)
            self.pagination = Pagination[T](all_rows)
            rows = self.pagination.list
            self.has_data = len(rows) > 0
            if len(rows) > 0 and rows[0] == brought_forward:
                rows = rows[1:]
            else:
                self.brought_forward = None
            if len(rows) > 0 and rows[-1] == total:
                rows = rows[:-1]
            else:
                self.total = None
            self.data_rows = rows
        if filler is not None:
            filler(self.data_rows)


class JournalParams(ReportParams[JournalRow]):
    """The parameters of a journal page."""

    def __init__(self,
                 period: Period,
                 data_rows: list[JournalRow],
                 filler: t.Callable[[list[JournalRow]], None]):
        """Constructs the parameters for the journal page.

        :param period: The period.
        :param data_rows: The data rows.
        :param filler: The callback to fill in the related data to the rows.
        """
        super().__init__(
            period_chooser=JournalPeriodChooser(),
            report_chooser=ReportChooser(ReportType.JOURNAL,
                                         period=period),
            data_rows=data_rows,
            is_paged=True,
            filler=filler)
        self.period: Period | None = period
        """The period."""


class LedgerParams(ReportParams[LedgerRow]):
    """The parameters of a ledger page."""

    def __init__(self,
                 currency: Currency,
                 account: Account,
                 period: Period,
                 data_rows: list[LedgerRow],
                 filler: t.Callable[[list[LedgerRow]], None],
                 brought_forward: LedgerRow | None,
                 total: LedgerRow):
        """Constructs the parameters for the ledger page.

        :param currency: The currency.
        :param account: The account.
        :param period: The period.
        :param data_rows: The data rows.
        :param filler: The callback to fill in the related data to the rows.
        :param brought_forward: The brought-forward row, if any.
        :param total: The total row, if any.
        """
        super().__init__(
            period_chooser=IncomeExpensesPeriodChooser(currency, account),
            report_chooser=ReportChooser(ReportType.LEDGER,
                                         currency=currency,
                                         account=account,
                                         period=period),
            data_rows=data_rows,
            is_paged=True,
            filler=filler,
            brought_forward=brought_forward,
            total=total)
        self.currency: Currency = currency
        """The currency."""
        self.account: Account = account
        """The account."""
        self.period: Period | None = period
        """The period."""

    @property
    def currency_options(self) -> list[OptionLink]:
        """Returns the currency options.

        :return: The currency options.
        """
        def get_url(currency: Currency):
            if self.period.is_default:
                return url_for("accounting.report.ledger-default",
                               currency=currency, account=self.account)
            return url_for("accounting.report.ledger",
                           currency=currency, account=self.account,
                           period=self.period)

        in_use: sa.Select = sa.Select(JournalEntry.currency_code)\
            .group_by(JournalEntry.currency_code)
        return [OptionLink(str(x), get_url(x), x.code == self.currency.code)
                for x in Currency.query.filter(Currency.code.in_(in_use))
                .order_by(Currency.code).all()]

    @property
    def account_options(self) -> list[OptionLink]:
        """Returns the account options.

        :return: The account options.
        """
        def get_url(account: Account):
            if self.period.is_default:
                return url_for("accounting.report.ledger-default",
                               currency=self.currency, account=account)
            return url_for("accounting.report.ledger",
                           currency=self.currency, account=account,
                           period=self.period)

        in_use: sa.Select = sa.Select(JournalEntry.account_id)\
            .filter(JournalEntry.currency_code == self.currency.code)\
            .group_by(JournalEntry.account_id)
        return [OptionLink(str(x), get_url(x), x.id == self.account.id)
                for x in Account.query.filter(Account.id.in_(in_use))
                .order_by(Account.base_code, Account.no).all()]


class IncomeExpensesParams(ReportParams[IncomeExpensesRow]):
    """The parameters of an income and expenses page."""

    def __init__(self,
                 currency: Currency,
                 account: Account,
                 period: Period,
                 data_rows: list[IncomeExpensesRow],
                 filler: t.Callable[[list[IncomeExpensesRow]], None],
                 brought_forward: IncomeExpensesRow | None,
                 total: IncomeExpensesRow):
        """Constructs the parameters for the income and expenses page.

        :param currency: The currency.
        :param account: The account.
        :param period: The period.
        :param data_rows: The data rows.
        :param filler: The callback to fill in the related data to the rows.
        :param brought_forward: The brought-forward row, if any.
        :param total: The total row, if any.
        """
        super().__init__(
            period_chooser=LedgerPeriodChooser(currency, account),
            report_chooser=ReportChooser(ReportType.INCOME_EXPENSES,
                                         currency=currency,
                                         account=account,
                                         period=period),
            data_rows=data_rows,
            is_paged=True,
            filler=filler,
            brought_forward=brought_forward,
            total=total)
        self.currency: Currency = currency
        """The currency."""
        self.account: Account = account
        """The account."""
        self.period: Period = period
        """The period."""

    @property
    def currency_options(self) -> list[OptionLink]:
        """Returns the currency options.

        :return: The currency options.
        """
        def get_url(currency: Currency):
            if self.period.is_default:
                return url_for("accounting.report.income-expenses-default",
                               currency=currency, account=self.account)
            return url_for("accounting.report.income-expenses",
                           currency=currency, account=self.account,
                           period=self.period)

        in_use: set[str] = set(db.session.scalars(
            sa.select(JournalEntry.currency_code)
            .group_by(JournalEntry.currency_code)).all())
        return [OptionLink(str(x), get_url(x), x.code == self.currency.code)
                for x in Currency.query.filter(Currency.code.in_(in_use))
                .order_by(Currency.code).all()]

    @property
    def account_options(self) -> list[OptionLink]:
        """Returns the account options.

        :return: The account options.
        """
        def get_url(account: Account):
            if self.period.is_default:
                return url_for("accounting.report.income-expenses-default",
                               currency=self.currency, account=account)
            return url_for("accounting.report.income-expenses",
                           currency=self.currency, account=account,
                           period=self.period)

        in_use: sa.Select = sa.Select(JournalEntry.account_id)\
            .join(Account)\
            .filter(JournalEntry.currency_code == self.currency.code,
                    sa.or_(Account.base_code.startswith("11"),
                           Account.base_code.startswith("12"),
                           Account.base_code.startswith("21"),
                           Account.base_code.startswith("22")))\
            .group_by(JournalEntry.account_id)
        return [OptionLink(str(x), get_url(x), x.id == self.account.id)
                for x in Account.query.filter(Account.id.in_(in_use))
                .order_by(Account.base_code, Account.no).all()]


class TrialBalanceParams(ReportParams[TrialBalanceRow]):
    """The parameters of a trial balance page."""

    def __init__(self,
                 currency: Currency,
                 period: Period,
                 data_rows: list[TrialBalanceRow],
                 total: TrialBalanceRow):
        """Constructs the parameters for the trial balance page.

        :param currency: The currency.
        :param period: The period.
        :param data_rows: The data rows.
        :param total: The total row, if any.
        """
        super().__init__(
            period_chooser=TrialBalancePeriodChooser(currency),
            report_chooser=ReportChooser(ReportType.TRIAL_BALANCE,
                                         currency=currency,
                                         period=period),
            data_rows=data_rows,
            is_paged=False,
            total=total)
        self.currency: Currency = currency
        """The currency."""
        self.period: Period | None = period
        """The period."""

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


class IncomeStatementParams(ReportParams[IncomeStatementRow]):
    """The parameters of an income statement page."""

    def __init__(self,
                 currency: Currency,
                 period: Period,
                 data_rows: list[IncomeStatementRow]):
        """Constructs the parameters for the income statement page.

        :param currency: The currency.
        :param period: The period.
        :param data_rows: The data rows.
        """
        super().__init__(
            period_chooser=IncomeStatementPeriodChooser(currency),
            report_chooser=ReportChooser(ReportType.INCOME_STATEMENT,
                                         currency=currency,
                                         period=period),
            data_rows=data_rows,
            is_paged=False)
        self.currency: Currency = currency
        """The currency."""
        self.period: Period | None = period
        """The period."""

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
