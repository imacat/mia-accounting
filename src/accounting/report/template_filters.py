# The Mia! Accounting Project.
# Author: imacat@mail.imacat.idv.tw (imacat), 2023/3/7

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
"""The template filters for the reports.

"""
from decimal import Decimal

from accounting.template_filters import format_amount as core_format_amount


def format_amount(value: Decimal | None) -> str | None:
    """Formats an amount for the report.

    :param value: The amount.
    :return: The formatted amount text.
    """
    if value is None:
        return ""
    is_negative: bool = value < 0
    formatted: str = core_format_amount(abs(value))
    if is_negative:
        formatted = f"({formatted})"
    return formatted
