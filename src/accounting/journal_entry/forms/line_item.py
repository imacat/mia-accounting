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
"""The line item sub-forms for the journal entry management.

"""
from datetime import date
from decimal import Decimal

import sqlalchemy as sa
from flask_babel import LazyString
from flask_wtf import FlaskForm
from sqlalchemy.orm import selectinload
from wtforms import StringField, ValidationError, DecimalField, IntegerField
from wtforms.validators import Optional

from accounting import db
from accounting.forms import ACCOUNT_REQUIRED, AccountExists, IsDebitAccount, \
    IsCreditAccount
from accounting.locale import lazy_gettext
from accounting.models import Account, JournalEntryLineItem
from accounting.template_filters import format_amount
from accounting.utils.cast import be
from accounting.utils.random_id import new_id
from accounting.utils.strip_text import strip_text
from accounting.utils.user import get_current_user_pk


class OriginalLineItemExists:
    """The validator to check if the original line item exists."""

    def __call__(self, form: FlaskForm, field: IntegerField) -> None:
        if field.data is None:
            return
        if db.session.get(JournalEntryLineItem, field.data) is None:
            raise ValidationError(lazy_gettext(
                "The original line item does not exist."))


class OriginalLineItemOppositeDebitCredit:
    """The validator to check if the original line item is on the opposite
    debit or credit."""

    def __call__(self, form: FlaskForm, field: IntegerField) -> None:
        if field.data is None:
            return
        original_line_item: JournalEntryLineItem | None \
            = db.session.get(JournalEntryLineItem, field.data)
        if original_line_item is None:
            return
        if isinstance(form, CreditLineItemForm) \
                and original_line_item.is_debit:
            return
        if isinstance(form, DebitLineItemForm) \
                and not original_line_item.is_debit:
            return
        raise ValidationError(lazy_gettext(
            "The original line item is on the same debit or credit."))


class OriginalLineItemNeedOffset:
    """The validator to check if the original line item needs offset."""

    def __call__(self, form: FlaskForm, field: IntegerField) -> None:
        if field.data is None:
            return
        original_line_item: JournalEntryLineItem | None \
            = db.session.get(JournalEntryLineItem, field.data)
        if original_line_item is None:
            return
        if not original_line_item.account.is_need_offset:
            raise ValidationError(lazy_gettext(
                "The original line item does not need offset."))


class OriginalLineItemNotOffset:
    """The validator to check if the original line item is not itself an
    offset item."""

    def __call__(self, form: FlaskForm, field: IntegerField) -> None:
        if field.data is None:
            return
        original_line_item: JournalEntryLineItem | None \
            = db.session.get(JournalEntryLineItem, field.data)
        if original_line_item is None:
            return
        if original_line_item.original_line_item_id is not None:
            raise ValidationError(lazy_gettext(
                "The original line item cannot be an offset item."))


class SameAccountAsOriginalLineItem:
    """The validator to check if the account is the same as the
    original line item."""

    def __call__(self, form: FlaskForm, field: StringField) -> None:
        assert isinstance(form, LineItemForm)
        if field.data is None or form.original_line_item_id.data is None:
            return
        original_line_item: JournalEntryLineItem | None \
            = db.session.get(JournalEntryLineItem,
                             form.original_line_item_id.data)
        if original_line_item is None:
            return
        if field.data != original_line_item.account_code:
            raise ValidationError(lazy_gettext(
                "The account must be the same as the original line item."))


class KeepAccountWhenHavingOffset:
    """The validator to check if the account is the same when having offset."""

    def __call__(self, form: FlaskForm, field: StringField) -> None:
        assert isinstance(form, LineItemForm)
        if field.data is None or form.id.data is None:
            return
        line_item: JournalEntryLineItem | None = db.session\
            .query(JournalEntryLineItem)\
            .filter(JournalEntryLineItem.id == form.id.data)\
            .options(selectinload(JournalEntryLineItem.offsets)).first()
        if line_item is None or len(line_item.offsets) == 0:
            return
        if field.data != line_item.account_code:
            raise ValidationError(lazy_gettext(
                "The account must not be changed when there is offset."))


