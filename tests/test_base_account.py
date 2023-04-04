# The Mia! Accounting Project.
# Author: imacat@mail.imacat.idv.tw (imacat), 2023/1/26

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
"""The test for the base account management.

"""
import csv
import typing as t
import unittest

import httpx
from click.testing import Result
from flask import Flask
from flask.testing import FlaskCliRunner

from testlib import create_test_app, get_client

LIST_URI: str = "/accounting/base-accounts"
"""The list URI."""
DETAIL_URI: str = "/accounting/base-accounts/1111"
"""The detail URI."""


class BaseAccountCommandTestCase(unittest.TestCase):
    """The base account console command test case."""

    def setUp(self) -> None:
        """Sets up the test.
        This is run once per test.

        :return: None.
        """
        from accounting.models import BaseAccount, BaseAccountL10n
        self.app: Flask = create_test_app()

        runner: FlaskCliRunner = self.app.test_cli_runner()
        with self.app.app_context():
            result: Result = runner.invoke(args="init-db")
            self.assertEqual(result.exit_code, 0)
            BaseAccountL10n.query.delete()
            BaseAccount.query.delete()

    def test_init(self) -> None:
        """Tests the "accounting-init-base" console command.

        :return: None.
        """
        from accounting import data_dir
        from accounting.models import BaseAccount

        with open(data_dir / "base_accounts.csv") as fp:
            data: dict[dict[str, t.Any]] \
                = {x["code"]: {"code": x["code"],
                               "title": x["title"],
                               "l10n": {y[5:]: x[y]
                                        for y in x if y.startswith("l10n-")}}
                   for x in csv.DictReader(fp)}

        runner: FlaskCliRunner = self.app.test_cli_runner()
        result: Result = runner.invoke(args="accounting-init-base")
        self.assertEqual(result.exit_code, 0)
        with self.app.app_context():
            accounts: list[BaseAccount] = BaseAccount.query.all()

        self.assertEqual(len(accounts), len(data))
        for account in accounts:
            self.assertIn(account.code, data)
            self.assertEqual(account.title_l10n, data[account.code]["title"])
            l10n: dict[str, str] = {x.locale: x.title for x in account.l10n}
            self.assertEqual(len(l10n), len(data[account.code]["l10n"]))
            for locale in l10n:
                self.assertIn(locale, data[account.code]["l10n"])
                self.assertEqual(l10n[locale],
                                 data[account.code]["l10n"][locale])


class BaseAccountTestCase(unittest.TestCase):
    """The base account test case."""

    def setUp(self) -> None:
        """Sets up the test.
        This is run once per test.

        :return: None.
        """
        from accounting.models import BaseAccount
        self.app: Flask = create_test_app()

        runner: FlaskCliRunner = self.app.test_cli_runner()
        with self.app.app_context():
            result: Result = runner.invoke(args="init-db")
            self.assertEqual(result.exit_code, 0)
            if BaseAccount.query.first() is None:
                result = runner.invoke(args="accounting-init-base")
                self.assertEqual(result.exit_code, 0)

    def test_nobody(self) -> None:
        """Test the permission as nobody.

        :return: None.
        """
        client, csrf_token = get_client(self.app, "nobody")
        response: httpx.Response

        response = client.get(LIST_URI)
        self.assertEqual(response.status_code, 403)

        response = client.get(DETAIL_URI)
        self.assertEqual(response.status_code, 403)

    def test_viewer(self) -> None:
        """Test the permission as viewer.

        :return: None.
        """
        client, csrf_token = get_client(self.app, "viewer")
        response: httpx.Response

        response = client.get(LIST_URI)
        self.assertEqual(response.status_code, 200)

        response = client.get(DETAIL_URI)
        self.assertEqual(response.status_code, 200)

    def test_editor(self) -> None:
        """Test the permission as editor.

        :return: None.
        """
        client, csrf_token = get_client(self.app, "editor")
        response: httpx.Response

        response = client.get(LIST_URI)
        self.assertEqual(response.status_code, 200)

        response = client.get(DETAIL_URI)
        self.assertEqual(response.status_code, 200)
