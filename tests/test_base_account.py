# The Mia! Accounting Flask Project.
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
import unittest

import httpx
from click.testing import Result
from flask import Flask
from flask.testing import FlaskCliRunner

from test_site import create_app
from testlib import get_client


class BaseAccountCommandTestCase(unittest.TestCase):
    """The base account console command test case."""

    def setUp(self) -> None:
        """Sets up the test.
        This is run once per test.

        :return: None.
        """
        from accounting.models import BaseAccount, BaseAccountL10n
        self.app: Flask = create_app(is_testing=True)

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
        from accounting.models import BaseAccount, BaseAccountL10n
        runner: FlaskCliRunner = self.app.test_cli_runner()
        result: Result = runner.invoke(args="accounting-init-base")
        self.assertEqual(result.exit_code, 0)
        with self.app.app_context():
            accounts: list[BaseAccount] = BaseAccount.query.all()
            l10n: list[BaseAccountL10n] = BaseAccountL10n.query.all()
        self.assertEqual(len(accounts), 527)
        self.assertEqual(len(l10n), 527 * 2)
        l10n_keys: set[str] = {f"{x.account_code}-{x.locale}" for x in l10n}
        for account in accounts:
            self.assertIn(f"{account.code}-zh_Hant", l10n_keys)
            self.assertIn(f"{account.code}-zh_Hant", l10n_keys)


class BaseAccountTestCase(unittest.TestCase):
    """The base account test case."""

    def setUp(self) -> None:
        """Sets up the test.
        This is run once per test.

        :return: None.
        """
        from accounting.models import BaseAccount
        self.app: Flask = create_app(is_testing=True)

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
        client, csrf_token = get_client(self, self.app, "nobody")
        response: httpx.Response

        response = client.get("/accounting/base-accounts")
        self.assertEqual(response.status_code, 403)

        response = client.get("/accounting/base-accounts/1111")
        self.assertEqual(response.status_code, 403)

    def test_viewer(self) -> None:
        """Test the permission as viewer.

        :return: None.
        """
        client, csrf_token = get_client(self, self.app, "viewer")
        response: httpx.Response

        response = client.get("/accounting/base-accounts")
        self.assertEqual(response.status_code, 200)

        response = client.get("/accounting/base-accounts/1111")
        self.assertEqual(response.status_code, 200)

    def test_editor(self) -> None:
        """Test the permission as editor.

        :return: None.
        """
        client, csrf_token = get_client(self, self.app, "editor")
        response: httpx.Response

        response = client.get("/accounting/base-accounts")
        self.assertEqual(response.status_code, 200)

        response = client.get("/accounting/base-accounts/1111")
        self.assertEqual(response.status_code, 200)
