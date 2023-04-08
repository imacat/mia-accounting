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
"""The queries for the unmatched offset management.

"""
import sqlalchemy as sa

from accounting import db
from accounting.models import Account, JournalEntryLineItem


def get_accounts_with_unmatched_offsets() -> list[Account]:
    """Returns the accounts with unmatched offsets.

    :return: The accounts with unmatched offsets, with the "count" property set
        to the number of unmatched offsets.
    """
    count_func: sa.Label \
        = sa.func.count(JournalEntryLineItem.id).label("count")
    select: sa.Select = sa.select(Account.id, count_func)\
        .select_from(Account).join(JournalEntryLineItem, isouter=True)\
        .filter(Account.is_need_offset,
                JournalEntryLineItem.original_line_item_id.is_(None),
                sa.or_(sa.and_(Account.base_code.startswith("2"),
                               JournalEntryLineItem.is_debit),
                       sa.and_(Account.base_code.startswith("1"),
                               sa.not_(JournalEntryLineItem.is_debit))))\
        .group_by(Account.id)\
        .having(count_func > 0)
    counts: dict[int, int] \
        = {x.id: x.count for x in db.session.execute(select)}
    accounts: list[Account] = Account.query.filter(Account.id.in_(counts))\
        .order_by(Account.base_code, Account.no).all()
    for account in accounts:
        account.count = counts[account.id]
    return accounts