class NotStartPayableFromDebit:
    """The validator to check that a payable line item does not start from
    debit."""

    def __call__(self, form: FlaskForm, field: StringField) -> None:
        assert isinstance(form, DebitLineItemForm)
        if field.data is None \
                or field.data[0] != "2" \
                or form.original_line_item_id.data is not None:
            return
        account: Account | None = Account.find_by_code(field.data)
        if account is not None and account.is_need_offset:
            raise ValidationError(lazy_gettext(
                "A payable line item cannot start from debit."))


class NotStartReceivableFromCredit:
    """The validator to check that a receivable line item does not start
    from credit."""

    def __call__(self, form: FlaskForm, field: StringField) -> None:
        assert isinstance(form, CreditLineItemForm)
        if field.data is None \
                or field.data[0] != "1" \
                or form.original_line_item_id.data is not None:
            return
        account: Account | None = Account.find_by_code(field.data)
        if account is not None and account.is_need_offset:
            raise ValidationError(lazy_gettext(
                "A receivable line item cannot start from credit."))


class PositiveAmount:
    """The validator to check if the amount is positive."""

    def __call__(self, form: FlaskForm, field: DecimalField) -> None:
        if field.data is None:
            return
        if field.data <= 0:
            raise ValidationError(lazy_gettext(
                "Please fill in a positive amount."))


class NotExceedingOriginalLineItemNetBalance:
    """The validator to check if the amount exceeds the net balance of the
    original line item."""

    def __call__(self, form: FlaskForm, field: DecimalField) -> None:
        assert isinstance(form, LineItemForm)
        if field.data is None or form.original_line_item_id.data is None:
            return
        original_line_item: JournalEntryLineItem | None \
            = db.session.get(JournalEntryLineItem,
                             form.original_line_item_id.data)
        if original_line_item is None:
            return
        is_debit: bool = isinstance(form, DebitLineItemForm)
        existing_line_item_id: set[int] = set()
        if form.journal_entry_form.obj is not None:
            existing_line_item_id \
                = {x.id for x in form.journal_entry_form.obj.line_items}
        offset_total_func: sa.Function = sa.func.sum(sa.case(
            (be(JournalEntryLineItem.is_debit == is_debit),
             JournalEntryLineItem.amount),
            else_=-JournalEntryLineItem.amount))
        offset_total_but_form: Decimal | None = db.session.scalar(
            sa.select(offset_total_func)
            .filter(be(JournalEntryLineItem.original_line_item_id
                       == original_line_item.id),
                    JournalEntryLineItem.id.not_in(existing_line_item_id)))
        if offset_total_but_form is None:
            offset_total_but_form = Decimal("0")
        offset_total_on_form: Decimal = sum(
            [x.amount.data for x in form.journal_entry_form.line_items
             if x.original_line_item_id.data == original_line_item.id
             and x.amount != field and x.amount.data is not None])
        net_balance: Decimal = original_line_item.amount \
            - offset_total_but_form - offset_total_on_form
        if field.data > net_balance:
            raise ValidationError(lazy_gettext(
                "The amount must not exceed the net balance %(balance)s of the"
                " original line item.", balance=format_amount(net_balance)))


class NotLessThanOffsetTotal:
    """The validator to check if the amount is less than the offset total."""

    def __call__(self, form: FlaskForm, field: DecimalField) -> None:
        assert isinstance(form, LineItemForm)
        if field.data is None or form.id.data is None:
            return
        is_debit: bool = isinstance(form, DebitLineItemForm)
        select_offset_total: sa.Select = sa.select(sa.func.sum(sa.case(
            (JournalEntryLineItem.is_debit != is_debit,
             JournalEntryLineItem.amount),
            else_=-JournalEntryLineItem.amount)))\
            .filter(be(JournalEntryLineItem.original_line_item_id
                       == form.id.data))
        offset_total: Decimal | None = db.session.scalar(select_offset_total)
        if offset_total is not None and field.data < offset_total:
            raise ValidationError(lazy_gettext(
                "The amount must not be less than the offset total %(total)s.",
                total=format_amount(offset_total)))


