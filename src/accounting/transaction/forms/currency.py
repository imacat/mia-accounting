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
"""The currency sub-forms for the transaction management.

"""
from decimal import Decimal

import sqlalchemy as sa
from flask_babel import LazyString
from flask_wtf import FlaskForm
from wtforms import StringField, ValidationError, FieldList, IntegerField, \
    BooleanField, FormField
from wtforms.validators import DataRequired

from accounting import db
from accounting.locale import lazy_gettext
from accounting.models import Currency, JournalEntry
from accounting.transaction.utils.offset_alias import offset_alias
from accounting.utils.cast import be
from accounting.utils.strip_text import strip_text
from .journal_entry import JournalEntryForm, CreditEntryForm, DebitEntryForm

CURRENCY_REQUIRED: DataRequired = DataRequired(
    lazy_gettext("Please select the currency."))
"""The validator to check if the currency code is empty."""


class CurrencyExists:
    """The validator to check if the account exists."""

    def __call__(self, form: FlaskForm, field: StringField) -> None:
        if field.data is None:
            return
        if db.session.get(Currency, field.data) is None:
            raise ValidationError(lazy_gettext(
                "The currency does not exist."))


class SameCurrencyAsOriginalEntries:
    """The validator to check if the currency is the same as the original
    entries."""

    def __call__(self, form: FlaskForm, field: StringField) -> None:
        assert isinstance(form, CurrencyForm)
        if field.data is None:
            return
        original_entry_id: set[int] = {x.original_entry_id.data
                                       for x in form.entries
                                       if x.original_entry_id.data is not None}
        if len(original_entry_id) == 0:
            return
        original_entry_currency_codes: set[str] = set(db.session.scalars(
            sa.select(JournalEntry.currency_code)
            .filter(JournalEntry.id.in_(original_entry_id))).all())
        for currency_code in original_entry_currency_codes:
            if field.data != currency_code:
                raise ValidationError(lazy_gettext(
                    "The currency must be the same as the original entry."))


class KeepCurrencyWhenHavingOffset:
    """The validator to check if the currency is the same when there is
    offset."""

    def __call__(self, form: FlaskForm, field: StringField) -> None:
        assert isinstance(form, CurrencyForm)
        if field.data is None:
            return
        offset: sa.Alias = offset_alias()
        original_entries: list[JournalEntry] = JournalEntry.query\
            .join(offset, be(JournalEntry.id == offset.c.original_entry_id),
                  isouter=True)\
            .filter(JournalEntry.id.in_({x.eid.data for x in form.entries
                                         if x.eid.data is not None}))\
            .group_by(JournalEntry.id, JournalEntry.currency_code)\
            .having(sa.func.count(offset.c.id) > 0).all()
        for original_entry in original_entries:
            if original_entry.currency_code != field.data:
                raise ValidationError(lazy_gettext(
                    "The currency must not be changed when there is offset."))


class NeedSomeJournalEntries:
    """The validator to check if there is any journal entry sub-form."""

    def __call__(self, form: FlaskForm, field: FieldList) -> None:
        if len(field) == 0:
            raise ValidationError(lazy_gettext(
                "Please add some journal entries."))


class IsBalanced:
    """The validator to check that the total amount of the debit and credit
    entries are equal."""

    def __call__(self, form: FlaskForm, field: BooleanField) -> None:
        assert isinstance(form, TransferCurrencyForm)
        if len(form.debit) == 0 or len(form.credit) == 0:
            return
        if form.debit_total != form.credit_total:
            raise ValidationError(lazy_gettext(
                "The totals of the debit and credit amounts do not match."))


class CurrencyForm(FlaskForm):
    """The form to create or edit a currency in a transaction."""
    no = IntegerField()
    """The order in the transaction."""
    code = StringField()
    """The currency code."""
    whole_form = BooleanField()
    """The pseudo field for the whole form validators."""

    @property
    def entries(self) -> list[JournalEntryForm]:
        """Returns the journal entry sub-forms.

        :return: The journal entry sub-forms.
        """
        entry_forms: list[JournalEntryForm] = []
        if isinstance(self, IncomeCurrencyForm):
            entry_forms.extend([x.form for x in self.credit])
        elif isinstance(self, ExpenseCurrencyForm):
            entry_forms.extend([x.form for x in self.debit])
        elif isinstance(self, TransferCurrencyForm):
            entry_forms.extend([x.form for x in self.debit])
            entry_forms.extend([x.form for x in self.credit])
        return entry_forms

    @property
    def is_code_locked(self) -> bool:
        """Returns whether the currency code should not be changed.

        :return: True if the currency code should not be changed, or False
            otherwise
        """
        entry_forms: list[JournalEntryForm] = self.entries
        original_entry_id: set[int] \
            = {x.original_entry_id.data for x in entry_forms
               if x.original_entry_id.data is not None}
        if len(original_entry_id) > 0:
            return True
        entry_id: set[int] = {x.eid.data for x in entry_forms
                              if x.eid.data is not None}
        select: sa.Select = sa.select(sa.func.count(JournalEntry.id))\
            .filter(JournalEntry.original_entry_id.in_(entry_id))
        return db.session.scalar(select) > 0


