# The Mia! Accounting Flask Project.
# Author: imacat@mail.imacat.idv.tw (imacat), 2023/2/18

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
"""The transaction forms for the transaction management.

"""
import datetime as dt
import typing as t
from abc import ABC, abstractmethod

import sqlalchemy as sa
from flask_babel import LazyString
from flask_wtf import FlaskForm
from wtforms import DateField, FieldList, FormField, TextAreaField, \
    BooleanField
from wtforms.validators import DataRequired, ValidationError

from accounting import db
from accounting.locale import lazy_gettext
from accounting.models import Transaction, Account, JournalEntry, \
    TransactionCurrency
from accounting.transaction.utils.account_option import AccountOption
from accounting.transaction.utils.original_entries import \
    get_selectable_original_entries
from accounting.transaction.utils.summary_editor import SummaryEditor
from accounting.utils.random_id import new_id
from accounting.utils.strip_text import strip_multiline_text
from accounting.utils.user import get_current_user_pk
from .currency import CurrencyForm, IncomeCurrencyForm, ExpenseCurrencyForm, \
    TransferCurrencyForm
from .journal_entry import JournalEntryForm, DebitEntryForm, CreditEntryForm
from .reorder import sort_transactions_in

DATE_REQUIRED: DataRequired = DataRequired(
    lazy_gettext("Please fill in the date."))
"""The validator to check if the date is empty."""


class NotBeforeOriginalEntries:
    """The validator to check if the date is not before the original
    entries."""

    def __call__(self, form: FlaskForm, field: DateField) -> None:
        assert isinstance(form, TransactionForm)
        if field.data is None:
            return
        min_date: dt.date | None = form.min_date
        if min_date is None:
            return
        if field.data < min_date:
            raise ValidationError(lazy_gettext(
                "The date cannot be earlier than the original entries."))


class NotAfterOffsetEntries:
    """The validator to check if the date is not after the offset entries."""

    def __call__(self, form: FlaskForm, field: DateField) -> None:
        assert isinstance(form, TransactionForm)
        if field.data is None:
            return
        max_date: dt.date | None = form.max_date
        if max_date is None:
            return
        if field.data > max_date:
            raise ValidationError(lazy_gettext(
                "The date cannot be later than the offset entries."))


class NeedSomeCurrencies:
    """The validator to check if there is any currency sub-form."""

    def __call__(self, form: FlaskForm, field: FieldList) -> None:
        if len(field) == 0:
            raise ValidationError(lazy_gettext("Please add some currencies."))


class CannotDeleteOriginalEntriesWithOffset:
    """The validator to check the original entries with offset."""

    def __call__(self, form: FlaskForm, field: FieldList) -> None:
        assert isinstance(form, TransactionForm)
        if form.obj is None:
            return
        existing_matched_original_entry_id: set[int] \
            = {x.id for x in form.obj.entries if len(x.offsets) > 0}
        entry_id_in_form: set[int] \
            = {x.eid.data for x in form.entries if x.eid.data is not None}
        for entry_id in existing_matched_original_entry_id:
            if entry_id not in entry_id_in_form:
                raise ValidationError(lazy_gettext(
                    "Journal entries with offset cannot be deleted."))


