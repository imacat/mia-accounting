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
"""The forms for the transaction management.

"""
from __future__ import annotations

import re
import typing as t
from abc import ABC, abstractmethod
from datetime import date
from decimal import Decimal

import sqlalchemy as sa
from flask import request
from flask_babel import LazyString
from flask_wtf import FlaskForm
from wtforms import DateField, StringField, FieldList, FormField, \
    IntegerField, TextAreaField, DecimalField, BooleanField
from wtforms.validators import DataRequired, ValidationError

from accounting import db
from accounting.locale import lazy_gettext
from accounting.models import Transaction, Account, JournalEntry, \
    TransactionCurrency, Currency
from accounting.transaction.summary_helper import SummaryHelper
from accounting.utils.random_id import new_id
from accounting.utils.strip_text import strip_text, strip_multiline_text
from accounting.utils.user import get_current_user_pk

MISSING_CURRENCY: LazyString = lazy_gettext("Please select the currency.")
"""The error message when the currency code is empty."""
MISSING_ACCOUNT: LazyString = lazy_gettext("Please select the account.")
"""The error message when the account code is empty."""


class NeedSomeCurrencies:
    """The validator to check if there is any currency sub-form."""

    def __call__(self, form: CurrencyForm, field: FieldList) \
            -> None:
        if len(field) == 0:
            raise ValidationError(lazy_gettext(
                "Please add some currencies."))


class CurrencyExists:
    """The validator to check if the account exists."""

    def __call__(self, form: FlaskForm, field: StringField) -> None:
        if field.data is None:
            return
        if db.session.get(Currency, field.data) is None:
            raise ValidationError(lazy_gettext(
                "The currency does not exist."))


