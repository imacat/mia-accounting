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

from test_site import create_app
from testlib import get_client


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

        self.client, self.csrf_token = get_client(self, self.app, "editor")
        response: httpx.Response

        response = self.client.post("/accounting/accounts/store",
                                    data={"csrf_token": self.csrf_token,
                                          "base_code": "1111",
                                          "title": "1111 title"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"],
                         "/accounting/accounts/1111-001")

        response = self.client.post("/accounting/accounts/store",
                                    data={"csrf_token": self.csrf_token,
                                          "base_code": "1112",
                                          "title": "1112 title"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"],
                         "/accounting/accounts/1112-001")

    def test_nobody(self) -> None:
        """Test the permission as nobody.

        :return: None.
        """
        from accounting.models import Account
        client, csrf_token = get_client(self, self.app, "nobody")
        response: httpx.Response

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

        response = client.get("/accounting/accounts/bases/1111")
        self.assertEqual(response.status_code, 403)

        with self.app.app_context():
            account_id: int = Account.find_by_code("1112-001").id

        response = client.post("/accounting/accounts/bases/1112",
                               data={"csrf_token": csrf_token,
                                     "next": "/next",
                                     f"{account_id}-no": "5"})
        self.assertEqual(response.status_code, 403)

    def test_viewer(self) -> None:
        """Test the permission as viewer.

        :return: None.
        """
        from accounting.models import Account
        client, csrf_token = get_client(self, self.app, "viewer")
        response: httpx.Response

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

        response = client.get("/accounting/accounts/bases/1111")
        self.assertEqual(response.status_code, 200)

        with self.app.app_context():
            account_id: int = Account.find_by_code("1112-001").id

        response = client.post("/accounting/accounts/bases/1112",
                               data={"csrf_token": csrf_token,
                                     "next": "/next",
                                     f"{account_id}-no": "5"})
        self.assertEqual(response.status_code, 403)

    def test_editor(self) -> None:
        """Test the permission as editor.

        :return: None.
        """
        from accounting.models import Account
        response: httpx.Response

        response = self.client.get("/accounting/accounts")
        self.assertEqual(response.status_code, 200)

        response = self.client.get("/accounting/accounts/1111-001")
        self.assertEqual(response.status_code, 200)

        response = self.client.get("/accounting/accounts/create")
        self.assertEqual(response.status_code, 200)

        response = self.client.post("/accounting/accounts/store",
                                    data={"csrf_token": self.csrf_token,
                                          "base_code": "1113",
                                          "title": "1113 title"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"],
                         "/accounting/accounts/1113-001")

        response = self.client.get("/accounting/accounts/1111-001/edit")
        self.assertEqual(response.status_code, 200)

        response = self.client.post("/accounting/accounts/1111-001/update",
                                    data={"csrf_token": self.csrf_token,
                                          "base_code": "1111",
                                          "title": "1111 title #2"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"],
                         "/accounting/accounts/1111-001")

        response = self.client.post("/accounting/accounts/1111-001/delete",
                                    data={"csrf_token": self.csrf_token})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"],
                         "/accounting/accounts")

        response = self.client.get("/accounting/accounts/bases/1111")
        self.assertEqual(response.status_code, 200)

        with self.app.app_context():
            account_id: int = Account.find_by_code("1112-001").id

        response = self.client.post("/accounting/accounts/bases/1112",
                                    data={"csrf_token": self.csrf_token,
                                          "next": "/next",
                                          f"{account_id}-no": "5"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/next")

    def test_change_base(self) -> None:
        """Tests to change the base account.

        :return: None.
        """
        from accounting.database import db
        from accounting.models import Account
        response: httpx.Response

        response = self.client.post("/accounting/accounts/store",
                                    data={"csrf_token": self.csrf_token,
                                          "base_code": "1111",
                                          "title": "Title #1"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"],
                         "/accounting/accounts/1111-002")

        response = self.client.post("/accounting/accounts/store",
                                    data={"csrf_token": self.csrf_token,
                                          "base_code": "1111",
                                          "title": "Title #1"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"],
                         "/accounting/accounts/1111-003")

        response = self.client.post("/accounting/accounts/store",
                                    data={"csrf_token": self.csrf_token,
                                          "base_code": "1112",
                                          "title": "Title #1"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"],
                         "/accounting/accounts/1112-002")

        with self.app.app_context():
            id_1: int = Account.find_by_code("1111-001").id
            id_2: int = Account.find_by_code("1111-002").id
            id_3: int = Account.find_by_code("1111-003").id
            id_4: int = Account.find_by_code("1112-001").id
            id_5: int = Account.find_by_code("1112-002").id

        response = self.client.post("/accounting/accounts/1111-002/update",
                                    data={"csrf_token": self.csrf_token,
                                          "base_code": "1112",
                                          "title": "Account #1"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"],
                         "/accounting/accounts/1112-003")

        with self.app.app_context():
            self.assertEqual(db.session.get(Account, id_1).code, "1111-001")
            self.assertEqual(db.session.get(Account, id_2).code, "1112-003")
            self.assertEqual(db.session.get(Account, id_3).code, "1111-002")
            self.assertEqual(db.session.get(Account, id_4).code, "1112-001")
            self.assertEqual(db.session.get(Account, id_5).code, "1112-002")

    def test_reorder(self) -> None:
        """Tests to reorder the accounts under a same base account.

        :return: None.
        """
        from accounting.database import db
        from accounting.models import Account
        response: httpx.Response

        for i in range(2, 6):
            response = self.client.post("/accounting/accounts/store",
                                        data={"csrf_token": self.csrf_token,
                                              "base_code": "1111",
                                              "title": "Title"})
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.headers["Location"],
                             f"/accounting/accounts/1111-00{i}")

        # Normal reorder
        with self.app.app_context():
            id_1: int = Account.find_by_code("1111-001").id
            id_2: int = Account.find_by_code("1111-002").id
            id_3: int = Account.find_by_code("1111-003").id
            id_4: int = Account.find_by_code("1111-004").id
            id_5: int = Account.find_by_code("1111-005").id

        response = self.client.post("/accounting/accounts/bases/1111",
                                    data={"csrf_token": self.csrf_token,
                                          "next": "/next",
                                          f"{id_1}-no": "4",
                                          f"{id_2}-no": "1",
                                          f"{id_3}-no": "5",
                                          f"{id_4}-no": "2",
                                          f"{id_5}-no": "3"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], f"/next")

        with self.app.app_context():
            self.assertEqual(db.session.get(Account, id_1).code, "1111-004")
            self.assertEqual(db.session.get(Account, id_2).code, "1111-001")
            self.assertEqual(db.session.get(Account, id_3).code, "1111-005")
            self.assertEqual(db.session.get(Account, id_4).code, "1111-002")
            self.assertEqual(db.session.get(Account, id_5).code, "1111-003")

        # Malformed orders
        with self.app.app_context():
            db.session.get(Account, id_1).no = 3
            db.session.get(Account, id_2).no = 4
            db.session.get(Account, id_3).no = 6
            db.session.get(Account, id_4).no = 8
            db.session.get(Account, id_5).no = 9
            db.session.commit()

        response = self.client.post("/accounting/accounts/bases/1111",
                                    data={"csrf_token": self.csrf_token,
                                          "next": "/next",
                                          f"{id_2}-no": "3a",
                                          f"{id_3}-no": "5",
                                          f"{id_4}-no": "2"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], f"/next")

        with self.app.app_context():
            self.assertEqual(db.session.get(Account, id_1).code, "1111-003")
            self.assertEqual(db.session.get(Account, id_2).code, "1111-004")
            self.assertEqual(db.session.get(Account, id_3).code, "1111-002")
            self.assertEqual(db.session.get(Account, id_4).code, "1111-001")
            self.assertEqual(db.session.get(Account, id_5).code, "1111-005")