class TransactionForm(FlaskForm):
    """The base form to create or edit a transaction."""
    date = DateField()
    """The date."""
    currencies = FieldList(FormField(CurrencyForm))
    """The journal entries categorized by their currencies."""
    note = TextAreaField()
    """The note."""

    def __init__(self, *args, **kwargs):
        """Constructs a base transaction form.

        :param args: The arguments.
        :param kwargs: The keyword arguments.
        """
        super().__init__(*args, **kwargs)
        self.is_modified: bool = False
        """Whether the transaction is modified during populate_obj()."""
        self.collector: t.Type[JournalEntryCollector] = JournalEntryCollector
        """The journal entry collector.  The default is the base abstract
        collector only to provide the correct type.  The subclass forms should
        provide their own collectors."""
        self.obj: Transaction | None = kwargs.get("obj")
        """The transaction, when editing an existing one."""
        self._is_need_payable: bool = False
        """Whether we need the payable original entries."""
        self._is_need_receivable: bool = False
        """Whether we need the receivable original entries."""
        self.__original_entry_options: list[JournalEntry] | None = None
        """The options of the original entries."""
        self.__net_balance_exceeded: dict[int, LazyString] | None = None
        """The original entries whose net balances were exceeded by the
        amounts in the journal entry sub-forms."""
        for entry in self.entries:
            entry.txn_form = self

    def populate_obj(self, obj: Transaction) -> None:
        """Populates the form data into a transaction object.

        :param obj: The transaction object.
        :return: None.
        """
        is_new: bool = obj.id is None
        if is_new:
            obj.id = new_id(Transaction)
        self.date: DateField
        self.__set_date(obj, self.date.data)
        obj.note = self.note.data

        collector_cls: t.Type[JournalEntryCollector] = self.collector
        collector: collector_cls = collector_cls(self, obj)
        collector.collect()

        to_delete: set[int] = {x.id for x in obj.entries
                               if x.id not in collector.to_keep}
        if len(to_delete) > 0:
            JournalEntry.query.filter(JournalEntry.id.in_(to_delete)).delete()
            self.is_modified = True

        if is_new or db.session.is_modified(obj):
            self.is_modified = True

        if is_new:
            current_user_pk: int = get_current_user_pk()
            obj.created_by_id = current_user_pk
            obj.updated_by_id = current_user_pk

    @property
    def entries(self) -> list[JournalEntryForm]:
        """Collects and returns the journal entry sub-forms.

        :return: The journal entry sub-forms.
        """
        entries: list[JournalEntryForm] = []
        for currency in self.currencies:
            entries.extend(currency.entries)
        return entries

    def __set_date(self, obj: Transaction, new_date: dt.date) -> None:
        """Sets the transaction date and number.

        :param obj: The transaction object.
        :param new_date: The new date.
        :return: None.
        """
        if obj.date is None or obj.date != new_date:
            if obj.date is not None:
                sort_transactions_in(obj.date, obj.id)
            if self.max_date is not None and new_date == self.max_date:
                db_min_no: int | None = db.session.scalar(
                    sa.select(sa.func.min(Transaction.no))
                    .filter(Transaction.date == new_date))
                if db_min_no is None:
                    obj.date = new_date
                    obj.no = 1
                else:
                    obj.date = new_date
                    obj.no = db_min_no - 1
                    sort_transactions_in(new_date)
            else:
                sort_transactions_in(new_date, obj.id)
                count: int = Transaction.query\
                    .filter(Transaction.date == new_date).count()
                obj.date = new_date
                obj.no = count + 1

    @property
    def debit_account_options(self) -> list[AccountOption]:
        """The selectable debit accounts.

        :return: The selectable debit accounts.
        """
        accounts: list[AccountOption] \
            = [AccountOption(x) for x in Account.debit()
               if not (x.code[0] == "2" and x.is_need_offset)]
        in_use: set[int] = set(db.session.scalars(
            sa.select(JournalEntry.account_id)
            .filter(JournalEntry.is_debit)
            .group_by(JournalEntry.account_id)).all())
        for account in accounts:
            account.is_in_use = account.id in in_use
        return accounts

    @property
    def credit_account_options(self) -> list[AccountOption]:
        """The selectable credit accounts.

        :return: The selectable credit accounts.
        """
        accounts: list[AccountOption] \
            = [AccountOption(x) for x in Account.credit()
               if not (x.code[0] == "1" and x.is_need_offset)]
        in_use: set[int] = set(db.session.scalars(
            sa.select(JournalEntry.account_id)
            .filter(sa.not_(JournalEntry.is_debit))
            .group_by(JournalEntry.account_id)).all())
        for account in accounts:
            account.is_in_use = account.id in in_use
        return accounts

    @property
    def currencies_errors(self) -> list[str | LazyString]:
        """Returns the currency errors, without the errors in their sub-forms.

        :return: The currency errors, without the errors in their sub-forms.
        """
        return [x for x in self.currencies.errors
                if isinstance(x, str) or isinstance(x, LazyString)]

    @property
    def summary_editor(self) -> SummaryEditor:
        """Returns the summary editor.

        :return: The summary editor.
        """
        return SummaryEditor()

    @property
    def original_entry_options(self) -> list[JournalEntry]:
        """Returns the selectable original entries.

        :return: The selectable original entries.
        """
        if self.__original_entry_options is None:
            self.__original_entry_options = get_selectable_original_entries(
                {x.eid.data for x in self.entries if x.eid.data is not None},
                self._is_need_payable, self._is_need_receivable)
        return self.__original_entry_options

    @property
    def min_date(self) -> dt.date | None:
        """Returns the minimal available date.

        :return: The minimal available date.
        """
        original_entry_id: set[int] \
            = {x.original_entry_id.data for x in self.entries
               if x.original_entry_id.data is not None}
        if len(original_entry_id) == 0:
            return None
        select: sa.Select = sa.select(sa.func.max(Transaction.date))\
            .join(JournalEntry).filter(JournalEntry.id.in_(original_entry_id))
        return db.session.scalar(select)

    @property
    def max_date(self) -> dt.date | None:
        """Returns the maximum available date.

        :return: The maximum available date.
        """
        entry_id: set[int] = {x.eid.data for x in self.entries
                              if x.eid.data is not None}
        select: sa.Select = sa.select(sa.func.min(Transaction.date))\
            .join(JournalEntry)\
            .filter(JournalEntry.original_entry_id.in_(entry_id))
        return db.session.scalar(select)


