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
import time
import unittest

import httpx
from click.testing import Result
from flask import Flask
from flask.testing import FlaskCliRunner

from test_site import create_app
from testlib import get_client, set_locale


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
            from accounting.database import db
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
        from accounting.models import Currency, CurrencyL10n
        runner: FlaskCliRunner = self.app.test_cli_runner()
        with self.app.app_context():
            result: Result = runner.invoke(
                args=["accounting-init-currencies", "-u", "editor"])
            self.assertEqual(result.exit_code, 0)
            currencies: list[Currency] = Currency.query.all()
            l10n: list[CurrencyL10n] = CurrencyL10n.query.all()
        self.assertEqual(len(currencies), 2)
        self.assertEqual(len(l10n), 2 * 2)
        l10n_keys: set[str] = {f"{x.currency_code}-{x.locale}" for x in l10n}
        for currency in currencies:
            self.assertIn(f"{currency.code}-zh_Hant", l10n_keys)
            self.assertIn(f"{currency.code}-zh_Hant", l10n_keys)


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
            from accounting.database import db
            from accounting.models import Currency, CurrencyL10n
            result: Result
            result = runner.invoke(args="init-db")
            self.assertEqual(result.exit_code, 0)
            CurrencyL10n.query.delete()
            Currency.query.delete()
            db.session.commit()

        self.client, self.csrf_token = get_client(self, self.app, "editor")
        response: httpx.Response

        response = self.client.post("/accounting/currencies/store",
                                    data={"csrf_token": self.csrf_token,
                                          "code": "ZZA",
                                          "name": "Testing Dollar #A"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"],
                         "/accounting/currencies/ZZA")

        response = self.client.post("/accounting/currencies/store",
                                    data={"csrf_token": self.csrf_token,
                                          "code": "ZZB",
                                          "name": "Testing Dollar #B"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"],
                         "/accounting/currencies/ZZB")

    def test_nobody(self) -> None:
        """Test the permission as nobody.

        :return: None.
        """
        client, csrf_token = get_client(self, self.app, "nobody")
        response: httpx.Response

        response = client.get("/accounting/currencies")
        self.assertEqual(response.status_code, 403)

        response = client.get("/accounting/currencies/ZZA")
        self.assertEqual(response.status_code, 403)

        response = client.get("/accounting/currencies/create")
        self.assertEqual(response.status_code, 403)

        response = client.post("/accounting/currencies/store",
                               data={"csrf_token": csrf_token,
                                     "code": "ZZC",
                                     "name": "Testing Dollar #C"})
        self.assertEqual(response.status_code, 403)

        response = client.get("/accounting/currencies/ZZA/edit")
        self.assertEqual(response.status_code, 403)

        response = client.post("/accounting/currencies/ZZA/update",
                               data={"csrf_token": csrf_token,
                                     "code": "ZZD",
                                     "name": "Testing Dollar #D"})
        self.assertEqual(response.status_code, 403)

        response = client.post("/accounting/currencies/ZZB/delete",
                               data={"csrf_token": csrf_token})
        self.assertEqual(response.status_code, 403)

    def test_viewer(self) -> None:
        """Test the permission as viewer.

        :return: None.
        """
        client, csrf_token = get_client(self, self.app, "viewer")
        response: httpx.Response

        response = client.get("/accounting/currencies")
        self.assertEqual(response.status_code, 200)

        response = client.get("/accounting/currencies/ZZA")
        self.assertEqual(response.status_code, 200)

        response = client.get("/accounting/currencies/create")
        self.assertEqual(response.status_code, 403)

        response = client.post("/accounting/currencies/store",
                               data={"csrf_token": csrf_token,
                                     "code": "ZZC",
                                     "name": "Testing Dollar #C"})
        self.assertEqual(response.status_code, 403)

        response = client.get("/accounting/currencies/ZZA/edit")
        self.assertEqual(response.status_code, 403)

        response = client.post("/accounting/currencies/ZZA/update",
                               data={"csrf_token": csrf_token,
                                     "code": "ZZD",
                                     "name": "Testing Dollar #D"})
        self.assertEqual(response.status_code, 403)

        response = client.post("/accounting/currencies/ZZB/delete",
                               data={"csrf_token": csrf_token})
        self.assertEqual(response.status_code, 403)

    def test_editor(self) -> None:
        """Test the permission as editor.

        :return: None.
        """
        response: httpx.Response

        response = self.client.get("/accounting/currencies")
        self.assertEqual(response.status_code, 200)

        response = self.client.get("/accounting/currencies/ZZA")
        self.assertEqual(response.status_code, 200)

        response = self.client.get("/accounting/currencies/create")
        self.assertEqual(response.status_code, 200)

        response = self.client.post("/accounting/currencies/store",
                                    data={"csrf_token": self.csrf_token,
                                          "code": "ZZC",
                                          "name": "Testing Dollar #C"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"],
                         "/accounting/currencies/ZZC")

        response = self.client.get("/accounting/currencies/ZZA/edit")
        self.assertEqual(response.status_code, 200)

        response = self.client.post("/accounting/currencies/ZZA/update",
                                    data={"csrf_token": self.csrf_token,
                                          "code": "ZZD",
                                          "name": "Testing Dollar #D"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"],
                         "/accounting/currencies/ZZD")

        response = self.client.post("/accounting/currencies/ZZB/delete",
                                    data={"csrf_token": self.csrf_token})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"],
                         "/accounting/currencies")

    def test_add(self) -> None:
        """Tests to add the currencies.

        :return: None.
        """
        from accounting.models import Currency
        from test_site import db
        zzc_code, zzc_name = "ZZC", "Testing Dollar #C"
        create_uri: str = "/accounting/currencies/create"
        store_uri: str = "/accounting/currencies/store"
        response: httpx.Response

        with self.app.app_context():
            self.assertEqual({x.code for x in Currency.query.all()},
                             {"ZZA", "ZZB"})

        # Missing CSRF token
        response = self.client.post(store_uri,
                                    data={"code": zzc_code,
                                          "name": zzc_name})
        self.assertEqual(response.status_code, 400)

        # CSRF token mismatch
        response = self.client.post(store_uri,
                                    data={"csrf_token": f"{self.csrf_token}-2",
                                          "code": zzc_code,
                                          "name": zzc_name})
        self.assertEqual(response.status_code, 400)

        # Empty code
        response = self.client.post(store_uri,
                                    data={"csrf_token": self.csrf_token,
                                          "code": " ",
                                          "name": zzc_name})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)

        # Blocked code, with spaces to be stripped
        response = self.client.post(store_uri,
                                    data={"csrf_token": self.csrf_token,
                                          "code": " create ",
                                          "name": zzc_name})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)

        # Bad code
        response = self.client.post(store_uri,
                                    data={"csrf_token": self.csrf_token,
                                          "code": " zzc ",
                                          "name": zzc_name})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)

        # Empty name
        response = self.client.post(store_uri,
                                    data={"csrf_token": self.csrf_token,
                                          "code": zzc_code,
                                          "name": " "})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)

        # Success, with spaces to be stripped
        response = self.client.post(store_uri,
                                    data={"csrf_token": self.csrf_token,
                                          "code": f" {zzc_code} ",
                                          "name": f" {zzc_name} "})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"],
                         f"/accounting/currencies/{zzc_code}")

        # Duplicated code
        response = self.client.post(store_uri,
                                    data={"csrf_token": self.csrf_token,
                                          "code": zzc_code,
                                          "name": zzc_name})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)

        with self.app.app_context():
            self.assertEqual({x.code for x in Currency.query.all()},
                             {"ZZA", "ZZB", zzc_code})

            zzc: Currency = db.session.get(Currency, zzc_code)
            self.assertEqual(zzc.code, zzc_code)
            self.assertEqual(zzc.name_l10n, zzc_name)

    def test_basic_update(self) -> None:
        """Tests the basic rules to update a user.

        :return: None.
        """
        from accounting.models import Currency
        from test_site import db
        zza_code: str = "ZZA"
        zzc_code, zzc_name = "ZZC", "Testing Dollar #C"
        edit_uri: str = f"/accounting/currencies/{zza_code}/edit"
        update_uri: str = f"/accounting/currencies/{zza_code}/update"
        response: httpx.Response

        # Success, with spaces to be stripped
        response = self.client.post(update_uri,
                                    data={"csrf_token": self.csrf_token,
                                          "code": f" {zza_code} ",
                                          "name": f" {zzc_name} "})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"],
                         f"/accounting/currencies/{zza_code}")

        with self.app.app_context():
            zza: Currency = db.session.get(Currency, zza_code)
            self.assertEqual(zza.code, zza_code)
            self.assertEqual(zza.name_l10n, zzc_name)

        # Empty code
        response = self.client.post(update_uri,
                                    data={"csrf_token": self.csrf_token,
                                          "code": " ",
                                          "name": zzc_name})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Blocked code, with spaces to be stripped
        response = self.client.post(update_uri,
                                    data={"csrf_token": self.csrf_token,
                                          "code": " create ",
                                          "name": zzc_name})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Bad code
        response = self.client.post(update_uri,
                                    data={"csrf_token": self.csrf_token,
                                          "code": "abc/def",
                                          "name": zzc_name})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Empty name
        response = self.client.post(update_uri,
                                    data={"csrf_token": self.csrf_token,
                                          "code": zzc_code,
                                          "name": " "})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Duplicated code
        response = self.client.post(update_uri,
                                    data={"csrf_token": self.csrf_token,
                                          "code": "ZZB",
                                          "name": zzc_name})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Change code
        response = self.client.post(update_uri,
                                    data={"csrf_token": self.csrf_token,
                                          "code": zzc_code,
                                          "name": zzc_name})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"],
                         f"/accounting/currencies/{zzc_code}")

        response = self.client.get(f"/accounting/currencies/{zza_code}")
        self.assertEqual(response.status_code, 404)

        response = self.client.get(f"/accounting/currencies/{zzc_code}")
        self.assertEqual(response.status_code, 200)

    def test_update_not_modified(self) -> None:
        """Tests that the data is not modified.

        :return: None.
        """
        from accounting.models import Currency
        from test_site import db
        zza_code, zza_name = "ZZA", "Testing Dollar #A"
        detail_uri: str = f"/accounting/currencies/{zza_code}"
        update_uri: str = f"/accounting/currencies/{zza_code}/update"
        response: httpx.Response
        time.sleep(1)

        response = self.client.post(update_uri,
                                    data={"csrf_token": self.csrf_token,
                                          "code": f" {zza_code} ",
                                          "name": f" {zza_name} "})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], detail_uri)

        with self.app.app_context():
            zza: Currency = db.session.get(Currency, zza_code)
            self.assertIsNotNone(zza)
            self.assertEqual(zza.created_at, zza.updated_at)

        response = self.client.post(update_uri,
                                    data={"csrf_token": self.csrf_token,
                                          "code": zza_code,
                                          "name": "Testing Dollar #C"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], detail_uri)

        with self.app.app_context():
            zza: Currency = db.session.get(Currency, zza_code)
            self.assertIsNotNone(zza)
            self.assertNotEqual(zza.created_at, zza.updated_at)

    def test_created_updated_by(self) -> None:
        """Tests the created-by and updated-by record.

        :return: None.
        """
        from accounting.models import Currency
        from test_site import db
        zza_code, zza_name = "ZZA", "Testing Dollar #A"
        editor_username, editor2_username = "editor", "editor2"
        client, csrf_token = get_client(self, self.app, editor2_username)
        response: httpx.Response

        with self.app.app_context():
            currency: Currency = db.session.get(Currency, zza_code)
            self.assertEqual(currency.created_by.username, editor_username)
            self.assertEqual(currency.updated_by.username, editor_username)

        response = client.post(f"/accounting/currencies/{zza_code}/update",
                               data={"csrf_token": csrf_token,
                                     "code": zza_code,
                                     "name": f"{zza_name}-2"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"],
                         f"/accounting/currencies/{zza_code}")

        with self.app.app_context():
            currency: Currency = db.session.get(Currency, zza_code)
            self.assertEqual(currency.created_by.username, editor_username)
            self.assertEqual(currency.updated_by.username, editor2_username)

    def test_l10n(self) -> None:
        """Tests the localization.

        :return: None
        """
        from accounting.models import Currency
        from test_site import db
        zza_code, zza_name = "ZZA", "Testing Dollar #A"
        detail_uri: str = f"/accounting/currencies/{zza_code}"
        update_uri: str = f"/accounting/currencies/{zza_code}/update"

        with self.app.app_context():
            zza: Currency = db.session.get(Currency, zza_code)
            self.assertEqual(zza.name_l10n, zza_name)
            self.assertEqual(zza.l10n, [])

        set_locale(self, self.client, self.csrf_token, "zh_Hant")

        response = self.client.post(update_uri,
                                    data={"csrf_token": self.csrf_token,
                                          "code": zza_code,
                                          "name": f"{zza_name}-zh_Hant"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], detail_uri)

        with self.app.app_context():
            zza: Currency = db.session.get(Currency, zza_code)
            self.assertEqual(zza.name_l10n, zza_name)
            self.assertEqual({(x.locale, x.name) for x in zza.l10n},
                             {("zh_Hant", f"{zza_name}-zh_Hant")})

        set_locale(self, self.client, self.csrf_token, "en")

        response = self.client.post(update_uri,
                                    data={"csrf_token": self.csrf_token,
                                          "code": zza_code,
                                          "name": f"{zza_name}-2"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], detail_uri)

        with self.app.app_context():
            zza: Currency = db.session.get(Currency, zza_code)
            self.assertEqual(zza.name_l10n, f"{zza_name}-2")
            self.assertEqual({(x.locale, x.name) for x in zza.l10n},
                             {("zh_Hant", f"{zza_name}-zh_Hant")})

        set_locale(self, self.client, self.csrf_token, "zh_Hant")

        response = self.client.post(update_uri,
                                    data={"csrf_token": self.csrf_token,
                                          "code": zza_code,
                                          "name": f"{zza_name}-zh_Hant-2"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], detail_uri)

        with self.app.app_context():
            zza: Currency = db.session.get(Currency, zza_code)
            self.assertEqual(zza.name_l10n, f"{zza_name}-2")
            self.assertEqual({(x.locale, x.name) for x in zza.l10n},
                             {("zh_Hant", f"{zza_name}-zh_Hant-2")})

    def test_delete(self) -> None:
        """Tests to delete a currency.

        :return: None.
        """
        from accounting.models import Currency
        zza_code, zzb_code = "ZZA", "ZZB"
        response: httpx.Response

        with self.app.app_context():
            self.assertEqual({x.code for x in Currency.query.all()},
                             {zza_code, zzb_code})

        response = self.client.get(f"/accounting/currencies/{zza_code}")
        self.assertEqual(response.status_code, 200)
        response = self.client.post(
            f"/accounting/currencies/{zza_code}/delete",
            data={"csrf_token": self.csrf_token})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"],
                         "/accounting/currencies")

        with self.app.app_context():
            self.assertEqual({x.code for x in Currency.query.all()},
                             {zzb_code})

        response = self.client.get(f"/accounting/currencies/{zza_code}")
        self.assertEqual(response.status_code, 404)
        response = self.client.post(
            f"/accounting/currencies/{zza_code}/delete",
            data={"csrf_token": self.csrf_token})
        self.assertEqual(response.status_code, 404)