class LineItemForm(FlaskForm):
    """The base form to create or edit a line item."""
    id = IntegerField()
    """The existing line item ID."""
    no = IntegerField()
    """The order in the currency."""
    original_line_item_id = IntegerField()
    """The Id of the original line item."""
    account_code = StringField()
    """The account code."""
    description = StringField()
    """The description."""
    amount = DecimalField()
    """The amount."""

    def __init__(self, *args, **kwargs):
        """Constructs a base line item form.

        :param args: The arguments.
        :param kwargs: The keyword arguments.
        """
        super().__init__(*args, **kwargs)
        from .journal_entry import JournalEntryForm
        self.journal_entry_form: JournalEntryForm | None = None
        """The source journal entry form."""

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
    def __original_line_item(self) -> JournalEntryLineItem | None:
        """Returns the original line item.

        :return: The original line item.
        """
        if not hasattr(self, "____original_line_item"):
            def get_line_item() -> JournalEntryLineItem | None:
                if self.original_line_item_id.data is None:
                    return None
                return db.session.get(JournalEntryLineItem,
                                      self.original_line_item_id.data)
            setattr(self, "____original_line_item", get_line_item())
        return getattr(self, "____original_line_item")

    @property
    def original_line_item_date(self) -> date | None:
        """Returns the text representation of the original line item.

        :return: The text representation of the original line item.
        """
        return None if self.__original_line_item is None \
            else self.__original_line_item.journal_entry.date

    @property
    def original_line_item_text(self) -> str | None:
        """Returns the text representation of the original line item.

        :return: The text representation of the original line item.
        """
        return None if self.__original_line_item is None \
            else str(self.__original_line_item)

    @property
    def is_need_offset(self) -> bool:
        """Returns whether the line item needs offset.

        :return: True if the line item needs offset, or False otherwise.
        """
        if self.account_code.data is None:
            return False
        if self.account_code.data[0] == "1":
            if isinstance(self, CreditLineItemForm):
                return False
        elif self.account_code.data[0] == "2":
            if isinstance(self, DebitLineItemForm):
                return False
        else:
            return False
        account: Account | None = Account.find_by_code(self.account_code.data)
        return account is not None and account.is_need_offset

    @property
    def offsets(self) -> list[JournalEntryLineItem]:
        """Returns the offsets.

        :return: The offsets.
        """
        if not hasattr(self, "__offsets"):
            def get_offsets() -> list[JournalEntryLineItem]:
                if not self.is_need_offset or self.id.data is None:
                    return []
                return JournalEntryLineItem.query\
                    .filter(JournalEntryLineItem.original_line_item_id
                            == self.id.data)\
                    .options(selectinload(JournalEntryLineItem.journal_entry),
                             selectinload(JournalEntryLineItem.account),
                             selectinload(JournalEntryLineItem.offsets)
                             .selectinload(
                                 JournalEntryLineItem.journal_entry)).all()
            setattr(self, "__offsets", get_offsets())
        return getattr(self, "__offsets")

    @property
    def offset_total(self) -> Decimal | None:
        """Returns the total amount of the offsets.

        :return: The total amount of the offsets.
        """
        if not hasattr(self, "__offset_total"):
            def get_offset_total():
                if not self.is_need_offset or self.id.data is None:
                    return None
                is_debit: bool = isinstance(self, DebitLineItemForm)
                return sum([x.amount if x.is_debit != is_debit else -x.amount
                            for x in self.offsets])
            setattr(self, "__offset_total", get_offset_total())
        return getattr(self, "__offset_total")

    @property
    def net_balance(self) -> Decimal | None:
        """Returns the net balance.

        :return: The net balance.
        """
        if not self.is_need_offset or self.id.data is None \
                or self.amount.data is None:
            return None
        return self.amount.data - self.offset_total

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


