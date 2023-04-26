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
"""The console commands for the account management.

"""
from secrets import randbelow
from typing import Any

import click
import sqlalchemy as sa

from accounting import db
from accounting.models import BaseAccount, Account, AccountL10n
from accounting.utils.user import get_user_pk

AccountData = tuple[int, str, int, str, str, str, bool]
"""The format of the account data, as a list of (ID, base account code, number,
English, Traditional Chinese, Simplified Chinese, is-need-offset) tuples."""


def init_accounts_command(username: str) -> None:
    """Initializes the accounts."""
    creator_pk: int = get_user_pk(username)

    bases: list[BaseAccount] = BaseAccount.query\
        .filter(db.func.length(BaseAccount.code) == 4)\
        .order_by(BaseAccount.code).all()
    if len(bases) == 0:
        raise click.Abort

    existing: list[Account] = Account.query.all()

    existing_base_code: set[str] = {x.base_code for x in existing}
    bases_to_add: list[BaseAccount] = [x for x in bases
                                       if x.code not in existing_base_code]
    if len(bases_to_add) == 0:
        return

    existing_id: set[int] = {x.id for x in existing}

    def get_new_id() -> int:
        """Returns a new random account ID.

        :return: The newly-generated random account ID.
        """
        while True:
            new_id: int = 100000000 + randbelow(900000000)
            if new_id not in existing_id:
                existing_id.add(new_id)
                return new_id

    data: list[dict[str, Any]] = []
    l10n_data: list[dict[str, Any]] = []
    for base in bases_to_add:
        l10n: dict[str, str] = {x.locale: x.title for x in base.l10n}
        account_id: int = get_new_id()
        data.append({"id": account_id,
                     "base_code": base.code,
                     "no": 1,
                     "title_l10n": base.title_l10n,
                     "is_need_offset": __is_need_offset(base.code),
                     "created_by_id": creator_pk,
                     "updated_by_id": creator_pk})
        for locale in {"zh_Hant", "zh_Hans"}:
            l10n_data.append({"account_id": account_id,
                              "locale": locale,
                              "title": l10n[locale]})
    db.session.execute(sa.insert(Account), data)
    db.session.execute(sa.insert(AccountL10n), l10n_data)


def __is_need_offset(base_code: str) -> bool:
    """Checks that whether journal entry line items in the account need offset.

    :param base_code: The code of the base account.
    :return: True if journal entry line items in the account need offset, or
        False otherwise.
    """
    # Assets
    if base_code[0] == "1":
        if base_code[:3] in {"113", "114", "118", "184", "186"}:
            return True
        if base_code in {"1286", "1411", "1421", "1431", "1441", "1511",
                         "1521", "1581", "1611", "1851"}:
            return True
        return False
    # Liabilities
    if base_code[0] == "2":
        if base_code in {"2111", "2114", "2284", "2293", "2861"}:
            return False
        return True
    # Only assets and liabilities need offset
    return False
