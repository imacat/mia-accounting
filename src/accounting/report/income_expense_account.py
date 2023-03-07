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
import typing as t

from accounting.locale import gettext
from accounting.models import Account


class IncomeExpensesAccount:
    """The pseudo account for the income and expenses log."""
    CURRENT_AL_CODE: str = "0000-000"
    """The account code for the current assets and liabilities."""

    def __init__(self, account: Account | None = None):
        """Constructs the pseudo account for the income and expenses log.

        :param account: The actual account.
        """
        self.account: Account | None = None
        self.id: int | None = None
        """The ID."""
        self.code: str | None = None
        """The code."""
        self.title: str | None = None
        """The title."""
        self.str: str = ""
        """The string representation of the account."""
        if account is not None:
            self.account = account
            self.id = account.id
            self.code = account.code
            self.title = account.title
            self.str = str(account)

    def __str__(self) -> str:
        """Returns the string representation of the account.

        :return: The string representation of the account.
        """
        return self.str

    @classmethod
    def current_assets_and_liabilities(cls) -> t.Self:
        """Returns the pseudo account for current assets and liabilities.

        :return: The pseudo account for current assets and liabilities.
        """
        account: cls = cls()
        account.id = 0
        account.code = cls.CURRENT_AL_CODE
        account.title = gettext("current assets and liabilities")
        account.str = account.title
        return account
