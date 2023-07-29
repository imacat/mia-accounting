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
"""The test for the console commands.

"""
import csv
import datetime as dt
import re
import unittest
from typing import Any

import sqlalchemy as sa
from click.testing import Result
from flask import Flask
from flask.testing import FlaskCliRunner
from sqlalchemy.sql.ddl import DropTable

from test_site import db
from testlib import create_test_app


class ConsoleCommandTestCase(unittest.TestCase):
    """The console command test case."""

    def setUp(self) -> None:
        """Sets up the test.
        This is run once per test.

        :return: None.
        """
        self.__app: Flask = create_test_app()
        """The Flask application."""

    def test_init_db(self) -> None:
        """Tests the "accounting-init-db" console command.

        :return: None.
        """
        with self.__app.app_context():
            # Drop every accounting table, to see if accounting-init-db
            # recreates them correctly.
            tables: list[sa.Table] \
                = [db.metadata.tables[x] for x in db.metadata.tables
                   if x.startswith("accounting_")]
            for table in tables:
                db.session.execute(DropTable(table))
            db.session.commit()
            inspector: sa.Inspector = sa.inspect(db.session.connection())
            self.assertEqual(len({x for x in inspector.get_table_names()
                                  if x.startswith("accounting_")}),
                             0)

        runner: FlaskCliRunner = self.__app.test_cli_runner()
        with self.__app.app_context():
            result: Result = runner.invoke(
                args=["accounting-init-db", "-u", "editor"])
        self.assertEqual(result.exit_code, 0,
                         result.output + str(result.exception))
        self.__test_base_account_data()
        self.__test_account_data()
        self.__test_currency_data()

    def __test_base_account_data(self) -> None:
        """Tests the base account data.

        :return: None.
        """
        from accounting import data_dir
        from accounting.models import BaseAccount

        with open(data_dir / "base_accounts.csv") as fp:
            rows: list[dict[str, str]] = list(csv.DictReader(fp))
        data: dict[dict[str, Any]] \
            = {x["code"]: {"code": x["code"],
                           "title": x["title"],
                           "l10n": {y[5:]: x[y]
                                    for y in x if y.startswith("l10n-")}}
               for x in rows}

        with self.__app.app_context():
            accounts: list[BaseAccount] = BaseAccount.query.all()

        self.assertEqual(len(accounts), len(data))
        for account in accounts:
            self.assertIn(account.code, data)
            self.assertEqual(account.title_l10n.lower(),
                             data[account.code]["title"].lower())
            self.__test_title_case(account.title_l10n)
            l10n: dict[str, str] = {x.locale: x.title for x in account.l10n}
            self.assertEqual(len(l10n), len(data[account.code]["l10n"]))
            for locale in l10n:
                self.assertIn(locale, data[account.code]["l10n"])
                self.assertEqual(l10n[locale],
                                 data[account.code]["l10n"][locale])

    def __test_title_case(self, s: str) -> None:
        """Tests the case of a base account title.

        :param s: The base account title.
        :return: None.
        """
        from accounting.utils.title_case import MINOR_WORDS

        self.assertTrue(s[0].isupper(), s)
        for word in re.findall(r"\w+", s):
            if len(word) >= 4:
                self.assertTrue(word.istitle(), s)
            elif word in MINOR_WORDS:
                self.assertTrue(word.islower(), s)
            else:
                self.assertTrue(word.istitle(), s)

    def __test_account_data(self) -> None:
        """Tests the account data.

        :return: None.
        """
        from accounting.models import BaseAccount, Account, AccountL10n

        with self.__app.app_context():
            bases: list[BaseAccount] = BaseAccount.query\
                .filter(sa.func.char_length(BaseAccount.code) == 4).all()
            accounts: list[Account] = Account.query.all()
            l10n: list[AccountL10n] = AccountL10n.query.all()

        self.assertEqual({x.code for x in bases},
                         {x.base_code for x in accounts})
        self.assertEqual(len(accounts), len(bases))
        self.assertEqual(len(l10n), len(bases) * 2)
        base_dict: dict[str, BaseAccount] = {x.code: x for x in bases}
        for account in accounts:
            base: BaseAccount = base_dict[account.base_code]
            self.assertEqual(account.no, 1)
            self.assertEqual(account.title_l10n, base.title_l10n)
            self.assertEqual({x.locale: x.title for x in account.l10n},
                             {x.locale: x.title for x in base.l10n})

    def __test_currency_data(self) -> None:
        """Tests the currency data.

        :return: None.
        """
        from accounting import data_dir
        from accounting.models import Currency

        with open(data_dir / "currencies.csv") as fp:
            data: dict[dict[str, Any]] \
                = {x["code"]: {"code": x["code"],
                               "name": x["name"],
                               "l10n": {y[5:]: x[y]
                                        for y in x if y.startswith("l10n-")}}
                   for x in csv.DictReader(fp)}

        with self.__app.app_context():
            currencies: list[Currency] = Currency.query.all()

        self.assertEqual(len(currencies), len(data))
        for currency in currencies:
            self.assertIn(currency.code, data)
            self.assertEqual(currency.name_l10n, data[currency.code]["name"])
            l10n: dict[str, str] = {x.locale: x.name for x in currency.l10n}
            self.assertEqual(len(l10n), len(data[currency.code]["l10n"]))
            for locale in l10n:
                self.assertIn(locale, data[currency.code]["l10n"])
                self.assertEqual(l10n[locale],
                                 data[currency.code]["l10n"][locale])

    def test_titleize(self) -> None:
        """Tests the "accounting-titleize" console command.

        :return: None.
        """
        from accounting.models import BaseAccount, Account
        from accounting.utils.random_id import new_id
        from accounting.utils.user import get_user_pk
        runner: FlaskCliRunner = self.__app.test_cli_runner()

        with self.__app.app_context():
            # Resets the accounts.
            tables: list[sa.Table] \
                = [db.metadata.tables[x] for x in db.metadata.tables
                   if x.startswith("accounting_")]
            for table in tables:
                db.session.execute(DropTable(table))
            db.session.commit()
            inspector: sa.Inspector = sa.inspect(db.session.connection())
            self.assertEqual(len({x for x in inspector.get_table_names()
                                  if x.startswith("accounting_")}),
                             0)
            result: Result = runner.invoke(
                args=["accounting-init-db", "-u", "editor"])
            self.assertEqual(result.exit_code, 0,
                             result.output + str(result.exception))

            # Turns the titles into lowercase.
            for base in BaseAccount.query:
                base.title_l10n = base.title_l10n.lower()
            for account in Account.query:
                account.title_l10n = account.title_l10n.lower()
                account.created_at \
                    = account.created_at - dt.timedelta(seconds=5)
                account.updated_at = account.created_at

            # Adds a custom account.
            custom_title = "MBK Bank"
            creator_pk: int = get_user_pk("editor")
            new_account: Account = Account(
                id=new_id(Account),
                base_code="1112",
                no="2",
                title_l10n=custom_title,
                is_need_offset=False,
                created_by_id=creator_pk,
                updated_by_id=creator_pk)
            db.session.add(new_account)
            db.session.commit()

            result: Result = runner.invoke(
                args=["accounting-titleize", "-u", "editor"])
            self.assertEqual(result.exit_code, 0,
                             result.output + str(result.exception))
            for base in BaseAccount.query:
                self.__test_title_case(base.title_l10n)
            for account in Account.query:
                if account.id != new_account.id:
                    self.__test_title_case(account.title_l10n)
                    self.assertNotEqual(account.created_at, account.updated_at)
                else:
                    self.assertEqual(account.title_l10n, custom_title)

            db.session.delete(new_account)
            db.session.commit()
