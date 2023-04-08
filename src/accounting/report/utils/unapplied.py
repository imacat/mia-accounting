# The Mia! Accounting Project.
# Author: imacat@mail.imacat.idv.tw (imacat), 2023/4/7

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
import sqlalchemy as sa

from accounting.journal_entry.utils.offset_alias import offset_alias
from accounting.models import Account, JournalEntryLineItem
from accounting.utils.cast import be


def get_accounts_with_unapplied() -> list[Account]:
    """Returns the accounts with unapplied original line items.

    :return: The accounts with unapplied original line items.
    """
    offset: sa.Alias = offset_alias()
    net_balance: sa.Label \
        = (JournalEntryLineItem.amount
           + sa.func.sum(sa.case(
                (be(offset.c.is_debit == JournalEntryLineItem.is_debit),
                 offset.c.amount),
                else_=-offset.c.amount))).label("net_balance")
    select_unapplied: sa.Select \
        = sa.select(JournalEntryLineItem.id)\
        .join(Account)\
        .join(offset, be(JournalEntryLineItem.id
                         == offset.c.original_line_item_id),
              isouter=True)\
        .filter(Account.is_need_offset,
                sa.or_(sa.and_(Account.base_code.startswith("2"),
                               sa.not_(JournalEntryLineItem.is_debit)),
                       sa.and_(Account.base_code.startswith("1"),
                               JournalEntryLineItem.is_debit)))\
        .group_by(JournalEntryLineItem.id)\
        .having(sa.or_(sa.func.count(offset.c.id) == 0, net_balance != 0))

    count_func: sa.Function \
        = sa.func.count(JournalEntryLineItem.id)
    select: sa.Select = sa.select(Account.id)\
        .join(JournalEntryLineItem, isouter=True)\
        .filter(JournalEntryLineItem.id.in_(select_unapplied))\
        .group_by(Account.id)\
        .having(count_func > 0)
    return Account.query.filter(Account.id.in_(select))\
        .order_by(Account.base_code, Account.no).all()
