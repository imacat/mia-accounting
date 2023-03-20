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
"""The voucher forms for the voucher management.

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
from accounting.models import Voucher, Account, VoucherLineItem, \
    VoucherCurrency
from accounting.voucher.utils.account_option import AccountOption
from accounting.voucher.utils.original_line_items import \
    get_selectable_original_line_items
from accounting.voucher.utils.description_editor import DescriptionEditor
from accounting.utils.random_id import new_id
from accounting.utils.strip_text import strip_multiline_text
from accounting.utils.user import get_current_user_pk
from .currency import CurrencyForm, CashReceiptCurrencyForm, \
    CashDisbursementCurrencyForm, TransferCurrencyForm
from .line_item import LineItemForm, DebitLineItemForm, CreditLineItemForm
from .reorder import sort_vouchers_in

DATE_REQUIRED: DataRequired = DataRequired(
    lazy_gettext("Please fill in the date."))
"""The validator to check if the date is empty."""


class NotBeforeOriginalLineItems:
    """The validator to check if the date is not before the
    original line items."""

    def __call__(self, form: FlaskForm, field: DateField) -> None:
        assert isinstance(form, VoucherForm)
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
        assert isinstance(form, VoucherForm)
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
        assert isinstance(form, VoucherForm)
        if form.obj is None:
            return
        existing_matched_original_line_item_id: set[int] \
            = {x.id for x in form.obj.line_items if len(x.offsets) > 0}
        line_item_id_in_form: set[int] \
            = {x.eid.data for x in form.line_items if x.eid.data is not None}
        for line_item_id in existing_matched_original_line_item_id:
            if line_item_id not in line_item_id_in_form:
                raise ValidationError(lazy_gettext(
                    "Line items with offset cannot be deleted."))


class VoucherForm(FlaskForm):
    """The base form to create or edit a voucher."""
    date = DateField()
    """The date."""
    currencies = FieldList(FormField(CurrencyForm))
    """The line items categorized by their currencies."""
    note = TextAreaField()
    """The note."""

    def __init__(self, *args, **kwargs):
        """Constructs a base voucher form.

        :param args: The arguments.
        :param kwargs: The keyword arguments.
        """
        super().__init__(*args, **kwargs)
        self.is_modified: bool = False
        """Whether the voucher is modified during populate_obj()."""
        self.collector: t.Type[LineItemCollector] = LineItemCollector
        """The line item collector.  The default is the base abstract
        collector only to provide the correct type.  The subclass forms should
        provide their own collectors."""
        self.obj: Voucher | None = kwargs.get("obj")
        """The voucher, when editing an existing one."""
        self._is_need_payable: bool = False
        """Whether we need the payable original line items."""
        self._is_need_receivable: bool = False
        """Whether we need the receivable original line items."""
        self.__original_line_item_options: list[VoucherLineItem] | None = None
        """The options of the original line items."""
        self.__net_balance_exceeded: dict[int, LazyString] | None = None
        """The original line items whose net balances were exceeded by the
        amounts in the line item sub-forms."""
        for line_item in self.line_items:
            line_item.voucher_form = self

    def populate_obj(self, obj: Voucher) -> None:
        """Populates the form data into a voucher object.

        :param obj: The voucher object.
        :return: None.
        """
        is_new: bool = obj.id is None
        if is_new:
            obj.id = new_id(Voucher)
        self.date: DateField
        self.__set_date(obj, self.date.data)
        obj.note = self.note.data

        collector_cls: t.Type[LineItemCollector] = self.collector
        collector: collector_cls = collector_cls(self, obj)
        collector.collect()

        to_delete: set[int] = {x.id for x in obj.line_items
                               if x.id not in collector.to_keep}
        if len(to_delete) > 0:
            VoucherLineItem.query\
                .filter(VoucherLineItem.id.in_(to_delete)).delete()
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

    def __set_date(self, obj: Voucher, new_date: dt.date) -> None:
        """Sets the voucher date and number.

        :param obj: The voucher object.
        :param new_date: The new date.
        :return: None.
        """
        if obj.date is None or obj.date != new_date:
            if obj.date is not None:
                sort_vouchers_in(obj.date, obj.id)
            if self.max_date is not None and new_date == self.max_date:
                db_min_no: int | None = db.session.scalar(
                    sa.select(sa.func.min(Voucher.no))
                    .filter(Voucher.date == new_date))
                if db_min_no is None:
                    obj.date = new_date
                    obj.no = 1
                else:
                    obj.date = new_date
                    obj.no = db_min_no - 1
                    sort_vouchers_in(new_date)
            else:
                sort_vouchers_in(new_date, obj.id)
                count: int = Voucher.query\
                    .filter(Voucher.date == new_date).count()
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
            sa.select(VoucherLineItem.account_id)
            .filter(VoucherLineItem.is_debit)
            .group_by(VoucherLineItem.account_id)).all())
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
            sa.select(VoucherLineItem.account_id)
            .filter(sa.not_(VoucherLineItem.is_debit))
            .group_by(VoucherLineItem.account_id)).all())
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
    def original_line_item_options(self) -> list[VoucherLineItem]:
        """Returns the selectable original line items.

        :return: The selectable original line items.
        """
        if self.__original_line_item_options is None:
            self.__original_line_item_options \
                = get_selectable_original_line_items(
                    {x.eid.data for x in self.line_items
                     if x.eid.data is not None},
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
        select: sa.Select = sa.select(sa.func.max(Voucher.date))\
            .join(VoucherLineItem)\
            .filter(VoucherLineItem.id.in_(original_line_item_id))
        return db.session.scalar(select)

    @property
    def max_date(self) -> dt.date | None:
        """Returns the maximum available date.

        :return: The maximum available date.
        """
        line_item_id: set[int] = {x.eid.data for x in self.line_items
                                  if x.eid.data is not None}
        select: sa.Select = sa.select(sa.func.min(Voucher.date))\
            .join(VoucherLineItem)\
            .filter(VoucherLineItem.original_line_item_id.in_(line_item_id))
        return db.session.scalar(select)


T = t.TypeVar("T", bound=VoucherForm)
"""A voucher form variant."""


class LineItemCollector(t.Generic[T], ABC):
    """The line item collector."""

    def __init__(self, form: T, obj: Voucher):
        """Constructs the line item collector.

        :param form: The voucher form.
        :param obj: The voucher.
        """
        self.form: T = form
        """The voucher form."""
        self.__obj: Voucher = obj
        """The voucher object."""
        self.__line_items: list[VoucherLineItem] = list(obj.line_items)
        """The existing line items."""
        self.__line_items_by_id: dict[int, VoucherLineItem] \
            = {x.id: x for x in self.__line_items}
        """A dictionary from the line item ID to their line items."""
        self.__no_by_id: dict[int, int] \
            = {x.id: x.no for x in self.__line_items}
        """A dictionary from the line item number to their line items."""
        self.__currencies: list[VoucherCurrency] = obj.currencies
        """The currencies in the voucher."""
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
        line_item: VoucherLineItem | None \
            = self.__line_items_by_id.get(form.eid.data)
        if line_item is not None:
            line_item.currency_code = currency_code
            form.populate_obj(line_item)
            line_item.no = no
            if db.session.is_modified(line_item):
                self.form.is_modified = True
        else:
            line_item = VoucherLineItem()
            line_item.currency_code = currency_code
            form.populate_obj(line_item)
            line_item.no = no
            self.__obj.line_items.append(line_item)
            self.form.is_modified = True
        self.to_keep.add(line_item.id)

    def _make_cash_line_item(self, forms: list[LineItemForm], is_debit: bool,
                             currency_code: str, no: int) -> None:
        """Composes the cash line item at the other side of the cash
        voucher.

        :param forms: The line item forms in the same currency.
        :param is_debit: True for a cash receipt voucher, or False for a
            cash disbursement voucher.
        :param currency_code: The code of the currency.
        :param no: The number of the line item.
        :return: None.
        """
        candidates: list[VoucherLineItem] \
            = [x for x in self.__line_items
               if x.is_debit == is_debit and x.currency_code == currency_code]
        line_item: VoucherLineItem
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
            line_item = VoucherLineItem()
            line_item.id = new_id(VoucherLineItem)
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


class CashReceiptVoucherForm(VoucherForm):
    """The form to create or edit a cash receipt voucher."""
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

        class Collector(LineItemCollector[CashReceiptVoucherForm]):
            """The line item collector for the cash receipt vouchers."""

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


class CashDisbursementVoucherForm(VoucherForm):
    """The form to create or edit a cash disbursement voucher."""
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

        class Collector(LineItemCollector[CashDisbursementVoucherForm]):
            """The line item collector for the cash disbursement vouchers."""

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


class TransferVoucherForm(VoucherForm):
    """The form to create or edit a transfer voucher."""
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

        class Collector(LineItemCollector[TransferVoucherForm]):
            """The line item collector for the transfer vouchers."""

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
