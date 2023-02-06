# The Mia! Accounting Flask Project.
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
import os

import click
from flask.cli import with_appcontext

from accounting.database import db
from accounting.models import Currency, CurrencyL10n
from accounting.utils.user import has_user, get_user_pk

CurrencyData = tuple[str, str, str, str]


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


@click.command("accounting-init-currencies")
@click.option("-u", "--username", metavar="USERNAME", prompt=True,
              help="The username.", callback=__validate_username,
              default=lambda: os.getlogin())
@with_appcontext
def init_currencies_command(username: str) -> None:
    """Initializes the currencies."""
    data: list[CurrencyData] = [
        ("TWD", "New Taiwan dollar", "新臺幣", "新台币"),
        ("USD", "United States dollar", "美元", "美元"),
    ]
    creator_pk: int = get_user_pk(username)
    existing: list[Currency] = Currency.query.all()
    existing_code: set[str] = {x.code for x in existing}
    to_add: list[CurrencyData] = [x for x in data if x[0] not in existing_code]
    if len(to_add) == 0:
        click.echo("No more currency to add.")
        return

    db.session.bulk_save_objects(
        [Currency(code=x[0], name_l10n=x[1],
                  created_by_id=creator_pk, updated_by_id=creator_pk)
         for x in data])
    db.session.bulk_save_objects(
        [CurrencyL10n(currency_code=x[0], locale=y[0], name=y[1])
         for x in data for y in (("zh_Hant", x[2]), ("zh_Hans", x[3]))])
    db.session.commit()

    click.echo(F"{len(to_add)} added.  Currencies initialized.")
