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

from testlib import get_csrf_token
from testsite import create_app


class BaseAccountTestCase(unittest.TestCase):
    """The base account test case."""

    def setUp(self) -> None:
        """Sets up the test.
        This is run once per test.

        :return: None.
        """
        self.app: Flask = create_app(is_testing=True)

        runner: FlaskCliRunner = self.app.test_cli_runner()
        with self.app.app_context():
            result: Result = runner.invoke(args="init-db")
            self.assertEqual(result.exit_code, 0)
        self.client: httpx.Client = httpx.Client(app=self.app,
                                                 base_url="https://testserver")
        self.client.headers["Referer"] = "https://testserver"
        self.csrf_token: str = get_csrf_token(self, self.client, "/login")

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

        list_uri: str = "/accounting/base-accounts"
        response: httpx.Response

        self.__logout()
        response = self.client.get(list_uri)
        self.assertEqual(response.status_code, 403)

        self.__logout()
        self.__login_as("viewer")
        response = self.client.get(list_uri)
        self.assertEqual(response.status_code, 200)

        self.__logout()
        self.__login_as("editor")
        response = self.client.get(list_uri)
        self.assertEqual(response.status_code, 200)

        self.__logout()
        self.__login_as("nobody")
        response = self.client.get(list_uri)
        self.assertEqual(response.status_code, 403)

    def __logout(self) -> None:
        """Logs out the currently logged-in user.

        :return: None.
        """
        response: httpx.Response = self.client.post(
            "/logout", data={"csrf_token": self.csrf_token})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/")

    def __login_as(self, username: str) -> None:
        """Logs in as a specific user.

        :param username: The username.
        :return: None.
        """
        response: httpx.Response = self.client.post(
            "/login", data={"csrf_token": self.csrf_token,
                            "username": username})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/")
