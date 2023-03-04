# The Mia! Accounting Flask Project.
# Author: imacat@mail.imacat.idv.tw (imacat), 2023/2/19

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
"""The view dispatcher for different transaction types.

"""
import typing as t
from abc import ABC, abstractmethod

from flask import render_template, request, abort
from flask_wtf import FlaskForm

from accounting.models import Transaction
from accounting.template_globals import default_currency_code
from accounting.utils.txn_types import TransactionTypeEnum
from .forms import TransactionForm, IncomeTransactionForm, \
    ExpenseTransactionForm, TransferTransactionForm


class TransactionType(ABC):
    """An abstract transaction type."""
    CHECK_ORDER: int = -1
    """The order when checking the transaction type."""

    @property
    @abstractmethod
    def form(self) -> t.Type[TransactionForm]:
        """Returns the form class.

        :return: The form class.
        """

    @abstractmethod
    def render_create_template(self, form: FlaskForm) -> str:
        """Renders the template for the form to create a transaction.

        :param form: The transaction form.
        :return: the form to create a transaction.
        """

    @abstractmethod
    def render_detail_template(self, txn: Transaction) -> str:
        """Renders the template for the detail page.

        :param txn: The transaction.
        :return: the detail page.
        """

    @abstractmethod
    def render_edit_template(self, txn: Transaction, form: FlaskForm) -> str:
        """Renders the template for the form to edit a transaction.

        :param txn: The transaction.
        :param form: The form.
        :return: the form to edit a transaction.
        """

    @abstractmethod
    def is_my_type(self, txn: Transaction) -> bool:
        """Checks and returns whether the transaction belongs to the type.

        :param txn: The transaction.
        :return: True if the transaction belongs to the type, or False
            otherwise.
        """

    @property
    def _entry_template(self) -> str:
        """Renders and returns the template for the journal entry sub-form.

        :return: The template for the journal entry sub-form.
        """
        return render_template(
            "accounting/transaction/include/form-entry-item.html",
            currency_index="CURRENCY_INDEX",
            entry_type="ENTRY_TYPE",
            entry_index="ENTRY_INDEX")


class IncomeTransaction(TransactionType):
    """An income transaction."""
    CHECK_ORDER: int = 2
    """The order when checking the transaction type."""

    @property
    def form(self) -> t.Type[TransactionForm]:
        """Returns the form class.

        :return: The form class.
        """
        return IncomeTransactionForm

    def render_create_template(self, form: IncomeTransactionForm) -> str:
        """Renders the template for the form to create a transaction.

        :param form: The transaction form.
        :return: the form to create a transaction.
        """
        return render_template("accounting/transaction/income/create.html",
                               form=form,
                               txn_type=TransactionTypeEnum.CASH_INCOME,
                               currency_template=self.__currency_template,
                               entry_template=self._entry_template)

    def render_detail_template(self, txn: Transaction) -> str:
        """Renders the template for the detail page.

        :param txn: The transaction.
        :return: the detail page.
        """
        return render_template("accounting/transaction/income/detail.html",
                               obj=txn)

    def render_edit_template(self, txn: Transaction,
                             form: IncomeTransactionForm) -> str:
        """Renders the template for the form to edit a transaction.

        :param txn: The transaction.
        :param form: The form.
        :return: the form to edit a transaction.
        """
        return render_template("accounting/transaction/income/edit.html",
                               txn=txn, form=form,
                               currency_template=self.__currency_template,
                               entry_template=self._entry_template)

    def is_my_type(self, txn: Transaction) -> bool:
        """Checks and returns whether the transaction belongs to the type.

        :param txn: The transaction.
        :return: True if the transaction belongs to the type, or False
            otherwise.
        """
        return txn.is_cash_income

    @property
    def __currency_template(self) -> str:
        """Renders and returns the template for the currency sub-form.

        :return: The template for the currency sub-form.
        """
        return render_template(
            "accounting/transaction/income/include/form-currency-item.html",
            currency_index="CURRENCY_INDEX",
            currency_code_data=default_currency_code(),
            credit_total="-")


