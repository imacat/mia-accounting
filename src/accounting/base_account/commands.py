# The Mia! Accounting Project.
# Author: imacat@mail.imacat.idv.tw (imacat), 2023/1/25

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
"""The console commands for the base account management.

"""
import csv

import click
from flask.cli import with_appcontext

from accounting import data_dir
from accounting import db
from accounting.models import BaseAccount, BaseAccountL10n


@click.command("accounting-init-base")
@with_appcontext
def init_base_accounts_command() -> None:
    """Initializes the base accounts."""
    if BaseAccount.query.first() is not None:
        click.echo("Base accounts already exist.")
        raise click.Abort

    with open(data_dir / "base_accounts.csv") as fp:
        data: list[dict[str, str]] = [x for x in csv.DictReader(fp)]
    account_data: list[dict[str, str]] = [{"code": x["code"],
                                           "title_l10n": x["title"]}
                                          for x in data]
    locales: list[str] = [x[5:] for x in data[0] if x.startswith("l10n-")]
    l10n_data: list[dict[str, str]] = [{"account_code": x["code"],
                                        "locale": y,
                                        "title": x[f"l10n-{y}"]}
                                       for x in data for y in locales]
    db.session.bulk_insert_mappings(BaseAccount, account_data)
    db.session.bulk_insert_mappings(BaseAccountL10n, l10n_data)
    db.session.commit()
    click.echo("Base accounts initialized.")