T = t.TypeVar("T", bound=TransactionForm)
"""A transaction form variant."""


class JournalEntryCollector(t.Generic[T], ABC):
    """The journal entry collector."""

    def __init__(self, form: T, obj: Transaction):
        """Constructs the journal entry collector.

        :param form: The transaction form.
        :param obj: The transaction.
        """
        self.form: T = form
        """The transaction form."""
        self.__obj: Transaction = obj
        """The transaction object."""
        self.__entries: list[JournalEntry] = list(obj.entries)
        """The existing journal entries."""
        self.__entries_by_id: dict[int, JournalEntry] \
            = {x.id: x for x in self.__entries}
        """A dictionary from the entry ID to their entries."""
        self.__no_by_id: dict[int, int] = {x.id: x.no for x in self.__entries}
        """A dictionary from the entry number to their entries."""
        self.__currencies: list[TransactionCurrency] = obj.currencies
        """The currencies in the transaction."""
        self._debit_no: int = 1
        """The number index for the debit entries."""
        self._credit_no: int = 1
        """The number index for the credit entries."""
        self.to_keep: set[int] = set()
        """The ID of the existing journal entries to keep."""

    @abstractmethod
    def collect(self) -> set[int]:
        """Collects the journal entries.

        :return: The ID of the journal entries to keep.
        """

    def _add_entry(self, form: JournalEntryForm, currency_code: str, no: int) \
            -> None:
        """Composes a journal entry from the form.

        :param form: The journal entry form.
        :param currency_code: The code of the currency.
        :param no: The number of the entry.
        :return: None.
        """
        entry: JournalEntry | None = self.__entries_by_id.get(form.eid.data)
        if entry is not None:
            entry.currency_code = currency_code
            form.populate_obj(entry)
            entry.no = no
            if db.session.is_modified(entry):
                self.form.is_modified = True
        else:
            entry = JournalEntry()
            entry.currency_code = currency_code
            form.populate_obj(entry)
            entry.no = no
            self.__obj.entries.append(entry)
            self.form.is_modified = True
        self.to_keep.add(entry.id)

    def _make_cash_entry(self, forms: list[JournalEntryForm], is_debit: bool,
                         currency_code: str, no: int) -> None:
        """Composes the cash journal entry at the other side of the cash
        transaction.

        :param forms: The journal entry forms in the same currency.
        :param is_debit: True for a cash income transaction, or False for a
            cash expense transaction.
        :param currency_code: The code of the currency.
        :param no: The number of the entry.
        :return: None.
        """
        candidates: list[JournalEntry] = [x for x in self.__entries
                                          if x.is_debit == is_debit
                                          and x.currency_code == currency_code]
        entry: JournalEntry
        if len(candidates) > 0:
            candidates.sort(key=lambda x: x.no)
            entry = candidates[0]
            entry.account_id = Account.cash().id
            entry.summary = None
            entry.amount = sum([x.amount.data for x in forms])
            entry.no = no
            if db.session.is_modified(entry):
                self.form.is_modified = True
        else:
            entry = JournalEntry()
            entry.id = new_id(JournalEntry)
            entry.is_debit = is_debit
            entry.currency_code = currency_code
            entry.account_id = Account.cash().id
            entry.summary = None
            entry.amount = sum([x.amount.data for x in forms])
            entry.no = no
            self.__obj.entries.append(entry)
            self.form.is_modified = True
        self.to_keep.add(entry.id)

    def _sort_entry_forms(self, forms: list[JournalEntryForm]) -> None:
        """Sorts the journal entry forms.

        :param forms: The journal entry forms.
        :return: None.
        """
        missing_no: int = 100 if len(self.__no_by_id) == 0 \
            else max(self.__no_by_id.values()) + 100
        ord_by_form: dict[JournalEntryForm, int] \
            = {forms[i]: i for i in range(len(forms))}
        recv_no: set[int] = {x.no.data for x in forms if x.no.data is not None}
        missing_recv_no: int = 100 if len(recv_no) == 0 else max(recv_no) + 100
        forms.sort(key=lambda x: (x.no.data or missing_recv_no,
                                  missing_no if x.eid.data is None else
                                  self.__no_by_id.get(x.eid.data, missing_no),
                                  ord_by_form.get(x)))

    def _sort_currency_forms(self, forms: list[CurrencyForm]) -> None:
        """Sorts the currency forms.

        :param forms: The currency forms.
        :return: None.
        """
        missing_no: int = len(self.__currencies) + 100
        no_by_code: dict[str, int] = {self.__currencies[i].code: i
                                      for i in range(len(self.__currencies))}
        ord_by_form: dict[CurrencyForm, int] \
            = {forms[i]: i for i in range(len(forms))}
        recv_no: set[int] = {x.no.data for x in forms if x.no.data is not None}
        missing_recv_no: int = 100 if len(recv_no) == 0 else max(recv_no) + 100
        forms.sort(key=lambda x: (x.no.data or missing_recv_no,
                                  no_by_code.get(x.code.data, missing_no),
                                  ord_by_form.get(x)))


