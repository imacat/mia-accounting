# The Mia! Accounting Demonstration Website.
# Author: imacat@mail.imacat.idv.tw (imacat), 2023/4/12

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
"""The data reset for the Mia! Accounting demonstration website.

"""
import csv
import typing as t
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import sqlalchemy as sa
from flask import Flask, Blueprint, url_for, flash, redirect, session, \
    render_template
from flask_babel import lazy_gettext

from accounting.utils.cast import s
from . import db
from .auth import User, current_user

bp: Blueprint = Blueprint("reset", __name__, url_prefix="/")


@bp.get("reset", endpoint="reset-page")
def reset() -> str:
    """Resets the sample data.

    :return: Redirection to the accounting application.
    """
    return render_template("reset.html")


@bp.post("sample", endpoint="sample")
def reset_sample() -> redirect:
    """Resets the sample data.

    :return: Redirection to the accounting application.
    """
    __reset_database()
    __populate_sample_data()
    flash(s(lazy_gettext(
        "The sample data are emptied and reset successfully.")), "success")
    return redirect(url_for("accounting-report.default"))


@bp.post("reset", endpoint="clean-up")
def clean_up() -> redirect:
    """Clean-up the database data.

    :return: Redirection to the accounting application.
    """
    __reset_database()
    db.session.commit()
    flash(s(lazy_gettext("The database is emptied successfully.")), "success")
    return redirect(url_for("accounting-report.default"))


def __populate_sample_data() -> None:
    """Populates the sample data.

    :return: None.
    """
    from accounting.models import Account, JournalEntry, JournalEntryLineItem
    data_dir: Path = Path(__file__).parent / "data"
    today: date = date.today()
    user: User | None = current_user()
    assert user is not None

    def filter_journal_entry(data: dict[str, t.Any]) -> dict[str, t.Any]:
        """Filters the journal entry data from JSON.

        :param data: The journal entry data.
        :return: The journal entry data from JSON.
        """
        data = data.copy()
        data["id"] = int(data["id"])
        data["date"] = today - timedelta(days=int(data["date"]))
        data["no"] = int(data["no"])
        if data["note"] == "":
            data["note"] = None
        data["created_by_id"] = user.id
        data["updated_by_id"] = user.id
        return data

    def filter_line_item(data: dict[str, t.Any]) -> dict[str, t.Any]:
        """Filters the journal entry line item data from JSON.

        :param data: The journal entry line item data.
        :return: The journal entry line item data from JSON.
        """
        data = data.copy()
        data["id"] = int(data["id"])
        data["journal_entry_id"] = int(data["journal_entry_id"])
        if data["original_line_item_id"] == "":
            data["original_line_item_id"] = None
        else:
            data["original_line_item_id"] = int(data["original_line_item_id"])
        data["is_debit"] = bool(data["is_debit"])
        data["no"] = int(data["no"])
        data["account_id"] = Account.find_by_code(data["account_id"]).id
        if data["description"] == "":
            data["description"] = None
        data["amount"] = Decimal(data["amount"])
        return data

    def import_journal_entries(file: Path) -> None:
        """Imports the journal entries.

        :param file: The CSV file.
        :return: None.
        """
        with open(file) as fp:
            reader: csv.DictReader = csv.DictReader(fp)
            db.session.execute(sa.insert(JournalEntry),
                               [filter_journal_entry(x) for x in reader])

    def import_line_items(file: Path) -> None:
        """Imports the journal entry line items.

        :param file: The CSV file.
        :return: None.
        """
        with open(file) as fp:
            reader: csv.DictReader = csv.DictReader(fp)
            db.session.execute(sa.insert(JournalEntryLineItem),
                               [filter_line_item(x) for x in reader])

    import_journal_entries(data_dir / "sample-journal_entries.csv")
    import_line_items(data_dir / "sample-journal_entry_line_items.csv")
    db.session.commit()


def __reset_database() -> None:
    """Resets the database.

    :return: None.
    """
    from accounting.models import Currency, CurrencyL10n, BaseAccount, \
        BaseAccountL10n, Account, AccountL10n, JournalEntry, \
        JournalEntryLineItem
    from accounting.base_account import init_base_accounts_command
    from accounting.account import init_accounts_command
    from accounting.currency import init_currencies_command

    JournalEntryLineItem.query.delete()
    JournalEntry.query.delete()
    CurrencyL10n.query.delete()
    Currency.query.delete()
    AccountL10n.query.delete()
    Account.query.delete()
    BaseAccountL10n.query.delete()
    BaseAccount.query.delete()
    init_base_accounts_command()
    init_accounts_command(session["user"])
    init_currencies_command(session["user"])


def init_app(app: Flask) -> None:
    """Initialize the localization.

    :param app: The Flask application.
    :return: None.
    """
    app.register_blueprint(bp)
