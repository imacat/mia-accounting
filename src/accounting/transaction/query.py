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
"""The transaction query.

"""
from datetime import datetime

import sqlalchemy as sa
from flask import request

from accounting.models import Transaction
from accounting.utils.query import parse_query_keywords


def get_transaction_query() -> list[Transaction]:
    """Returns the transactions, optionally filtered by the query.

    :return: The transactions.
    """
    keywords: list[str] = parse_query_keywords(request.args.get("q"))
    if len(keywords) == 0:
        return Transaction.query\
            .order_by(Transaction.date, Transaction.no).all()
    conditions: list[sa.BinaryExpression] = []
    for k in keywords:
        sub_conditions: list[sa.BinaryExpression] \
            = [Transaction.note.contains(k)]
        date: datetime
        try:
            date = datetime.strptime(k, "%Y")
            sub_conditions.append(
                sa.extract("year", Transaction.date) == date.year)
        except ValueError:
            pass
        try:
            date = datetime.strptime(k, "%Y/%m")
            sub_conditions.append(sa.and_(
                sa.extract("year", Transaction.date) == date.year,
                sa.extract("month", Transaction.date) == date.month))
        except ValueError:
            pass
        try:
            date = datetime.strptime(f"2000/{k}", "%Y/%m/%d")
            sub_conditions.append(sa.and_(
                sa.extract("month", Transaction.date) == date.month,
                sa.extract("day", Transaction.date) == date.day))
        except ValueError:
            pass
        conditions.append(sa.or_(*sub_conditions))
    return Transaction.query.filter(*conditions)\
        .order_by(Transaction.date, Transaction.no).all()
