# The Mia! Accounting Project.
# Author: imacat@mail.imacat.idv.tw (imacat), 2023/4/10

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
"""The console commands.

"""
import os

import click
from flask.cli import with_appcontext

from accounting import db
from accounting.account import init_accounts_command
from accounting.base_account import init_base_accounts_command
from accounting.currency import init_currencies_command
from accounting.models import BaseAccount, Account
from accounting.utils.title_case import title_case
from accounting.utils.user import has_user, get_user_pk
import sqlalchemy as sa


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


@click.command("accounting-init-db")
@click.option("-u", "--username", metavar="USERNAME", prompt=True,
              help="The username.", callback=__validate_username,
              default=lambda: os.getlogin())
@click.option("--skip-accounts", is_flag=True, default=False,
              help="Skip initializing accounts.")
@click.option("--skip-currencies", is_flag=True, default=False,
              help="Skip initializing currencies.")
@with_appcontext
def init_db_command(username: str, skip_accounts: bool,
                    skip_currencies: bool) -> None:
    """Initializes the accounting database."""
    db.create_all()
    init_base_accounts_command()
    if not skip_accounts:
        init_accounts_command(username)
    if not skip_currencies:
        init_currencies_command(username)
    db.session.commit()
    click.echo("Accounting database initialized.")


@click.command("accounting-titleize")
@click.option("-u", "--username", metavar="USERNAME", prompt=True,
              help="The username.", callback=__validate_username,
              default=lambda: os.getlogin())
@with_appcontext
def titleize_command(username: str) -> None:
    """Capitalize the account titles."""
    updater_pk: int = get_user_pk(username)
    updated: int = 0
    for base in BaseAccount.query:
        new_title: str = title_case(base.title_l10n)
        if base.title_l10n != new_title:
            base.title_l10n = new_title
            updated = updated + 1
    for account in Account.query:
        if account.title_l10n.lower() == account.base.title_l10n.lower():
            new_title: str = title_case(account.title_l10n)
            if account.title_l10n != new_title:
                account.title_l10n = new_title
                account.updated_at = sa.func.now()
                account.updated_by_id = updater_pk
                updated = updated + 1
    if updated == 0:
        click.echo("All account titles were already capitalized.")
        return
    db.session.commit()
    click.echo(f"{updated} account titles capitalized.")
