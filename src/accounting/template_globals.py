# The Mia! Accounting Project.
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
"""The template globals.

"""
from accounting.models import Currency
from accounting.utils.options import options


def currency_options() -> str:
    """Returns the currency options.

    :return: The currency options.
    """
    return Currency.query.order_by(Currency.code).all()


def default_currency_code() -> str:
    """Returns the default currency code.

    :return: The default currency code.
    """
    return options.default_currency_code
