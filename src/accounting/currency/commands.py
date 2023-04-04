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
import os
import typing as t

import click
from flask.cli import with_appcontext

from accounting import db, data_dir
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
    existing_codes: set[str] = {x.code for x in Currency.query.all()}

    with open(data_dir / "currencies.csv") as fp:
        data: list[dict[str, str]] = [x for x in csv.DictReader(fp)]
    to_add: list[dict[str, str]] = [x for x in data
                                    if x["code"] not in existing_codes]
    if len(to_add) == 0:
        click.echo("No more currency to add.")
        return

    creator_pk: int = get_user_pk(username)
    currency_data: list[dict[str, t.Any]] = [{"code": x["code"],
                                              "name_l10n": x["name"],
                                              "created_by_id": creator_pk,
                                              "updated_by_id": creator_pk}
                                             for x in to_add]
    locales: list[str] = [x[5:] for x in to_add[0] if x.startswith("l10n-")]
    l10n_data: list[dict[str, str]] = [{"currency_code": x["code"],
                                        "locale": y,
                                        "name": x[f"l10n-{y}"]}
                                       for x in to_add for y in locales]
    db.session.bulk_insert_mappings(Currency, currency_data)
    db.session.bulk_insert_mappings(CurrencyL10n, l10n_data)
    db.session.commit()

    click.echo(F"{len(to_add)} added.  Currencies initialized.")
