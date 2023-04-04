# The Mia! Accounting Project.
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
"""The currency sub-forms for the journal entry management.

"""
from decimal import Decimal

import sqlalchemy as sa
from flask_babel import LazyString
from flask_wtf import FlaskForm
from wtforms import StringField, ValidationError, FieldList, IntegerField, \
    BooleanField, FormField
from wtforms.validators import DataRequired

from accounting import db
from accounting.forms import CurrencyExists
from accounting.journal_entry.utils.offset_alias import offset_alias
from accounting.locale import lazy_gettext
from accounting.models import JournalEntryLineItem
from accounting.utils.cast import be
from accounting.utils.strip_text import strip_text
from .line_item import LineItemForm, CreditLineItemForm, DebitLineItemForm


CURRENCY_REQUIRED: DataRequired = DataRequired(
    lazy_gettext("Please select the currency."))
"""The validator to check if the currency code is empty."""


class SameCurrencyAsOriginalLineItems:
    """The validator to check if the currency is the same as the
    original line items."""

    def __call__(self, form: FlaskForm, field: StringField) -> None:
        assert isinstance(form, CurrencyForm)
        if field.data is None:
            return
        original_line_item_id: set[int] \
            = {x.original_line_item_id.data
               for x in form.line_items
               if x.original_line_item_id.data is not None}
        if len(original_line_item_id) == 0:
            return
        original_line_item_currency_codes: set[str] = set(db.session.scalars(
            sa.select(JournalEntryLineItem.currency_code)
            .filter(JournalEntryLineItem.id.in_(original_line_item_id))).all())
        for currency_code in original_line_item_currency_codes:
            if field.data != currency_code:
                raise ValidationError(lazy_gettext(
                    "The currency must be the same as the"
                    " original line item."))


class KeepCurrencyWhenHavingOffset:
    """The validator to check if the currency is the same when there is
    offset."""

    def __call__(self, form: FlaskForm, field: StringField) -> None:
        assert isinstance(form, CurrencyForm)
        if field.data is None:
            return
        offset: sa.Alias = offset_alias()
        original_line_items: list[JournalEntryLineItem]\
            = JournalEntryLineItem.query\
            .join(offset, be(JournalEntryLineItem.id
                             == offset.c.original_line_item_id),
                  isouter=True)\
            .filter(JournalEntryLineItem.id
                    .in_({x.id.data for x in form.line_items
                          if x.id.data is not None}))\
            .group_by(JournalEntryLineItem.id,
                      JournalEntryLineItem.currency_code)\
            .having(sa.func.count(offset.c.id) > 0).all()
        for original_line_item in original_line_items:
            if original_line_item.currency_code != field.data:
                raise ValidationError(lazy_gettext(
                    "The currency must not be changed when there is offset."))


class NeedSomeLineItems:
    """The validator to check if there is any line item sub-form."""

    def __call__(self, form: FlaskForm, field: FieldList) -> None:
        if len(field) == 0:
            raise ValidationError(lazy_gettext(
                "Please add some line items."))


class IsBalanced:
    """The validator to check that the total amount of the debit and credit
    line items are equal."""

    def __call__(self, form: FlaskForm, field: BooleanField) -> None:
        assert isinstance(form, TransferCurrencyForm)
        if len(form.debit) == 0 or len(form.credit) == 0:
            return
        if form.debit_total != form.credit_total:
            raise ValidationError(lazy_gettext(
                "The totals of the debit and credit amounts do not match."))


class CurrencyForm(FlaskForm):
    """The form to create or edit a currency in a journal entry."""
    no = IntegerField()
    """The order in the journal entry."""
    code = StringField()
    """The currency code."""
    whole_form = BooleanField()
    """The pseudo field for the whole form validators."""

    @property
    def line_items(self) -> list[LineItemForm]:
        """Returns the line item sub-forms.

        :return: The line item sub-forms.
        """
        line_item_forms: list[LineItemForm] = []
        if isinstance(self, CashReceiptCurrencyForm):
            line_item_forms.extend([x.form for x in self.credit])
        elif isinstance(self, CashDisbursementCurrencyForm):
            line_item_forms.extend([x.form for x in self.debit])
        elif isinstance(self, TransferCurrencyForm):
            line_item_forms.extend([x.form for x in self.debit])
            line_item_forms.extend([x.form for x in self.credit])
        return line_item_forms

    @property
    def is_code_locked(self) -> bool:
        """Returns whether the currency code should not be changed.

        :return: True if the currency code should not be changed, or False
            otherwise
        """
        line_item_forms: list[LineItemForm] = self.line_items
        original_line_item_id: set[int] \
            = {x.original_line_item_id.data for x in line_item_forms
               if x.original_line_item_id.data is not None}
        if len(original_line_item_id) > 0:
            return True
        line_item_id: set[int] = {x.id.data for x in line_item_forms
                                  if x.id.data is not None}
        select: sa.Select = sa.select(sa.func.count(JournalEntryLineItem.id))\
            .filter(JournalEntryLineItem.original_line_item_id
                    .in_(line_item_id))
        return db.session.scalar(select) > 0


