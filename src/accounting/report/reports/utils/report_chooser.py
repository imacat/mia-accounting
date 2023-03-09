# The Mia! Accounting Flask Project.
# Author: imacat@mail.imacat.idv.tw (imacat), 2023/3/4

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
"""The report chooser.

This file is largely taken from the NanoParma ERP project, first written in
2021/9/16 by imacat (imacat@nanoparma.com).

"""
import re
import typing as t

from flask import url_for
from flask_babel import LazyString

from accounting import db
from accounting.locale import gettext
from accounting.models import Currency, Account
from accounting.report.income_expense_account import IncomeExpensesAccount
from accounting.report.period import Period
from accounting.template_globals import default_currency_code
from .get_url import get_ledger_url, get_income_expenses_url
from .option_link import OptionLink
from .report_type import ReportType


class ReportChooser:
    """The report chooser."""

    def __init__(self, active_report: ReportType,
                 period: Period | None = None,
                 currency: Currency | None = None,
                 account: Account | None = None):
        """Constructs the report chooser.

        :param active_report: The active report.
        :param period: The period.
        :param currency: The currency.
        :param account: The account.
        """
        self.__active_report: ReportType = active_report
        """The currently active report."""
        self.__period: Period = Period.get_instance() if period is None \
            else period
        """The period."""
        self.__currency: Currency = db.session.get(
            Currency, default_currency_code()) \
            if currency is None else currency
        """The currency."""
        self.__account: Account = Account.cash() if account is None \
            else account
        """The currency."""
        self.__reports: list[OptionLink] = []
        """The links to the reports."""
        self.current_report: str | LazyString = ""
        """The title of the current report."""
        self.is_search: bool = active_report == ReportType.SEARCH
        """Whether the current report is the search page."""
        self.__reports.append(self.__journal)
        self.__reports.append(self.__ledger)
        self.__reports.append(self.__income_expenses)
        self.__reports.append(self.__trial_balance)
        self.__reports.append(self.__income_statement)
        self.__reports.append(self.__balance_sheet)
        for report in self.__reports:
            if report.is_active:
                self.current_report = report.title
        if self.is_search:
            self.current_report = gettext("Search")

    @property
    def __journal(self) -> OptionLink:
        """Returns the journal.

        :return: The journal.
        """
        url: str = url_for("accounting.report.journal-default") \
            if self.__period.is_default \
            else url_for("accounting.report.journal", period=self.__period)
        return OptionLink(gettext("Journal"), url,
                          self.__active_report == ReportType.JOURNAL,
                          fa_icon="fa-solid fa-book")

    @property
    def __ledger(self) -> OptionLink:
        """Returns the ledger.

        :return: The ledger.
        """
        return OptionLink(gettext("Ledger"),
                          get_ledger_url(self.__currency, self.__account,
                                         self.__period),
                          self.__active_report == ReportType.LEDGER,
                          fa_icon="fa-solid fa-clipboard")

    @property
    def __income_expenses(self) -> OptionLink:
        """Returns the income and expenses log.

        :return: The income and expenses log.
        """
        account: Account = self.__account
        if not re.match(r"[12][12]", account.base_code):
            account: Account = Account.cash()
        return OptionLink(gettext("Income and Expenses Log"),
                          get_income_expenses_url(
                              self.__currency,
                              IncomeExpensesAccount(account),
                              self.__period),
                          self.__active_report == ReportType.INCOME_EXPENSES,
                          fa_icon="fa-solid fa-money-bill-wave")

    @property
    def __trial_balance(self) -> OptionLink:
        """Returns the trial balance.

        :return: The trial balance.
        """
        url: str = url_for("accounting.report.trial-balance-default",
                           currency=self.__currency) \
            if self.__period.is_default \
            else url_for("accounting.report.trial-balance",
                         currency=self.__currency, period=self.__period)
        return OptionLink(gettext("Trial Balance"), url,
                          self.__active_report == ReportType.TRIAL_BALANCE,
                          fa_icon="fa-solid fa-scale-unbalanced")

    @property
    def __income_statement(self) -> OptionLink:
        """Returns the income statement.

        :return: The income statement.
        """
        url: str = url_for("accounting.report.income-statement-default",
                           currency=self.__currency) \
            if self.__period.is_default \
            else url_for("accounting.report.income-statement",
                         currency=self.__currency, period=self.__period)
        return OptionLink(gettext("Income Statement"), url,
                          self.__active_report == ReportType.INCOME_STATEMENT,
                          fa_icon="fa-solid fa-file-invoice-dollar")

    @property
    def __balance_sheet(self) -> OptionLink:
        """Returns the balance sheet.

        :return: The balance sheet.
        """
        url: str = url_for("accounting.report.balance-sheet-default",
                           currency=self.__currency) \
            if self.__period.is_default \
            else url_for("accounting.report.balance-sheet",
                         currency=self.__currency, period=self.__period)
        return OptionLink(gettext("Balance Sheet"), url,
                          self.__active_report == ReportType.BALANCE_SHEET,
                          fa_icon="fa-solid fa-scale-balanced")

    def __iter__(self) -> t.Iterator[OptionLink]:
        """Returns the iteration of the reports.

        :return: The iteration of the reports.
        """
        return iter(self.__reports)
