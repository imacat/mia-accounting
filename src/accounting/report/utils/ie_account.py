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
"""The pseudo account for the income and expenses log.

"""
from flask import current_app

from accounting.models import Account
from accounting.utils.ie_account import IncomeExpensesAccount


def default_ie_account_code() -> str:
    """Returns the default account code for the income and expenses log.

    :return: The default account code for the income and expenses log.
    """
    return current_app.config.get("ACCOUNTING_DEFAULT_IE_ACCOUNT",
                                  Account.CASH_CODE)


def default_ie_account() -> IncomeExpensesAccount:
    """Returns the default account for the income and expenses log.

    :return: The default account for the income and expenses log.
    """
    code: str = default_ie_account_code()
    if code == IncomeExpensesAccount.CURRENT_AL_CODE:
        return IncomeExpensesAccount.current_assets_and_liabilities()
    return IncomeExpensesAccount(Account.find_by_code(code))