class IncomeTransactionForm(TransactionForm):
    """The form to create or edit a cash income transaction."""
    date = DateField(
        validators=[DATE_REQUIRED,
                    NotBeforeOriginalEntries(),
                    NotAfterOffsetEntries()])
    """The date."""
    currencies = FieldList(FormField(IncomeCurrencyForm), name="currency",
                           validators=[NeedSomeCurrencies()])
    """The journal entries categorized by their currencies."""
    note = TextAreaField(filters=[strip_multiline_text])
    """The note."""
    whole_form = BooleanField(
        validators=[CannotDeleteOriginalEntriesWithOffset()])
    """The pseudo field for the whole form validators."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._is_need_receivable = True

        class Collector(JournalEntryCollector[IncomeTransactionForm]):
            """The journal entry collector for the cash income transactions."""

            def collect(self) -> None:
                currencies: list[IncomeCurrencyForm] \
                    = [x.form for x in self.form.currencies]
                self._sort_currency_forms(currencies)
                for currency in currencies:
                    # The debit cash entry
                    self._make_cash_entry(list(currency.credit), True,
                                          currency.code.data, self._debit_no)
                    self._debit_no = self._debit_no + 1

                    # The credit forms
                    credit_forms: list[CreditEntryForm] \
                        = [x.form for x in currency.credit]
                    self._sort_entry_forms(credit_forms)
                    for credit_form in credit_forms:
                        self._add_entry(credit_form, currency.code.data,
                                        self._credit_no)
                        self._credit_no = self._credit_no + 1

        self.collector = Collector


class ExpenseTransactionForm(TransactionForm):
    """The form to create or edit a cash expense transaction."""
    date = DateField(
        validators=[DATE_REQUIRED,
                    NotBeforeOriginalEntries(),
                    NotAfterOffsetEntries()])
    """The date."""
    currencies = FieldList(FormField(ExpenseCurrencyForm), name="currency",
                           validators=[NeedSomeCurrencies()])
    """The journal entries categorized by their currencies."""
    note = TextAreaField(filters=[strip_multiline_text])
    """The note."""
    whole_form = BooleanField(
        validators=[CannotDeleteOriginalEntriesWithOffset()])
    """The pseudo field for the whole form validators."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._is_need_payable = True

        class Collector(JournalEntryCollector[ExpenseTransactionForm]):
            """The journal entry collector for the cash expense
            transactions."""

            def collect(self) -> None:
                currencies: list[ExpenseCurrencyForm] \
                    = [x.form for x in self.form.currencies]
                self._sort_currency_forms(currencies)
                for currency in currencies:
                    # The debit forms
                    debit_forms: list[DebitEntryForm] \
                        = [x.form for x in currency.debit]
                    self._sort_entry_forms(debit_forms)
                    for debit_form in debit_forms:
                        self._add_entry(debit_form, currency.code.data,
                                        self._debit_no)
                        self._debit_no = self._debit_no + 1

                    # The credit forms
                    self._make_cash_entry(list(currency.debit), False,
                                          currency.code.data, self._credit_no)
                    self._credit_no = self._credit_no + 1

        self.collector = Collector


