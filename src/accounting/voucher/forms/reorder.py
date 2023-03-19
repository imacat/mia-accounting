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
"""The reorder forms for the voucher management.

"""
from datetime import date

import sqlalchemy as sa
from flask import request

from accounting import db
from accounting.models import Voucher


def sort_vouchers_in(voucher_date: date, exclude: int | None = None) -> None:
    """Sorts the vouchers under a date after changing the date or deleting
    a voucher.

    :param voucher_date: The date of the voucher.
    :param exclude: The voucher ID to exclude.
    :return: None.
    """
    conditions: list[sa.BinaryExpression] = [Voucher.date == voucher_date]
    if exclude is not None:
        conditions.append(Voucher.id != exclude)
    vouchers: list[Voucher] = Voucher.query\
        .filter(*conditions)\
        .order_by(Voucher.no).all()
    for i in range(len(vouchers)):
        if vouchers[i].no != i + 1:
            vouchers[i].no = i + 1


class VoucherReorderForm:
    """The form to reorder the vouchers."""

    def __init__(self, voucher_date: date):
        """Constructs the form to reorder the vouchers in a day.

        :param voucher_date: The date.
        """
        self.date: date = voucher_date
        self.is_modified: bool = False

    def save_order(self) -> None:
        """Saves the order of the account.

        :return:
        """
        vouchers: list[Voucher] = Voucher.query\
            .filter(Voucher.date == self.date).all()

        # Collects the specified order.
        orders: dict[Voucher, int] = {}
        for voucher in vouchers:
            if f"{voucher.id}-no" in request.form:
                try:
                    orders[voucher] = int(request.form[f"{voucher.id}-no"])
                except ValueError:
                    pass

        # Missing and invalid orders are appended to the end.
        missing: list[Voucher] \
            = [x for x in vouchers if x not in orders]
        if len(missing) > 0:
            next_no: int = 1 if len(orders) == 0 else max(orders.values()) + 1
            for voucher in missing:
                orders[voucher] = next_no

        # Sort by the specified order first, and their original order.
        vouchers.sort(key=lambda x: (orders[x], x.no))

        # Update the orders.
        with db.session.no_autoflush:
            for i in range(len(vouchers)):
                if vouchers[i].no != i + 1:
                    vouchers[i].no = i + 1
                    self.is_modified = True
