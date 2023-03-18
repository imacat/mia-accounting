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
"""The selectable original entries.

"""
from decimal import Decimal

import sqlalchemy as sa
from flask_babel import LazyString
from sqlalchemy.orm import selectinload

from accounting import db
from accounting.locale import lazy_gettext
from accounting.models import Account, Transaction, JournalEntry
from accounting.transaction.forms.journal_entry import JournalEntryForm
from accounting.utils.cast import be
from .offset_alias import offset_alias


def get_selectable_original_entries(
        entry_id_on_form: set[int], is_payable: bool, is_receivable: bool) \
        -> list[JournalEntry]:
    """Queries and returns the selectable original entries, with their net
    balances.  The offset amounts of the form is excluded.

    :param entry_id_on_form: The ID of the journal entries on the form.
    :param is_payable: True to check the payable original entries, or False
        otherwise.
    :param is_receivable: True to check the receivable original entries, or
        False otherwise.
    :return: The selectable original entries, with their net balances.
    """
    assert is_payable or is_receivable
    offset: sa.Alias = offset_alias()
    net_balance: sa.Label = (JournalEntry.amount + sa.func.sum(sa.case(
        (offset.c.id.in_(entry_id_on_form), 0),
        (be(offset.c.is_debit == JournalEntry.is_debit), offset.c.amount),
        else_=-offset.c.amount))).label("net_balance")
    conditions: list[sa.BinaryExpression] = [Account.is_need_offset]
    sub_conditions: list[sa.BinaryExpression] = []
    if is_payable:
        sub_conditions.append(sa.and_(Account.base_code.startswith("2"),
                                      sa.not_(JournalEntry.is_debit)))
    if is_receivable:
        sub_conditions.append(sa.and_(Account.base_code.startswith("1"),
                                      JournalEntry.is_debit))
    conditions.append(sa.or_(*sub_conditions))
    select_net_balances: sa.Select = sa.select(JournalEntry.id, net_balance)\
        .join(Account)\
        .join(offset, be(JournalEntry.id == offset.c.original_entry_id),
              isouter=True)\
        .filter(*conditions)\
        .group_by(JournalEntry.id)\
        .having(sa.or_(sa.func.count(offset.c.id) == 0, net_balance != 0))
    net_balances: dict[int, Decimal] \
        = {x.id: x.net_balance
           for x in db.session.execute(select_net_balances).all()}
    entries: list[JournalEntry] = JournalEntry.query\
        .filter(JournalEntry.id.in_({x for x in net_balances}))\
        .join(Transaction)\
        .order_by(Transaction.date, JournalEntry.is_debit, JournalEntry.no)\
        .options(selectinload(JournalEntry.currency),
                 selectinload(JournalEntry.account),
                 selectinload(JournalEntry.transaction)).all()
    for entry in entries:
        entry.net_balance = entry.amount if net_balances[entry.id] is None \
            else net_balances[entry.id]
    return entries
