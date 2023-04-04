# The Mia! Accounting Project.
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
"""The journal entry forms for the journal entry management.

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
from accounting.models import JournalEntry, Account, JournalEntryLineItem, \
    JournalEntryCurrency
from accounting.journal_entry.utils.account_option import AccountOption
from accounting.journal_entry.utils.original_line_items import \
    get_selectable_original_line_items
from accounting.journal_entry.utils.description_editor import DescriptionEditor
from accounting.utils.random_id import new_id
from accounting.utils.strip_text import strip_multiline_text
from accounting.utils.user import get_current_user_pk
from .currency import CurrencyForm, CashReceiptCurrencyForm, \
    CashDisbursementCurrencyForm, TransferCurrencyForm
from .line_item import LineItemForm, DebitLineItemForm, CreditLineItemForm
from .reorder import sort_journal_entries_in

DATE_REQUIRED: DataRequired = DataRequired(
    lazy_gettext("Please fill in the date."))
"""The validator to check if the date is empty."""


class NotBeforeOriginalLineItems:
    """The validator to check if the date is not before the
    original line items."""

    def __call__(self, form: FlaskForm, field: DateField) -> None:
        assert isinstance(form, JournalEntryForm)
        if field.data is None:
            return
        min_date: dt.date | None = form.min_date
        if min_date is None:
            return
        if field.data < min_date:
            raise ValidationError(lazy_gettext(
                "The date cannot be earlier than the original line items."))


class NotAfterOffsetItems:
    """The validator to check if the date is not after the offset items."""

    def __call__(self, form: FlaskForm, field: DateField) -> None:
        assert isinstance(form, JournalEntryForm)
        if field.data is None:
            return
        max_date: dt.date | None = form.max_date
        if max_date is None:
            return
        if field.data > max_date:
            raise ValidationError(lazy_gettext(
                "The date cannot be later than the offset items."))


class NeedSomeCurrencies:
    """The validator to check if there is any currency sub-form."""

    def __call__(self, form: FlaskForm, field: FieldList) -> None:
        if len(field) == 0:
            raise ValidationError(lazy_gettext("Please add some currencies."))


class CannotDeleteOriginalLineItemsWithOffset:
    """The validator to check the original line items with offset."""

    def __call__(self, form: FlaskForm, field: FieldList) -> None:
        assert isinstance(form, JournalEntryForm)
        if form.obj is None:
            return
        existing_matched_original_line_item_id: set[int] \
            = {x.id for x in form.obj.line_items if len(x.offsets) > 0}
        line_item_id_in_form: set[int] \
            = {x.id.data for x in form.line_items if x.id.data is not None}
        for line_item_id in existing_matched_original_line_item_id:
            if line_item_id not in line_item_id_in_form:
                raise ValidationError(lazy_gettext(
                    "Line items with offset cannot be deleted."))


class JournalEntryForm(FlaskForm):
    """The base form to create or edit a journal entry."""
    date = DateField()
    """The date."""
    currencies = FieldList(FormField(CurrencyForm))
    """The line items categorized by their currencies."""
    note = TextAreaField()
    """The note."""

    def __init__(self, *args, **kwargs):
        """Constructs a base journal entry form.

        :param args: The arguments.
        :param kwargs: The keyword arguments.
        """
        super().__init__(*args, **kwargs)
        self.is_modified: bool = False
        """Whether the journal entry is modified during populate_obj()."""
        self.collector: t.Type[LineItemCollector] = LineItemCollector
        """The line item collector.  The default is the base abstract
        collector only to provide the correct type.  The subclass forms should
        provide their own collectors."""
        self.obj: JournalEntry | None = kwargs.get("obj")
        """The journal entry, when editing an existing one."""
        self._is_need_payable: bool = False
        """Whether we need the payable original line items."""
        self._is_need_receivable: bool = False
        """Whether we need the receivable original line items."""
        self.__original_line_item_options: list[JournalEntryLineItem] | None \
            = None
        """The options of the original line items."""
        self.__net_balance_exceeded: dict[int, LazyString] | None = None
        """The original line items whose net balances were exceeded by the
        amounts in the line item sub-forms."""
        for line_item in self.line_items:
            line_item.journal_entry_form = self

    def populate_obj(self, obj: JournalEntry) -> None:
        """Populates the form data into a journal entry object.

        :param obj: The journal entry object.
        :return: None.
        """
        is_new: bool = obj.id is None
        if is_new:
            obj.id = new_id(JournalEntry)
        self.date: DateField
        self.__set_date(obj, self.date.data)
        obj.note = self.note.data

        collector_cls: t.Type[LineItemCollector] = self.collector
        collector: collector_cls = collector_cls(self, obj)
        collector.collect()

        to_delete: set[int] = {x.id for x in obj.line_items
                               if x.id not in collector.to_keep}
        if len(to_delete) > 0:
            JournalEntryLineItem.query\
                .filter(JournalEntryLineItem.id.in_(to_delete)).delete()
            self.is_modified = True

        if is_new or db.session.is_modified(obj):
            self.is_modified = True

        if is_new:
            current_user_pk: int = get_current_user_pk()
            obj.created_by_id = current_user_pk
            obj.updated_by_id = current_user_pk

    @property
    def line_items(self) -> list[LineItemForm]:
        """Collects and returns the line item sub-forms.

        :return: The line item sub-forms.
        """
        line_items: list[LineItemForm] = []
        for currency in self.currencies:
            line_items.extend(currency.line_items)
        return line_items

    def __set_date(self, obj: JournalEntry, new_date: dt.date) -> None:
        """Sets the journal entry date and number.

        :param obj: The journal entry object.
        :param new_date: The new date.
        :return: None.
        """
        if obj.date is None or obj.date != new_date:
            if obj.date is not None:
                sort_journal_entries_in(obj.date, obj.id)
            if self.max_date is not None and new_date == self.max_date:
                db_min_no: int | None = db.session.scalar(
                    sa.select(sa.func.min(JournalEntry.no))
                    .filter(JournalEntry.date == new_date))
                if db_min_no is None:
                    obj.date = new_date
                    obj.no = 1
                else:
                    obj.date = new_date
                    obj.no = db_min_no - 1
                    sort_journal_entries_in(new_date)
            else:
                sort_journal_entries_in(new_date, obj.id)
                count: int = JournalEntry.query\
                    .filter(JournalEntry.date == new_date).count()
                obj.date = new_date
                obj.no = count + 1

    @property
    def debit_account_options(self) -> list[AccountOption]:
        """The selectable debit accounts.

        :return: The selectable debit accounts.
        """
        accounts: list[AccountOption] \
            = [AccountOption(x) for x in Account.selectable_debit()
               if not (x.code[0] == "2" and x.is_need_offset)]
        in_use: set[int] = set(db.session.scalars(
            sa.select(JournalEntryLineItem.account_id)
            .filter(JournalEntryLineItem.is_debit)
            .group_by(JournalEntryLineItem.account_id)).all())
        for account in accounts:
            account.is_in_use = account.id in in_use
        return accounts

    @property
    def credit_account_options(self) -> list[AccountOption]:
        """The selectable credit accounts.

        :return: The selectable credit accounts.
        """
        accounts: list[AccountOption] \
            = [AccountOption(x) for x in Account.selectable_credit()
               if not (x.code[0] == "1" and x.is_need_offset)]
        in_use: set[int] = set(db.session.scalars(
            sa.select(JournalEntryLineItem.account_id)
            .filter(sa.not_(JournalEntryLineItem.is_debit))
            .group_by(JournalEntryLineItem.account_id)).all())
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
    def description_editor(self) -> DescriptionEditor:
        """Returns the description editor.

        :return: The description editor.
        """
        return DescriptionEditor()

    @property
    def original_line_item_options(self) -> list[JournalEntryLineItem]:
        """Returns the selectable original line items.

        :return: The selectable original line items.
        """
        if self.__original_line_item_options is None:
            self.__original_line_item_options \
                = get_selectable_original_line_items(
                    {x.id.data for x in self.line_items
                     if x.id.data is not None},
                    self._is_need_payable, self._is_need_receivable)
        return self.__original_line_item_options

    @property
    def min_date(self) -> dt.date | None:
        """Returns the minimal available date.

        :return: The minimal available date.
        """
        original_line_item_id: set[int] \
            = {x.original_line_item_id.data for x in self.line_items
               if x.original_line_item_id.data is not None}
        if len(original_line_item_id) == 0:
            return None
        select: sa.Select = sa.select(sa.func.max(JournalEntry.date))\
            .join(JournalEntryLineItem)\
            .filter(JournalEntryLineItem.id.in_(original_line_item_id))
        return db.session.scalar(select)

    @property
    def max_date(self) -> dt.date | None:
        """Returns the maximum available date.

        :return: The maximum available date.
        """
        line_item_id: set[int] = {x.id.data for x in self.line_items
                                  if x.id.data is not None}
        select: sa.Select = sa.select(sa.func.min(JournalEntry.date))\
            .join(JournalEntryLineItem)\
            .filter(JournalEntryLineItem.original_line_item_id
                    .in_(line_item_id))
        return db.session.scalar(select)


T = t.TypeVar("T", bound=JournalEntryForm)
"""A journal entry form variant."""


class LineItemCollector(t.Generic[T], ABC):
    """The line item collector."""

    def __init__(self, form: T, obj: JournalEntry):
        """Constructs the line item collector.

        :param form: The journal entry form.
        :param obj: The journal entry.
        """
        self.form: T = form
        """The journal entry form."""
        self.__obj: JournalEntry = obj
        """The journal entry object."""
        self.__line_items: list[JournalEntryLineItem] = list(obj.line_items)
        """The existing line items."""
        self.__line_items_by_id: dict[int, JournalEntryLineItem] \
            = {x.id: x for x in self.__line_items}
        """A dictionary from the line item ID to their line items."""
        self.__no_by_id: dict[int, int] \
            = {x.id: x.no for x in self.__line_items}
        """A dictionary from the line item number to their line items."""
        self.__currencies: list[JournalEntryCurrency] = obj.currencies
        """The currencies in the journal entry."""
        self._debit_no: int = 1
        """The number index for the debit line items."""
        self._credit_no: int = 1
        """The number index for the credit line items."""
        self.to_keep: set[int] = set()
        """The ID of the existing line items to keep."""

    @abstractmethod
    def collect(self) -> set[int]:
        """Collects the line items.

        :return: The ID of the line items to keep.
        """

    def _add_line_item(self, form: LineItemForm, currency_code: str, no: int) \
            -> None:
        """Composes a line item from the form.

        :param form: The line item form.
        :param currency_code: The code of the currency.
        :param no: The number of the line item.
        :return: None.
        """
        line_item: JournalEntryLineItem | None \
            = self.__line_items_by_id.get(form.id.data)
        if line_item is not None:
            line_item.currency_code = currency_code
            form.populate_obj(line_item)
            line_item.no = no
            if db.session.is_modified(line_item):
                self.form.is_modified = True
        else:
            line_item = JournalEntryLineItem()
            line_item.currency_code = currency_code
            form.populate_obj(line_item)
            line_item.no = no
            self.__obj.line_items.append(line_item)
            self.form.is_modified = True
        self.to_keep.add(line_item.id)

    def _make_cash_line_item(self, forms: list[LineItemForm], is_debit: bool,
                             currency_code: str, no: int) -> None:
        """Composes the cash line item at the other debit or credit of the
        cash journal entry.

        :param forms: The line item forms in the same currency.
        :param is_debit: True for a cash receipt journal entry, or False for a
            cash disbursement journal entry.
        :param currency_code: The code of the currency.
        :param no: The number of the line item.
        :return: None.
        """
        candidates: list[JournalEntryLineItem] \
            = [x for x in self.__line_items
               if x.is_debit == is_debit and x.currency_code == currency_code]
        line_item: JournalEntryLineItem
        if len(candidates) > 0:
            candidates.sort(key=lambda x: x.no)
            line_item = candidates[0]
            line_item.account_id = Account.cash().id
            line_item.description = None
            line_item.amount = sum([x.amount.data for x in forms])
            line_item.no = no
            if db.session.is_modified(line_item):
                self.form.is_modified = True
        else:
            line_item = JournalEntryLineItem()
            line_item.id = new_id(JournalEntryLineItem)
            line_item.is_debit = is_debit
            line_item.currency_code = currency_code
            line_item.account_id = Account.cash().id
            line_item.description = None
            line_item.amount = sum([x.amount.data for x in forms])
            line_item.no = no
            self.__obj.line_items.append(line_item)
            self.form.is_modified = True
        self.to_keep.add(line_item.id)

    def _sort_line_item_forms(self, forms: list[LineItemForm]) -> None:
        """Sorts the line item sub-forms.

        :param forms: The line item sub-forms.
        :return: None.
        """
        missing_no: int = 100 if len(self.__no_by_id) == 0 \
            else max(self.__no_by_id.values()) + 100
        ord_by_form: dict[LineItemForm, int] \
            = {forms[i]: i for i in range(len(forms))}
        recv_no: set[int] = {x.no.data for x in forms if x.no.data is not None}
        missing_recv_no: int = 100 if len(recv_no) == 0 else max(recv_no) + 100
        forms.sort(key=lambda x: (x.no.data or missing_recv_no,
                                  missing_no if x.id.data is None else
                                  self.__no_by_id.get(x.id.data, missing_no),
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


class CashReceiptJournalEntryForm(JournalEntryForm):
    """The form to create or edit a cash receipt journal entry."""
    date = DateField(
        validators=[DATE_REQUIRED,
                    NotBeforeOriginalLineItems(),
                    NotAfterOffsetItems()])
    """The date."""
    currencies = FieldList(FormField(CashReceiptCurrencyForm), name="currency",
                           validators=[NeedSomeCurrencies()])
    """The line items categorized by their currencies."""
    note = TextAreaField(filters=[strip_multiline_text])
    """The note."""
    whole_form = BooleanField(
        validators=[CannotDeleteOriginalLineItemsWithOffset()])
    """The pseudo field for the whole form validators."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._is_need_receivable = True

        class Collector(LineItemCollector[CashReceiptJournalEntryForm]):
            """The line item collector for the cash receipt journal entries."""

            def collect(self) -> None:
                currencies: list[CashReceiptCurrencyForm] \
                    = [x.form for x in self.form.currencies]
                self._sort_currency_forms(currencies)
                for currency in currencies:
                    # The debit cash line item
                    self._make_cash_line_item(list(currency.credit), True,
                                              currency.code.data,
                                              self._debit_no)
                    self._debit_no = self._debit_no + 1

                    # The credit forms
                    credit_forms: list[CreditLineItemForm] \
                        = [x.form for x in currency.credit]
                    self._sort_line_item_forms(credit_forms)
                    for credit_form in credit_forms:
                        self._add_line_item(credit_form, currency.code.data,
                                            self._credit_no)
                        self._credit_no = self._credit_no + 1

        self.collector = Collector


