# The Mia! Accounting Project.
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
"""The operators for different journal entry types.

"""
import typing as t
from abc import ABC, abstractmethod

from flask import render_template, request, abort
from flask_wtf import FlaskForm

from accounting.models import JournalEntry
from accounting.template_globals import default_currency_code
from accounting.utils.journal_entry_types import JournalEntryType
from accounting.journal_entry.forms import JournalEntryForm, \
    CashReceiptJournalEntryForm, CashDisbursementJournalEntryForm, \
    TransferJournalEntryForm
from accounting.journal_entry.forms.line_item import LineItemForm


class JournalEntryOperator(ABC):
    """The base journal entry operator."""
    CHECK_ORDER: int = -1
    """The order when checking the journal entry operator."""

    @property
    @abstractmethod
    def form(self) -> t.Type[JournalEntryForm]:
        """Returns the form class.

        :return: The form class.
        """

    @abstractmethod
    def render_create_template(self, form: FlaskForm) -> str:
        """Renders the template for the form to create a journal entry.

        :param form: The journal entry form.
        :return: the form to create a journal entry.
        """

    @abstractmethod
    def render_detail_template(self, journal_entry: JournalEntry) -> str:
        """Renders the template for the detail page.

        :param journal_entry: The journal entry.
        :return: the detail page.
        """

    @abstractmethod
    def render_edit_template(self, journal_entry: JournalEntry,
                             form: FlaskForm) -> str:
        """Renders the template for the form to edit a journal entry.

        :param journal_entry: The journal entry.
        :param form: The form.
        :return: the form to edit a journal entry.
        """

    @abstractmethod
    def is_my_type(self, journal_entry: JournalEntry) -> bool:
        """Checks and returns whether the journal entry belongs to the type.

        :param journal_entry: The journal entry.
        :return: True if the journal entry belongs to the type, or False
            otherwise.
        """

    @property
    def _line_item_template(self) -> str:
        """Renders and returns the template for the line item sub-form.

        :return: The template for the line item sub-form.
        """
        return render_template(
            "accounting/journal-entry/include/form-line-item.html",
            currency_index="CURRENCY_INDEX",
            debit_credit="DEBIT_CREDIT",
            line_item_index="LINE_ITEM_INDEX",
            form=LineItemForm())


class CashReceiptJournalEntry(JournalEntryOperator):
    """A cash receipt journal entry."""
    CHECK_ORDER: int = 2
    """The order when checking the journal entry operator."""

    @property
    def form(self) -> t.Type[JournalEntryForm]:
        """Returns the form class.

        :return: The form class.
        """
        return CashReceiptJournalEntryForm

    def render_create_template(self, form: CashReceiptJournalEntryForm) -> str:
        """Renders the template for the form to create a journal entry.

        :param form: The journal entry form.
        :return: the form to create a journal entry.
        """
        return render_template(
            "accounting/journal-entry/receipt/create.html",
            form=form,
            journal_entry_type=JournalEntryType.CASH_RECEIPT,
            currency_template=self.__currency_template,
            line_item_template=self._line_item_template)

    def render_detail_template(self, journal_entry: JournalEntry) -> str:
        """Renders the template for the detail page.

        :param journal_entry: The journal entry.
        :return: the detail page.
        """
        return render_template("accounting/journal-entry/receipt/detail.html",
                               obj=journal_entry)

    def render_edit_template(self, journal_entry: JournalEntry,
                             form: CashReceiptJournalEntryForm) -> str:
        """Renders the template for the form to edit a journal entry.

        :param journal_entry: The journal entry.
        :param form: The form.
        :return: the form to edit a journal entry.
        """
        return render_template("accounting/journal-entry/receipt/edit.html",
                               journal_entry=journal_entry, form=form,
                               currency_template=self.__currency_template,
                               line_item_template=self._line_item_template)

    def is_my_type(self, journal_entry: JournalEntry) -> bool:
        """Checks and returns whether the journal entry belongs to the type.

        :param journal_entry: The journal entry.
        :return: True if the journal entry belongs to the type, or False
            otherwise.
        """
        return journal_entry.is_cash_receipt

    @property
    def __currency_template(self) -> str:
        """Renders and returns the template for the currency sub-form.

        :return: The template for the currency sub-form.
        """
        return render_template(
            "accounting/journal-entry/receipt/include/form-currency.html",
            currency_index="CURRENCY_INDEX",
            currency_code_data=default_currency_code(),
            credit_total="-")


