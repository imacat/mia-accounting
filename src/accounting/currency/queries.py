# The Mia! Accounting Project.
# Author: imacat@mail.imacat.idv.tw (imacat), 2023/2/6

#  Copyright (c) 2023-2026 imacat.
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
"""The queries for the currency management.

"""
import sqlalchemy as sa
from flask import request

from .. import db
from ..models import Currency, CurrencyL10n
from ..utils.query import parse_query_keywords


def get_currency_query() -> list[Currency]:
    """Returns the base accounts, optionally filtered by the query.

    :return: The base accounts.
    """
    keywords: list[str] = parse_query_keywords(request.args.get("q"))
    if len(keywords) == 0:
        return db.session.scalars(
            sa.select(Currency).order_by(Currency.code)).unique().all()
    conditions: list[sa.ColumnElement[bool]] = []
    for k in keywords:
        l10n: list[CurrencyL10n] = db.session.scalars(
            sa.select(CurrencyL10n)
            .where(CurrencyL10n.name.icontains(k))).all()
        l10n_matches: set[str] = {x.account_code for x in l10n}
        conditions.append(sa.or_(Currency.code.icontains(k),
                                 Currency.name_l10n.icontains(k),
                                 Currency.code.in_(l10n_matches)))
    return db.session.scalars(
        sa.select(Currency).where(*conditions)
        .order_by(Currency.code)).unique().all()
