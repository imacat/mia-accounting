# The Mia! Accounting Flask Project.
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

from accounting.models import Currency, Account
from accounting.utils.permission import has_permission, can_view
from .period import Period
from .reports import Journal, Ledger, IncomeExpenses, TrialBalance

bp: Blueprint = Blueprint("report", __name__)
"""The view blueprint for the reports."""


@bp.get("journal", endpoint="journal-default")
@has_permission(can_view)
def get_default_journal_list() -> str | Response:
    """Returns the journal in the default period.

    :return: The journal in the default period.
    """
    return __get_journal_list(Period.get_instance())


@bp.get("journal/<period:period>", endpoint="journal")
@has_permission(can_view)
def get_journal_list(period: Period) -> str | Response:
    """Returns the journal.

    :param period: The period.
    :return: The journal in the period.
    """
    return __get_journal_list(period)


def __get_journal_list(period: Period) -> str | Response:
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
def get_default_ledger_list(currency: Currency, account: Account) \
        -> str | Response:
    """Returns the ledger in the default period.

    :param currency: The currency.
    :param account: The account.
    :return: The ledger in the default period.
    """
    return __get_ledger_list(currency, account, Period.get_instance())


@bp.get("ledger/<currency:currency>/<account:account>/<period:period>",
        endpoint="ledger")
@has_permission(can_view)
def get_ledger_list(currency: Currency, account: Account, period: Period) \
        -> str | Response:
    """Returns the ledger.

    :param currency: The currency.
    :param account: The account.
    :param period: The period.
    :return: The ledger in the period.
    """
    return __get_ledger_list(currency, account, period)


def __get_ledger_list(currency: Currency, account: Account, period: Period) \
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


@bp.get("income-expenses/<currency:currency>/<account:account>",
        endpoint="income-expenses-default")
@has_permission(can_view)
def get_default_income_expenses_list(currency: Currency, account: Account) \
        -> str | Response:
    """Returns the income and expenses in the default period.

    :param currency: The currency.
    :param account: The account.
    :return: The income and expenses in the default period.
    """
    return __get_income_expenses_list(currency, account, Period.get_instance())


@bp.get(
    "income-expenses/<currency:currency>/<account:account>/<period:period>",
    endpoint="income-expenses")
@has_permission(can_view)
def get_income_expenses_list(currency: Currency, account: Account,
                             period: Period) -> str | Response:
    """Returns the income and expenses.

    :param currency: The currency.
    :param account: The account.
    :param period: The period.
    :return: The income and expenses in the period.
    """
    return __get_income_expenses_list(currency, account, period)


def __get_income_expenses_list(currency: Currency, account: Account,
                               period: Period) -> str | Response:
    """Returns the income and expenses.

    :param currency: The currency.
    :param account: The account.
    :param period: The period.
    :return: The income and expenses in the period.
    """
    report: IncomeExpenses = IncomeExpenses(currency, account, period)
    if "as" in request.args and request.args["as"] == "csv":
        return report.csv()
    return report.html()


@bp.get("trial-balance/<currency:currency>",
        endpoint="trial-balance-default")
@has_permission(can_view)
def get_default_trial_balance_list(currency: Currency) -> str | Response:
    """Returns the trial balance in the default period.

    :param currency: The currency.
    :return: The trial balance in the default period.
    """
    return __get_trial_balance_list(currency, Period.get_instance())


@bp.get("trial-balance/<currency:currency>/<period:period>",
        endpoint="trial-balance")
@has_permission(can_view)
def get_trial_balance_list(currency: Currency, period: Period) \
        -> str | Response:
    """Returns the trial balance.

    :param currency: The currency.
    :param period: The period.
    :return: The trial balance in the period.
    """
    return __get_trial_balance_list(currency, period)


def __get_trial_balance_list(currency: Currency, period: Period) \
        -> str | Response:
    """Returns the trial balance.

    :param currency: The currency.
    :param period: The period.
    :return: The trial balance in the period.
    """
    report: TrialBalance = TrialBalance(currency, period)
    if "as" in request.args and request.args["as"] == "csv":
        return report.csv()
    return report.html()
