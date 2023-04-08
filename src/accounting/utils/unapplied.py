# The Mia! Accounting Project.
# Author: imacat@mail.imacat.idv.tw (imacat), 2023/4/8

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
"""The unapplied original line item utilities.

"""
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy.orm import selectinload

from accounting import db
from accounting.models import Account, JournalEntry, JournalEntryLineItem
from accounting.utils.cast import be
from accounting.utils.offset_alias import offset_alias


def get_unapplied_original_line_items(account: Account) \
        -> list[JournalEntryLineItem]:
    """Queries and returns the unapplied original line items in an account.

    :param account: The account.
    :return: The unapplied original line items in the account.
    """
    offset: sa.Alias = offset_alias()
    net_balance: sa.Label \
        = (JournalEntryLineItem.amount
           + sa.func.sum(sa.case(
                (be(offset.c.is_debit == JournalEntryLineItem.is_debit),
                 offset.c.amount),
                else_=-offset.c.amount))).label("net_balance")
    select_net_balances: sa.Select \
        = sa.select(JournalEntryLineItem.id, net_balance) \
        .join(Account) \
        .join(offset, be(JournalEntryLineItem.id
                         == offset.c.original_line_item_id),
              isouter=True) \
        .filter(be(Account.id == account.id),
                sa.or_(sa.and_(Account.base_code.startswith("2"),
                               sa.not_(JournalEntryLineItem.is_debit)),
                       sa.and_(Account.base_code.startswith("1"),
                               JournalEntryLineItem.is_debit))) \
        .group_by(JournalEntryLineItem.id) \
        .having(sa.or_(sa.func.count(offset.c.id) == 0, net_balance != 0))
    net_balances: dict[int, Decimal] \
        = {x.id: x.net_balance
           for x in db.session.execute(select_net_balances).all()}
    line_items: list[JournalEntryLineItem] = JournalEntryLineItem.query \
        .filter(JournalEntryLineItem.id.in_({x for x in net_balances})) \
        .join(JournalEntry) \
        .order_by(JournalEntry.date, JournalEntry.no,
                  JournalEntryLineItem.is_debit, JournalEntryLineItem.no) \
        .options(selectinload(JournalEntryLineItem.currency),
                 selectinload(JournalEntryLineItem.journal_entry)).all()
    for line_item in line_items:
        line_item.net_balance = line_item.amount \
            if net_balances[line_item.id] is None \
            else net_balances[line_item.id]
    return line_items