class DebitLineItemForm(LineItemForm):
    """The form to create or edit a debit line item."""
    id = IntegerField()
    """The existing line item ID."""
    no = IntegerField()
    """The order in the currency."""
    original_line_item_id = IntegerField(
        validators=[Optional(),
                    OriginalLineItemExists(),
                    OriginalLineItemOppositeDebitCredit(),
                    OriginalLineItemNeedOffset(),
                    OriginalLineItemNotOffset()])
    """The ID of the original line item."""
    account_code = StringField(
        filters=[strip_text],
        validators=[
            ACCOUNT_REQUIRED,
            AccountExists(),
            IsDebitAccount(lazy_gettext(
                "This account is not for debit line items.")),
            SameAccountAsOriginalLineItem(),
            KeepAccountWhenHavingOffset(),
            NotStartPayableFromDebit()])
    """The account code."""
    description = StringField(filters=[strip_text])
    """The description."""
    amount = DecimalField(
        validators=[PositiveAmount(),
                    NotExceedingOriginalLineItemNetBalance(),
                    NotLessThanOffsetTotal()])
    """The amount."""

    def populate_obj(self, obj: JournalEntryLineItem) -> None:
        """Populates the form data into a line item object.

        :param obj: The line item object.
        :return: None.
        """
        is_new: bool = obj.id is None
        if is_new:
            obj.id = new_id(JournalEntryLineItem)
        obj.original_line_item_id = self.original_line_item_id.data
        obj.account_id = Account.find_by_code(self.account_code.data).id
        obj.description = self.description.data
        obj.is_debit = True
        obj.amount = self.amount.data
        if is_new:
            current_user_pk: int = get_current_user_pk()
            obj.created_by_id = current_user_pk
            obj.updated_by_id = current_user_pk


class CreditLineItemForm(LineItemForm):
    """The form to create or edit a credit line item."""
    id = IntegerField()
    """The existing line item ID."""
    no = IntegerField()
    """The order in the currency."""
    original_line_item_id = IntegerField(
        validators=[Optional(),
                    OriginalLineItemExists(),
                    OriginalLineItemOppositeDebitCredit(),
                    OriginalLineItemNeedOffset(),
                    OriginalLineItemNotOffset()])
    """The ID of the original line item."""
    account_code = StringField(
        filters=[strip_text],
        validators=[
            ACCOUNT_REQUIRED,
            AccountExists(),
            IsCreditAccount(lazy_gettext(
                "This account is not for credit line items.")),
            SameAccountAsOriginalLineItem(),
            KeepAccountWhenHavingOffset(),
            NotStartReceivableFromCredit()])
    """The account code."""
    description = StringField(filters=[strip_text])
    """The description."""
    amount = DecimalField(
        validators=[PositiveAmount(),
                    NotExceedingOriginalLineItemNetBalance(),
                    NotLessThanOffsetTotal()])
    """The amount."""

    def populate_obj(self, obj: JournalEntryLineItem) -> None:
        """Populates the form data into a line item object.

        :param obj: The line item object.
        :return: None.
        """
        is_new: bool = obj.id is None
        if is_new:
            obj.id = new_id(JournalEntryLineItem)
        obj.original_line_item_id = self.original_line_item_id.data
        obj.account_id = Account.find_by_code(self.account_code.data).id
        obj.description = self.description.data
        obj.is_debit = False
        obj.amount = self.amount.data
        if is_new:
            current_user_pk: int = get_current_user_pk()
            obj.created_by_id = current_user_pk
            obj.updated_by_id = current_user_pk
