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
"""The journal entry sub-forms for the transaction management.

"""
import re
from datetime import date
from decimal import Decimal

import sqlalchemy as sa
from flask_babel import LazyString
from flask_wtf import FlaskForm
from sqlalchemy.orm import selectinload
from wtforms import StringField, ValidationError, DecimalField, IntegerField
from wtforms.validators import DataRequired, Optional

from accounting import db
from accounting.locale import lazy_gettext
from accounting.models import Account, JournalEntry
from accounting.template_filters import format_amount
from accounting.utils.cast import be
from accounting.utils.random_id import new_id
from accounting.utils.strip_text import strip_text
from accounting.utils.user import get_current_user_pk

ACCOUNT_REQUIRED: DataRequired = DataRequired(
    lazy_gettext("Please select the account."))
"""The validator to check if the account code is empty."""


class OriginalEntryExists:
    """The validator to check if the original entry exists."""

    def __call__(self, form: FlaskForm, field: IntegerField) -> None:
        if field.data is None:
            return
        if db.session.get(JournalEntry, field.data) is None:
            raise ValidationError(lazy_gettext(
                "The original entry does not exist."))


class OriginalEntryOppositeSide:
    """The validator to check if the original entry is on the opposite side."""

    def __call__(self, form: FlaskForm, field: IntegerField) -> None:
        if field.data is None:
            return
        original_entry: JournalEntry | None \
            = db.session.get(JournalEntry, field.data)
        if original_entry is None:
            return
        if isinstance(form, CreditEntryForm) and original_entry.is_debit:
            return
        if isinstance(form, DebitEntryForm) and not original_entry.is_debit:
            return
        raise ValidationError(lazy_gettext(
            "The original entry is on the same side."))


class OriginalEntryNeedOffset:
    """The validator to check if the original entry needs offset."""

    def __call__(self, form: FlaskForm, field: IntegerField) -> None:
        if field.data is None:
            return
        original_entry: JournalEntry | None \
            = db.session.get(JournalEntry, field.data)
        if original_entry is None:
            return
        if not original_entry.account.is_offset_needed:
            raise ValidationError(lazy_gettext(
                "The original entry does not need offset."))


class OriginalEntryNotOffset:
    """The validator to check if the original entry is not itself an offset
    entry."""

    def __call__(self, form: FlaskForm, field: IntegerField) -> None:
        if field.data is None:
            return
        original_entry: JournalEntry | None \
            = db.session.get(JournalEntry, field.data)
        if original_entry is None:
            return
        if original_entry.original_entry_id is not None:
            raise ValidationError(lazy_gettext(
                "The original entry cannot be an offset entry."))


class AccountExists:
    """The validator to check if the account exists."""

    def __call__(self, form: FlaskForm, field: StringField) -> None:
        if field.data is None:
            return
        if Account.find_by_code(field.data) is None:
            raise ValidationError(lazy_gettext(
                "The account does not exist."))


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


class SameAccountAsOriginalEntry:
    """The validator to check if the account is the same as the original
    entry."""

    def __call__(self, form: FlaskForm, field: StringField) -> None:
        assert isinstance(form, JournalEntryForm)
        if field.data is None or form.original_entry_id.data is None:
            return
        original_entry: JournalEntry | None \
            = db.session.get(JournalEntry, form.original_entry_id.data)
        if original_entry is None:
            return
        if field.data != original_entry.account_code:
            raise ValidationError(lazy_gettext(
                "The account must be the same as the original entry."))


class KeepAccountWhenHavingOffset:
    """The validator to check if the account is the same when having offset."""

    def __call__(self, form: FlaskForm, field: StringField) -> None:
        assert isinstance(form, JournalEntryForm)
        if field.data is None or form.eid.data is None:
            return
        entry: JournalEntry | None = db.session.query(JournalEntry)\
            .filter(JournalEntry.id == form.eid.data)\
            .options(selectinload(JournalEntry.offsets)).first()
        if entry is None or len(entry.offsets) == 0:
            return
        if field.data != entry.account_code:
            raise ValidationError(lazy_gettext(
                "The account must not be changed when there is offset."))


