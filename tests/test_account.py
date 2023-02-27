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
from datetime import timedelta

import httpx
import sqlalchemy as sa
from click.testing import Result
from flask import Flask
from flask.testing import FlaskCliRunner

from test_site import create_app, db
from testlib import get_client, set_locale

NEXT_URI: str = "/_next"
"""The next URI."""


class AccountData:
    """The account data."""

    def __init__(self, base_code: str, no: int, title: str):
        """Constructs the account data.

        :param base_code: The base code.
        :param no: The number.
        :param title: The title.
        """
        self.base_code: str = base_code
        """The base code."""
        self.no: int = no
        """The number."""
        self.title: str = title
        """The title."""
        self.code: str = f"{self.base_code}-{self.no:03d}"
        """The code."""


cash: AccountData = AccountData("1111", 1, "Cash")
"""The cash account."""
bank: AccountData = AccountData("1113", 1, "Bank")
"""The bank account."""
stock: AccountData = AccountData("1121", 1, "Stock")
"""The stock account."""
loan: AccountData = AccountData("2112", 1, "Loan")
"""The loan account."""
PREFIX: str = "/accounting/accounts"
"""The URL prefix of the currency management."""


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

        self.client, self.csrf_token = get_client(self.app, "editor")
        response: httpx.Response

        response = self.client.post(f"{PREFIX}/store",
                                    data={"csrf_token": self.csrf_token,
                                          "base_code": cash.base_code,
                                          "title": cash.title})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"],
                         f"{PREFIX}/{cash.code}")

        response = self.client.post(f"{PREFIX}/store",
                                    data={"csrf_token": self.csrf_token,
                                          "base_code": bank.base_code,
                                          "title": bank.title})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"],
                         f"{PREFIX}/{bank.code}")

    def test_nobody(self) -> None:
        """Test the permission as nobody.

        :return: None.
        """
        from accounting.models import Account
        client, csrf_token = get_client(self.app, "nobody")
        response: httpx.Response

        response = client.get(PREFIX)
        self.assertEqual(response.status_code, 403)

        response = client.get(f"{PREFIX}/{cash.code}")
        self.assertEqual(response.status_code, 403)

        response = client.get(f"{PREFIX}/create")
        self.assertEqual(response.status_code, 403)

        response = client.post(f"{PREFIX}/store",
                               data={"csrf_token": csrf_token,
                                     "base_code": stock.base_code,
                                     "title": stock.title})
        self.assertEqual(response.status_code, 403)

        response = client.get(f"{PREFIX}/{cash.code}/edit")
        self.assertEqual(response.status_code, 403)

        response = client.post(f"{PREFIX}/{cash.code}/update",
                               data={"csrf_token": csrf_token,
                                     "base_code": cash.base_code,
                                     "title": f"{cash.title}-2"})
        self.assertEqual(response.status_code, 403)

        response = client.post(f"{PREFIX}/{cash.code}/delete",
                               data={"csrf_token": csrf_token})
        self.assertEqual(response.status_code, 403)

        response = client.get(f"{PREFIX}/bases/{cash.base_code}")
        self.assertEqual(response.status_code, 403)

        with self.app.app_context():
            bank_id: int = Account.find_by_code(bank.code).id

        response = client.post(f"{PREFIX}/bases/{bank.base_code}",
                               data={"csrf_token": csrf_token,
                                     "next": NEXT_URI,
                                     f"{bank_id}-no": "5"})
        self.assertEqual(response.status_code, 403)

    def test_viewer(self) -> None:
        """Test the permission as viewer.

        :return: None.
        """
        from accounting.models import Account
        client, csrf_token = get_client(self.app, "viewer")
        response: httpx.Response

        response = client.get(PREFIX)
        self.assertEqual(response.status_code, 200)

        response = client.get(f"{PREFIX}/{cash.code}")
        self.assertEqual(response.status_code, 200)

        response = client.get(f"{PREFIX}/create")
        self.assertEqual(response.status_code, 403)

        response = client.post(f"{PREFIX}/store",
                               data={"csrf_token": csrf_token,
                                     "base_code": stock.base_code,
                                     "title": stock.title})
        self.assertEqual(response.status_code, 403)

        response = client.get(f"{PREFIX}/{cash.code}/edit")
        self.assertEqual(response.status_code, 403)

        response = client.post(f"{PREFIX}/{cash.code}/update",
                               data={"csrf_token": csrf_token,
                                     "base_code": cash.base_code,
                                     "title": f"{cash.title}-2"})
        self.assertEqual(response.status_code, 403)

        response = client.post(f"{PREFIX}/{cash.code}/delete",
                               data={"csrf_token": csrf_token})
        self.assertEqual(response.status_code, 403)

        response = client.get(f"{PREFIX}/bases/{cash.base_code}")
        self.assertEqual(response.status_code, 200)

        with self.app.app_context():
            bank_id: int = Account.find_by_code(bank.code).id

        response = client.post(f"{PREFIX}/bases/{bank.base_code}",
                               data={"csrf_token": csrf_token,
                                     "next": NEXT_URI,
                                     f"{bank_id}-no": "5"})
        self.assertEqual(response.status_code, 403)

    def test_editor(self) -> None:
        """Test the permission as editor.

        :return: None.
        """
        from accounting.models import Account
        response: httpx.Response

        response = self.client.get(PREFIX)
        self.assertEqual(response.status_code, 200)

        response = self.client.get(f"{PREFIX}/{cash.code}")
        self.assertEqual(response.status_code, 200)

        response = self.client.get(f"{PREFIX}/create")
        self.assertEqual(response.status_code, 200)

        response = self.client.post(f"{PREFIX}/store",
                                    data={"csrf_token": self.csrf_token,
                                          "base_code": stock.base_code,
                                          "title": stock.title})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"],
                         f"{PREFIX}/{stock.code}")

        response = self.client.get(f"{PREFIX}/{cash.code}/edit")
        self.assertEqual(response.status_code, 200)

        response = self.client.post(f"{PREFIX}/{cash.code}/update",
                                    data={"csrf_token": self.csrf_token,
                                          "base_code": cash.base_code,
                                          "title": f"{cash.title}-2"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], f"{PREFIX}/{cash.code}")

        response = self.client.post(f"{PREFIX}/{cash.code}/delete",
                                    data={"csrf_token": self.csrf_token})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], PREFIX)

        response = self.client.get(f"{PREFIX}/bases/{cash.base_code}")
        self.assertEqual(response.status_code, 200)

        with self.app.app_context():
            bank_id: int = Account.find_by_code(bank.code).id

        response = self.client.post(f"{PREFIX}/bases/{bank.base_code}",
                                    data={"csrf_token": self.csrf_token,
                                          "next": NEXT_URI,
                                          f"{bank_id}-no": "5"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], NEXT_URI)

    def test_add(self) -> None:
        """Tests to add the currencies.

        :return: None.
        """
        from accounting.models import Account
        create_uri: str = f"{PREFIX}/create"
        store_uri: str = f"{PREFIX}/store"
        detail_uri: str = f"{PREFIX}/{stock.code}"
        response: httpx.Response

        with self.app.app_context():
            self.assertEqual({x.code for x in Account.query.all()},
                             {cash.code, bank.code})

        # Missing CSRF token
        response = self.client.post(store_uri,
                                    data={"base_code": stock.base_code,
                                          "title": stock.title})
        self.assertEqual(response.status_code, 400)

        # CSRF token mismatch
        response = self.client.post(store_uri,
                                    data={"csrf_token": f"{self.csrf_token}-2",
                                          "base_code": stock.base_code,
                                          "title": stock.title})
        self.assertEqual(response.status_code, 400)

        # Empty base account code
        response = self.client.post(store_uri,
                                    data={"csrf_token": self.csrf_token,
                                          "base_code": " ",
                                          "title": stock.title})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)

        # Non-existing base account
        response = self.client.post(store_uri,
                                    data={"csrf_token": self.csrf_token,
                                          "base_code": "9999",
                                          "title": stock.title})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)

        # Unavailable base account
        response = self.client.post(store_uri,
                                    data={"csrf_token": self.csrf_token,
                                          "base_code": "1",
                                          "title": stock.title})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)

        # Empty name
        response = self.client.post(store_uri,
                                    data={"csrf_token": self.csrf_token,
                                          "base_code": stock.base_code,
                                          "title": " "})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)

        # Success, with spaces to be stripped
        response = self.client.post(store_uri,
                                    data={"csrf_token": self.csrf_token,
                                          "base_code": f" {stock.base_code} ",
                                          "title": f" {stock.title} "})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], detail_uri)

        # Success under the same base
        response = self.client.post(store_uri,
                                    data={"csrf_token": self.csrf_token,
                                          "base_code": stock.base_code,
                                          "title": stock.title})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"],
                         f"{PREFIX}/{stock.base_code}-002")

        # Success under the same base, with order in a mess.
        with self.app.app_context():
            stock_2: Account = Account.find_by_code(f"{stock.base_code}-002")
            stock_2.no = 66
            db.session.commit()

        response = self.client.post(store_uri,
                                    data={"csrf_token": self.csrf_token,
                                          "base_code": stock.base_code,
                                          "title": stock.title})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"],
                         f"{PREFIX}/{stock.base_code}-003")

        with self.app.app_context():
            self.assertEqual({x.code for x in Account.query.all()},
                             {cash.code, bank.code, stock.code,
                              f"{stock.base_code}-002",
                              f"{stock.base_code}-003"})

            stock_account: Account = Account.find_by_code(stock.code)
            self.assertEqual(stock_account.base_code, stock.base_code)
            self.assertEqual(stock_account.title_l10n, stock.title)

    def test_basic_update(self) -> None:
        """Tests the basic rules to update a user.

        :return: None.
        """
        from accounting.models import Account
        detail_uri: str = f"{PREFIX}/{cash.code}"
        edit_uri: str = f"{PREFIX}/{cash.code}/edit"
        update_uri: str = f"{PREFIX}/{cash.code}/update"
        detail_c_uri: str = f"{PREFIX}/{stock.code}"
        response: httpx.Response

        # Success, with spaces to be stripped
        response = self.client.post(update_uri,
                                    data={"csrf_token": self.csrf_token,
                                          "base_code": f" {cash.base_code} ",
                                          "title": f" {cash.title}-1 "})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], detail_uri)

        with self.app.app_context():
            cash_account: Account = Account.find_by_code(cash.code)
            self.assertEqual(cash_account.base_code, cash.base_code)
            self.assertEqual(cash_account.title_l10n, f"{cash.title}-1")

        # Empty base account code
        response = self.client.post(update_uri,
                                    data={"csrf_token": self.csrf_token,
                                          "base_code": " ",
                                          "title": stock.title})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Non-existing base account
        response = self.client.post(update_uri,
                                    data={"csrf_token": self.csrf_token,
                                          "base_code": "9999",
                                          "title": stock.title})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Unavailable base account
        response = self.client.post(update_uri,
                                    data={"csrf_token": self.csrf_token,
                                          "base_code": "1",
                                          "title": stock.title})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Empty name
        response = self.client.post(update_uri,
                                    data={"csrf_token": self.csrf_token,
                                          "base_code": stock.base_code,
                                          "title": " "})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Change the base account
        response = self.client.post(update_uri,
                                    data={"csrf_token": self.csrf_token,
                                          "base_code": stock.base_code,
                                          "title": stock.title})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], detail_c_uri)

        response = self.client.get(detail_uri)
        self.assertEqual(response.status_code, 404)

        response = self.client.get(detail_c_uri)
        self.assertEqual(response.status_code, 200)

    def test_update_not_modified(self) -> None:
        """Tests that the data is not modified.

        :return: None.
        """
        from accounting.models import Account
        detail_uri: str = f"{PREFIX}/{cash.code}"
        update_uri: str = f"{PREFIX}/{cash.code}/update"
        cash_account: Account
        response: httpx.Response

        response = self.client.post(update_uri,
                                    data={"csrf_token": self.csrf_token,
                                          "base_code": f" {cash.base_code} ",
                                          "title": f" {cash.title} "})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], detail_uri)

        with self.app.app_context():
            cash_account = Account.find_by_code(cash.code)
            self.assertIsNotNone(cash_account)
            cash_account.created_at \
                = cash_account.created_at - timedelta(seconds=5)
            cash_account.updated_at = cash_account.created_at
            db.session.commit()

        response = self.client.post(update_uri,
                                    data={"csrf_token": self.csrf_token,
                                          "base_code": cash.base_code,
                                          "title": stock.title})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], detail_uri)

        with self.app.app_context():
            cash_account = Account.find_by_code(cash.code)
            self.assertIsNotNone(cash_account)
            self.assertLess(cash_account.created_at,
                            cash_account.updated_at)

    def test_created_updated_by(self) -> None:
        """Tests the created-by and updated-by record.

        :return: None.
        """
        from accounting.models import Account
        editor_username, editor2_username = "editor", "editor2"
        client, csrf_token = get_client(self.app, editor2_username)
        detail_uri: str = f"{PREFIX}/{cash.code}"
        update_uri: str = f"{PREFIX}/{cash.code}/update"
        response: httpx.Response

        with self.app.app_context():
            cash_account: Account = Account.find_by_code(cash.code)
            self.assertEqual(cash_account.created_by.username, editor_username)
            self.assertEqual(cash_account.updated_by.username, editor_username)

        response = client.post(update_uri,
                               data={"csrf_token": csrf_token,
                                     "base_code": cash.base_code,
                                     "title": f"{cash.title}-2"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], detail_uri)

        with self.app.app_context():
            cash_account: Account = Account.find_by_code(cash.code)
            self.assertEqual(cash_account.created_by.username,
                             editor_username)
            self.assertEqual(cash_account.updated_by.username,
                             editor2_username)

    def test_l10n(self) -> None:
        """Tests the localization.

        :return: None
        """
        from accounting.models import Account
        detail_uri: str = f"{PREFIX}/{cash.code}"
        update_uri: str = f"{PREFIX}/{cash.code}/update"
        response: httpx.Response

        with self.app.app_context():
            cash_account: Account = Account.find_by_code(cash.code)
            self.assertEqual(cash_account.title_l10n, cash.title)
            self.assertEqual(cash_account.l10n, [])

        set_locale(self.client, self.csrf_token, "zh_Hant")

        response = self.client.post(update_uri,
                                    data={"csrf_token": self.csrf_token,
                                          "base_code": cash.base_code,
                                          "title": f"{cash.title}-zh_Hant"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], detail_uri)

        with self.app.app_context():
            cash_account: Account = Account.find_by_code(cash.code)
            self.assertEqual(cash_account.title_l10n, cash.title)
            self.assertEqual({(x.locale, x.title) for x in cash_account.l10n},
                             {("zh_Hant", f"{cash.title}-zh_Hant")})

        set_locale(self.client, self.csrf_token, "en")

        response = self.client.post(update_uri,
                                    data={"csrf_token": self.csrf_token,
                                          "base_code": cash.base_code,
                                          "title": f"{cash.title}-2"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], detail_uri)

        with self.app.app_context():
            cash_account: Account = Account.find_by_code(cash.code)
            self.assertEqual(cash_account.title_l10n, f"{cash.title}-2")
            self.assertEqual({(x.locale, x.title) for x in cash_account.l10n},
                             {("zh_Hant", f"{cash.title}-zh_Hant")})

        set_locale(self.client, self.csrf_token, "zh_Hant")

        response = self.client.post(update_uri,
                                    data={"csrf_token": self.csrf_token,
                                          "base_code": cash.base_code,
                                          "title": f"{cash.title}-zh_Hant-2"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], detail_uri)

        with self.app.app_context():
            cash_account: Account = Account.find_by_code(cash.code)
            self.assertEqual(cash_account.title_l10n, f"{cash.title}-2")
            self.assertEqual({(x.locale, x.title) for x in cash_account.l10n},
                             {("zh_Hant", f"{cash.title}-zh_Hant-2")})

    def test_delete(self) -> None:
        """Tests to delete a currency.

        :return: None.
        """
        from accounting.models import Account
        detail_uri: str = f"{PREFIX}/{cash.code}"
        delete_uri: str = f"{PREFIX}/{cash.code}/delete"
        list_uri: str = PREFIX
        response: httpx.Response

        with self.app.app_context():
            self.assertEqual({x.code for x in Account.query.all()},
                             {cash.code, bank.code})

        response = self.client.get(detail_uri)
        self.assertEqual(response.status_code, 200)
        response = self.client.post(delete_uri,
                                    data={"csrf_token": self.csrf_token})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], list_uri)

        with self.app.app_context():
            self.assertEqual({x.code for x in Account.query.all()},
                             {bank.code})

        response = self.client.get(detail_uri)
        self.assertEqual(response.status_code, 404)
        response = self.client.post(delete_uri,
                                    data={"csrf_token": self.csrf_token})
        self.assertEqual(response.status_code, 404)

    def test_change_base_code(self) -> None:
        """Tests to change the base code of an account.

        :return: None.
        """
        from accounting.models import Account
        response: httpx.Response

        for i in range(2, 6):
            response = self.client.post(f"{PREFIX}/store",
                                        data={"csrf_token": self.csrf_token,
                                              "base_code": "1111",
                                              "title": "Title"})
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.headers["Location"],
                             f"{PREFIX}/1111-00{i}")

        with self.app.app_context():
            account_1: Account = Account.find_by_code("1111-001")
            id_1: int = account_1.id
            account_2: Account = Account.find_by_code("1111-002")
            id_2: int = account_2.id
            account_3: Account = Account.find_by_code("1111-003")
            id_3: int = account_3.id
            account_4: Account = Account.find_by_code("1111-004")
            id_4: int = account_4.id
            account_5: Account = Account.find_by_code("1111-005")
            id_5: int = account_5.id
            account_1.no = 3
            account_2.no = 5
            account_3.no = 8
            account_4.base_code = "1112"
            account_4.no = 2
            account_5.base_code = "1112"
            account_5.no = 6
            db.session.commit()

        response = self.client.post(f"{PREFIX}/1111-005/update",
                                    data={"csrf_token": self.csrf_token,
                                          "base_code": "1112",
                                          "title": "Title"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], f"{PREFIX}/1112-003")

        with self.app.app_context():
            self.assertEqual(db.session.get(Account, id_1).no, 1)
            self.assertEqual(db.session.get(Account, id_2).no, 3)
            self.assertEqual(db.session.get(Account, id_3).no, 2)
            self.assertEqual(db.session.get(Account, id_4).no, 1)
            self.assertEqual(db.session.get(Account, id_5).no, 2)

    def test_reorder(self) -> None:
        """Tests to reorder the accounts under a same base account.

        :return: None.
        """
        from accounting.models import Account
        response: httpx.Response

        for i in range(2, 6):
            response = self.client.post(f"{PREFIX}/store",
                                        data={"csrf_token": self.csrf_token,
                                              "base_code": "1111",
                                              "title": "Title"})
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.headers["Location"],
                             f"{PREFIX}/1111-00{i}")

        # Normal reorder
        with self.app.app_context():
            id_1: int = Account.find_by_code("1111-001").id
            id_2: int = Account.find_by_code("1111-002").id
            id_3: int = Account.find_by_code("1111-003").id
            id_4: int = Account.find_by_code("1111-004").id
            id_5: int = Account.find_by_code("1111-005").id

        response = self.client.post(f"{PREFIX}/bases/1111",
                                    data={"csrf_token": self.csrf_token,
                                          "next": NEXT_URI,
                                          f"{id_1}-no": "4",
                                          f"{id_2}-no": "1",
                                          f"{id_3}-no": "5",
                                          f"{id_4}-no": "2",
                                          f"{id_5}-no": "3"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], NEXT_URI)

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

        response = self.client.post(f"{PREFIX}/bases/1111",
                                    data={"csrf_token": self.csrf_token,
                                          "next": NEXT_URI,
                                          f"{id_2}-no": "3a",
                                          f"{id_3}-no": "5",
                                          f"{id_4}-no": "2"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], NEXT_URI)

        with self.app.app_context():
            self.assertEqual(db.session.get(Account, id_1).code, "1111-003")
            self.assertEqual(db.session.get(Account, id_2).code, "1111-004")
            self.assertEqual(db.session.get(Account, id_3).code, "1111-002")
            self.assertEqual(db.session.get(Account, id_4).code, "1111-001")
            self.assertEqual(db.session.get(Account, id_5).code, "1111-005")
