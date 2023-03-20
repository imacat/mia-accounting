# The Mia! Accounting Flask Project.
# Author: imacat@mail.imacat.idv.tw (imacat), 2023/2/19

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
"""The path converters for the voucher management.

"""
from datetime import date

from flask import abort
from sqlalchemy.orm import selectinload
from werkzeug.routing import BaseConverter

from accounting.models import Voucher, JournalEntryLineItem
from accounting.utils.voucher_types import VoucherType


class VoucherConverter(BaseConverter):
    """The voucher converter to convert the voucher ID from and to the
    corresponding voucher in the routes."""

    def to_python(self, value: str) -> Voucher:
        """Converts a voucher ID to a voucher.

        :param value: The voucher ID.
        :return: The corresponding voucher.
        """
        voucher: Voucher | None = Voucher.query.join(JournalEntryLineItem)\
            .filter(Voucher.id == value)\
            .options(selectinload(Voucher.line_items)
                     .selectinload(JournalEntryLineItem.offsets)
                     .selectinload(JournalEntryLineItem.voucher))\
            .first()
        if voucher is None:
            abort(404)
        return voucher

    def to_url(self, value: Voucher) -> str:
        """Converts a voucher to its ID.

        :param value: The voucher.
        :return: The ID.
        """
        return str(value.id)


class VoucherTypeConverter(BaseConverter):
    """The voucher converter to convert the voucher type ID from and to the
    corresponding voucher type in the routes."""

    def to_python(self, value: str) -> VoucherType:
        """Converts a voucher ID to a voucher.

        :param value: The voucher ID.
        :return: The corresponding voucher type.
        """
        type_dict: dict[str, VoucherType] = {x.value: x for x in VoucherType}
        voucher_type: VoucherType | None = type_dict.get(value)
        if voucher_type is None:
            abort(404)
        return voucher_type

    def to_url(self, value: VoucherType) -> str:
        """Converts a voucher type to its ID.

        :param value: The voucher type.
        :return: The ID.
        """
        return str(value.value)


class DateConverter(BaseConverter):
    """The date converter to convert the ISO date from and to the
    corresponding date in the routes."""

    def to_python(self, value: str) -> date:
        """Converts an ISO date to a date.

        :param value: The ISO date.
        :return: The corresponding date.
        """
        try:
            return date.fromisoformat(value)
        except ValueError:
            abort(404)

    def to_url(self, value: date) -> str:
        """Converts a date to its ISO date.

        :param value: The date.
        :return: The ISO date.
        """
        return value.isoformat()
