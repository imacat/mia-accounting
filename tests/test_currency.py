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
"""The test for the currency management.

"""
import csv
import typing as t
import unittest
from datetime import timedelta

import httpx
from click.testing import Result
from flask import Flask
from flask.testing import FlaskCliRunner

from test_site import create_app, db
from testlib import get_client, set_locale


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


zza: CurrencyData = CurrencyData("ZZA", "Testing Dollar #A")
"""The first test currency."""
zzb: CurrencyData = CurrencyData("ZZB", "Testing Dollar #B")
"""The second test currency."""
zzc: CurrencyData = CurrencyData("ZZC", "Testing Dollar #C")
"""The third test currency."""
zzd: CurrencyData = CurrencyData("ZZD", "Testing Dollar #D")
"""The fourth test currency."""
PREFIX: str = "/accounting/currencies"
"""The URL prefix for the currency management."""


class CurrencyCommandTestCase(unittest.TestCase):
    """The account console command test case."""

    def setUp(self) -> None:
        """Sets up the test.
        This is run once per test.

        :return: None.
        """
        self.app: Flask = create_app(is_testing=True)

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
        self.app: Flask = create_app(is_testing=True)

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
                                          "code": zza.code,
                                          "name": zza.name})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], f"{PREFIX}/{zza.code}")

        response = self.client.post(f"{PREFIX}/store",
                                    data={"csrf_token": self.csrf_token,
                                          "code": zzb.code,
                                          "name": zzb.name})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], f"{PREFIX}/{zzb.code}")

    def test_nobody(self) -> None:
        """Test the permission as nobody.

        :return: None.
        """
        client, csrf_token = get_client(self.app, "nobody")
        response: httpx.Response

        response = client.get(PREFIX)
        self.assertEqual(response.status_code, 403)

        response = client.get(f"{PREFIX}/{zza.code}")
        self.assertEqual(response.status_code, 403)

        response = client.get(f"{PREFIX}/create")
        self.assertEqual(response.status_code, 403)

        response = client.post(f"{PREFIX}/store",
                               data={"csrf_token": csrf_token,
                                     "code": zzc.code,
                                     "name": zzc.name})
        self.assertEqual(response.status_code, 403)

        response = client.get(f"{PREFIX}/{zza.code}/edit")
        self.assertEqual(response.status_code, 403)

        response = client.post(f"{PREFIX}/{zza.code}/update",
                               data={"csrf_token": csrf_token,
                                     "code": zzd.code,
                                     "name": zzd.name})
        self.assertEqual(response.status_code, 403)

        response = client.post(f"{PREFIX}/{zzb.code}/delete",
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

        response = client.get(f"{PREFIX}/{zza.code}")
        self.assertEqual(response.status_code, 200)

        response = client.get(f"{PREFIX}/create")
        self.assertEqual(response.status_code, 403)

        response = client.post(f"{PREFIX}/store",
                               data={"csrf_token": csrf_token,
                                     "code": zzc.code,
                                     "name": zzc.name})
        self.assertEqual(response.status_code, 403)

        response = client.get(f"{PREFIX}/{zza.code}/edit")
        self.assertEqual(response.status_code, 403)

        response = client.post(f"{PREFIX}/{zza.code}/update",
                               data={"csrf_token": csrf_token,
                                     "code": zzd.code,
                                     "name": zzd.name})
        self.assertEqual(response.status_code, 403)

        response = client.post(f"{PREFIX}/{zzb.code}/delete",
                               data={"csrf_token": csrf_token})
        self.assertEqual(response.status_code, 403)

    def test_editor(self) -> None:
        """Test the permission as editor.

        :return: None.
        """
        response: httpx.Response

        response = self.client.get(PREFIX)
        self.assertEqual(response.status_code, 200)

        response = self.client.get(f"{PREFIX}/{zza.code}")
        self.assertEqual(response.status_code, 200)

        response = self.client.get(f"{PREFIX}/create")
        self.assertEqual(response.status_code, 200)

        response = self.client.post(f"{PREFIX}/store",
                                    data={"csrf_token": self.csrf_token,
                                          "code": zzc.code,
                                          "name": zzc.name})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], f"{PREFIX}/{zzc.code}")

        response = self.client.get(f"{PREFIX}/{zza.code}/edit")
        self.assertEqual(response.status_code, 200)

        response = self.client.post(f"{PREFIX}/{zza.code}/update",
                                    data={"csrf_token": self.csrf_token,
                                          "code": zzd.code,
                                          "name": zzd.name})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], f"{PREFIX}/{zzd.code}")

        response = self.client.post(f"{PREFIX}/{zzb.code}/delete",
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
        detail_uri: str = f"{PREFIX}/{zzc.code}"
        response: httpx.Response

        with self.app.app_context():
            self.assertEqual({x.code for x in Currency.query.all()},
                             {zza.code, zzb.code})

        # Missing CSRF token
        response = self.client.post(store_uri,
                                    data={"code": zzc.code,
                                          "name": zzc.name})
        self.assertEqual(response.status_code, 400)

        # CSRF token mismatch
        response = self.client.post(store_uri,
                                    data={"csrf_token": f"{self.csrf_token}-2",
                                          "code": zzc.code,
                                          "name": zzc.name})
        self.assertEqual(response.status_code, 400)

        # Empty code
        response = self.client.post(store_uri,
                                    data={"csrf_token": self.csrf_token,
                                          "code": " ",
                                          "name": zzc.name})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)

        # Blocked code, with spaces to be stripped
        response = self.client.post(store_uri,
                                    data={"csrf_token": self.csrf_token,
                                          "code": " create ",
                                          "name": zzc.name})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)

        # Bad code
        response = self.client.post(store_uri,
                                    data={"csrf_token": self.csrf_token,
                                          "code": " zzc ",
                                          "name": zzc.name})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)

        # Empty name
        response = self.client.post(store_uri,
                                    data={"csrf_token": self.csrf_token,
                                          "code": zzc.code,
                                          "name": " "})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)

        # Success, with spaces to be stripped
        response = self.client.post(store_uri,
                                    data={"csrf_token": self.csrf_token,
                                          "code": f" {zzc.code} ",
                                          "name": f" {zzc.name} "})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], detail_uri)

        # Duplicated code
        response = self.client.post(store_uri,
                                    data={"csrf_token": self.csrf_token,
                                          "code": zzc.code,
                                          "name": zzc.name})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)

        with self.app.app_context():
            self.assertEqual({x.code for x in Currency.query.all()},
                             {zza.code, zzb.code, zzc.code})

            zzc_currency: Currency = db.session.get(Currency, zzc.code)
            self.assertEqual(zzc_currency.code, zzc.code)
            self.assertEqual(zzc_currency.name_l10n, zzc.name)

    def test_basic_update(self) -> None:
        """Tests the basic rules to update a user.

        :return: None.
        """
        from accounting.models import Currency
        detail_uri: str = f"{PREFIX}/{zza.code}"
        edit_uri: str = f"{PREFIX}/{zza.code}/edit"
        update_uri: str = f"{PREFIX}/{zza.code}/update"
        detail_c_uri: str = f"{PREFIX}/{zzc.code}"
        response: httpx.Response

        # Success, with spaces to be stripped
        response = self.client.post(update_uri,
                                    data={"csrf_token": self.csrf_token,
                                          "code": f" {zza.code} ",
                                          "name": f" {zza.name}-1 "})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], detail_uri)

        with self.app.app_context():
            zza_currency: Currency = db.session.get(Currency, zza.code)
            self.assertEqual(zza_currency.code, zza.code)
            self.assertEqual(zza_currency.name_l10n, f"{zza.name}-1")

        # Empty code
        response = self.client.post(update_uri,
                                    data={"csrf_token": self.csrf_token,
                                          "code": " ",
                                          "name": zzc.name})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Blocked code, with spaces to be stripped
        response = self.client.post(update_uri,
                                    data={"csrf_token": self.csrf_token,
                                          "code": " create ",
                                          "name": zzc.name})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Bad code
        response = self.client.post(update_uri,
                                    data={"csrf_token": self.csrf_token,
                                          "code": "abc/def",
                                          "name": zzc.name})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Empty name
        response = self.client.post(update_uri,
                                    data={"csrf_token": self.csrf_token,
                                          "code": zzc.code,
                                          "name": " "})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Duplicated code
        response = self.client.post(update_uri,
                                    data={"csrf_token": self.csrf_token,
                                          "code": zzb.code,
                                          "name": zzc.name})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Change code
        response = self.client.post(update_uri,
                                    data={"csrf_token": self.csrf_token,
                                          "code": zzc.code,
                                          "name": zzc.name})
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
        detail_uri: str = f"{PREFIX}/{zza.code}"
        update_uri: str = f"{PREFIX}/{zza.code}/update"
        zza_currency: Currency
        response: httpx.Response

        response = self.client.post(update_uri,
                                    data={"csrf_token": self.csrf_token,
                                          "code": f" {zza.code} ",
                                          "name": f" {zza.name} "})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], detail_uri)

        with self.app.app_context():
            zza_currency = db.session.get(Currency, zza.code)
            self.assertIsNotNone(zza_currency)
            zza_currency.created_at \
                = zza_currency.created_at - timedelta(seconds=5)
            zza_currency.updated_at = zza_currency.created_at
            db.session.commit()

        response = self.client.post(update_uri,
                                    data={"csrf_token": self.csrf_token,
                                          "code": zza.code,
                                          "name": zzc.name})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], detail_uri)

        with self.app.app_context():
            zza_currency = db.session.get(Currency, zza.code)
            self.assertIsNotNone(zza_currency)
            self.assertLess(zza_currency.created_at,
                            zza_currency.updated_at)

    def test_created_updated_by(self) -> None:
        """Tests the created-by and updated-by record.

        :return: None.
        """
        from accounting.models import Currency
        editor_username, editor2_username = "editor", "editor2"
        client, csrf_token = get_client(self.app, editor2_username)
        detail_uri: str = f"{PREFIX}/{zza.code}"
        update_uri: str = f"{PREFIX}/{zza.code}/update"
        response: httpx.Response

        with self.app.app_context():
            zza_currency: Currency = db.session.get(Currency, zza.code)
            self.assertEqual(zza_currency.created_by.username, editor_username)
            self.assertEqual(zza_currency.updated_by.username, editor_username)

        response = client.post(update_uri,
                               data={"csrf_token": csrf_token,
                                     "code": zza.code,
                                     "name": f"{zza.name}-2"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], detail_uri)

        with self.app.app_context():
            zza_currency: Currency = db.session.get(Currency, zza.code)
            self.assertEqual(zza_currency.created_by.username, editor_username)
            self.assertEqual(zza_currency.updated_by.username, editor2_username)

    def test_api_exists(self) -> None:
        """Tests the API to check if a code exists.

        :return: None.
        """
        response: httpx.Response

        response = self.client.get(
            f"/accounting/api/currencies/exists-code?q={zza.code}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(set(data.keys()), {"exists"})
        self.assertTrue(data["exists"])

        response = self.client.get(
            f"/accounting/api/currencies/exists-code?q={zza.code}-1")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(set(data.keys()), {"exists"})
        self.assertFalse(data["exists"])

    def test_l10n(self) -> None:
        """Tests the localization.

        :return: None
        """
        from accounting.models import Currency
        detail_uri: str = f"{PREFIX}/{zza.code}"
        update_uri: str = f"{PREFIX}/{zza.code}/update"
        response: httpx.Response

        with self.app.app_context():
            zza_currency: Currency = db.session.get(Currency, zza.code)
            self.assertEqual(zza_currency.name_l10n, zza.name)
            self.assertEqual(zza_currency.l10n, [])

        set_locale(self.client, self.csrf_token, "zh_Hant")

        response = self.client.post(update_uri,
                                    data={"csrf_token": self.csrf_token,
                                          "code": zza.code,
                                          "name": f"{zza.name}-zh_Hant"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], detail_uri)

        with self.app.app_context():
            zza_currency: Currency = db.session.get(Currency, zza.code)
            self.assertEqual(zza_currency.name_l10n, zza.name)
            self.assertEqual({(x.locale, x.name) for x in zza_currency.l10n},
                             {("zh_Hant", f"{zza.name}-zh_Hant")})

        set_locale(self.client, self.csrf_token, "en")

        response = self.client.post(update_uri,
                                    data={"csrf_token": self.csrf_token,
                                          "code": zza.code,
                                          "name": f"{zza.name}-2"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], detail_uri)

        with self.app.app_context():
            zza_currency: Currency = db.session.get(Currency, zza.code)
            self.assertEqual(zza_currency.name_l10n, f"{zza.name}-2")
            self.assertEqual({(x.locale, x.name) for x in zza_currency.l10n},
                             {("zh_Hant", f"{zza.name}-zh_Hant")})

        set_locale(self.client, self.csrf_token, "zh_Hant")

        response = self.client.post(update_uri,
                                    data={"csrf_token": self.csrf_token,
                                          "code": zza.code,
                                          "name": f"{zza.name}-zh_Hant-2"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], detail_uri)

        with self.app.app_context():
            zza_currency: Currency = db.session.get(Currency, zza.code)
            self.assertEqual(zza_currency.name_l10n, f"{zza.name}-2")
            self.assertEqual({(x.locale, x.name) for x in zza_currency.l10n},
                             {("zh_Hant", f"{zza.name}-zh_Hant-2")})

    def test_delete(self) -> None:
        """Tests to delete a currency.

        :return: None.
        """
        from accounting.models import Currency
        detail_uri: str = f"{PREFIX}/{zza.code}"
        delete_uri: str = f"{PREFIX}/{zza.code}/delete"
        list_uri: str = PREFIX
        response: httpx.Response

        with self.app.app_context():
            self.assertEqual({x.code for x in Currency.query.all()},
                             {zza.code, zzb.code})

        response = self.client.get(detail_uri)
        self.assertEqual(response.status_code, 200)
        response = self.client.post(delete_uri,
                                    data={"csrf_token": self.csrf_token})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], list_uri)

        with self.app.app_context():
            self.assertEqual({x.code for x in Currency.query.all()},
                             {zzb.code})

        response = self.client.get(detail_uri)
        self.assertEqual(response.status_code, 404)
        response = self.client.post(delete_uri,
                                    data={"csrf_token": self.csrf_token})
        self.assertEqual(response.status_code, 404)