class NotStartPayableFromDebit:
    """The validator to check that a payable journal entry does not start from
    the debit side."""

    def __call__(self, form: FlaskForm, field: StringField) -> None:
        assert isinstance(form, DebitEntryForm)
        if field.data is None \
                or field.data[0] != "2" \
                or form.original_entry_id.data is not None:
            return
        account: Account | None = Account.find_by_code(field.data)
        if account is not None and account.is_offset_needed:
            raise ValidationError(lazy_gettext(
                "A payable entry cannot start from the debit side."))


class NotStartReceivableFromCredit:
    """The validator to check that a receivable journal entry does not start
    from the credit side."""

    def __call__(self, form: FlaskForm, field: StringField) -> None:
        assert isinstance(form, CreditEntryForm)
        if field.data is None \
                or field.data[0] != "1" \
                or form.original_entry_id.data is not None:
            return
        account: Account | None = Account.find_by_code(field.data)
        if account is not None and account.is_offset_needed:
            raise ValidationError(lazy_gettext(
                "A receivable entry cannot start from the credit side."))


class PositiveAmount:
    """The validator to check if the amount is positive."""

    def __call__(self, form: FlaskForm, field: DecimalField) -> None:
        if field.data is None:
            return
        if field.data <= 0:
            raise ValidationError(lazy_gettext(
                "Please fill in a positive amount."))


class NotExceedingOriginalEntryNetBalance:
    """The validator to check if the amount exceeds the net balance of the
    original entry."""

    def __call__(self, form: FlaskForm, field: DecimalField) -> None:
        assert isinstance(form, JournalEntryForm)
        if field.data is None or form.original_entry_id.data is None:
            return
        original_entry: JournalEntry | None \
            = db.session.get(JournalEntry, form.original_entry_id.data)
        if original_entry is None:
            return
        is_debit: bool = isinstance(form, DebitEntryForm)
        existing_entry_id: set[int] = set()
        if form.txn_form.obj is not None:
            existing_entry_id = {x.id for x in form.txn_form.obj.entries}
        offset_total_func: sa.Function = sa.func.sum(sa.case(
            (be(JournalEntry.is_debit == is_debit), JournalEntry.amount),
            else_=-JournalEntry.amount))
        offset_total_but_form: Decimal | None = db.session.scalar(
            sa.select(offset_total_func)
            .filter(be(JournalEntry.original_entry_id == original_entry.id),
                    JournalEntry.id.not_in(existing_entry_id)))
        if offset_total_but_form is None:
            offset_total_but_form = Decimal("0")
        offset_total_on_form: Decimal = sum(
            [x.amount.data for x in form.txn_form.entries
             if x.original_entry_id.data == original_entry.id
             and x.amount != field and x.amount.data is not None])
        net_balance: Decimal = original_entry.amount - offset_total_but_form \
            - offset_total_on_form
        if field.data > net_balance:
            raise ValidationError(lazy_gettext(
                "The amount must not exceed the net balance %(balance)s of the"
                " original entry.", balance=format_amount(net_balance)))


class NotLessThanOffsetTotal:
    """The validator to check if the amount is less than the offset total."""

    def __call__(self, form: FlaskForm, field: DecimalField) -> None:
        assert isinstance(form, JournalEntryForm)
        if field.data is None or form.eid.data is None:
            return
        is_debit: bool = isinstance(form, DebitEntryForm)
        select_offset_total: sa.Select = sa.select(sa.func.sum(sa.case(
            (JournalEntry.is_debit != is_debit, JournalEntry.amount),
            else_=-JournalEntry.amount)))\
            .filter(be(JournalEntry.original_entry_id == form.eid.data))
        offset_total: Decimal | None = db.session.scalar(select_offset_total)
        if offset_total is not None and field.data < offset_total:
            raise ValidationError(lazy_gettext(
                "The amount must not be less than the offset total %(total)s.",
                total=format_amount(offset_total)))