class CashReceiptCurrencyForm(CurrencyForm):
    """The form to create or edit a currency in a
    cash receipt journal entry."""
    no = IntegerField()
    """The order in the journal entry."""
    code = StringField(
        filters=[strip_text],
        validators=[CURRENCY_REQUIRED,
                    CurrencyExists(),
                    SameCurrencyAsOriginalLineItems(),
                    KeepCurrencyWhenHavingOffset()])
    """The currency code."""
    credit = FieldList(FormField(CreditLineItemForm),
                       validators=[NeedSomeLineItems()])
    """The credit line items."""
    whole_form = BooleanField()
    """The pseudo field for the whole form validators."""

    @property
    def credit_total(self) -> Decimal:
        """Returns the total amount of the credit line items.

        :return: The total amount of the credit line items.
        """
        return sum([x.amount.data for x in self.credit
                    if x.amount.data is not None])

    @property
    def credit_errors(self) -> list[str | LazyString]:
        """Returns the credit line item errors, without the errors in their
        sub-forms.

        :return:
        """
        return [x for x in self.credit.errors
                if isinstance(x, str) or isinstance(x, LazyString)]


class CashDisbursementCurrencyForm(CurrencyForm):
    """The form to create or edit a currency in a
    cash disbursement journal entry."""
    no = IntegerField()
    """The order in the journal entry."""
    code = StringField(
        filters=[strip_text],
        validators=[CURRENCY_REQUIRED,
                    CurrencyExists(),
                    SameCurrencyAsOriginalLineItems(),
                    KeepCurrencyWhenHavingOffset()])
    """The currency code."""
    debit = FieldList(FormField(DebitLineItemForm),
                      validators=[NeedSomeLineItems()])
    """The debit line items."""
    whole_form = BooleanField()
    """The pseudo field for the whole form validators."""

    @property
    def debit_total(self) -> Decimal:
        """Returns the total amount of the debit line items.

        :return: The total amount of the debit line items.
        """
        return sum([x.amount.data for x in self.debit
                    if x.amount.data is not None])

    @property
    def debit_errors(self) -> list[str | LazyString]:
        """Returns the debit line item errors, without the errors in their
        sub-forms.

        :return:
        """
        return [x for x in self.debit.errors
                if isinstance(x, str) or isinstance(x, LazyString)]


class TransferCurrencyForm(CurrencyForm):
    """The form to create or edit a currency in a transfer journal entry."""
    no = IntegerField()
    """The order in the journal entry."""
    code = StringField(
        filters=[strip_text],
        validators=[CURRENCY_REQUIRED,
                    CurrencyExists(),
                    SameCurrencyAsOriginalLineItems(),
                    KeepCurrencyWhenHavingOffset()])
    """The currency code."""
    debit = FieldList(FormField(DebitLineItemForm),
                      validators=[NeedSomeLineItems()])
    """The debit line items."""
    credit = FieldList(FormField(CreditLineItemForm),
                       validators=[NeedSomeLineItems()])
    """The credit line items."""
    whole_form = BooleanField(validators=[IsBalanced()])
    """The pseudo field for the whole form validators."""

    @property
    def debit_total(self) -> Decimal:
        """Returns the total amount of the debit line items.

        :return: The total amount of the debit line items.
        """
        return sum([x.amount.data for x in self.debit
                    if x.amount.data is not None])

    @property
    def credit_total(self) -> Decimal:
        """Returns the total amount of the credit line items.

        :return: The total amount of the credit line items.
        """
        return sum([x.amount.data for x in self.credit
                    if x.amount.data is not None])

    @property
    def debit_errors(self) -> list[str | LazyString]:
        """Returns the debit line item errors, without the errors in their
        sub-forms.

        :return:
        """
        return [x for x in self.debit.errors
                if isinstance(x, str) or isinstance(x, LazyString)]

    @property
    def credit_errors(self) -> list[str | LazyString]:
        """Returns the credit line item errors, without the errors in their
        sub-forms.

        :return:
        """
        return [x for x in self.credit.errors
                if isinstance(x, str) or isinstance(x, LazyString)]
