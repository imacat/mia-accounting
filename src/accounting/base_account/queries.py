# The Mia! Accounting Project.
# Author: imacat@mail.imacat.idv.tw (imacat), 2023/1/26

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
"""The queries for the base account management.

"""
import sqlalchemy as sa
from flask import request

from accounting.models import BaseAccount, BaseAccountL10n
from accounting.utils.query import parse_query_keywords


def get_base_account_query() -> list[BaseAccount]:
    """Returns the base accounts, optionally filtered by the query.

    :return: The base accounts.
    """
    keywords: list[str] = parse_query_keywords(request.args.get("q"))
    if len(keywords) == 0:
        return BaseAccount.query.order_by(BaseAccount.code).all()
    conditions: list[sa.BinaryExpression] = []
    for k in keywords:
        l10n: list[BaseAccountL10n] = BaseAccountL10n.query\
            .filter(BaseAccountL10n.title.icontains(k)).all()
        l10n_matches: set[str] = {x.account_code for x in l10n}
        conditions.append(sa.or_(BaseAccount.code.contains(k),
                                 BaseAccount.title_l10n.icontains(k),
                                 BaseAccount.code.in_(l10n_matches)))
    return BaseAccount.query.filter(*conditions)\
        .order_by(BaseAccount.code).all()