class CashDisbursementJournalEntryForm(JournalEntryForm):
    """The form to create or edit a cash disbursement journal entry."""
    date = DateField(
        validators=[DATE_REQUIRED,
                    NotBeforeOriginalLineItems(),
                    NotAfterOffsetItems()])
    """The date."""
    currencies = FieldList(FormField(CashDisbursementCurrencyForm),
                           name="currency",
                           validators=[NeedSomeCurrencies()])
    """The line items categorized by their currencies."""
    note = TextAreaField(filters=[strip_multiline_text])
    """The note."""
    whole_form = BooleanField(
        validators=[CannotDeleteOriginalLineItemsWithOffset()])
    """The pseudo field for the whole form validators."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._is_need_payable = True

        class Collector(LineItemCollector[CashDisbursementJournalEntryForm]):
            """The line item collector for the cash disbursement journal
            entries."""

            def collect(self) -> None:
                currencies: list[CashDisbursementCurrencyForm] \
                    = [x.form for x in self.form.currencies]
                self._sort_currency_forms(currencies)
                for currency in currencies:
                    # The debit forms
                    debit_forms: list[DebitLineItemForm] \
                        = [x.form for x in currency.debit]
                    self._sort_line_item_forms(debit_forms)
                    for debit_form in debit_forms:
                        self._add_line_item(debit_form, currency.code.data,
                                            self._debit_no)
                        self._debit_no = self._debit_no + 1

                    # The credit forms
                    self._make_cash_line_item(list(currency.debit), False,
                                              currency.code.data,
                                              self._credit_no)
                    self._credit_no = self._credit_no + 1

        self.collector = Collector


class TransferJournalEntryForm(JournalEntryForm):
    """The form to create or edit a transfer journal entry."""
    date = DateField(
        validators=[DATE_REQUIRED,
                    NotBeforeOriginalLineItems(),
                    NotAfterOffsetItems()])
    """The date."""
    currencies = FieldList(FormField(TransferCurrencyForm), name="currency",
                           validators=[NeedSomeCurrencies()])
    """The line items categorized by their currencies."""
    note = TextAreaField(filters=[strip_multiline_text])
    """The note."""
    whole_form = BooleanField(
        validators=[CannotDeleteOriginalLineItemsWithOffset()])
    """The pseudo field for the whole form validators."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._is_need_payable = True
        self._is_need_receivable = True

        class Collector(LineItemCollector[TransferJournalEntryForm]):
            """The line item collector for the transfer journal entries."""

            def collect(self) -> None:
                currencies: list[TransferCurrencyForm] \
                    = [x.form for x in self.form.currencies]
                self._sort_currency_forms(currencies)
                for currency in currencies:
                    # The debit forms
                    debit_forms: list[DebitLineItemForm] \
                        = [x.form for x in currency.debit]
                    self._sort_line_item_forms(debit_forms)
                    for debit_form in debit_forms:
                        self._add_line_item(debit_form, currency.code.data,
                                            self._debit_no)
                        self._debit_no = self._debit_no + 1

                    # The credit forms
                    credit_forms: list[CreditLineItemForm] \
                        = [x.form for x in currency.credit]
                    self._sort_line_item_forms(credit_forms)
                    for credit_form in credit_forms:
                        self._add_line_item(credit_form, currency.code.data,
                                            self._credit_no)
                        self._credit_no = self._credit_no + 1

        self.collector = Collector