class ExpenseTransaction(TransactionType):
    """An expense transaction."""
    CHECK_ORDER: int = 1
    """The order when checking the transaction type."""

    @property
    def form(self) -> t.Type[TransactionForm]:
        """Returns the form class.

        :return: The form class.
        """
        return ExpenseTransactionForm

    def render_create_template(self, form: ExpenseTransactionForm) -> str:
        """Renders the template for the form to create a transaction.

        :param form: The transaction form.
        :return: the form to create a transaction.
        """
        return render_template("accounting/transaction/expense/create.html",
                               form=form,
                               txn_type=TransactionTypeEnum.CASH_EXPENSE,
                               currency_template=self.__currency_template,
                               entry_template=self._entry_template)

    def render_detail_template(self, txn: Transaction) -> str:
        """Renders the template for the detail page.

        :param txn: The transaction.
        :return: the detail page.
        """
        return render_template("accounting/transaction/expense/detail.html",
                               obj=txn)

    def render_edit_template(self, txn: Transaction,
                             form: ExpenseTransactionForm) -> str:
        """Renders the template for the form to edit a transaction.

        :param txn: The transaction.
        :param form: The form.
        :return: the form to edit a transaction.
        """
        return render_template("accounting/transaction/expense/edit.html",
                               txn=txn, form=form,
                               currency_template=self.__currency_template,
                               entry_template=self._entry_template)

    def is_my_type(self, txn: Transaction) -> bool:
        """Checks and returns whether the transaction belongs to the type.

        :param txn: The transaction.
        :return: True if the transaction belongs to the type, or False
            otherwise.
        """
        return txn.is_cash_expense

    @property
    def __currency_template(self) -> str:
        """Renders and returns the template for the currency sub-form.

        :return: The template for the currency sub-form.
        """
        return render_template(
            "accounting/transaction/expense/include/form-currency-item.html",
            currency_index="CURRENCY_INDEX",
            currency_code_data=default_currency_code(),
            debit_total="-")


class TransferTransaction(TransactionType):
    """A transfer transaction."""
    CHECK_ORDER: int = 3
    """The order when checking the transaction type."""

    @property
    def form(self) -> t.Type[TransactionForm]:
        """Returns the form class.

        :return: The form class.
        """
        return TransferTransactionForm

    def render_create_template(self, form: TransferTransactionForm) -> str:
        """Renders the template for the form to create a transaction.

        :param form: The transaction form.
        :return: the form to create a transaction.
        """
        return render_template("accounting/transaction/transfer/create.html",
                               form=form,
                               txn_type=TransactionTypeEnum.TRANSFER,
                               currency_template=self.__currency_template,
                               entry_template=self._entry_template)

    def render_detail_template(self, txn: Transaction) -> str:
        """Renders the template for the detail page.

        :param txn: The transaction.
        :return: the detail page.
        """
        return render_template("accounting/transaction/transfer/detail.html",
                               obj=txn)

    def render_edit_template(self, txn: Transaction,
                             form: TransferTransactionForm) -> str:
        """Renders the template for the form to edit a transaction.

        :param txn: The transaction.
        :param form: The form.
        :return: the form to edit a transaction.
        """
        return render_template("accounting/transaction/transfer/edit.html",
                               txn=txn, form=form,
                               currency_template=self.__currency_template,
                               entry_template=self._entry_template)

    def is_my_type(self, txn: Transaction) -> bool:
        """Checks and returns whether the transaction belongs to the type.

        :param txn: The transaction.
        :return: True if the transaction belongs to the type, or False
            otherwise.
        """
        return True

    @property
    def __currency_template(self) -> str:
        """Renders and returns the template for the currency sub-form.

        :return: The template for the currency sub-form.
        """
        return render_template(
            "accounting/transaction/transfer/include/form-currency-item.html",
            currency_index="CURRENCY_INDEX",
            currency_code_data=default_currency_code(),
            debit_total="-", credit_total="-")


TXN_ENUM_TO_OP: dict[TransactionTypeEnum, TransactionType] \
    = {TransactionTypeEnum.CASH_INCOME: IncomeTransaction(),
       TransactionTypeEnum.CASH_EXPENSE: ExpenseTransaction(),
       TransactionTypeEnum.TRANSFER: TransferTransaction()}
"""The map from the transaction type enum to its operator."""


def get_txn_type_op(txn: Transaction) -> TransactionType:
    """Returns the transaction type operator that may be specified in the "as"
    query parameter.  If it is not specified, check the transaction type from
    the transaction.

    :param txn: The transaction.
    :return: None.
    """
    if "as" in request.args:
        type_dict: dict[str, TransactionTypeEnum] \
            = {x.value: x for x in TransactionTypeEnum}
        if request.args["as"] not in type_dict:
            abort(404)
        return TXN_ENUM_TO_OP[type_dict[request.args["as"]]]
    for txn_type in sorted(TXN_ENUM_TO_OP.values(),
                           key=lambda x: x.CHECK_ORDER):
        if txn_type.is_my_type(txn):
            return txn_type
