# The Mia! Accounting Project.
# Author: imacat@mail.imacat.idv.tw (imacat), 2023/3/22

#  Copyright (c) 2023-2026 imacat.
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
"""The test for the options.

"""
import datetime as dt
import unittest

import httpx
from flask import Flask

from accounting.utils.next_uri import encode_next
from test_site import db
from testlib import NEXT_URI, Accounts, create_test_app, get_client, \
    get_csrf_token

PREFIX: str = "/accounting/options"
"""The URL prefix for the option management."""


class OptionTestCase(unittest.TestCase):
    """The option test case."""

    def setUp(self) -> None:
        """Sets up the test.
        This is run once per test.

        :return: None.
        """
        self.__app: Flask = create_test_app()
        """The Flask application."""

        with self.__app.app_context():
            from accounting.models import Option
            Option.query.delete()
            self.__encoded_next_uri: str = encode_next(NEXT_URI)
            """The encoded next URI."""

        self.__client: httpx.Client = get_client(self.__app, "admin")
        """The user client."""
        self.__csrf_token: str = get_csrf_token(self.__client)
        """The CSRF token."""

    def tearDown(self) -> None:
        """Tears down the test.
        This is run once per test.

        :return: None.
        """
        with self.__app.app_context():
            db.engine.dispose()

    def test_nobody(self) -> None:
        """Test the permission as nobody.

        :return: None.
        """
        client: httpx.Client = get_client(self.__app, "nobody")
        csrf_token: str = get_csrf_token(client)
        detail_uri: str = f"{PREFIX}?next={self.__encoded_next_uri}"
        edit_uri: str = f"{PREFIX}/edit?next={self.__encoded_next_uri}"
        update_uri: str = f"{PREFIX}/update"
        response: httpx.Response

        response = client.get(detail_uri)
        self.assertEqual(response.status_code, 403)

        response = client.get(edit_uri)
        self.assertEqual(response.status_code, 403)

        response = client.post(update_uri, data=self.__get_form(csrf_token))
        self.assertEqual(response.status_code, 403)

    def test_viewer(self) -> None:
        """Test the permission as viewer.

        :return: None.
        """
        client: httpx.Client = get_client(self.__app, "viewer")
        csrf_token: str = get_csrf_token(client)
        detail_uri: str = f"{PREFIX}?next={self.__encoded_next_uri}"
        edit_uri: str = f"{PREFIX}/edit?next={self.__encoded_next_uri}"
        update_uri: str = f"{PREFIX}/update"
        response: httpx.Response

        response = client.get(detail_uri)
        self.assertEqual(response.status_code, 403)

        response = client.get(edit_uri)
        self.assertEqual(response.status_code, 403)

        response = client.post(update_uri, data=self.__get_form(csrf_token))
        self.assertEqual(response.status_code, 403)

    def test_editor(self) -> None:
        """Test the permission as editor.

        :return: None.
        """
        client: httpx.Client = get_client(self.__app, "editor")
        csrf_token: str = get_csrf_token(client)
        detail_uri: str = f"{PREFIX}?next={self.__encoded_next_uri}"
        edit_uri: str = f"{PREFIX}/edit?next={self.__encoded_next_uri}"
        update_uri: str = f"{PREFIX}/update"
        response: httpx.Response

        response = client.get(detail_uri)
        self.assertEqual(response.status_code, 403)

        response = client.get(edit_uri)
        self.assertEqual(response.status_code, 403)

        response = client.post(update_uri, data=self.__get_form(csrf_token))
        self.assertEqual(response.status_code, 403)

    def test_admin(self) -> None:
        """Test the permission as administrator.

        :return: None.
        """
        detail_uri: str = f"{PREFIX}?next={self.__encoded_next_uri}"
        edit_uri: str = f"{PREFIX}/edit?next={self.__encoded_next_uri}"
        update_uri: str = f"{PREFIX}/update"
        response: httpx.Response

        response = self.__client.get(detail_uri)
        self.assertEqual(response.status_code, 200)

        response = self.__client.get(edit_uri)
        self.assertEqual(response.status_code, 200)

        response = self.__client.post(update_uri, data=self.__get_form())
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], detail_uri)

    def test_set(self) -> None:
        """Test to set the options.

        :return: None.
        """
        from accounting.utils.options import options
        detail_uri: str = f"{PREFIX}?next={self.__encoded_next_uri}"
        edit_uri: str = f"{PREFIX}/edit?next={self.__encoded_next_uri}"
        update_uri: str = f"{PREFIX}/update"
        form: dict[str, str]
        response: httpx.Response

        # Empty currency code
        form = self.__get_form()
        form["default_currency_code"] = " "
        response = self.__client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Non-existing currency code
        form = self.__get_form()
        form["default_currency_code"] = "ZZZ"
        response = self.__client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Empty current account
        form = self.__get_form()
        form["default_ie_account_code"] = " "
        response = self.__client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Non-existing current account
        form = self.__get_form()
        form["default_ie_account_code"] = "9999-999"
        response = self.__client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Not a current account
        form = self.__get_form()
        form["default_ie_account_code"] = Accounts.MEAL
        response = self.__client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Recurring item name empty
        form = self.__get_form()
        key = [x for x in form if x.endswith("-name")][0]
        form[key] = " "
        response = self.__client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Recurring item account empty
        form = self.__get_form()
        key = [x for x in form if x.endswith("-account_code")][0]
        form[key] = " "
        response = self.__client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Recurring item non-expense account
        form = self.__get_form()
        key = [x for x in form
               if x.startswith("recurring-expense-")
               and x.endswith("-account_code")][0]
        form[key] = Accounts.SERVICE
        response = self.__client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Recurring item non-income account
        form = self.__get_form()
        key = [x for x in form
               if x.startswith("recurring-income-")
               and x.endswith("-account_code")][0]
        form[key] = Accounts.UTILITIES
        response = self.__client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Recurring item payable expense
        form = self.__get_form()
        key = [x for x in form
               if x.startswith("recurring-expense-")
               and x.endswith("-account_code")][0]
        form[key] = Accounts.PAYABLE
        response = self.__client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Recurring item receivable income
        form = self.__get_form()
        key = [x for x in form
               if x.startswith("recurring-income-")
               and x.endswith("-account_code")][0]
        form[key] = Accounts.RECEIVABLE
        response = self.__client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Recurring item description template empty
        form = self.__get_form()
        key = [x for x in form if x.endswith("-description_template")][0]
        form[key] = " "
        response = self.__client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Success, with malformed order
        with self.__app.app_context():
            self.assertEqual(options.default_currency_code, "USD")
            self.assertEqual(options.default_ie_account_code, "1111-001")
            self.assertEqual(len(options.recurring.expenses), 0)
            self.assertEqual(len(options.recurring.incomes), 0)

        response = self.__client.post(update_uri, data=self.__get_form())
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], detail_uri)

        with self.__app.app_context():
            self.assertEqual(options.default_currency_code, "EUR")
            self.assertEqual(options.default_ie_account_code, "0000-000")
            self.assertEqual(len(options.recurring.expenses), 4)
            self.assertEqual(options.recurring.expenses[0].account_code,
                             Accounts.INSURANCE)
            self.assertEqual(options.recurring.expenses[1].account_code,
                             Accounts.POSTAGE)
            self.assertEqual(options.recurring.expenses[2].account_code,
                             Accounts.UTILITIES)
            self.assertEqual(options.recurring.expenses[3].account_code,
                             Accounts.RENT_EXPENSE)
            self.assertEqual(len(options.recurring.incomes), 2)
            self.assertEqual(options.recurring.incomes[0].account_code,
                             Accounts.SERVICE)
            self.assertEqual(options.recurring.incomes[1].account_code,
                             Accounts.DONATION)

        # Success, with no recurring data
        form = self.__get_form()
        form = {x: form[x] for x in form if not x.startswith("recurring-")}
        response = self.__client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], detail_uri)

        with self.__app.app_context():
            self.assertEqual(len(options.recurring.expenses), 0)
            self.assertEqual(len(options.recurring.incomes), 0)

    def test_update_not_modified(self) -> None:
        """Tests that the data is not modified.

        :return: None.
        """
        from accounting.models import Option
        detail_uri: str = f"{PREFIX}?next={self.__encoded_next_uri}"
        update_uri: str = f"{PREFIX}/update"
        form: dict[str, str]
        option: Option | None
        resource: httpx.Response

        response = self.__client.post(update_uri, data=self.__get_form())
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], detail_uri)

        with self.__app.app_context():
            option = db.session.get(Option, "recurring")
            self.assertIsNotNone(option)
            timestamp: dt.datetime \
                = option.created_at - dt.timedelta(seconds=5)
            option.created_at = timestamp
            option.updated_at = timestamp
            db.session.commit()

        # The recurring setting was not modified
        form = self.__get_form()
        form["default_currency_code"] = "JPY"
        response = self.__client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], detail_uri)

        with self.__app.app_context():
            option = db.session.get(Option, "recurring")
            self.assertIsNotNone(option)
            self.assertEqual(option.created_at, timestamp)
            self.assertEqual(option.updated_at, timestamp)

        # The recurring setting was modified
        form = self.__get_form()
        key: str = [x for x in form
                    if x.startswith("recurring-expense-")
                    and x.endswith("-account_code")][0]
        form[key] = Accounts.MEAL
        response = self.__client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], detail_uri)

        with self.__app.app_context():
            option = db.session.get(Option, "recurring")
            self.assertIsNotNone(option)
            self.assertLess(option.created_at, option.updated_at)

    def test_created_updated_by(self) -> None:
        """Tests the created-by and updated-by record.

        :return: None.
        """
        from accounting.models import Option
        from accounting.utils.user import get_user_pk
        admin_username, editor_username = "admin", "editor"
        detail_uri: str = f"{PREFIX}?next={self.__encoded_next_uri}"
        update_uri: str = f"{PREFIX}/update"
        option: Option | None
        response: httpx.Response

        response = self.__client.post(update_uri, data=self.__get_form())
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], detail_uri)

        with self.__app.app_context():
            editor_pk: int = get_user_pk(editor_username)
            option = db.session.get(Option, "recurring")
            self.assertIsNotNone(option)
            option.created_by_id = editor_pk
            option.updated_by_id = editor_pk
            db.session.commit()

        form: dict[str, str] = self.__get_form()
        key: str = [x for x in form
                    if x.startswith("recurring-expense-")
                    and x.endswith("-account_code")][0]
        form[key] = Accounts.MEAL
        response = self.__client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], detail_uri)

        with self.__app.app_context():
            option = db.session.get(Option, "recurring")
            self.assertIsNotNone(option)
            self.assertEqual(option.created_by.username, editor_username)
            self.assertEqual(option.updated_by.username, admin_username)

    def __get_form(self, csrf_token: str | None = None) -> dict[str, str]:
        """Returns the option form.

        :param csrf_token: The CSRF token.
        :return: The option form.
        """
        if csrf_token is None:
            csrf_token = self.__csrf_token
        return {"csrf_token": csrf_token,
                "next": self.__encoded_next_uri,
                "default_currency_code": "EUR",
                "default_ie_account_code": "0000-000",
                "recurring-expense-1-name": "Water bill",
                "recurring-expense-1-account_code": Accounts.UTILITIES,
                "recurring-expense-1-description_template":
                    "Water bill for {last_bimonthly_name}",
                "recurring-expense-3-no": "16",
                "recurring-expense-3-name": "Phone bill",
                "recurring-expense-3-account_code": Accounts.POSTAGE,
                "recurring-expense-3-description_template":
                    "Phone bill for {last_month_name}",
                "recurring-expense-12-name": "Rent",
                "recurring-expense-12-account_code": Accounts.RENT_EXPENSE,
                "recurring-expense-12-description_template":
                    "Rent for {this_month_name}",
                "recurring-expense-26-no": "7",
                "recurring-expense-26-name": "Insurance",
                "recurring-expense-26-account_code": Accounts.INSURANCE,
                "recurring-expense-26-description_template":
                    "Insurance for {last_month_name}",
                "recurring-income-2-no": "12",
                "recurring-income-2-name": "Donation",
                "recurring-income-2-account_code": Accounts.DONATION,
                "recurring-income-2-description_template":
                    "Donation for {this_month_name}",
                "recurring-income-15-no": "4",
                "recurring-income-15-name": "Payroll",
                "recurring-income-15-account_code": Accounts.SERVICE,
                "recurring-income-15-description_template":
                    "Payroll for {last_month_name}"}