class NeedSomeJournalEntries:
    """The validator to check if there is any journal entry sub-form."""

    def __call__(self, form: TransferCurrencyForm, field: FieldList) \
            -> None:
        if len(field) == 0:
            raise ValidationError(lazy_gettext(
                "Please add some journal entries."))


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
        validators=[DataRequired(MISSING_ACCOUNT),
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
        validators=[DataRequired(MISSING_ACCOUNT),
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


class CurrencyForm(FlaskForm):
    """The form to create or edit a currency in a transaction."""
    no = IntegerField()
    """The order in the transaction."""
    code = StringField()
    """The currency code."""
    whole_form = BooleanField()
    """The pseudo field for the whole form validators."""


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
        self.__in_use_account_id: set[int] | None = None
        """The ID of the accounts that are in use."""

    def populate_obj(self, obj: Transaction) -> None:
        """Populates the form data into a transaction object.

        :param obj: The transaction object.
        :return: None.
        """
        is_new: bool = obj.id is None
        if is_new:
            obj.id = new_id(Transaction)
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

    @staticmethod
    def __set_date(obj: Transaction, new_date: date) -> None:
        """Sets the transaction date and number.

        :param obj: The transaction object.
        :param new_date: The new date.
        :return: None.
        """
        if obj.date is None or obj.date != new_date:
            if obj.date is not None:
                sort_transactions_in(obj.date, obj.id)
            sort_transactions_in(new_date, obj.id)
            count: int = Transaction.query\
                .filter(Transaction.date == new_date).count()
            obj.date = new_date
            obj.no = count + 1

    @property
    def debit_account_options(self) -> list[Account]:
        """The selectable debit accounts.

        :return: The selectable debit accounts.
        """
        accounts: list[Account] = Account.debit()
        in_use: set[int] = self.__get_in_use_account_id()
        for account in accounts:
            account.is_in_use = account.id in in_use
        return accounts

    @property
    def credit_account_options(self) -> list[Account]:
        """The selectable credit accounts.

        :return: The selectable credit accounts.
        """
        accounts: list[Account] = Account.credit()
        in_use: set[int] = self.__get_in_use_account_id()
        for account in accounts:
            account.is_in_use = account.id in in_use
        return accounts

    def __get_in_use_account_id(self) -> set[int]:
        """Returns the ID of the accounts that are in use.

        :return: The ID of the accounts that are in use.
        """
        if self.__in_use_account_id is None:
            self.__in_use_account_id = set(db.session.scalars(
                sa.select(JournalEntry.account_id)
                .group_by(JournalEntry.account_id)).all())
        return self.__in_use_account_id

    @property
    def currencies_errors(self) -> list[str | LazyString]:
        """Returns the currency errors, without the errors in their sub-forms.

        :return: The currency errors, without the errors in their sub-forms.
        """
        return [x for x in self.currencies.errors
                if isinstance(x, str) or isinstance(x, LazyString)]


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


class IncomeCurrencyForm(CurrencyForm):
    """The form to create or edit a currency in a cash income transaction."""
    no = IntegerField()
    """The order in the transaction."""
    code = StringField(
        filters=[strip_text],
        validators=[DataRequired(MISSING_CURRENCY),
                    CurrencyExists()])
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


class IncomeTransactionForm(TransactionForm):
    """The form to create or edit a cash income transaction."""
    date = DateField(default=date.today())
    """The date."""
    currencies = FieldList(FormField(IncomeCurrencyForm), name="currency",
                           validators=[NeedSomeCurrencies()])
    """The journal entries categorized by their currencies."""
    note = TextAreaField(filters=[strip_multiline_text])
    """The note."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

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


class ExpenseCurrencyForm(CurrencyForm):
    """The form to create or edit a currency in a cash expense transaction."""
    no = IntegerField()
    """The order in the transaction."""
    code = StringField(
        filters=[strip_text],
        validators=[DataRequired(MISSING_CURRENCY),
                    CurrencyExists()])
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


class ExpenseTransactionForm(TransactionForm):
    """The form to create or edit a cash expense transaction."""
    date = DateField(default=date.today())
    """The date."""
    currencies = FieldList(FormField(ExpenseCurrencyForm), name="currency",
                           validators=[NeedSomeCurrencies()])
    """The journal entries categorized by their currencies."""
    note = TextAreaField(filters=[strip_multiline_text])
    """The note."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

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


class TransferCurrencyForm(CurrencyForm):
    """The form to create or edit a currency in a transfer transaction."""

    class IsBalanced:
        """The validator to check that the total amount of the debit and credit
        entries are equal."""
        def __call__(self, form: TransferCurrencyForm, field: BooleanField)\
                -> None:
            if len(form.debit) == 0 or len(form.credit) == 0:
                return
            if form.debit_total != form.credit_total:
                raise ValidationError(lazy_gettext(
                    "The totals of the debit and credit amounts do not"
                    " match."))

    no = IntegerField()
    """The order in the transaction."""
    code = StringField(
        filters=[strip_text],
        validators=[DataRequired(MISSING_CURRENCY),
                    CurrencyExists()])
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


class TransferTransactionForm(TransactionForm):
    """The form to create or edit a transfer transaction."""
    date = DateField(default=date.today())
    """The date."""
    currencies = FieldList(FormField(TransferCurrencyForm), name="currency",
                           validators=[NeedSomeCurrencies()])
    """The journal entries categorized by their currencies."""
    note = TextAreaField(filters=[strip_multiline_text])
    """The note."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

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


def sort_transactions_in(txn_date: date, exclude: int) -> None:
    """Sorts the transactions under a date after changing the date or deleting
    a transaction.

    :param txn_date: The date of the transaction.
    :param exclude: The transaction ID to exclude.
    :return: None.
    """
    transactions: list[Transaction] = Transaction.query\
        .filter(Transaction.date == txn_date,
                Transaction.id != exclude)\
        .order_by(Transaction.no).all()
    for i in range(len(transactions)):
        if transactions[i].no != i + 1:
            transactions[i].no = i + 1


class TransactionReorderForm:
    """The form to reorder the transactions."""

    def __init__(self, txn_date: date):
        """Constructs the form to reorder the transactions in a day.

        :param txn_date: The date.
        """
        self.date: date = txn_date
        self.is_modified: bool = False

    def save_order(self) -> None:
        """Saves the order of the account.

        :return:
        """
        transactions: list[Transaction] = Transaction.query\
            .filter(Transaction.date == self.date).all()

        # Collects the specified order.
        orders: dict[Transaction, int] = {}
        for txn in transactions:
            if f"{txn.id}-no" in request.form:
                try:
                    orders[txn] = int(request.form[f"{txn.id}-no"])
                except ValueError:
                    pass

        # Missing and invalid orders are appended to the end.
        missing: list[Transaction] \
            = [x for x in transactions if x not in orders]
        if len(missing) > 0:
            next_no: int = 1 if len(orders) == 0 else max(orders.values()) + 1
            for txn in missing:
                orders[txn] = next_no

        # Sort by the specified order first, and their original order.
        transactions.sort(key=lambda x: (orders[x], x.no))

        # Update the orders.
        with db.session.no_autoflush:
            for i in range(len(transactions)):
                if transactions[i].no != i + 1:
                    transactions[i].no = i + 1
                    self.is_modified = True
