# The Mia! Accounting Project.
# Author: imacat@mail.imacat.idv.tw (imacat), 2023/3/9

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
"""The utilities to get the ledger URL.

"""
from flask import url_for

from accounting.models import Currency, Account
from accounting.report.period import Period
from accounting.template_globals import default_currency_code
from accounting.utils.current_account import CurrentAccount
from accounting.utils.options import options


def journal_url(period: Period) \
        -> str:
    """Returns the URL of a journal.

    :param period: The period.
    :return: The URL of the journal.
    """
    if period.is_default:
        return url_for("accounting-report.journal-default")
    return url_for("accounting-report.journal", period=period)


def ledger_url(currency: Currency, account: Account, period: Period) \
        -> str:
    """Returns the URL of a ledger.

    :param currency: The currency.
    :param account: The account.
    :param period: The period.
    :return: The URL of the ledger.
    """
    if currency.code == default_currency_code() \
            and account.code == Account.CASH_CODE \
            and period.is_default:
        return url_for("accounting-report.ledger-default")
    return url_for("accounting-report.ledger",
                   currency=currency, account=account,
                   period=period)


def income_expenses_url(currency: Currency, account: CurrentAccount,
                        period: Period) -> str:
    """Returns the URL of an income and expenses log.

    :param currency: The currency.
    :param account: The account.
    :param period: The period.
    :return: The URL of the income and expenses log.
    """
    if currency.code == default_currency_code() \
            and account.code == options.default_ie_account_code \
            and period.is_default:
        return url_for("accounting-report.default")
    return url_for("accounting-report.income-expenses",
                   currency=currency, account=account,
                   period=period)


def trial_balance_url(currency: Currency, period: Period) -> str:
    """Returns the URL of a trial balance.

    :param currency: The currency.
    :param period: The period.
    :return: The URL of the trial balance.
    """
    if currency.code == default_currency_code() and period.is_default:
        return url_for("accounting-report.trial-balance-default")
    return url_for("accounting-report.trial-balance",
                   currency=currency, period=period)


def income_statement_url(currency: Currency, period: Period) -> str:
    """Returns the URL of an income statement.

    :param currency: The currency.
    :param period: The period.
    :return: The URL of the income statement.
    """
    if currency.code == default_currency_code() and period.is_default:
        return url_for("accounting-report.income-statement-default")
    return url_for("accounting-report.income-statement",
                   currency=currency, period=period)


def balance_sheet_url(currency: Currency, period: Period) -> str:
    """Returns the URL of a balance sheet.

    :param currency: The currency.
    :param period: The period.
    :return: The URL of the balance sheet.
    """
    if currency.code == default_currency_code() and period.is_default:
        return url_for("accounting-report.balance-sheet-default")
    return url_for("accounting-report.balance-sheet",
                   currency=currency, period=period)


def unapplied_url(currency: Currency, account: Account | None) -> str:
    """Returns the URL of the unapplied original line items.

    :param currency: The currency.
    :param account: The account, or None to list the accounts with unapplied
        original line items.
    :return: The URL of the unapplied original line items.
    """
    if account is None:
        if currency.code == default_currency_code():
            return url_for("accounting-report.unapplied-accounts-default")
        return url_for("accounting-report.unapplied-accounts",
                       currency=currency)
    return url_for("accounting-report.unapplied",
                   currency=currency, account=account)


def unmatched_url(currency: Currency, account: Account | None) -> str:
    """Returns the URL of the unmatched offset line items.

    :param currency: The currency.
    :param account: The account, or None to list the accounts with unmatched
        offset line items.
    :return: The URL of the unmatched offset line items.
    """
    if account is None:
        if currency.code == default_currency_code():
            return url_for("accounting-report.unmatched-accounts-default")
        return url_for("accounting-report.unmatched-accounts",
                       currency=currency)
    return url_for("accounting-report.unmatched",
                   currency=currency, account=account)
