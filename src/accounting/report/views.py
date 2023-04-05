# The Mia! Accounting Project.
# Author: imacat@mail.imacat.idv.tw (imacat), 2023/3/3

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
"""The views for the report management.

"""
from flask import Blueprint, request, Response

from accounting import db
from accounting.models import Currency, Account
from accounting.report.period import Period, get_period
from accounting.template_globals import default_currency_code
from accounting.utils.current_account import CurrentAccount
from accounting.utils.options import options
from accounting.utils.permission import has_permission, can_view
from .reports import Journal, Ledger, IncomeExpenses, TrialBalance, \
    IncomeStatement, BalanceSheet, Search
from .template_filters import format_amount

bp: Blueprint = Blueprint("accounting-report", __name__)
"""The view blueprint for the reports."""
bp.add_app_template_filter(format_amount, "accounting_report_format_amount")


@bp.get("", endpoint="default")
@has_permission(can_view)
def get_default_report() -> str | Response:
    """Returns the income and expenses log in the default period.

    :return: The income and expenses log in the default period.
    """
    return __get_income_expenses(
        db.session.get(Currency, default_currency_code()),
        options.default_ie_account,
        get_period())


@bp.get("journal", endpoint="journal-default")
@has_permission(can_view)
def get_default_journal() -> str | Response:
    """Returns the journal in the default period.

    :return: The journal in the default period.
    """
    return __get_journal(get_period())


@bp.get("journal/<period:period>", endpoint="journal")
@has_permission(can_view)
def get_journal(period: Period) -> str | Response:
    """Returns the journal.

    :param period: The period.
    :return: The journal in the period.
    """
    return __get_journal(period)


def __get_journal(period: Period) -> str | Response:
    """Returns the journal.

    :param period: The period.
    :return: The journal in the period.
    """
    report: Journal = Journal(period)
    if "as" in request.args and request.args["as"] == "csv":
        return report.csv()
    return report.html()


@bp.get("ledger/<currency:currency>/<account:account>",
        endpoint="ledger-default")
@has_permission(can_view)
def get_default_ledger(currency: Currency, account: Account) -> str | Response:
    """Returns the ledger in the default period.

    :param currency: The currency.
    :param account: The account.
    :return: The ledger in the default period.
    """
    return __get_ledger(currency, account, get_period())


@bp.get("ledger/<currency:currency>/<account:account>/<period:period>",
        endpoint="ledger")
@has_permission(can_view)
def get_ledger(currency: Currency, account: Account, period: Period) \
        -> str | Response:
    """Returns the ledger.

    :param currency: The currency.
    :param account: The account.
    :param period: The period.
    :return: The ledger in the period.
    """
    return __get_ledger(currency, account, period)


def __get_ledger(currency: Currency, account: Account, period: Period) \
        -> str | Response:
    """Returns the ledger.

    :param currency: The currency.
    :param account: The account.
    :param period: The period.
    :return: The ledger in the period.
    """
    report: Ledger = Ledger(currency, account, period)
    if "as" in request.args and request.args["as"] == "csv":
        return report.csv()
    return report.html()


@bp.get("income-expenses/<currency:currency>/<ieAccount:account>",
        endpoint="income-expenses-default")
@has_permission(can_view)
def get_default_income_expenses(currency: Currency, account: CurrentAccount) \
        -> str | Response:
    """Returns the income and expenses log in the default period.

    :param currency: The currency.
    :param account: The account.
    :return: The income and expenses log in the default period.
    """
    return __get_income_expenses(currency, account, get_period())


@bp.get(
    "income-expenses/<currency:currency>/<ieAccount:account>/<period:period>",
    endpoint="income-expenses")
@has_permission(can_view)
def get_income_expenses(currency: Currency, account: CurrentAccount,
                        period: Period) -> str | Response:
    """Returns the income and expenses log.

    :param currency: The currency.
    :param account: The account.
    :param period: The period.
    :return: The income and expenses log in the period.
    """
    return __get_income_expenses(currency, account, period)


