# The Mia! Accounting Project.
# Author: imacat@mail.imacat.idv.tw (imacat), 2023/2/6

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
"""The path converters for the currency management.

"""
from flask import abort
from werkzeug.routing import BaseConverter

from accounting import db
from accounting.models import Currency


class CurrencyConverter(BaseConverter):
    """The currency converter to convert the currency code and to the
    corresponding currency in the routes."""

    def to_python(self, value: str) -> Currency:
        """Converts a currency code to a currency.

        :param value: The currency code.
        :return: The corresponding currency.
        """
        currency: Currency | None = db.session.get(Currency, value)
        if currency is None:
            abort(404)
        return currency

    def to_url(self, value: Currency) -> str:
        """Converts a currency to its code.

        :param value: The currency.
        :return: The code.
        """
        return value.code
