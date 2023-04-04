# The Mia! Accounting Project.
# Author: imacat@mail.imacat.idv.tw (imacat), 2023/3/10

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
"""The account option for the journal entry management.

"""
from accounting.models import Account


class AccountOption:
    """An account option."""

    def __init__(self, account: Account):
        """Constructs an account option.

        :param account: The account.
        """
        self.id: str = account.id
        """The account ID."""
        self.code: str = account.code
        """The account code."""
        self.query_values: list[str] = account.query_values
        """The values to be queried."""
        self.__str: str = str(account)
        """The string representation of the account option."""
        self.is_in_use: bool = False
        """True if this account is in use, or False otherwise."""
        self.is_need_offset: bool = account.is_need_offset
        """True if this account needs offset, or False otherwise."""

    def __str__(self) -> str:
        """Returns the string representation of the account option.

        :return: The string representation of the account option.
        """
        return self.__str
