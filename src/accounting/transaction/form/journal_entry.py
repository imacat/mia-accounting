# The Mia! Accounting Flask Project.
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
"""The journal entry sub-forms for the transaction management.

"""
from __future__ import annotations

import re

from flask_babel import LazyString
from flask_wtf import FlaskForm
from wtforms import StringField, ValidationError, DecimalField, IntegerField
from wtforms.validators import DataRequired

from accounting.locale import lazy_gettext
from accounting.models import Account, JournalEntry
from accounting.utils.random_id import new_id
from accounting.utils.strip_text import strip_text
from accounting.utils.user import get_current_user_pk

ACCOUNT_REQUIRED: DataRequired = DataRequired(
    lazy_gettext("Please select the account."))
"""The validator to check if the account code is empty."""


class AccountExists:
    """The validator to check if the account exists."""

    def __call__(self, form: FlaskForm, field: StringField) -> None:
        if field.data is None:
            return
        if Account.find_by_code(field.data) is None:
            raise ValidationError(lazy_gettext(
                "The account does not exist."))


class PositiveAmount:
    """The validator to check if the amount is positive."""

    def __call__(self, form: FlaskForm, field: DecimalField) -> None:
        if field.data is None:
            return
        if field.data <= 0:
            raise ValidationError(lazy_gettext(
                "Please fill in a positive amount."))


class IsDebitAccount:
    """The validator to check if the account is for debit journal entries."""

    def __call__(self, form: FlaskForm, field: StringField) -> None:
        if field.data is None:
            return
        if re.match(r"^(?:[1235689]|7[5678])", field.data) \
                and not field.data.startswith("3351-") \
                and not field.data.startswith("3353-"):
            return
        raise ValidationError(lazy_gettext(
            "This account is not for debit entries."))


class JournalEntryForm(FlaskForm):
    """The base form to create or edit a journal entry."""
    eid = IntegerField()
    """The existing journal entry ID."""
    no = IntegerField()
    """The order in the currency."""
    account_code = StringField()
    """The account code."""
    amount = DecimalField()
    """The amount."""

    @property
    def account_text(self) -> str:
        """Returns the text representation of the account.

        :return: The text representation of the account.
        """
        if self.account_code.data is None:
            return ""
        account: Account | None = Account.find_by_code(self.account_code.data)
        if account is None:
            return ""
        return str(account)

    @property
    def all_errors(self) -> list[str | LazyString]:
        """Returns all the errors of the form.

        :return: All the errors of the form.
        """
        all_errors: list[str | LazyString] = []
        for key in self.errors:
            if key != "csrf_token":
                all_errors.extend(self.errors[key])
        return all_errors


class DebitEntryForm(JournalEntryForm):
    """The form to create or edit a debit journal entry."""
    eid = IntegerField()
    """The existing journal entry ID."""
    no = IntegerField()
    """The order in the currency."""
    account_code = StringField(
        filters=[strip_text],
        validators=[ACCOUNT_REQUIRED,
                    AccountExists(),
                    IsDebitAccount()])
    """The account code."""
    summary = StringField(filters=[strip_text])
    """The summary."""
    amount = DecimalField(validators=[PositiveAmount()])
    """The amount."""

    def populate_obj(self, obj: JournalEntry) -> None:
        """Populates the form data into a journal entry object.

        :param obj: The journal entry object.
        :return: None.
        """
        is_new: bool = obj.id is None
        if is_new:
            obj.id = new_id(JournalEntry)
        obj.account_id = Account.find_by_code(self.account_code.data).id
        obj.summary = self.summary.data
        obj.is_debit = True
        obj.amount = self.amount.data
        if is_new:
            current_user_pk: int = get_current_user_pk()
            obj.created_by_id = current_user_pk
            obj.updated_by_id = current_user_pk


class IsCreditAccount:
    """The validator to check if the account is for credit journal entries."""

    def __call__(self, form: FlaskForm, field: StringField) -> None:
        if field.data is None:
            return
        if re.match(r"^(?:[123489]|7[1234])", field.data) \
                and not field.data.startswith("3351-") \
                and not field.data.startswith("3353-"):
            return
        raise ValidationError(lazy_gettext(
            "This account is not for credit entries."))


class CreditEntryForm(JournalEntryForm):
    """The form to create or edit a credit journal entry."""
    eid = IntegerField()
    """The existing journal entry ID."""
    no = IntegerField()
    """The order in the currency."""
    account_code = StringField(
        filters=[strip_text],
        validators=[ACCOUNT_REQUIRED,
                    AccountExists(),
                    IsCreditAccount()])
    """The account code."""
    summary = StringField(filters=[strip_text])
    """The summary."""
    amount = DecimalField(validators=[PositiveAmount()])
    """The amount."""

    def populate_obj(self, obj: JournalEntry) -> None:
        """Populates the form data into a journal entry object.

        :param obj: The journal entry object.
        :return: None.
        """
        is_new: bool = obj.id is None
        if is_new:
            obj.id = new_id(JournalEntry)
        obj.account_id = Account.find_by_code(self.account_code.data).id
        obj.summary = self.summary.data
        obj.is_debit = False
        obj.amount = self.amount.data
        if is_new:
            current_user_pk: int = get_current_user_pk()
            obj.created_by_id = current_user_pk
            obj.updated_by_id = current_user_pk
