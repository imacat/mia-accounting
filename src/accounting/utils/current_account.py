# The Mia! Accounting Flask Project.
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
"""The current account.

"""
import typing as t

from accounting import db
from accounting.locale import gettext
from accounting.models import Account
import sqlalchemy as sa


class CurrentAccount:
    """The current account."""
    CURRENT_AL_CODE: str = "0000-000"
    """The account code for the current assets and liabilities."""

    def __init__(self, account: Account | None = None):
        """Constructs the current account.

        :param account: The account.
        """
        self.account: Account | None = account
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
        """Returns the pseudo account for current assets and liabilities.

        :return: The pseudo account for current assets and liabilities.
        """
        account: cls = cls()
        account.id = 0
        account.code = cls.CURRENT_AL_CODE
        account.title = gettext("current assets and liabilities")
        account.str = account.title
        return account


def current_accounts() -> list[CurrentAccount]:
    """Returns accounts for the income and expenses log.

    :return: The accounts for the income and expenses log.
    """
    accounts: list[CurrentAccount] \
        = [CurrentAccount.current_assets_and_liabilities()]
    accounts.extend([CurrentAccount(x)
                     for x in db.session.query(Account)
                    .filter(sa.or_(Account.base_code.startswith("11"),
                                   Account.base_code.startswith("12"),
                                   Account.base_code.startswith("21"),
                                   Account.base_code.startswith("22")))
                    .order_by(Account.base_code, Account.no)])
    return accounts
