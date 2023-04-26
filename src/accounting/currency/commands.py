# The Mia! Accounting Project.
# Author: imacat@mail.imacat.idv.tw (imacat), 2023/2/6

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
"""The console commands for the currency management.

"""
import csv
from typing import Any

import sqlalchemy as sa

from accounting import db, data_dir
from accounting.models import Currency, CurrencyL10n
from accounting.utils.user import get_user_pk


def init_currencies_command(username: str) -> None:
    """Initializes the currencies."""
    existing_codes: set[str] = {x.code for x in Currency.query.all()}

    with open(data_dir / "currencies.csv") as fp:
        data: list[dict[str, str]] = [x for x in csv.DictReader(fp)]
    to_add: list[dict[str, str]] = [x for x in data
                                    if x["code"] not in existing_codes]
    if len(to_add) == 0:
        return

    creator_pk: int = get_user_pk(username)
    currency_data: list[dict[str, Any]] = [{"code": x["code"],
                                            "name_l10n": x["name"],
                                            "created_by_id": creator_pk,
                                            "updated_by_id": creator_pk}
                                           for x in to_add]
    locales: list[str] = [x[5:] for x in to_add[0] if x.startswith("l10n-")]
    l10n_data: list[dict[str, str]] = [{"currency_code": x["code"],
                                        "locale": y,
                                        "name": x[f"l10n-{y}"]}
                                       for x in to_add for y in locales]
    db.session.execute(sa.insert(Currency), currency_data)
    db.session.execute(sa.insert(CurrencyL10n), l10n_data)
