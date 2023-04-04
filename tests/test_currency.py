# The Mia! Accounting Project.
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
"""The test for the currency management.

"""
import csv
import typing as t
import unittest
from datetime import timedelta, date

import httpx
from click.testing import Result
from flask import Flask
from flask.testing import FlaskCliRunner

from test_site import db
from testlib import NEXT_URI, create_test_app, get_client, set_locale
from testlib_journal_entry import add_journal_entry


class CurrencyData:
    """The currency data."""

    def __init__(self, code: str, name: str):
        """Constructs the currency data.

        :param code: The code.
        :param name: The name.
        """
        self.code: str = code
        """The code."""
        self.name: str = name
        """The name."""


USD: CurrencyData = CurrencyData("USD", "US Dollar")
"""The US dollars."""
EUR: CurrencyData = CurrencyData("EUR", "Euro")
"""The European dollars."""
TWD: CurrencyData = CurrencyData("TWD", "Taiwan dollars")
"""The Taiwan dollars."""
JPY: CurrencyData = CurrencyData("JPY", "Japanese yen")
"""The Japanese yen."""
PREFIX: str = "/accounting/currencies"
"""The URL prefix for the currency management."""


class CurrencyCommandTestCase(unittest.TestCase):
    """The account console command test case."""

    def setUp(self) -> None:
        """Sets up the test.
        This is run once per test.

        :return: None.
        """
        self.app: Flask = create_test_app()

        runner: FlaskCliRunner = self.app.test_cli_runner()
        with self.app.app_context():
            from accounting.models import Currency, CurrencyL10n
            result: Result
            result = runner.invoke(args="init-db")
            self.assertEqual(result.exit_code, 0)
            CurrencyL10n.query.delete()
            Currency.query.delete()
            db.session.commit()

    def test_init(self) -> None:
        """Tests the "accounting-init-currencies" console command.

        :return: None.
        """
        from accounting import data_dir
        from accounting.models import Currency

        with open(data_dir / "currencies.csv") as fp:
            data: dict[dict[str, t.Any]] \
                = {x["code"]: {"code": x["code"],
                               "name": x["name"],
                               "l10n": {y[5:]: x[y]
                                        for y in x if y.startswith("l10n-")}}
                   for x in csv.DictReader(fp)}

        runner: FlaskCliRunner = self.app.test_cli_runner()
        with self.app.app_context():
            result: Result = runner.invoke(
                args=["accounting-init-currencies", "-u", "editor"])
            self.assertEqual(result.exit_code, 0)
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