class TransferTransactionForm(TransactionForm):
    """The form to create or edit a transfer transaction."""
    date = DateField(
        validators=[DATE_REQUIRED,
                    NotBeforeOriginalEntries(),
                    NotAfterOffsetEntries()])
    """The date."""
    currencies = FieldList(FormField(TransferCurrencyForm), name="currency",
                           validators=[NeedSomeCurrencies()])
    """The journal entries categorized by their currencies."""
    note = TextAreaField(filters=[strip_multiline_text])
    """The note."""
    whole_form = BooleanField(
        validators=[CannotDeleteOriginalEntriesWithOffset()])
    """The pseudo field for the whole form validators."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._is_need_payable = True
        self._is_need_receivable = True

        class Collector(JournalEntryCollector[TransferTransactionForm]):
            """The journal entry collector for the transfer transactions."""

            def collect(self) -> None:
                currencies: list[TransferCurrencyForm] \
                    = [x.form for x in self.form.currencies]
                self._sort_currency_forms(currencies)
                for currency in currencies:
                    # The debit forms
                    debit_forms: list[DebitEntryForm] \
                        = [x.form for x in currency.debit]
                    self._sort_entry_forms(debit_forms)
                    for debit_form in debit_forms:
                        self._add_entry(debit_form, currency.code.data,
                                        self._debit_no)
                        self._debit_no = self._debit_no + 1

                    # The credit forms
                    credit_forms: list[CreditEntryForm] \
                        = [x.form for x in currency.credit]
                    self._sort_entry_forms(credit_forms)
                    for credit_form in credit_forms:
                        self._add_entry(credit_form, currency.code.data,
                                        self._credit_no)
                        self._credit_no = self._credit_no + 1

        self.collector = Collector