class CashDisbursementJournalEntry(JournalEntryOperator):
    """A cash disbursement journal entry."""
    CHECK_ORDER: int = 1
    """The order when checking the journal entry operator."""

    @property
    def form(self) -> t.Type[JournalEntryForm]:
        """Returns the form class.

        :return: The form class.
        """
        return CashDisbursementJournalEntryForm

    def render_create_template(self, form: CashDisbursementJournalEntryForm) \
            -> str:
        """Renders the template for the form to create a journal entry.

        :param form: The journal entry form.
        :return: the form to create a journal entry.
        """
        return render_template(
            "accounting/journal-entry/disbursement/create.html",
            form=form,
            journal_entry_type=JournalEntryType.CASH_DISBURSEMENT,
            currency_template=self.__currency_template,
            line_item_template=self._line_item_template)

    def render_detail_template(self, journal_entry: JournalEntry) -> str:
        """Renders the template for the detail page.

        :param journal_entry: The journal entry.
        :return: the detail page.
        """
        return render_template(
            "accounting/journal-entry/disbursement/detail.html",
            obj=journal_entry)

    def render_edit_template(self, journal_entry: JournalEntry,
                             form: CashDisbursementJournalEntryForm) -> str:
        """Renders the template for the form to edit a journal entry.

        :param journal_entry: The journal entry.
        :param form: The form.
        :return: the form to edit a journal entry.
        """
        return render_template(
            "accounting/journal-entry/disbursement/edit.html",
            journal_entry=journal_entry, form=form,
            currency_template=self.__currency_template,
            line_item_template=self._line_item_template)

    def is_my_type(self, journal_entry: JournalEntry) -> bool:
        """Checks and returns whether the journal entry belongs to the type.

        :param journal_entry: The journal entry.
        :return: True if the journal entry belongs to the type, or False
            otherwise.
        """
        return journal_entry.is_cash_disbursement

    @property
    def __currency_template(self) -> str:
        """Renders and returns the template for the currency sub-form.

        :return: The template for the currency sub-form.
        """
        return render_template(
            "accounting/journal-entry/disbursement/include/form-currency.html",
            currency_index="CURRENCY_INDEX",
            currency_code_data=default_currency_code(),
            debit_total="-")


class TransferJournalEntry(JournalEntryOperator):
    """A transfer journal entry."""
    CHECK_ORDER: int = 3
    """The order when checking the journal entry operator."""

    @property
    def form(self) -> t.Type[JournalEntryForm]:
        """Returns the form class.

        :return: The form class.
        """
        return TransferJournalEntryForm

    def render_create_template(self, form: TransferJournalEntryForm) -> str:
        """Renders the template for the form to create a journal entry.

        :param form: The journal entry form.
        :return: the form to create a journal entry.
        """
        return render_template(
            "accounting/journal-entry/transfer/create.html",
            form=form,
            journal_entry_type=JournalEntryType.TRANSFER,
            currency_template=self.__currency_template,
            line_item_template=self._line_item_template)

    def render_detail_template(self, journal_entry: JournalEntry) -> str:
        """Renders the template for the detail page.

        :param journal_entry: The journal entry.
        :return: the detail page.
        """
        return render_template("accounting/journal-entry/transfer/detail.html",
                               obj=journal_entry)

    def render_edit_template(self, journal_entry: JournalEntry,
                             form: TransferJournalEntryForm) -> str:
        """Renders the template for the form to edit a journal entry.

        :param journal_entry: The journal entry.
        :param form: The form.
        :return: the form to edit a journal entry.
        """
        return render_template("accounting/journal-entry/transfer/edit.html",
                               journal_entry=journal_entry, form=form,
                               currency_template=self.__currency_template,
                               line_item_template=self._line_item_template)

    def is_my_type(self, journal_entry: JournalEntry) -> bool:
        """Checks and returns whether the journal entry belongs to the type.

        :param journal_entry: The journal entry.
        :return: True if the journal entry belongs to the type, or False
            otherwise.
        """
        return True

    @property
    def __currency_template(self) -> str:
        """Renders and returns the template for the currency sub-form.

        :return: The template for the currency sub-form.
        """
        return render_template(
            "accounting/journal-entry/transfer/include/form-currency.html",
            currency_index="CURRENCY_INDEX",
            currency_code_data=default_currency_code(),
            debit_total="-", credit_total="-")


JOURNAL_ENTRY_TYPE_TO_OP: dict[JournalEntryType, JournalEntryOperator] \
    = {JournalEntryType.CASH_RECEIPT: CashReceiptJournalEntry(),
       JournalEntryType.CASH_DISBURSEMENT: CashDisbursementJournalEntry(),
       JournalEntryType.TRANSFER: TransferJournalEntry()}
"""The map from the journal entry types to their operators."""


def get_journal_entry_op(journal_entry: JournalEntry,
                         is_check_as: bool = False) -> JournalEntryOperator:
    """Returns the journal entry operator that may be specified in the "as"
    query parameter.  If it is not specified, check the journal entry type from
    the journal entry.

    :param journal_entry: The journal entry.
    :param is_check_as: True to check the "as" parameter, or False otherwise.
    :return: None.
    """
    if is_check_as and "as" in request.args:
        type_dict: dict[str, JournalEntryType] \
            = {x.value: x for x in JournalEntryType}
        if request.args["as"] not in type_dict:
            abort(404)
        return JOURNAL_ENTRY_TYPE_TO_OP[type_dict[request.args["as"]]]
    for journal_entry_type in sorted(JOURNAL_ENTRY_TYPE_TO_OP.values(),
                                     key=lambda x: x.CHECK_ORDER):
        if journal_entry_type.is_my_type(journal_entry):
            return journal_entry_type