class CurrencyTestCase(unittest.TestCase):
    """The currency test case."""

    def setUp(self) -> None:
        """Sets up the test.
        This is run once per test.

        :return: None.
        """
        self.app: Flask = create_test_app()

        runner: FlaskCliRunner = self.app.test_cli_runner()
        with self.app.app_context():
            from accounting.models import Currency, CurrencyL10n
            result: Result
            result = runner.invoke(args="init-db")
            self.assertEqual(result.exit_code, 0)
            CurrencyL10n.query.delete()
            Currency.query.delete()
            db.session.commit()

        self.client, self.csrf_token = get_client(self.app, "editor")
        response: httpx.Response

        response = self.client.post(f"{PREFIX}/store",
                                    data={"csrf_token": self.csrf_token,
                                          "code": USD.code,
                                          "name": USD.name})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], f"{PREFIX}/{USD.code}")

        response = self.client.post(f"{PREFIX}/store",
                                    data={"csrf_token": self.csrf_token,
                                          "code": EUR.code,
                                          "name": EUR.name})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], f"{PREFIX}/{EUR.code}")

    def test_nobody(self) -> None:
        """Test the permission as nobody.

        :return: None.
        """
        client, csrf_token = get_client(self.app, "nobody")
        response: httpx.Response

        response = client.get(PREFIX)
        self.assertEqual(response.status_code, 403)

        response = client.get(f"{PREFIX}/{USD.code}")
        self.assertEqual(response.status_code, 403)

        response = client.get(f"{PREFIX}/create")
        self.assertEqual(response.status_code, 403)

        response = client.post(f"{PREFIX}/store",
                               data={"csrf_token": csrf_token,
                                     "code": TWD.code,
                                     "name": TWD.name})
        self.assertEqual(response.status_code, 403)

        response = client.get(f"{PREFIX}/{USD.code}/edit")
        self.assertEqual(response.status_code, 403)

        response = client.post(f"{PREFIX}/{USD.code}/update",
                               data={"csrf_token": csrf_token,
                                     "code": JPY.code,
                                     "name": JPY.name})
        self.assertEqual(response.status_code, 403)

        response = client.post(f"{PREFIX}/{EUR.code}/delete",
                               data={"csrf_token": csrf_token})
        self.assertEqual(response.status_code, 403)

    def test_viewer(self) -> None:
        """Test the permission as viewer.

        :return: None.
        """
        client, csrf_token = get_client(self.app, "viewer")
        response: httpx.Response

        response = client.get(PREFIX)
        self.assertEqual(response.status_code, 200)

        response = client.get(f"{PREFIX}/{USD.code}")
        self.assertEqual(response.status_code, 200)

        response = client.get(f"{PREFIX}/create")
        self.assertEqual(response.status_code, 403)

        response = client.post(f"{PREFIX}/store",
                               data={"csrf_token": csrf_token,
                                     "code": TWD.code,
                                     "name": TWD.name})
        self.assertEqual(response.status_code, 403)

        response = client.get(f"{PREFIX}/{USD.code}/edit")
        self.assertEqual(response.status_code, 403)

        response = client.post(f"{PREFIX}/{USD.code}/update",
                               data={"csrf_token": csrf_token,
                                     "code": JPY.code,
                                     "name": JPY.name})
        self.assertEqual(response.status_code, 403)

        response = client.post(f"{PREFIX}/{EUR.code}/delete",
                               data={"csrf_token": csrf_token})
        self.assertEqual(response.status_code, 403)

    def test_editor(self) -> None:
        """Test the permission as editor.

        :return: None.
        """
        response: httpx.Response

        response = self.client.get(PREFIX)
        self.assertEqual(response.status_code, 200)

        response = self.client.get(f"{PREFIX}/{USD.code}")
        self.assertEqual(response.status_code, 200)

        response = self.client.get(f"{PREFIX}/create")
        self.assertEqual(response.status_code, 200)

        response = self.client.post(f"{PREFIX}/store",
                                    data={"csrf_token": self.csrf_token,
                                          "code": TWD.code,
                                          "name": TWD.name})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], f"{PREFIX}/{TWD.code}")

        response = self.client.get(f"{PREFIX}/{USD.code}/edit")
        self.assertEqual(response.status_code, 200)

        response = self.client.post(f"{PREFIX}/{USD.code}/update",
                                    data={"csrf_token": self.csrf_token,
                                          "code": JPY.code,
                                          "name": JPY.name})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], f"{PREFIX}/{JPY.code}")

        response = self.client.post(f"{PREFIX}/{EUR.code}/delete",
                                    data={"csrf_token": self.csrf_token})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], PREFIX)

    def test_add(self) -> None:
        """Tests to add the currencies.

        :return: None.
        """
        from accounting.models import Currency
        create_uri: str = f"{PREFIX}/create"
        store_uri: str = f"{PREFIX}/store"
        detail_uri: str = f"{PREFIX}/{TWD.code}"
        response: httpx.Response

        with self.app.app_context():
            self.assertEqual({x.code for x in Currency.query.all()},
                             {USD.code, EUR.code})

        # Missing CSRF token
        response = self.client.post(store_uri,
                                    data={"code": TWD.code,
                                          "name": TWD.name})
        self.assertEqual(response.status_code, 400)

        # CSRF token mismatch
        response = self.client.post(store_uri,
                                    data={"csrf_token": f"{self.csrf_token}-2",
                                          "code": TWD.code,
                                          "name": TWD.name})
        self.assertEqual(response.status_code, 400)

        # Empty code
        response = self.client.post(store_uri,
                                    data={"csrf_token": self.csrf_token,
                                          "code": " ",
                                          "name": TWD.name})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)

        # Blocked code, with spaces to be stripped
        response = self.client.post(store_uri,
                                    data={"csrf_token": self.csrf_token,
                                          "code": " create ",
                                          "name": TWD.name})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)

        # Bad code
        response = self.client.post(store_uri,
                                    data={"csrf_token": self.csrf_token,
                                          "code": " zzc ",
                                          "name": TWD.name})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)

        # Empty name
        response = self.client.post(store_uri,
                                    data={"csrf_token": self.csrf_token,
                                          "code": TWD.code,
                                          "name": " "})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)

        # Success, with spaces to be stripped
        response = self.client.post(store_uri,
                                    data={"csrf_token": self.csrf_token,
                                          "code": f" {TWD.code} ",
                                          "name": f" {TWD.name} "})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], detail_uri)

        # Duplicated code
        response = self.client.post(store_uri,
                                    data={"csrf_token": self.csrf_token,
                                          "code": TWD.code,
                                          "name": TWD.name})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)

        with self.app.app_context():
            self.assertEqual({x.code for x in Currency.query.all()},
                             {USD.code, EUR.code, TWD.code})

            currency: Currency = db.session.get(Currency, TWD.code)
            self.assertEqual(currency.code, TWD.code)
            self.assertEqual(currency.name_l10n, TWD.name)

    def test_basic_update(self) -> None:
        """Tests the basic rules to update a user.

        :return: None.
        """
        from accounting.models import Currency
        detail_uri: str = f"{PREFIX}/{USD.code}"
        edit_uri: str = f"{PREFIX}/{USD.code}/edit"
        update_uri: str = f"{PREFIX}/{USD.code}/update"
        detail_c_uri: str = f"{PREFIX}/{TWD.code}"
        response: httpx.Response

        # Success, with spaces to be stripped
        response = self.client.post(update_uri,
                                    data={"csrf_token": self.csrf_token,
                                          "code": f" {USD.code} ",
                                          "name": f" {USD.name}-1 "})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], detail_uri)

        with self.app.app_context():
            currency: Currency = db.session.get(Currency, USD.code)
            self.assertEqual(currency.code, USD.code)
            self.assertEqual(currency.name_l10n, f"{USD.name}-1")

        # Empty code
        response = self.client.post(update_uri,
                                    data={"csrf_token": self.csrf_token,
                                          "code": " ",
                                          "name": TWD.name})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Blocked code, with spaces to be stripped
        response = self.client.post(update_uri,
                                    data={"csrf_token": self.csrf_token,
                                          "code": " create ",
                                          "name": TWD.name})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Bad code
        response = self.client.post(update_uri,
                                    data={"csrf_token": self.csrf_token,
                                          "code": "abc/def",
                                          "name": TWD.name})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Empty name
        response = self.client.post(update_uri,
                                    data={"csrf_token": self.csrf_token,
                                          "code": TWD.code,
                                          "name": " "})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Duplicated code
        response = self.client.post(update_uri,
                                    data={"csrf_token": self.csrf_token,
                                          "code": EUR.code,
                                          "name": TWD.name})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Change code
        response = self.client.post(update_uri,
                                    data={"csrf_token": self.csrf_token,
                                          "code": TWD.code,
                                          "name": TWD.name})
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
        from accounting.models import Currency
        detail_uri: str = f"{PREFIX}/{USD.code}"
        update_uri: str = f"{PREFIX}/{USD.code}/update"
        currency: Currency | None
        response: httpx.Response

        response = self.client.post(update_uri,
                                    data={"csrf_token": self.csrf_token,
                                          "code": f" {USD.code} ",
                                          "name": f" {USD.name} "})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], detail_uri)

        with self.app.app_context():
            currency = db.session.get(Currency, USD.code)
            self.assertIsNotNone(currency)
            currency.created_at \
                = currency.created_at - timedelta(seconds=5)
            currency.updated_at = currency.created_at
            db.session.commit()

        response = self.client.post(update_uri,
                                    data={"csrf_token": self.csrf_token,
                                          "code": USD.code,
                                          "name": TWD.name})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], detail_uri)

        with self.app.app_context():
            currency = db.session.get(Currency, USD.code)
            self.assertIsNotNone(currency)
            self.assertLess(currency.created_at,
                            currency.updated_at)

    def test_created_updated_by(self) -> None:
        """Tests the created-by and updated-by record.

        :return: None.
        """
        from accounting.models import Currency
        editor_username, admin_username = "editor", "admin"
        client, csrf_token = get_client(self.app, admin_username)
        detail_uri: str = f"{PREFIX}/{USD.code}"
        update_uri: str = f"{PREFIX}/{USD.code}/update"
        currency: Currency
        response: httpx.Response

        with self.app.app_context():
            currency = db.session.get(Currency, USD.code)
            self.assertEqual(currency.created_by.username, editor_username)
            self.assertEqual(currency.updated_by.username, editor_username)

        response = client.post(update_uri,
                               data={"csrf_token": csrf_token,
                                     "code": USD.code,
                                     "name": f"{USD.name}-2"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], detail_uri)

        with self.app.app_context():
            currency = db.session.get(Currency, USD.code)
            self.assertEqual(currency.created_by.username, editor_username)
            self.assertEqual(currency.updated_by.username, admin_username)

    def test_api_exists(self) -> None:
        """Tests the API to check if a code exists.

        :return: None.
        """
        response: httpx.Response

        response = self.client.get(
            f"/accounting/api/currencies/exists-code?q={USD.code}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(set(data.keys()), {"exists"})
        self.assertTrue(data["exists"])

        response = self.client.get(
            f"/accounting/api/currencies/exists-code?q={USD.code}-1")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(set(data.keys()), {"exists"})
        self.assertFalse(data["exists"])

    def test_l10n(self) -> None:
        """Tests the localization.

        :return: None
        """
        from accounting.models import Currency
        detail_uri: str = f"{PREFIX}/{USD.code}"
        update_uri: str = f"{PREFIX}/{USD.code}/update"
        currency: Currency
        response: httpx.Response

        with self.app.app_context():
            currency = db.session.get(Currency, USD.code)
            self.assertEqual(currency.name_l10n, USD.name)
            self.assertEqual(currency.l10n, [])

        set_locale(self.client, self.csrf_token, "zh_Hant")

        response = self.client.post(update_uri,
                                    data={"csrf_token": self.csrf_token,
                                          "code": USD.code,
                                          "name": f"{USD.name}-zh_Hant"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], detail_uri)

        with self.app.app_context():
            currency = db.session.get(Currency, USD.code)
            self.assertEqual(currency.name_l10n, USD.name)
            self.assertEqual({(x.locale, x.name) for x in currency.l10n},
                             {("zh_Hant", f"{USD.name}-zh_Hant")})

        set_locale(self.client, self.csrf_token, "en")

        response = self.client.post(update_uri,
                                    data={"csrf_token": self.csrf_token,
                                          "code": USD.code,
                                          "name": f"{USD.name}-2"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], detail_uri)

        with self.app.app_context():
            currency = db.session.get(Currency, USD.code)
            self.assertEqual(currency.name_l10n, f"{USD.name}-2")
            self.assertEqual({(x.locale, x.name) for x in currency.l10n},
                             {("zh_Hant", f"{USD.name}-zh_Hant")})

        set_locale(self.client, self.csrf_token, "zh_Hant")

        response = self.client.post(update_uri,
                                    data={"csrf_token": self.csrf_token,
                                          "code": USD.code,
                                          "name": f"{USD.name}-zh_Hant-2"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], detail_uri)

        with self.app.app_context():
            currency = db.session.get(Currency, USD.code)
            self.assertEqual(currency.name_l10n, f"{USD.name}-2")
            self.assertEqual({(x.locale, x.name) for x in currency.l10n},
                             {("zh_Hant", f"{USD.name}-zh_Hant-2")})

    def test_delete(self) -> None:
        """Tests to delete a currency.

        :return: None.
        """
        from accounting.models import Currency
        detail_uri: str = f"{PREFIX}/{JPY.code}"
        delete_uri: str = f"{PREFIX}/{JPY.code}/delete"
        list_uri: str = PREFIX
        response: httpx.Response

        runner: FlaskCliRunner = self.app.test_cli_runner()
        with self.app.app_context():
            from accounting.models import BaseAccount
            if BaseAccount.query.first() is None:
                result = runner.invoke(args="accounting-init-base")
                self.assertEqual(result.exit_code, 0)

        response = self.client.post("/accounting/accounts/store",
                                    data={"csrf_token": self.csrf_token,
                                          "base_code": "1111",
                                          "title": "Cash"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"],
                         "/accounting/accounts/1111-001")

        response = self.client.post(f"{PREFIX}/store",
                                    data={"csrf_token": self.csrf_token,
                                          "code": JPY.code,
                                          "name": JPY.name})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], detail_uri)

        add_journal_entry(self.client,
                          form={"csrf_token": self.csrf_token,
                                "next": NEXT_URI,
                                "date": date.today().isoformat(),
                                "currency-1-code": EUR.code,
                                "currency-1-credit-1-account_code": "1111-001",
                                "currency-1-credit-1-amount": "20"})

        with self.app.app_context():
            self.assertEqual({x.code for x in Currency.query.all()},
                             {USD.code, EUR.code, JPY.code})

        # Cannot delete the default currency
        response = self.client.post(f"{PREFIX}/{USD.code}/delete",
                                    data={"csrf_token": self.csrf_token})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], f"{PREFIX}/{USD.code}")

        # Cannot delete the account that is in use
        response = self.client.post(f"{PREFIX}/{EUR.code}/delete",
                                    data={"csrf_token": self.csrf_token})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], f"{PREFIX}/{EUR.code}")

        # Success
        response = self.client.get(detail_uri)
        self.assertEqual(response.status_code, 200)
        response = self.client.post(delete_uri,
                                    data={"csrf_token": self.csrf_token})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], list_uri)

        with self.app.app_context():
            self.assertEqual({x.code for x in Currency.query.all()},
                             {USD.code, EUR.code})

        response = self.client.get(detail_uri)
        self.assertEqual(response.status_code, 404)
        response = self.client.post(delete_uri,
                                    data={"csrf_token": self.csrf_token})
        self.assertEqual(response.status_code, 404)