class IncomeCurrencyForm(CurrencyForm):
    """The form to create or edit a currency in a cash income transaction."""
    no = IntegerField()
    """The order in the transaction."""
    code = StringField(
        filters=[strip_text],
        validators=[CURRENCY_REQUIRED,
                    CurrencyExists(),
                    SameCurrencyAsOriginalEntries(),
                    KeepCurrencyWhenHavingOffset()])
    """The currency code."""
    credit = FieldList(FormField(CreditEntryForm),
                       validators=[NeedSomeJournalEntries()])
    """The credit entries."""
    whole_form = BooleanField()
    """The pseudo field for the whole form validators."""

    @property
    def credit_total(self) -> Decimal:
        """Returns the total amount of the credit journal entries.

        :return: The total amount of the credit journal entries.
        """
        return sum([x.amount.data for x in self.credit
                    if x.amount.data is not None])

    @property
    def credit_errors(self) -> list[str | LazyString]:
        """Returns the credit journal entry errors, without the errors in their
        sub-forms.

        :return:
        """
        return [x for x in self.credit.errors
                if isinstance(x, str) or isinstance(x, LazyString)]


class ExpenseCurrencyForm(CurrencyForm):
    """The form to create or edit a currency in a cash expense transaction."""
    no = IntegerField()
    """The order in the transaction."""
    code = StringField(
        filters=[strip_text],
        validators=[CURRENCY_REQUIRED,
                    CurrencyExists(),
                    SameCurrencyAsOriginalEntries(),
                    KeepCurrencyWhenHavingOffset()])
    """The currency code."""
    debit = FieldList(FormField(DebitEntryForm),
                      validators=[NeedSomeJournalEntries()])
    """The debit entries."""
    whole_form = BooleanField()
    """The pseudo field for the whole form validators."""

    @property
    def debit_total(self) -> Decimal:
        """Returns the total amount of the debit journal entries.

        :return: The total amount of the debit journal entries.
        """
        return sum([x.amount.data for x in self.debit
                    if x.amount.data is not None])

    @property
    def debit_errors(self) -> list[str | LazyString]:
        """Returns the debit journal entry errors, without the errors in their
        sub-forms.

        :return:
        """
        return [x for x in self.debit.errors
                if isinstance(x, str) or isinstance(x, LazyString)]


class TransferCurrencyForm(CurrencyForm):
    """The form to create or edit a currency in a transfer transaction."""
    no = IntegerField()
    """The order in the transaction."""
    code = StringField(
        filters=[strip_text],
        validators=[CURRENCY_REQUIRED,
                    CurrencyExists(),
                    SameCurrencyAsOriginalEntries(),
                    KeepCurrencyWhenHavingOffset()])
    """The currency code."""
    debit = FieldList(FormField(DebitEntryForm),
                      validators=[NeedSomeJournalEntries()])
    """The debit entries."""
    credit = FieldList(FormField(CreditEntryForm),
                       validators=[NeedSomeJournalEntries()])
    """The credit entries."""
    whole_form = BooleanField(validators=[IsBalanced()])
    """The pseudo field for the whole form validators."""

    @property
    def debit_total(self) -> Decimal:
        """Returns the total amount of the debit journal entries.

        :return: The total amount of the debit journal entries.
        """
        return sum([x.amount.data for x in self.debit
                    if x.amount.data is not None])

    @property
    def credit_total(self) -> Decimal:
        """Returns the total amount of the credit journal entries.

        :return: The total amount of the credit journal entries.
        """
        return sum([x.amount.data for x in self.credit
                    if x.amount.data is not None])

    @property
    def debit_errors(self) -> list[str | LazyString]:
        """Returns the debit journal entry errors, without the errors in their
        sub-forms.

        :return:
        """
        return [x for x in self.debit.errors
                if isinstance(x, str) or isinstance(x, LazyString)]

    @property
    def credit_errors(self) -> list[str | LazyString]:
        """Returns the credit journal entry errors, without the errors in their
        sub-forms.

        :return:
        """
        return [x for x in self.credit.errors
                if isinstance(x, str) or isinstance(x, LazyString)]
