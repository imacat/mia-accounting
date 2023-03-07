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
"""The path converters for the report management.

"""
import re

from flask import abort
from werkzeug.routing import BaseConverter

from accounting.models import Account
from .income_expense_account import IncomeExpensesAccount
from .period import Period


class PeriodConverter(BaseConverter):
    """The supplier converter to convert the period specification from and to
    the corresponding period in the routes."""

    def to_python(self, value: str) -> Period:
        """Converts a period specification to a period.

        :param value: The period specification.
        :return: The corresponding period.
        """
        try:
            return Period.get_instance(value)
        except ValueError:
            abort(404)

    def to_url(self, value: Period) -> str:
        """Converts a period to its specification.

        :param value: The period.
        :return: Its specification.
        """
        return value.spec


class IncomeExpensesAccountConverter(BaseConverter):
    """The supplier converter to convert the income and expenses pseudo account
    code from and to the corresponding pseudo account in the routes."""

    def to_python(self, value: str) -> IncomeExpensesAccount:
        """Converts an account code to an account.

        :param value: The account code.
        :return: The corresponding account.
        """
        if value == IncomeExpensesAccount.CURRENT_AL_CODE:
            return IncomeExpensesAccount.current_assets_and_liabilities()
        if not re.match("^[12][12]", value):
            abort(404)
        account: Account | None = Account.find_by_code(value)
        if account is None:
            abort(404)
        return IncomeExpensesAccount(account)

    def to_url(self, value: IncomeExpensesAccount) -> str:
        """Converts an account to account code.

        :param value: The account.
        :return: Its code.
        """
        return value.code
