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
"""The forms.

"""
import re

from flask_babel import LazyString
from flask_wtf import FlaskForm
from wtforms import StringField, ValidationError
from wtforms.validators import DataRequired

from accounting import db
from accounting.locale import lazy_gettext
from accounting.models import Currency, Account


ACCOUNT_REQUIRED: DataRequired = DataRequired(
    lazy_gettext("Please select the account."))
"""The validator to check if the account code is empty."""


class CurrencyExists:
    """The validator to check if the account exists."""

    def __call__(self, form: FlaskForm, field: StringField) -> None:
        if field.data is None:
            return
        if db.session.get(Currency, field.data) is None:
            raise ValidationError(lazy_gettext(
                "The currency does not exist."))


class AccountExists:
    """The validator to check if the account exists."""

    def __call__(self, form: FlaskForm, field: StringField) -> None:
        if field.data is None:
            return
        if Account.find_by_code(field.data) is None:
            raise ValidationError(lazy_gettext(
                "The account does not exist."))


class IsDebitAccount:
    """The validator to check if the account is for debit line items."""

    def __init__(self, message: str | LazyString):
        """Constructs the validator.

        :param message: The error message.
        """
        self.__message: str | LazyString = message

    def __call__(self, form: FlaskForm, field: StringField) -> None:
        if field.data is None:
            return
        if re.match(r"^(?:[1235689]|7[5678])", field.data) \
                and not field.data.startswith("3351-") \
                and not field.data.startswith("3353-"):
            return
        raise ValidationError(self.__message)


class IsCreditAccount:
    """The validator to check if the account is for credit line items."""

    def __init__(self, message: str | LazyString):
        """Constructs the validator.

        :param message: The error message.
        """
        self.__message: str | LazyString = message

    def __call__(self, form: FlaskForm, field: StringField) -> None:
        if field.data is None:
            return
        if re.match(r"^(?:[123489]|7[1234])", field.data) \
                and not field.data.startswith("3351-") \
                and not field.data.startswith("3353-"):
            return
        raise ValidationError(self.__message)
