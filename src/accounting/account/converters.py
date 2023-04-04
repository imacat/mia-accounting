# The Mia! Accounting Project.
# Author: imacat@mail.imacat.idv.tw (imacat), 2023/1/31

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
"""The path converters for the account management.

"""
from flask import abort
from werkzeug.routing import BaseConverter

from accounting.models import Account


class AccountConverter(BaseConverter):
    """The account converter to convert the account code and to the
    corresponding account in the routes."""

    def to_python(self, value: str) -> Account:
        """Converts an account code to an account.

        :param value: The account code.
        :return: The corresponding account.
        """
        account: Account | None = Account.find_by_code(value)
        if account is None:
            abort(404)
        return account

    def to_url(self, value: Account) -> str:
        """Converts an account to its code.

        :param value: The account.
        :return: The code.
        """
        return value.code
