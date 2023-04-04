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
"""The forms for the option management.

"""
from flask import render_template
from flask_babel import LazyString
from flask_wtf import FlaskForm
from wtforms import StringField, FieldList, FormField, IntegerField
from wtforms.validators import DataRequired, ValidationError

from accounting.forms import ACCOUNT_REQUIRED, CurrencyExists, AccountExists, \
    IsDebitAccount, IsCreditAccount
from accounting.locale import lazy_gettext
from accounting.models import Account
from accounting.utils.current_account import CurrentAccount
from accounting.utils.options import Options
from accounting.utils.strip_text import strip_text


class CurrentAccountExists:
    """The validator to check that the current account exists."""

    def __call__(self, form: FlaskForm, field: StringField) -> None:
        if field.data is None or field.data == CurrentAccount.CURRENT_AL_CODE:
            return
        if Account.find_by_code(field.data) is None:
            raise ValidationError(lazy_gettext(
                "The account does not exist."))


class AccountNotCurrent:
    """The validator to check that the account is a current account."""

    def __call__(self, form: FlaskForm, field: StringField) -> None:
        if field.data is None or field.data == CurrentAccount.CURRENT_AL_CODE:
            return
        if field.data[:2] not in {"11", "12", "21", "22"}:
            raise ValidationError(lazy_gettext(
                "This is not a current account."))


class NotStartPayableFromExpense:
    """The validator to check that a payable line item does not start from
    expense."""

    def __call__(self, form: FlaskForm, field: StringField) -> None:
        if field.data is None or field.data[0] != "2":
            return
        account: Account | None = Account.find_by_code(field.data)
        if account is not None and account.is_need_offset:
            raise ValidationError(lazy_gettext(
                "You cannot select a payable account as expense."))


class NotStartReceivableFromIncome:
    """The validator to check that a receivable line item does not start
    from income."""

    def __call__(self, form: FlaskForm, field: StringField) -> None:
        if field.data is None or field.data[0] != "1":
            return
        account: Account | None = Account.find_by_code(field.data)
        if account is not None and account.is_need_offset:
            raise ValidationError(lazy_gettext(
                "You cannot select a receivable account as income."))


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

    @property
    def account_text(self) -> str | None:
        """Returns the account text.

        :return: The account text.
        """
        if self.account_code.data is None:
            return None
        account: Account | None = Account.find_by_code(self.account_code.data)
        return None if account is None else str(account)

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
        validators=[
            ACCOUNT_REQUIRED,
            AccountExists(),
            IsDebitAccount(lazy_gettext("This account is not for expense.")),
            NotStartPayableFromExpense()])
    """The account code."""
    description_template = StringField(
        filters=[strip_text],
        validators=[
            DataRequired(lazy_gettext(
                "Please fill in the description template."))])
    """The template for the line item description."""


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
        validators=[
            ACCOUNT_REQUIRED,
            AccountExists(),
            IsCreditAccount(lazy_gettext("This account is not for income.")),
            NotStartReceivableFromIncome()])
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
    incomes = FieldList(FormField(RecurringIncomeForm), name="income")
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
        return Account.selectable_debit()

    @property
    def income_accounts(self) -> list[Account]:
        """The income accounts.

        :return: None.
        """
        return Account.selectable_credit()

    @property
    def as_data(self) -> dict[str, list[tuple[str, str, str]]]:
        """Returns the form data.

        :return: The form data.
        """
        def as_tuple(item: RecurringItemForm) -> tuple[str, str, str]:
            return (item.name.data, item.account_code.data,
                    item.description_template.data)

        expenses: list[RecurringItemForm] = [x.form for x in self.expenses]
        self.__sort_item_forms(expenses)
        incomes: list[RecurringItemForm] = [x.form for x in self.incomes]
        self.__sort_item_forms(incomes)
        return {"expense": [as_tuple(x) for x in expenses],
                "income": [as_tuple(x) for x in incomes]}

    @staticmethod
    def __sort_item_forms(forms: list[RecurringItemForm]) -> None:
        """Sorts the recurring item sub-forms.

        :param forms: The recurring item sub-forms.
        :return: None.
        """
        ord_by_form: dict[RecurringItemForm, int] \
            = {forms[i]: i for i in range(len(forms))}
        recv_no: set[int] = {x.no.data for x in forms if x.no.data is not None}
        missing_recv_no: int = 100 if len(recv_no) == 0 else max(recv_no) + 100
        forms.sort(key=lambda x: (x.no.data or missing_recv_no,
                                  ord_by_form.get(x)))


class OptionForm(FlaskForm):
    """The form to update the options."""
    default_currency_code = StringField(
        filters=[strip_text],
        validators=[
            DataRequired(lazy_gettext("Please select the default currency.")),
            CurrencyExists()])
    """The default currency code."""
    default_ie_account_code = StringField(
        filters=[strip_text],
        validators=[
            DataRequired(lazy_gettext(
                "Please select the default account"
                " for the income and expenses log.")),
            CurrentAccountExists(),
            AccountNotCurrent()])
    """The default account code for the income and expenses log."""
    recurring = FormField(RecurringForm)
    """The recurring expenses and incomes."""

    def populate_obj(self, obj: Options) -> None:
        """Populates the form data into a currency object.

        :param obj: The currency object.
        :return: None.
        """
        obj.default_currency_code = self.default_currency_code.data
        obj.default_ie_account_code = self.default_ie_account_code.data
        obj.recurring_data = self.recurring.form.as_data

    @property
    def current_accounts(self) -> list[CurrentAccount]:
        """Returns the current accounts.

        :return: The current accounts.
        """
        return CurrentAccount.accounts()
