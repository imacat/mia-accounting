# The Mia! Accounting Project.
# Author: imacat@mail.imacat.idv.tw (imacat), 2023/3/22

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
"""The current assets and liabilities account.

"""
import typing as t

from accounting import db
from accounting.locale import gettext
from accounting.models import Account
import sqlalchemy as sa


class CurrentAccount:
    """A current assets and liabilities account."""
    CURRENT_AL_CODE: str = "0000-000"
    """The account code for all current assets and liabilities."""

    def __init__(self, account: Account | None = None):
        """Constructs the current assets and liabilities account.

        :param account: The actual account.
        """
        self.account: Account | None = account
        """The actual account."""
        self.id: int = -1 if account is None else account.id
        """The ID."""
        self.code: str = "" if account is None else account.code
        """The code."""
        self.title: str = "" if account is None else account.title
        """The title."""
        self.str: str = "" if account is None else str(account)
        """The string representation of the account."""

    def __str__(self) -> str:
        """Returns the string representation of the account.

        :return: The string representation of the account.
        """
        return self.str

    @classmethod
    def current_assets_and_liabilities(cls) -> t.Self:
        """Returns the pseudo account for all current assets and liabilities.

        :return: The pseudo account for all current assets and liabilities.
        """
        account: cls = cls()
        account.id = 0
        account.code = cls.CURRENT_AL_CODE
        account.title = gettext("current assets and liabilities")
        account.str = account.title
        return account

    @classmethod
    def accounts(cls) -> list[t.Self]:
        """Returns the current assets and liabilities accounts.

        :return: The current assets and liabilities accounts.
        """
        accounts: list[cls] = [cls.current_assets_and_liabilities()]
        accounts.extend([CurrentAccount(x)
                         for x in db.session.query(Account)
                        .filter(cls.sql_condition())
                        .order_by(Account.base_code, Account.no)])
        return accounts

    @classmethod
    def sql_condition(cls) -> sa.BinaryExpression:
        """Returns the SQL condition for the current assets and liabilities
        accounts.

        :return: The SQL condition for the current assets and liabilities
            accounts.
        """
        return sa.or_(Account.base_code.startswith("11"),
                      Account.base_code.startswith("12"),
                      Account.base_code.startswith("21"),
                      Account.base_code.startswith("22"))