class JournalEntryForm(FlaskForm):
    """The base form to create or edit a journal entry."""
    eid = IntegerField()
    """The existing journal entry ID."""
    no = IntegerField()
    """The order in the currency."""
    original_entry_id = IntegerField()
    """The Id of the original entry."""
    account_code = StringField()
    """The account code."""
    amount = DecimalField()
    """The amount."""

    def __init__(self, *args, **kwargs):
        """Constructs a base transaction form.

        :param args: The arguments.
        :param kwargs: The keyword arguments.
        """
        super().__init__(*args, **kwargs)
        from .transaction import TransactionForm
        self.txn_form: TransactionForm | None = None
        """The source transaction form."""

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
    def __original_entry(self) -> JournalEntry | None:
        """Returns the original entry.

        :return: The original entry.
        """
        if not hasattr(self, "____original_entry"):
            def get_entry() -> JournalEntry | None:
                if self.original_entry_id.data is None:
                    return None
                return db.session.get(JournalEntry,
                                      self.original_entry_id.data)
            setattr(self, "____original_entry", get_entry())
        return getattr(self, "____original_entry")

    @property
    def original_entry_date(self) -> date | None:
        """Returns the text representation of the original entry.

        :return: The text representation of the original entry.
        """
        return None if self.__original_entry is None \
            else self.__original_entry.transaction.date

    @property
    def original_entry_text(self) -> str | None:
        """Returns the text representation of the original entry.

        :return: The text representation of the original entry.
        """
        return None if self.__original_entry is None \
            else str(self.__original_entry)

    @property
    def __entry(self) -> JournalEntry | None:
        """Returns the journal entry.

        :return: The journal entry.
        """
        if not hasattr(self, "____entry"):
            def get_entry() -> JournalEntry | None:
                if self.eid.data is None:
                    return None
                return JournalEntry.query\
                    .filter(JournalEntry.id == self.eid.data)\
                    .options(selectinload(JournalEntry.transaction),
                             selectinload(JournalEntry.account),
                             selectinload(JournalEntry.offsets)
                             .selectinload(JournalEntry.transaction))\
                    .first()
            setattr(self, "____entry", get_entry())
        return getattr(self, "____entry")

    @property
    def is_original_entry(self) -> bool:
        """Returns whether the entry is an original entry.

        :return: True if the entry is an original entry, or False otherwise.
        """
        if self.account_code.data is None:
            return False
        if self.account_code.data[0] == "1":
            if isinstance(self, CreditEntryForm):
                return False
        elif self.account_code.data[0] == "2":
            if isinstance(self, DebitEntryForm):
                return False
        else:
            return False
        account: Account | None = Account.find_by_code(self.account_code.data)
        return account is not None and account.is_offset_needed

    @property
    def offsets(self) -> list[JournalEntry]:
        """Returns the offsets.

        :return: The offsets.
        """
        if not hasattr(self, "__offsets"):
            def get_offsets() -> list[JournalEntry]:
                if not self.is_original_entry or self.eid.data is None:
                    return []
                return JournalEntry.query\
                    .filter(JournalEntry.original_entry_id == self.eid.data)\
                    .options(selectinload(JournalEntry.transaction),
                             selectinload(JournalEntry.account),
                             selectinload(JournalEntry.offsets)
                             .selectinload(JournalEntry.transaction)).all()
            setattr(self, "__offsets", get_offsets())
        return getattr(self, "__offsets")

    @property
    def offset_total(self) -> Decimal | None:
        """Returns the total amount of the offsets.

        :return: The total amount of the offsets.
        """
        if not hasattr(self, "__offset_total"):
            def get_offset_total():
                if not self.is_original_entry or self.eid.data is None:
                    return None
                is_debit: bool = isinstance(self, DebitEntryForm)
                return sum([x.amount if x.is_debit != is_debit else -x.amount
                            for x in self.offsets])
            setattr(self, "__offset_total", get_offset_total())
        return getattr(self, "__offset_total")

    @property
    def net_balance(self) -> Decimal | None:
        """Returns the net balance.

        :return: The net balance.
        """
        if not self.is_original_entry or self.eid.data is None \
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