def __get_income_expenses(currency: Currency, account: CurrentAccount,
                          period: Period) -> str | Response:
    """Returns the income and expenses log.

    :param currency: The currency.
    :param account: The account.
    :param period: The period.
    :return: The income and expenses log in the period.
    """
    report: IncomeExpenses = IncomeExpenses(currency, account, period)
    if "as" in request.args and request.args["as"] == "csv":
        return report.csv()
    return report.html()


@bp.get("trial-balance/<currency:currency>",
        endpoint="trial-balance-default")
@has_permission(can_view)
def get_default_trial_balance(currency: Currency) -> str | Response:
    """Returns the trial balance in the default period.

    :param currency: The currency.
    :return: The trial balance in the default period.
    """
    return __get_trial_balance(currency, get_period())


@bp.get("trial-balance/<currency:currency>/<period:period>",
        endpoint="trial-balance")
@has_permission(can_view)
def get_trial_balance(currency: Currency, period: Period) -> str | Response:
    """Returns the trial balance.

    :param currency: The currency.
    :param period: The period.
    :return: The trial balance in the period.
    """
    return __get_trial_balance(currency, period)


def __get_trial_balance(currency: Currency, period: Period) -> str | Response:
    """Returns the trial balance.

    :param currency: The currency.
    :param period: The period.
    :return: The trial balance in the period.
    """
    report: TrialBalance = TrialBalance(currency, period)
    if "as" in request.args and request.args["as"] == "csv":
        return report.csv()
    return report.html()


@bp.get("income-statement/<currency:currency>",
        endpoint="income-statement-default")
@has_permission(can_view)
def get_default_income_statement(currency: Currency) -> str | Response:
    """Returns the income statement in the default period.

    :param currency: The currency.
    :return: The income statement in the default period.
    """
    return __get_income_statement(currency, get_period())


@bp.get("income-statement/<currency:currency>/<period:period>",
        endpoint="income-statement")
@has_permission(can_view)
def get_income_statement(currency: Currency, period: Period) -> str | Response:
    """Returns the income statement.

    :param currency: The currency.
    :param period: The period.
    :return: The income statement in the period.
    """
    return __get_income_statement(currency, period)


def __get_income_statement(currency: Currency, period: Period) \
        -> str | Response:
    """Returns the income statement.

    :param currency: The currency.
    :param period: The period.
    :return: The income statement in the period.
    """
    report: IncomeStatement = IncomeStatement(currency, period)
    if "as" in request.args and request.args["as"] == "csv":
        return report.csv()
    return report.html()


@bp.get("balance-sheet/<currency:currency>",
        endpoint="balance-sheet-default")
@has_permission(can_view)
def get_default_balance_sheet(currency: Currency) -> str | Response:
    """Returns the balance sheet in the default period.

    :param currency: The currency.
    :return: The balance sheet in the default period.
    """
    return __get_balance_sheet(currency, get_period())


@bp.get("balance-sheet/<currency:currency>/<period:period>",
        endpoint="balance-sheet")
@has_permission(can_view)
def get_balance_sheet(currency: Currency, period: Period) \
        -> str | Response:
    """Returns the balance sheet.

    :param currency: The currency.
    :param period: The period.
    :return: The balance sheet in the period.
    """
    return __get_balance_sheet(currency, period)


def __get_balance_sheet(currency: Currency, period: Period) \
        -> str | Response:
    """Returns the balance sheet.

    :param currency: The currency.
    :param period: The period.
    :return: The balance sheet in the period.
    """
    report: BalanceSheet = BalanceSheet(currency, period)
    if "as" in request.args and request.args["as"] == "csv":
        return report.csv()
    return report.html()


@bp.get("search", endpoint="search")
@has_permission(can_view)
def search() -> str | Response:
    """Returns the search result.

    :return: The search result.
    """
    report: Search = Search()
    if "as" in request.args and request.args["as"] == "csv":
        return report.csv()
    return report.html()
