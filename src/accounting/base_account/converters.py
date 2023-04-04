# The Mia! Accounting Project.
# Author: imacat@mail.imacat.idv.tw (imacat), 2023/2/1

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
"""The path converters for the base account management.

"""
from flask import abort
from werkzeug.routing import BaseConverter

from accounting import db
from accounting.models import BaseAccount


class BaseAccountConverter(BaseConverter):
    """The account converter to convert the account code and to the
    corresponding base account in the routes."""

    def to_python(self, value: str) -> BaseAccount:
        """Converts an account code to a base account.

        :param value: The account code.
        :return: The corresponding base account.
        """
        account: BaseAccount | None = db.session.get(BaseAccount, value)
        if account is None:
            abort(404)
        return account

    def to_url(self, value: BaseAccount) -> str:
        """Converts a base account to its code.

        :param value: The base account.
        :return: The code.
        """
        return value.code