class DebitEntryForm(JournalEntryForm):
    """The form to create or edit a debit journal entry."""
    eid = IntegerField()
    """The existing journal entry ID."""
    no = IntegerField()
    """The order in the currency."""
    original_entry_id = IntegerField(
        validators=[Optional(),
                    OriginalEntryExists(),
                    OriginalEntryOppositeSide(),
                    OriginalEntryNeedOffset(),
                    OriginalEntryNotOffset()])
    """The Id of the original entry."""
    account_code = StringField(
        filters=[strip_text],
        validators=[ACCOUNT_REQUIRED,
                    AccountExists(),
                    IsDebitAccount(),
                    SameAccountAsOriginalEntry(),
                    KeepAccountWhenHavingOffset(),
                    NotStartPayableFromDebit()])
    """The account code."""
    offset_original_entry_id = IntegerField()
    """The Id of the original entry."""
    summary = StringField(filters=[strip_text])
    """The summary."""
    amount = DecimalField(
        validators=[PositiveAmount(),
                    NotExceedingOriginalEntryNetBalance(),
                    NotLessThanOffsetTotal()])
    """The amount."""

    def populate_obj(self, obj: JournalEntry) -> None:
        """Populates the form data into a journal entry object.

        :param obj: The journal entry object.
        :return: None.
        """
        is_new: bool = obj.id is None
        if is_new:
            obj.id = new_id(JournalEntry)
        obj.original_entry_id = self.original_entry_id.data
        obj.account_id = Account.find_by_code(self.account_code.data).id
        obj.summary = self.summary.data
        obj.is_debit = True
        obj.amount = self.amount.data
        if is_new:
            current_user_pk: int = get_current_user_pk()
            obj.created_by_id = current_user_pk
            obj.updated_by_id = current_user_pk


class CreditEntryForm(JournalEntryForm):
    """The form to create or edit a credit journal entry."""
    eid = IntegerField()
    """The existing journal entry ID."""
    no = IntegerField()
    """The order in the currency."""
    original_entry_id = IntegerField(
        validators=[Optional(),
                    OriginalEntryExists(),
                    OriginalEntryOppositeSide(),
                    OriginalEntryNeedOffset(),
                    OriginalEntryNotOffset()])
    """The Id of the original entry."""
    account_code = StringField(
        filters=[strip_text],
        validators=[ACCOUNT_REQUIRED,
                    AccountExists(),
                    IsCreditAccount(),
                    SameAccountAsOriginalEntry(),
                    KeepAccountWhenHavingOffset(),
                    NotStartReceivableFromCredit()])
    """The account code."""
    summary = StringField(filters=[strip_text])
    """The summary."""
    amount = DecimalField(
        validators=[PositiveAmount(),
                    NotExceedingOriginalEntryNetBalance(),
                    NotLessThanOffsetTotal()])
    """The amount."""

    def populate_obj(self, obj: JournalEntry) -> None:
        """Populates the form data into a journal entry object.

        :param obj: The journal entry object.
        :return: None.
        """
        is_new: bool = obj.id is None
        if is_new:
            obj.id = new_id(JournalEntry)
        obj.original_entry_id = self.original_entry_id.data
        obj.account_id = Account.find_by_code(self.account_code.data).id
        obj.summary = self.summary.data
        obj.is_debit = False
        obj.amount = self.amount.data
        if is_new:
            current_user_pk: int = get_current_user_pk()
            obj.created_by_id = current_user_pk
            obj.updated_by_id = current_user_pk
