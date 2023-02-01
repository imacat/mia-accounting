# The Mia! Accounting Flask Project.
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
import os
import re
from secrets import randbelow

import click
from flask.cli import with_appcontext

from accounting.database import db
from accounting.models import BaseAccount, Account, AccountL10n
from accounting.utils.user import has_user, get_user_pk

AccountData = tuple[int, str, int, str, str, str, bool]
"""The format of the account data, as a list of (ID, base account code, number,
English, Traditional Chinese, Simplified Chinese, is-offset-needed) tuples."""


def __validate_username(ctx: click.core.Context, param: click.core.Option,
                        value: str) -> str:
    """Validates the username for the click console command.

    :param ctx: The console command context.
    :param param: The console command option.
    :param value: The username.
    :raise click.BadParameter: When validation fails.
    :return: The username.
    """
    value = value.strip()
    if value == "":
        raise click.BadParameter("Username empty.")
    if not has_user(value):
        raise click.BadParameter(f"User {value} does not exist.")
    return value


@click.command("accounting-init-accounts")
@click.option("-u", "--username", metavar="USERNAME", prompt=True,
              help="The username.", callback=__validate_username,
              default=lambda: os.getlogin())
@with_appcontext
def init_accounts_command(username: str) -> None:
    """Initializes the accounts."""
    creator_pk: int = get_user_pk(username)

    bases: list[BaseAccount] = BaseAccount.query\
        .filter(db.func.length(BaseAccount.code) == 4)\
        .order_by(BaseAccount.code).all()
    if len(bases) == 0:
        click.echo("Please initialize the base accounts with "
                   "\"flask accounting-init-base\" first.")
        raise click.Abort

    existing: list[Account] = Account.query.all()

    existing_base_code: set[str] = {x.base_code for x in existing}
    bases_to_add: list[BaseAccount] = [x for x in bases
                                       if x.code not in existing_base_code]
    if len(bases_to_add) == 0:
        click.echo("No more account to import.")
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

    data: list[AccountData] = []
    for base in bases_to_add:
        l10n: dict[str, str] = {x.locale: x.title for x in base.l10n}
        is_offset_needed: bool = True if re.match("^[12]1[34]", base.code) \
            else False
        data.append((get_new_id(), base.code, 1, base.title_l10n,
                     l10n["zh_Hant"], l10n["zh_Hans"], is_offset_needed))
    __add_accounting_accounts(data, creator_pk)
    click.echo(F"{len(data)} added.  Accounting accounts initialized.")


def __add_accounting_accounts(data: list[AccountData], creator_pk: int)\
        -> None:
    """Adds the accounts.

    :param data: A list of (base code, number, title) tuples.
    :param creator_pk: The primary key of the creator.
    :return: None.
    """
    accounts: list[Account] = [Account(id=x[0],
                                       base_code=x[1],
                                       no=x[2],
                                       title_l10n=x[3],
                                       is_offset_needed=x[6],
                                       created_by_id=creator_pk,
                                       updated_by_id=creator_pk)
                               for x in data]
    l10n: list[AccountL10n] = [AccountL10n(account_id=x[0],
                                           locale=y[0],
                                           title=y[1])
                               for x in data
                               for y in (("zh_Hant", x[4]), ("zh_Hans", x[5]))]
    db.session.bulk_save_objects(accounts)
    db.session.bulk_save_objects(l10n)
    db.session.commit()
