# The Mia! Accounting Flask Project.
# Author: imacat@mail.imacat.idv.tw (imacat), 2023/2/1

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

"""The test for the account management.

"""
import unittest

import httpx
import sqlalchemy as sa
from click.testing import Result
from flask import Flask
from flask.testing import FlaskCliRunner

from testlib import UserClient, get_user_client
from testsite import create_app


class AccountCommandTestCase(unittest.TestCase):
    """The account console command test case."""

    def setUp(self) -> None:
        """Sets up the test.
        This is run once per test.

        :return: None.
        """
        self.app: Flask = create_app(is_testing=True)

        runner: FlaskCliRunner = self.app.test_cli_runner()
        with self.app.app_context():
            from accounting.database import db
            from accounting.models import BaseAccount, Account, AccountL10n
            result: Result
            result = runner.invoke(args="init-db")
            self.assertEqual(result.exit_code, 0)
            if BaseAccount.query.first() is None:
                result = runner.invoke(args="accounting-init-base")
                self.assertEqual(result.exit_code, 0)
            AccountL10n.query.delete()
            Account.query.delete()
            db.session.commit()

    def test_init(self) -> None:
        """Tests the "accounting-init-account" console command.

        :return: None.
        """
        from accounting.models import BaseAccount, Account, AccountL10n
        runner: FlaskCliRunner = self.app.test_cli_runner()
        with self.app.app_context():
            result: Result = runner.invoke(args=["accounting-init-accounts",
                                                 "-u", "editor"])
            self.assertEqual(result.exit_code, 0)
        with self.app.app_context():
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


class AccountTestCase(unittest.TestCase):
    """The account test case."""

    def setUp(self) -> None:
        """Sets up the test.
        This is run once per test.

        :return: None.
        """
        self.app: Flask = create_app(is_testing=True)

        runner: FlaskCliRunner = self.app.test_cli_runner()
        with self.app.app_context():
            from accounting.database import db
            from accounting.models import BaseAccount, Account, AccountL10n
            result: Result
            result = runner.invoke(args="init-db")
            self.assertEqual(result.exit_code, 0)
            if BaseAccount.query.first() is None:
                result = runner.invoke(args="accounting-init-base")
                self.assertEqual(result.exit_code, 0)
            AccountL10n.query.delete()
            Account.query.delete()
            db.session.commit()

        self.viewer: UserClient = get_user_client(self, self.app, "viewer")
        self.editor: UserClient = get_user_client(self, self.app, "editor")
        self.nobody: UserClient = get_user_client(self, self.app, "nobody")

        client: httpx.Client = self.editor.client
        csrf_token: str = self.editor.csrf_token
        response: httpx.Response

        response = client.post("/accounting/accounts/store",
                               data={"csrf_token": csrf_token,
                                     "base_code": "1111",
                                     "title": "1111 title"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"],
                         "/accounting/accounts/1111-001")

        response = client.post("/accounting/accounts/store",
                               data={"csrf_token": csrf_token,
                                     "base_code": "1112",
                                     "title": "1112 title"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"],
                         "/accounting/accounts/1112-001")

    def test_nobody(self) -> None:
        """Test the permission as nobody.

        :return: None.
        """
        response: httpx.Response
        client: httpx.Client = self.nobody.client
        csrf_token: str = self.nobody.csrf_token

        response = client.get("/accounting/accounts")
        self.assertEqual(response.status_code, 403)

        response = client.get("/accounting/accounts/1111-001")
        self.assertEqual(response.status_code, 403)

        response = client.get("/accounting/accounts/create")
        self.assertEqual(response.status_code, 403)

        response = client.post("/accounting/accounts/store",
                               data={"csrf_token": csrf_token,
                                     "base_code": "1113",
                                     "title": "1113 title"})
        self.assertEqual(response.status_code, 403)

        response = client.get("/accounting/accounts/1111-001/edit")
        self.assertEqual(response.status_code, 403)

        response = client.post("/accounting/accounts/1111-001/update",
                               data={"csrf_token": csrf_token,
                                     "base_code": "1111",
                                     "title": "1111 title #2"})
        self.assertEqual(response.status_code, 403)

        response = client.post("/accounting/accounts/1111-001/delete",
                               data={"csrf_token": csrf_token})
        self.assertEqual(response.status_code, 403)

    def test_viewer(self) -> None:
        """Test the permission as viewer.

        :return: None.
        """
        response: httpx.Response
        client: httpx.Client = self.viewer.client
        csrf_token: str = self.viewer.csrf_token

        response = client.get("/accounting/accounts")
        self.assertEqual(response.status_code, 200)

        response = client.get("/accounting/accounts/1111-001")
        self.assertEqual(response.status_code, 200)

        response = client.get("/accounting/accounts/create")
        self.assertEqual(response.status_code, 403)

        response = client.post("/accounting/accounts/store",
                               data={"csrf_token": csrf_token,
                                     "base_code": "1113",
                                     "title": "1113 title"})
        self.assertEqual(response.status_code, 403)

        response = client.get("/accounting/accounts/1111-001/edit")
        self.assertEqual(response.status_code, 403)

        response = client.post("/accounting/accounts/1111-001/update",
                               data={"csrf_token": csrf_token,
                                     "base_code": "1111",
                                     "title": "1111 title #2"})
        self.assertEqual(response.status_code, 403)

        response = client.post("/accounting/accounts/1111-001/delete",
                               data={"csrf_token": csrf_token})
        self.assertEqual(response.status_code, 403)
