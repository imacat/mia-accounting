# The Mia! Accounting Project.
# Author: imacat@mail.imacat.idv.tw (imacat), 2023/1/30

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
"""The queries for the account management.

"""
import sqlalchemy as sa
from flask import request

from accounting.locale import gettext
from accounting.models import Account, AccountL10n
from accounting.utils.query import parse_query_keywords


def get_account_query() -> list[Account]:
    """Returns the accounts, optionally filtered by the query.

    :return: The accounts.
    """
    keywords: list[str] = parse_query_keywords(request.args.get("q"))
    if len(keywords) == 0:
        return Account.query.order_by(Account.base_code, Account.no).all()
    code: sa.BinaryExpression = Account.base_code + "-" \
        + sa.func.substr("000" + sa.cast(Account.no, sa.String),
                         sa.func.char_length(sa.cast(Account.no,
                                                     sa.String)) + 1)
    conditions: list[sa.BinaryExpression] = []
    for k in keywords:
        l10n: list[AccountL10n] = AccountL10n.query\
            .filter(AccountL10n.title.icontains(k)).all()
        l10n_matches: set[str] = {x.account_id for x in l10n}
        sub_conditions: list[sa.BinaryExpression] \
            = [Account.base_code.contains(k),
               Account.title_l10n.icontains(k),
               code.contains(k),
               Account.id.in_(l10n_matches)]
        if k in gettext("Needs Offset"):
            sub_conditions.append(Account.is_need_offset)
        conditions.append(sa.or_(*sub_conditions))

    return Account.query.filter(*conditions)\
        .order_by(Account.base_code, Account.no).all()
