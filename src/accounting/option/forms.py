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
"""The forms for the option management.

"""
import re
import typing as t

from flask import render_template
from flask_wtf import FlaskForm
from wtforms import StringField, FieldList, FormField, IntegerField
from wtforms.validators import DataRequired, ValidationError

from accounting.forms import CURRENCY_REQUIRED, CurrencyExists
from accounting.locale import lazy_gettext
from accounting.models import Account
from accounting.utils.ie_account import IncomeExpensesAccount, ie_accounts
from accounting.utils.strip_text import strip_text
from .options import Options


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

    def __call__(self, form: FlaskForm, field: StringField) -> None:
        if field.data is None:
            return
        if re.match(r"^(?:[1235689]|7[5678])", field.data) \
                and not field.data.startswith("3351-") \
                and not field.data.startswith("3353-"):
            return
        raise ValidationError(lazy_gettext(
            "This account is not for debit line items."))


class IsCreditAccount:
    """The validator to check if the account is for credit line items."""

    def __call__(self, form: FlaskForm, field: StringField) -> None:
        if field.data is None:
            return
        if re.match(r"^(?:[123489]|7[1234])", field.data) \
                and not field.data.startswith("3351-") \
                and not field.data.startswith("3353-"):
            return
        raise ValidationError(lazy_gettext(
            "This account is not for credit line items."))


class NotStartPayableFromDebit:
    """The validator to check that a payable line item does not start from
    debit."""

    def __call__(self, form: FlaskForm, field: StringField) -> None:
        if field.data is None or field.data[0] != "2":
            return
        account: Account | None = Account.find_by_code(field.data)
        if account is not None and account.is_need_offset:
            raise ValidationError(lazy_gettext(
                "A payable line item cannot start from debit."))


class NotStartReceivableFromCredit:
    """The validator to check that a receivable line item does not start
    from credit."""

    def __call__(self, form: FlaskForm, field: StringField) -> None:
        if field.data is None or field.data[0] != "1":
            return
        account: Account | None = Account.find_by_code(field.data)
        if account is not None and account.is_need_offset:
            raise ValidationError(lazy_gettext(
                "A receivable line item cannot start from credit."))


class RecurringItemForm(FlaskForm):
    """The base sub-form to add or update the recurring item."""
    no = IntegerField()
    """The order number of this recurring item."""
    name = StringField()
    """The name of the recurring item."""
    account_code = StringField()
    """The account code."""
    description_template = StringField()
    """The description template."""


class RecurringExpenseForm(RecurringItemForm):
    """The sub-form to add or update the recurring expenses."""
    no = IntegerField()
    """The order number of this recurring item."""
    name = StringField(
        filters=[strip_text],
        validators=[DataRequired(lazy_gettext("Please fill in the name."))])
    """The name of the recurring item."""
    account_code = StringField(
        filters=[strip_text],
        validators=[AccountExists(),
                    IsDebitAccount(),
                    NotStartPayableFromDebit()])
    """The account code."""
    description_template = StringField(
        filters=[strip_text],
        validators=[
            DataRequired(lazy_gettext(
                "Please fill in the template of the description."))])
    """The template for the line item description."""

    @property
    def account_text(self) -> str | None:
        """Returns the account text.

        :return: The account text.
        """
        if self.account_code.data is None:
            return None
        account: Account | None = Account.find_by_code(self.account_code.data)
        return None if account is None else str(account)


class RecurringIncomeForm(RecurringItemForm):
    """The sub-form to add or update the recurring incomes."""
    no = IntegerField()
    """The order number of this recurring item."""
    name = StringField(
        filters=[strip_text],
        validators=[DataRequired(lazy_gettext("Please fill in the name."))])
    """The name of the recurring item."""
    account_code = StringField(
        filters=[strip_text],
        validators=[AccountExists(),
                    IsDebitAccount(),
                    NotStartReceivableFromCredit()])
    """The account code."""
    description_template = StringField(
        filters=[strip_text],
        validators=[
            DataRequired(lazy_gettext(
                "Please fill in the description template."))])
    """The description template."""


class RecurringForm(RecurringItemForm):
    """The sub-form for the recurring expenses and incomes."""
    expenses = FieldList(FormField(RecurringExpenseForm), name="expense")
    """The recurring expenses."""
    incomes = FieldList(FormField(RecurringExpenseForm), name="income")
    """The recurring incomes."""

    @property
    def item_template(self) -> str:
        """Returns the template of a recurring item.

        :return: The template of a recurring item.
        """
        return render_template(
            "accounting/option/include/form-recurring-item.html",
            expense_income="EXPENSE_INCOME",
            item_index="ITEM_INDEX",
            form=RecurringItemForm())

    @property
    def expense_accounts(self) -> list[Account]:
        """The expense accounts.

        :return: None.
        """
        return Account.debit()

    @property
    def income_accounts(self) -> list[Account]:
        """The income accounts.

        :return: None.
        """
        return Account.credit()

    @property
    def as_data(self) -> dict[str, list[tuple[str, str, str]]]:
        """Returns the form data.

        :return: The form data.
        """
        def as_tuple(item: RecurringItemForm) -> tuple[str, str, str]:
            return (item.name.data, item.account_code.data,
                    item.description_template.data)

        return {"expense": [as_tuple(x.form) for x in self.expenses],
                "income": [as_tuple(x.form) for x in self.incomes]}


class OptionForm(FlaskForm):
    """The form to update the options."""
    default_currency = StringField(
        filters=[strip_text],
        validators=[CURRENCY_REQUIRED,
                    CurrencyExists()])
    """The default currency code."""
    default_ie_account_code = StringField(
        filters=[strip_text],
        validators=[
            DataRequired(lazy_gettext(
                "Please fill in the default account code"
                " for the income and expenses log."))])
    """The default account code for the income and expenses log."""
    recurring = FormField(RecurringForm)
    """The recurring expenses and incomes."""

    def populate_obj(self, obj: Options) -> None:
        """Populates the form data into a currency object.

        :param obj: The currency object.
        :return: None.
        """
        obj.default_currency = self.default_currency.data
        obj.default_ie_account_code = self.default_ie_account_code.data
        obj.recurring_data = self.recurring.form.as_data

    @property
    def ie_accounts(self) -> list[IncomeExpensesAccount]:
        """Returns the accounts for the income and expenses log.

        :return: The accounts for the income and expenses log.
        """
        return ie_accounts()