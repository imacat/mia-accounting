# The Mia! Accounting Flask Project.
# Author: imacat@mail.imacat.idv.tw (imacat), 2023/2/24

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
"""The test for the voucher management.

"""
import unittest
from datetime import date, timedelta
from decimal import Decimal

import httpx
from click.testing import Result
from flask import Flask
from flask.testing import FlaskCliRunner

from test_site import db
from testlib import create_test_app, get_client
from testlib_voucher import NEXT_URI, NON_EMPTY_NOTE, EMPTY_NOTE, Accounts, \
    get_add_form, get_unchanged_update_form, get_update_form, \
    match_voucher_detail, set_negative_amount, remove_debit_in_a_currency, \
    remove_credit_in_a_currency, add_voucher

PREFIX: str = "/accounting/vouchers"
"""The URL prefix for the voucher management."""
RETURN_TO_URI: str = "/accounting/reports"
"""The URL to return to after the operation."""


class CashReceiptVoucherTestCase(unittest.TestCase):
    """The cash receipt voucher test case."""

    def setUp(self) -> None:
        """Sets up the test.
        This is run once per test.

        :return: None.
        """
        self.app: Flask = create_test_app()

        runner: FlaskCliRunner = self.app.test_cli_runner()
        with self.app.app_context():
            from accounting.models import BaseAccount, Voucher, \
                VoucherLineItem
            result: Result
            result = runner.invoke(args="init-db")
            self.assertEqual(result.exit_code, 0)
            if BaseAccount.query.first() is None:
                result = runner.invoke(args="accounting-init-base")
                self.assertEqual(result.exit_code, 0)
            result = runner.invoke(args=["accounting-init-currencies",
                                         "-u", "editor"])
            self.assertEqual(result.exit_code, 0)
            result = runner.invoke(args=["accounting-init-accounts",
                                         "-u", "editor"])
            self.assertEqual(result.exit_code, 0)
            Voucher.query.delete()
            VoucherLineItem.query.delete()

        self.client, self.csrf_token = get_client(self.app, "editor")

    def test_nobody(self) -> None:
        """Test the permission as nobody.

        :return: None.
        """
        client, csrf_token = get_client(self.app, "nobody")
        voucher_id: int = add_voucher(self.client, self.__get_add_form())
        add_form: dict[str, str] = self.__get_add_form()
        add_form["csrf_token"] = csrf_token
        update_form: dict[str, str] = self.__get_update_form(voucher_id)
        update_form["csrf_token"] = csrf_token
        response: httpx.Response

        response = client.get(f"{PREFIX}/{voucher_id}")
        self.assertEqual(response.status_code, 403)

        response = client.get(f"{PREFIX}/create/receipt")
        self.assertEqual(response.status_code, 403)

        response = client.post(f"{PREFIX}/store/receipt", data=add_form)
        self.assertEqual(response.status_code, 403)

        response = client.get(f"{PREFIX}/{voucher_id}/edit")
        self.assertEqual(response.status_code, 403)

        response = client.post(f"{PREFIX}/{voucher_id}/update",
                               data=update_form)
        self.assertEqual(response.status_code, 403)

        response = client.post(f"{PREFIX}/{voucher_id}/delete",
                               data={"csrf_token": csrf_token})
        self.assertEqual(response.status_code, 403)

    def test_viewer(self) -> None:
        """Test the permission as viewer.

        :return: None.
        """
        client, csrf_token = get_client(self.app, "viewer")
        voucher_id: int = add_voucher(self.client, self.__get_add_form())
        add_form: dict[str, str] = self.__get_add_form()
        add_form["csrf_token"] = csrf_token
        update_form: dict[str, str] = self.__get_update_form(voucher_id)
        update_form["csrf_token"] = csrf_token
        response: httpx.Response

        response = client.get(f"{PREFIX}/{voucher_id}")
        self.assertEqual(response.status_code, 200)

        response = client.get(f"{PREFIX}/create/receipt")
        self.assertEqual(response.status_code, 403)

        response = client.post(f"{PREFIX}/store/receipt", data=add_form)
        self.assertEqual(response.status_code, 403)

        response = client.get(f"{PREFIX}/{voucher_id}/edit")
        self.assertEqual(response.status_code, 403)

        response = client.post(f"{PREFIX}/{voucher_id}/update",
                               data=update_form)
        self.assertEqual(response.status_code, 403)

        response = client.post(f"{PREFIX}/{voucher_id}/delete",
                               data={"csrf_token": csrf_token})
        self.assertEqual(response.status_code, 403)

    def test_editor(self) -> None:
        """Test the permission as editor.

        :return: None.
        """
        voucher_id: int = add_voucher(self.client, self.__get_add_form())
        add_form: dict[str, str] = self.__get_add_form()
        update_form: dict[str, str] = self.__get_update_form(voucher_id)
        response: httpx.Response

        response = self.client.get(f"{PREFIX}/{voucher_id}")
        self.assertEqual(response.status_code, 200)

        response = self.client.get(f"{PREFIX}/create/receipt")
        self.assertEqual(response.status_code, 200)

        response = self.client.post(f"{PREFIX}/store/receipt",
                                    data=add_form)
        self.assertEqual(response.status_code, 302)
        match_voucher_detail(response.headers["Location"])

        response = self.client.get(f"{PREFIX}/{voucher_id}/edit")
        self.assertEqual(response.status_code, 200)

        response = self.client.post(f"{PREFIX}/{voucher_id}/update",
                                    data=update_form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"],
                         f"{PREFIX}/{voucher_id}?next=%2F_next")

        response = self.client.post(f"{PREFIX}/{voucher_id}/delete",
                                    data={"csrf_token": self.csrf_token})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], RETURN_TO_URI)

    def test_add(self) -> None:
        """Tests to add the vouchers.

        :return: None.
        """
        from accounting.models import Voucher, VoucherCurrency
        create_uri: str = f"{PREFIX}/create/receipt?next=%2F_next"
        store_uri: str = f"{PREFIX}/store/receipt"
        response: httpx.Response
        form: dict[str, str]
        voucher: Voucher | None

        # No currency content
        form = self.__get_add_form()
        form = {x: form[x] for x in form if not x.startswith("currency-")}
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)

        # Missing currency
        form = self.__get_add_form()
        key: str = [x for x in form.keys() if x.endswith("-code")][0]
        form[key] = ""
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)

        # Non-existing currency
        form = self.__get_add_form()
        key: str = [x for x in form.keys() if x.endswith("-code")][0]
        form[key] = "ZZZ"
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)

        # No credit content in a currency
        form = self.__get_add_form()
        remove_credit_in_a_currency(form)
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)

        # Non-existing account
        form = self.__get_add_form()
        key: str = [x for x in form.keys() if x.endswith("-account_code")][0]
        form[key] = "9999-999"
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)

        # Non-credit account
        form = self.__get_add_form()
        key: str = [x for x in form.keys()
                    if x.endswith("-account_code") and "-credit-" in x][0]
        form[key] = Accounts.OFFICE
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)

        # A receivable line item cannot start from the credit side
        form = self.__get_add_form()
        key: str = [x for x in form.keys()
                    if x.endswith("-account_code") and "-credit-" in x][0]
        form[key] = Accounts.RECEIVABLE
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)

        # Negative amount
        form = self.__get_add_form()
        set_negative_amount(form)
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)

        # Success
        response = self.client.post(store_uri,
                                    data=self.__get_add_form())
        self.assertEqual(response.status_code, 302)
        voucher_id: int = match_voucher_detail(response.headers["Location"])

        with self.app.app_context():
            voucher = db.session.get(Voucher, voucher_id)
            self.assertIsNotNone(voucher)
            currencies: list[VoucherCurrency] = voucher.currencies
            self.assertEqual(len(currencies), 3)

            self.assertEqual(currencies[0].code, "JPY")
            self.assertEqual(len(currencies[0].debit), 1)
            self.assertEqual(currencies[0].debit[0].no, 1)
            self.assertEqual(currencies[0].debit[0].account.code,
                             Accounts.CASH)
            self.assertIsNone(currencies[0].debit[0].summary)
            self.assertEqual(currencies[0].debit[0].amount,
                             sum([x.amount for x in currencies[0].credit]))
            self.assertEqual(len(currencies[0].credit), 2)
            self.assertEqual(currencies[0].credit[0].no, 1)
            self.assertEqual(currencies[0].credit[0].account.code,
                             Accounts.DONATION)
            self.assertEqual(currencies[0].credit[1].no, 2)
            self.assertEqual(currencies[0].credit[1].account.code,
                             Accounts.AGENCY)

            self.assertEqual(currencies[1].code, "USD")
            self.assertEqual(len(currencies[1].debit), 1)
            self.assertEqual(currencies[1].debit[0].no, 2)
            self.assertEqual(currencies[1].debit[0].account.code,
                             Accounts.CASH)
            self.assertIsNone(currencies[1].debit[0].summary)
            self.assertEqual(currencies[1].debit[0].amount,
                             sum([x.amount for x in currencies[1].credit]))
            self.assertEqual(len(currencies[1].credit), 3)
            self.assertEqual(currencies[1].credit[0].no, 3)
            self.assertEqual(currencies[1].credit[0].account.code,
                             Accounts.SERVICE)
            self.assertEqual(currencies[1].credit[1].no, 4)
            self.assertEqual(currencies[1].credit[1].account.code,
                             Accounts.SALES)
            self.assertEqual(currencies[1].credit[2].no, 5)
            self.assertEqual(currencies[1].credit[2].account.code,
                             Accounts.INTEREST)

            self.assertEqual(currencies[2].code, "TWD")
            self.assertEqual(len(currencies[2].debit), 1)
            self.assertEqual(currencies[2].debit[0].no, 3)
            self.assertEqual(currencies[2].debit[0].account.code,
                             Accounts.CASH)
            self.assertIsNone(currencies[2].debit[0].summary)
            self.assertEqual(currencies[2].debit[0].amount,
                             sum([x.amount for x in currencies[2].credit]))
            self.assertEqual(len(currencies[2].credit), 2)
            self.assertEqual(currencies[2].credit[0].no, 6)
            self.assertEqual(currencies[2].credit[0].account.code,
                             Accounts.RENT)
            self.assertEqual(currencies[2].credit[1].no, 7)
            self.assertEqual(currencies[2].credit[1].account.code,
                             Accounts.DONATION)

            self.assertEqual(voucher.note, NON_EMPTY_NOTE)

        # Success, with empty note
        form = self.__get_add_form()
        form["note"] = EMPTY_NOTE
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        voucher_id: int = match_voucher_detail(response.headers["Location"])

        with self.app.app_context():
            voucher = db.session.get(Voucher, voucher_id)
            self.assertIsNotNone(voucher)
            self.assertIsNone(voucher.note)

    def test_basic_update(self) -> None:
        """Tests the basic rules to update a voucher.

        :return: None.
        """
        from accounting.models import Voucher, VoucherCurrency
        voucher_id: int = add_voucher(self.client, self.__get_add_form())
        detail_uri: str = f"{PREFIX}/{voucher_id}?next=%2F_next"
        edit_uri: str = f"{PREFIX}/{voucher_id}/edit?next=%2F_next"
        update_uri: str = f"{PREFIX}/{voucher_id}/update"
        form_0: dict[str, str] = self.__get_update_form(voucher_id)

        with self.app.app_context():
            voucher = db.session.get(Voucher, voucher_id)
            self.assertIsNotNone(voucher)
            currencies0: list[VoucherCurrency] = voucher.currencies
            old_id: set[int] = set()
            for currency in currencies0:
                old_id.update({x.id for x in currency.debit})

        # No currency content
        form = form_0.copy()
        form = {x: form[x] for x in form if not x.startswith("currency-")}
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Missing currency
        form = form_0.copy()
        key: str = [x for x in form.keys() if x.endswith("-code")][0]
        form[key] = ""
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Non-existing currency
        form = form_0.copy()
        key: str = [x for x in form.keys() if x.endswith("-code")][0]
        form[key] = "ZZZ"
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # No credit content in a currency
        form = form_0.copy()
        remove_credit_in_a_currency(form)
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Non-existing account
        form: dict[str, str] = form_0.copy()
        key: str = [x for x in form.keys() if x.endswith("-account_code")][0]
        form[key] = "9999-999"
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Non-credit account
        form: dict[str, str] = form_0.copy()
        key: str = [x for x in form.keys()
                    if x.endswith("-account_code") and "-credit-" in x][0]
        form[key] = Accounts.OFFICE
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # A receivable line item cannot start from the credit side
        form = self.__get_add_form()
        key: str = [x for x in form.keys()
                    if x.endswith("-account_code") and "-credit-" in x][0]
        form[key] = Accounts.RECEIVABLE
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Negative amount
        form: dict[str, str] = form_0.copy()
        set_negative_amount(form)
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Success
        response = self.client.post(update_uri, data=form_0)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], detail_uri)

        with self.app.app_context():
            voucher = db.session.get(Voucher, voucher_id)
            self.assertIsNotNone(voucher)
            currencies1: list[VoucherCurrency] = voucher.currencies
            self.assertEqual(len(currencies1), 3)

            self.assertEqual(currencies1[0].code, "AUD")
            self.assertEqual(len(currencies1[0].debit), 1)
            self.assertNotIn(currencies1[0].debit[0].id, old_id)
            self.assertEqual(currencies1[0].debit[0].no, 1)
            self.assertEqual(currencies1[0].debit[0].account.code,
                             Accounts.CASH)
            self.assertIsNone(currencies1[0].debit[0].summary)
            self.assertEqual(currencies1[0].debit[0].amount,
                             sum([x.amount for x in currencies1[0].credit]))
            self.assertEqual(len(currencies1[0].credit), 2)
            self.assertNotIn(currencies1[0].credit[0].id, old_id)
            self.assertEqual(currencies1[0].credit[0].no, 1)
            self.assertEqual(currencies1[0].credit[0].account.code,
                             Accounts.DONATION)
            self.assertNotIn(currencies1[0].credit[1].id, old_id)
            self.assertEqual(currencies1[0].credit[1].no, 2)
            self.assertEqual(currencies1[0].credit[1].account.code,
                             Accounts.RENT)

            self.assertEqual(currencies1[1].code, "EUR")
            self.assertEqual(len(currencies1[1].debit), 1)
            self.assertNotIn(currencies1[1].debit[0].id, old_id)
            self.assertEqual(currencies1[1].debit[0].no, 2)
            self.assertEqual(currencies1[1].debit[0].account.code,
                             Accounts.CASH)
            self.assertIsNone(currencies1[1].debit[0].summary)
            self.assertEqual(currencies1[1].debit[0].amount,
                             sum([x.amount for x in currencies1[1].credit]))
            self.assertEqual(len(currencies1[1].credit), 2)
            self.assertEqual(currencies1[1].credit[0].id,
                             currencies0[2].credit[0].id)
            self.assertEqual(currencies1[1].credit[0].no, 3)
            self.assertEqual(currencies1[1].credit[0].account.code,
                             Accounts.RENT)
            self.assertEqual(currencies1[1].credit[1].id,
                             currencies0[2].credit[1].id)
            self.assertEqual(currencies1[1].credit[1].no, 4)
            self.assertEqual(currencies1[1].credit[1].account.code,
                             Accounts.DONATION)

            self.assertEqual(currencies1[2].code, "USD")
            self.assertEqual(len(currencies1[2].debit), 1)
            self.assertEqual(currencies1[2].debit[0].id,
                             currencies0[1].debit[0].id)
            self.assertEqual(currencies1[2].debit[0].no, 3)
            self.assertEqual(currencies1[2].debit[0].account.code,
                             Accounts.CASH)
            self.assertIsNone(currencies1[2].debit[0].summary)
            self.assertEqual(currencies1[2].debit[0].amount,
                             sum([x.amount for x in currencies1[2].credit]))
            self.assertEqual(len(currencies1[2].credit), 3)
            self.assertNotIn(currencies1[2].credit[0].id, old_id)
            self.assertEqual(currencies1[2].credit[0].no, 5)
            self.assertEqual(currencies1[2].credit[0].account.code,
                             Accounts.AGENCY)
            self.assertEqual(currencies1[2].credit[1].id,
                             currencies0[1].credit[2].id)
            self.assertEqual(currencies1[2].credit[1].no, 6)
            self.assertEqual(currencies1[2].credit[1].account.code,
                             Accounts.INTEREST)
            self.assertEqual(currencies1[2].credit[2].id,
                             currencies0[1].credit[0].id)
            self.assertEqual(currencies1[2].credit[2].no, 7)
            self.assertEqual(currencies1[2].credit[2].account.code,
                             Accounts.SERVICE)

            self.assertEqual(voucher.note, NON_EMPTY_NOTE)

    def test_update_not_modified(self) -> None:
        """Tests that the data is not modified.

        :return: None.
        """
        from accounting.models import Voucher
        voucher_id: int = add_voucher(self.client, self.__get_add_form())
        detail_uri: str = f"{PREFIX}/{voucher_id}?next=%2F_next"
        update_uri: str = f"{PREFIX}/{voucher_id}/update"
        voucher: Voucher
        response: httpx.Response

        response = self.client.post(
            update_uri, data=self.__get_unchanged_update_form(voucher_id))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], detail_uri)

        with self.app.app_context():
            voucher = db.session.get(Voucher, voucher_id)
            self.assertIsNotNone(voucher)
            voucher.created_at = voucher.created_at - timedelta(seconds=5)
            voucher.updated_at = voucher.created_at
            db.session.commit()

        response = self.client.post(
            update_uri, data=self.__get_update_form(voucher_id))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], detail_uri)

        with self.app.app_context():
            voucher = db.session.get(Voucher, voucher_id)
            self.assertIsNotNone(voucher)
            self.assertLess(voucher.created_at, voucher.updated_at)

    def test_created_updated_by(self) -> None:
        """Tests the created-by and updated-by record.

        :return: None.
        """
        from accounting.models import Voucher
        voucher_id: int = add_voucher(self.client, self.__get_add_form())
        editor_username, editor2_username = "editor", "editor2"
        client, csrf_token = get_client(self.app, editor2_username)
        detail_uri: str = f"{PREFIX}/{voucher_id}?next=%2F_next"
        update_uri: str = f"{PREFIX}/{voucher_id}/update"
        voucher: Voucher
        response: httpx.Response

        with self.app.app_context():
            voucher = db.session.get(Voucher, voucher_id)
            self.assertEqual(voucher.created_by.username, editor_username)
            self.assertEqual(voucher.updated_by.username, editor_username)

        form: dict[str, str] = self.__get_update_form(voucher_id)
        form["csrf_token"] = csrf_token
        response = client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], detail_uri)

        with self.app.app_context():
            voucher = db.session.get(Voucher, voucher_id)
            self.assertEqual(voucher.created_by.username, editor_username)
            self.assertEqual(voucher.updated_by.username, editor2_username)

    def test_delete(self) -> None:
        """Tests to delete a voucher.

        :return: None.
        """
        voucher_id: int = add_voucher(self.client, self.__get_add_form())
        detail_uri: str = f"{PREFIX}/{voucher_id}?next=%2F_next"
        delete_uri: str = f"{PREFIX}/{voucher_id}/delete"
        response: httpx.Response

        response = self.client.get(detail_uri)
        self.assertEqual(response.status_code, 200)
        response = self.client.post(delete_uri,
                                    data={"csrf_token": self.csrf_token,
                                          "next": NEXT_URI})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], NEXT_URI)

        response = self.client.get(detail_uri)
        self.assertEqual(response.status_code, 404)
        response = self.client.post(delete_uri,
                                    data={"csrf_token": self.csrf_token,
                                          "next": NEXT_URI})
        self.assertEqual(response.status_code, 404)

    def __get_add_form(self) -> dict[str, str]:
        """Returns the form data to add a new voucher.

        :return: The form data to add a new voucher.
        """
        form: dict[str, str] = get_add_form(self.csrf_token)
        form = {x: form[x] for x in form if "-debit-" not in x}
        return form

    def __get_unchanged_update_form(self, voucher_id: int) -> dict[str, str]:
        """Returns the form data to update a voucher, where the data are not
        changed.

        :param voucher_id: The voucher ID.
        :return: The form data to update the voucher, where the data are not
            changed.
        """
        form: dict[str, str] = get_unchanged_update_form(
            voucher_id, self.app, self.csrf_token)
        form = {x: form[x] for x in form if "-debit-" not in x}
        return form

    def __get_update_form(self, voucher_id: int) -> dict[str, str]:
        """Returns the form data to update a voucher, where the data are
        changed.

        :param voucher_id: The voucher ID.
        :return: The form data to update the voucher, where the data are
            changed.
        """
        form: dict[str, str] = get_update_form(
            voucher_id, self.app, self.csrf_token, False)
        form = {x: form[x] for x in form if "-debit-" not in x}
        return form


class CashDisbursementVoucherTestCase(unittest.TestCase):
    """The cash disbursement voucher test case."""

    def setUp(self) -> None:
        """Sets up the test.
        This is run once per test.

        :return: None.
        """
        self.app: Flask = create_test_app()

        runner: FlaskCliRunner = self.app.test_cli_runner()
        with self.app.app_context():
            from accounting.models import BaseAccount, Voucher, \
                VoucherLineItem
            result: Result
            result = runner.invoke(args="init-db")
            self.assertEqual(result.exit_code, 0)
            if BaseAccount.query.first() is None:
                result = runner.invoke(args="accounting-init-base")
                self.assertEqual(result.exit_code, 0)
            result = runner.invoke(args=["accounting-init-currencies",
                                         "-u", "editor"])
            self.assertEqual(result.exit_code, 0)
            result = runner.invoke(args=["accounting-init-accounts",
                                         "-u", "editor"])
            self.assertEqual(result.exit_code, 0)
            Voucher.query.delete()
            VoucherLineItem.query.delete()

        self.client, self.csrf_token = get_client(self.app, "editor")

    def test_nobody(self) -> None:
        """Test the permission as nobody.

        :return: None.
        """
        client, csrf_token = get_client(self.app, "nobody")
        voucher_id: int = add_voucher(self.client, self.__get_add_form())
        add_form: dict[str, str] = self.__get_add_form()
        add_form["csrf_token"] = csrf_token
        update_form: dict[str, str] = self.__get_update_form(voucher_id)
        update_form["csrf_token"] = csrf_token
        response: httpx.Response

        response = client.get(f"{PREFIX}/{voucher_id}")
        self.assertEqual(response.status_code, 403)

        response = client.get(f"{PREFIX}/create/disbursement")
        self.assertEqual(response.status_code, 403)

        response = client.post(f"{PREFIX}/store/disbursement", data=add_form)
        self.assertEqual(response.status_code, 403)

        response = client.get(f"{PREFIX}/{voucher_id}/edit")
        self.assertEqual(response.status_code, 403)

        response = client.post(f"{PREFIX}/{voucher_id}/update",
                               data=update_form)
        self.assertEqual(response.status_code, 403)

        response = client.post(f"{PREFIX}/{voucher_id}/delete",
                               data={"csrf_token": csrf_token})
        self.assertEqual(response.status_code, 403)

    def test_viewer(self) -> None:
        """Test the permission as viewer.

        :return: None.
        """
        client, csrf_token = get_client(self.app, "viewer")
        voucher_id: int = add_voucher(self.client, self.__get_add_form())
        add_form: dict[str, str] = self.__get_add_form()
        add_form["csrf_token"] = csrf_token
        update_form: dict[str, str] = self.__get_update_form(voucher_id)
        update_form["csrf_token"] = csrf_token
        response: httpx.Response

        response = client.get(f"{PREFIX}/{voucher_id}")
        self.assertEqual(response.status_code, 200)

        response = client.get(f"{PREFIX}/create/disbursement")
        self.assertEqual(response.status_code, 403)

        response = client.post(f"{PREFIX}/store/disbursement", data=add_form)
        self.assertEqual(response.status_code, 403)

        response = client.get(f"{PREFIX}/{voucher_id}/edit")
        self.assertEqual(response.status_code, 403)

        response = client.post(f"{PREFIX}/{voucher_id}/update",
                               data=update_form)
        self.assertEqual(response.status_code, 403)

        response = client.post(f"{PREFIX}/{voucher_id}/delete",
                               data={"csrf_token": csrf_token})
        self.assertEqual(response.status_code, 403)

    def test_editor(self) -> None:
        """Test the permission as editor.

        :return: None.
        """
        voucher_id: int = add_voucher(self.client, self.__get_add_form())
        add_form: dict[str, str] = self.__get_add_form()
        update_form: dict[str, str] = self.__get_update_form(voucher_id)
        response: httpx.Response

        response = self.client.get(f"{PREFIX}/{voucher_id}")
        self.assertEqual(response.status_code, 200)

        response = self.client.get(f"{PREFIX}/create/disbursement")
        self.assertEqual(response.status_code, 200)

        response = self.client.post(f"{PREFIX}/store/disbursement",
                                    data=add_form)
        self.assertEqual(response.status_code, 302)
        match_voucher_detail(response.headers["Location"])

        response = self.client.get(f"{PREFIX}/{voucher_id}/edit")
        self.assertEqual(response.status_code, 200)

        response = self.client.post(f"{PREFIX}/{voucher_id}/update",
                                    data=update_form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"],
                         f"{PREFIX}/{voucher_id}?next=%2F_next")

        response = self.client.post(f"{PREFIX}/{voucher_id}/delete",
                                    data={"csrf_token": self.csrf_token})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], RETURN_TO_URI)

    def test_add(self) -> None:
        """Tests to add the vouchers.

        :return: None.
        """
        from accounting.models import Voucher, VoucherCurrency
        create_uri: str = f"{PREFIX}/create/disbursement?next=%2F_next"
        store_uri: str = f"{PREFIX}/store/disbursement"
        response: httpx.Response
        form: dict[str, str]
        voucher: Voucher | None

        # No currency content
        form = self.__get_add_form()
        form = {x: form[x] for x in form if not x.startswith("currency-")}
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)

        # Missing currency
        form = self.__get_add_form()
        key: str = [x for x in form.keys() if x.endswith("-code")][0]
        form[key] = ""
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)

        # Non-existing currency
        form = self.__get_add_form()
        key: str = [x for x in form.keys() if x.endswith("-code")][0]
        form[key] = "ZZZ"
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)

        # No debit content in a currency
        form = self.__get_add_form()
        remove_debit_in_a_currency(form)
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)

        # Non-existing account
        form = self.__get_add_form()
        key: str = [x for x in form.keys() if x.endswith("-account_code")][0]
        form[key] = "9999-999"
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)

        # Non-debit account
        form = self.__get_add_form()
        key: str = [x for x in form.keys()
                    if x.endswith("-account_code") and "-debit-" in x][0]
        form[key] = Accounts.SERVICE
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)

        # A payable line item cannot start from the debit side
        form = self.__get_add_form()
        key: str = [x for x in form.keys()
                    if x.endswith("-account_code") and "-debit-" in x][0]
        form[key] = Accounts.PAYABLE
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)

        # Negative amount
        form = self.__get_add_form()
        set_negative_amount(form)
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)

        # Success
        response = self.client.post(store_uri,
                                    data=self.__get_add_form())
        self.assertEqual(response.status_code, 302)
        voucher_id: int = match_voucher_detail(response.headers["Location"])

        with self.app.app_context():
            voucher = db.session.get(Voucher, voucher_id)
            self.assertIsNotNone(voucher)
            currencies: list[VoucherCurrency] = voucher.currencies
            self.assertEqual(len(currencies), 3)

            self.assertEqual(currencies[0].code, "JPY")
            self.assertEqual(len(currencies[0].debit), 2)
            self.assertEqual(currencies[0].debit[0].no, 1)
            self.assertEqual(currencies[0].debit[0].account.code,
                             Accounts.CASH)
            self.assertEqual(currencies[0].debit[1].no, 2)
            self.assertEqual(currencies[0].debit[1].account.code,
                             Accounts.BANK)
            self.assertEqual(len(currencies[0].credit), 1)
            self.assertEqual(currencies[0].credit[0].no, 1)
            self.assertEqual(currencies[0].credit[0].account.code,
                             Accounts.CASH)
            self.assertIsNone(currencies[0].credit[0].summary)
            self.assertEqual(currencies[0].credit[0].amount,
                             sum([x.amount for x in currencies[0].debit]))

            self.assertEqual(currencies[1].code, "USD")
            self.assertEqual(len(currencies[1].debit), 3)
            self.assertEqual(currencies[1].debit[0].no, 3)
            self.assertEqual(currencies[1].debit[0].account.code,
                             Accounts.BANK)
            self.assertEqual(currencies[1].debit[0].summary, "Deposit")
            self.assertEqual(currencies[1].debit[1].no, 4)
            self.assertEqual(currencies[1].debit[1].account.code,
                             Accounts.OFFICE)
            self.assertEqual(currencies[1].debit[1].summary, "Pens")
            self.assertEqual(currencies[1].debit[2].no, 5)
            self.assertEqual(currencies[1].debit[2].account.code,
                             Accounts.CASH)
            self.assertIsNone(currencies[1].debit[2].summary)
            self.assertEqual(len(currencies[1].credit), 1)
            self.assertEqual(currencies[1].credit[0].no, 2)
            self.assertEqual(currencies[1].credit[0].account.code,
                             Accounts.CASH)
            self.assertIsNone(currencies[1].credit[0].summary)
            self.assertEqual(currencies[1].credit[0].amount,
                             sum([x.amount for x in currencies[1].debit]))

            self.assertEqual(currencies[2].code, "TWD")
            self.assertEqual(len(currencies[2].debit), 2)
            self.assertEqual(currencies[2].debit[0].no, 6)
            self.assertEqual(currencies[2].debit[0].account.code,
                             Accounts.CASH)
            self.assertEqual(currencies[2].debit[1].no, 7)
            self.assertEqual(currencies[2].debit[1].account.code,
                             Accounts.TRAVEL)
            self.assertEqual(len(currencies[2].credit), 1)
            self.assertEqual(currencies[2].credit[0].no, 3)
            self.assertEqual(currencies[2].credit[0].account.code,
                             Accounts.CASH)
            self.assertIsNone(currencies[2].credit[0].summary)
            self.assertEqual(currencies[2].credit[0].amount,
                             sum([x.amount for x in currencies[2].debit]))

            self.assertEqual(voucher.note, NON_EMPTY_NOTE)

        # Success, with empty note
        form = self.__get_add_form()
        form["note"] = EMPTY_NOTE
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        voucher_id: int = match_voucher_detail(response.headers["Location"])

        with self.app.app_context():
            voucher = db.session.get(Voucher, voucher_id)
            self.assertIsNotNone(voucher)
            self.assertIsNone(voucher.note)

    def test_basic_update(self) -> None:
        """Tests the basic rules to update a voucher.

        :return: None.
        """
        from accounting.models import Voucher, VoucherCurrency
        voucher_id: int = add_voucher(self.client, self.__get_add_form())
        detail_uri: str = f"{PREFIX}/{voucher_id}?next=%2F_next"
        edit_uri: str = f"{PREFIX}/{voucher_id}/edit?next=%2F_next"
        update_uri: str = f"{PREFIX}/{voucher_id}/update"
        form_0: dict[str, str] = self.__get_update_form(voucher_id)

        with self.app.app_context():
            voucher = db.session.get(Voucher, voucher_id)
            self.assertIsNotNone(voucher)
            currencies0: list[VoucherCurrency] = voucher.currencies
            old_id: set[int] = set()
            for currency in currencies0:
                old_id.update({x.id for x in currency.debit})

        # No currency content
        form = form_0.copy()
        form = {x: form[x] for x in form if not x.startswith("currency-")}
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Missing currency
        form = form_0.copy()
        key: str = [x for x in form.keys() if x.endswith("-code")][0]
        form[key] = ""
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Non-existing currency
        form = form_0.copy()
        key: str = [x for x in form.keys() if x.endswith("-code")][0]
        form[key] = "ZZZ"
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # No debit content in a currency
        form = form_0.copy()
        remove_debit_in_a_currency(form)
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Non-existing account
        form: dict[str, str] = form_0.copy()
        key: str = [x for x in form.keys() if x.endswith("-account_code")][0]
        form[key] = "9999-999"
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Non-debit account
        form: dict[str, str] = form_0.copy()
        key: str = [x for x in form.keys()
                    if x.endswith("-account_code") and "-debit-" in x][0]
        form[key] = Accounts.SERVICE
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # A payable line item cannot start from the debit side
        form = self.__get_add_form()
        key: str = [x for x in form.keys()
                    if x.endswith("-account_code") and "-debit-" in x][0]
        form[key] = Accounts.PAYABLE
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Negative amount
        form: dict[str, str] = form_0.copy()
        set_negative_amount(form)
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Success
        response = self.client.post(update_uri, data=form_0)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], detail_uri)

        with self.app.app_context():
            voucher = db.session.get(Voucher, voucher_id)
            self.assertIsNotNone(voucher)
            currencies1: list[VoucherCurrency] = voucher.currencies
            self.assertEqual(len(currencies1), 3)

            self.assertEqual(currencies1[0].code, "AUD")
            self.assertEqual(len(currencies1[0].debit), 2)
            self.assertNotIn(currencies1[0].debit[0].id, old_id)
            self.assertEqual(currencies1[0].debit[0].no, 1)
            self.assertEqual(currencies1[0].debit[0].account.code,
                             Accounts.OFFICE)
            self.assertNotIn(currencies1[0].debit[1].id, old_id)
            self.assertEqual(currencies1[0].debit[1].no, 2)
            self.assertEqual(currencies1[0].debit[1].account.code,
                             Accounts.CASH)
            self.assertEqual(len(currencies1[0].credit), 1)
            self.assertNotIn(currencies1[0].credit[0].id, old_id)
            self.assertEqual(currencies1[0].credit[0].no, 1)
            self.assertEqual(currencies1[0].credit[0].account.code,
                             Accounts.CASH)
            self.assertIsNone(currencies1[0].credit[0].summary)
            self.assertEqual(currencies1[0].credit[0].amount,
                             sum([x.amount for x in currencies1[0].debit]))

            self.assertEqual(currencies1[1].code, "EUR")
            self.assertEqual(len(currencies1[1].debit), 2)
            self.assertEqual(currencies1[1].debit[0].id,
                             currencies0[2].debit[0].id)
            self.assertEqual(currencies1[1].debit[0].no, 3)
            self.assertEqual(currencies1[1].debit[0].account.code,
                             Accounts.CASH)
            self.assertIsNone(currencies1[1].debit[0].summary)
            self.assertEqual(currencies1[1].debit[1].id,
                             currencies0[2].debit[1].id)
            self.assertEqual(currencies1[1].debit[1].no, 4)
            self.assertEqual(currencies1[1].debit[1].account.code,
                             Accounts.TRAVEL)
            self.assertEqual(len(currencies1[1].credit), 1)
            self.assertNotIn(currencies1[1].credit[0].id, old_id)
            self.assertEqual(currencies1[1].credit[0].no, 2)
            self.assertEqual(currencies1[1].credit[0].account.code,
                             Accounts.CASH)
            self.assertIsNone(currencies1[1].credit[0].summary)
            self.assertEqual(currencies1[1].credit[0].amount,
                             sum([x.amount for x in currencies1[1].debit]))

            self.assertEqual(currencies1[2].code, "USD")
            self.assertEqual(len(currencies1[2].debit), 3)
            self.assertNotIn(currencies1[2].debit[0].id, old_id)
            self.assertEqual(currencies1[2].debit[0].no, 5)
            self.assertEqual(currencies1[2].debit[0].account.code,
                             Accounts.TRAVEL)
            self.assertIsNone(currencies1[2].debit[0].summary)
            self.assertEqual(currencies1[2].debit[1].id,
                             currencies0[1].debit[2].id)
            self.assertEqual(currencies1[2].debit[1].no, 6)
            self.assertEqual(currencies1[2].debit[1].account.code,
                             Accounts.CASH)
            self.assertIsNone(currencies1[2].debit[1].summary)
            self.assertEqual(currencies1[2].debit[2].id,
                             currencies0[1].debit[0].id)
            self.assertEqual(currencies1[2].debit[2].no, 7)
            self.assertEqual(currencies1[2].debit[2].account.code,
                             Accounts.BANK)
            self.assertEqual(currencies1[2].debit[2].summary, "Deposit")
            self.assertEqual(len(currencies1[2].credit), 1)
            self.assertEqual(currencies1[2].credit[0].id,
                             currencies0[1].credit[0].id)
            self.assertEqual(currencies1[2].credit[0].no, 3)
            self.assertEqual(currencies1[2].credit[0].account.code,
                             Accounts.CASH)
            self.assertIsNone(currencies1[2].credit[0].summary)
            self.assertEqual(currencies1[2].credit[0].amount,
                             sum([x.amount for x in currencies1[2].debit]))

            self.assertEqual(voucher.note, NON_EMPTY_NOTE)

    def test_update_not_modified(self) -> None:
        """Tests that the data is not modified.

        :return: None.
        """
        from accounting.models import Voucher
        voucher_id: int = add_voucher(self.client, self.__get_add_form())
        detail_uri: str = f"{PREFIX}/{voucher_id}?next=%2F_next"
        update_uri: str = f"{PREFIX}/{voucher_id}/update"
        voucher: Voucher
        response: httpx.Response

        response = self.client.post(
            update_uri, data=self.__get_unchanged_update_form(voucher_id))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], detail_uri)

        with self.app.app_context():
            voucher = db.session.get(Voucher, voucher_id)
            self.assertIsNotNone(voucher)
            voucher.created_at = voucher.created_at - timedelta(seconds=5)
            voucher.updated_at = voucher.created_at
            db.session.commit()

        response = self.client.post(
            update_uri, data=self.__get_update_form(voucher_id))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], detail_uri)

        with self.app.app_context():
            voucher = db.session.get(Voucher, voucher_id)
            self.assertIsNotNone(voucher)
            self.assertLess(voucher.created_at, voucher.updated_at)

    def test_created_updated_by(self) -> None:
        """Tests the created-by and updated-by record.

        :return: None.
        """
        from accounting.models import Voucher
        voucher_id: int = add_voucher(self.client, self.__get_add_form())
        editor_username, editor2_username = "editor", "editor2"
        client, csrf_token = get_client(self.app, editor2_username)
        detail_uri: str = f"{PREFIX}/{voucher_id}?next=%2F_next"
        update_uri: str = f"{PREFIX}/{voucher_id}/update"
        voucher: Voucher
        response: httpx.Response

        with self.app.app_context():
            voucher = db.session.get(Voucher, voucher_id)
            self.assertEqual(voucher.created_by.username, editor_username)
            self.assertEqual(voucher.updated_by.username, editor_username)

        form: dict[str, str] = self.__get_update_form(voucher_id)
        form["csrf_token"] = csrf_token
        response = client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], detail_uri)

        with self.app.app_context():
            voucher = db.session.get(Voucher, voucher_id)
            self.assertEqual(voucher.created_by.username, editor_username)
            self.assertEqual(voucher.updated_by.username, editor2_username)

    def test_delete(self) -> None:
        """Tests to delete a voucher.

        :return: None.
        """
        voucher_id: int = add_voucher(self.client, self.__get_add_form())
        detail_uri: str = f"{PREFIX}/{voucher_id}?next=%2F_next"
        delete_uri: str = f"{PREFIX}/{voucher_id}/delete"
        response: httpx.Response

        response = self.client.get(detail_uri)
        self.assertEqual(response.status_code, 200)
        response = self.client.post(delete_uri,
                                    data={"csrf_token": self.csrf_token,
                                          "next": NEXT_URI})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], NEXT_URI)

        response = self.client.get(detail_uri)
        self.assertEqual(response.status_code, 404)
        response = self.client.post(delete_uri,
                                    data={"csrf_token": self.csrf_token,
                                          "next": NEXT_URI})
        self.assertEqual(response.status_code, 404)

    def __get_add_form(self) -> dict[str, str]:
        """Returns the form data to add a new voucher.

        :return: The form data to add a new voucher.
        """
        form: dict[str, str] = get_add_form(self.csrf_token)
        form = {x: form[x] for x in form if "-credit-" not in x}
        return form

    def __get_unchanged_update_form(self, voucher_id: int) -> dict[str, str]:
        """Returns the form data to update a voucher, where the data are
        not changed.

        :param voucher_id: The voucher ID.
        :return: The form data to update the voucher, where the data are
            not changed.
        """
        form: dict[str, str] = get_unchanged_update_form(
            voucher_id, self.app, self.csrf_token)
        form = {x: form[x] for x in form if "-credit-" not in x}
        return form

    def __get_update_form(self, voucher_id: int) -> dict[str, str]:
        """Returns the form data to update a voucher, where the data are
        changed.

        :param voucher_id: The voucher ID.
        :return: The form data to update the voucher, where the data are
            changed.
        """
        form: dict[str, str] = get_update_form(
            voucher_id, self.app, self.csrf_token, True)
        form = {x: form[x] for x in form if "-credit-" not in x}
        return form


class TransferVoucherTestCase(unittest.TestCase):
    """The transfer voucher test case."""

    def setUp(self) -> None:
        """Sets up the test.
        This is run once per test.

        :return: None.
        """
        self.app: Flask = create_test_app()

        runner: FlaskCliRunner = self.app.test_cli_runner()
        with self.app.app_context():
            from accounting.models import BaseAccount, Voucher, \
                VoucherLineItem
            result: Result
            result = runner.invoke(args="init-db")
            self.assertEqual(result.exit_code, 0)
            if BaseAccount.query.first() is None:
                result = runner.invoke(args="accounting-init-base")
                self.assertEqual(result.exit_code, 0)
            result = runner.invoke(args=["accounting-init-currencies",
                                         "-u", "editor"])
            self.assertEqual(result.exit_code, 0)
            result = runner.invoke(args=["accounting-init-accounts",
                                         "-u", "editor"])
            self.assertEqual(result.exit_code, 0)
            Voucher.query.delete()
            VoucherLineItem.query.delete()

        self.client, self.csrf_token = get_client(self.app, "editor")

    def test_nobody(self) -> None:
        """Test the permission as nobody.

        :return: None.
        """
        client, csrf_token = get_client(self.app, "nobody")
        voucher_id: int = add_voucher(self.client, self.__get_add_form())
        add_form: dict[str, str] = self.__get_add_form()
        add_form["csrf_token"] = csrf_token
        update_form: dict[str, str] = self.__get_update_form(voucher_id)
        update_form["csrf_token"] = csrf_token
        response: httpx.Response

        response = client.get(f"{PREFIX}/{voucher_id}")
        self.assertEqual(response.status_code, 403)

        response = client.get(f"{PREFIX}/create/transfer")
        self.assertEqual(response.status_code, 403)

        response = client.post(f"{PREFIX}/store/transfer", data=add_form)
        self.assertEqual(response.status_code, 403)

        response = client.get(f"{PREFIX}/{voucher_id}/edit")
        self.assertEqual(response.status_code, 403)

        response = client.post(f"{PREFIX}/{voucher_id}/update",
                               data=update_form)
        self.assertEqual(response.status_code, 403)

        response = client.post(f"{PREFIX}/{voucher_id}/delete",
                               data={"csrf_token": csrf_token})
        self.assertEqual(response.status_code, 403)

    def test_viewer(self) -> None:
        """Test the permission as viewer.

        :return: None.
        """
        client, csrf_token = get_client(self.app, "viewer")
        voucher_id: int = add_voucher(self.client, self.__get_add_form())
        add_form: dict[str, str] = self.__get_add_form()
        add_form["csrf_token"] = csrf_token
        update_form: dict[str, str] = self.__get_update_form(voucher_id)
        update_form["csrf_token"] = csrf_token
        response: httpx.Response

        response = client.get(f"{PREFIX}/{voucher_id}")
        self.assertEqual(response.status_code, 200)

        response = client.get(f"{PREFIX}/create/transfer")
        self.assertEqual(response.status_code, 403)

        response = client.post(f"{PREFIX}/store/transfer", data=add_form)
        self.assertEqual(response.status_code, 403)

        response = client.get(f"{PREFIX}/{voucher_id}/edit")
        self.assertEqual(response.status_code, 403)

        response = client.post(f"{PREFIX}/{voucher_id}/update",
                               data=update_form)
        self.assertEqual(response.status_code, 403)

        response = client.post(f"{PREFIX}/{voucher_id}/delete",
                               data={"csrf_token": csrf_token})
        self.assertEqual(response.status_code, 403)

    def test_editor(self) -> None:
        """Test the permission as editor.

        :return: None.
        """
        voucher_id: int = add_voucher(self.client, self.__get_add_form())
        add_form: dict[str, str] = self.__get_add_form()
        update_form: dict[str, str] = self.__get_update_form(voucher_id)
        response: httpx.Response

        response = self.client.get(f"{PREFIX}/{voucher_id}")
        self.assertEqual(response.status_code, 200)

        response = self.client.get(f"{PREFIX}/create/transfer")
        self.assertEqual(response.status_code, 200)

        response = self.client.post(f"{PREFIX}/store/transfer",
                                    data=add_form)
        self.assertEqual(response.status_code, 302)
        match_voucher_detail(response.headers["Location"])

        response = self.client.get(f"{PREFIX}/{voucher_id}/edit")
        self.assertEqual(response.status_code, 200)

        response = self.client.post(f"{PREFIX}/{voucher_id}/update",
                                    data=update_form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"],
                         f"{PREFIX}/{voucher_id}?next=%2F_next")

        response = self.client.post(f"{PREFIX}/{voucher_id}/delete",
                                    data={"csrf_token": self.csrf_token})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], RETURN_TO_URI)

    def test_add(self) -> None:
        """Tests to add the vouchers.

        :return: None.
        """
        from accounting.models import Voucher, VoucherCurrency
        create_uri: str = f"{PREFIX}/create/transfer?next=%2F_next"
        store_uri: str = f"{PREFIX}/store/transfer"
        response: httpx.Response
        form: dict[str, str]
        voucher: Voucher | None

        # No currency content
        form = self.__get_add_form()
        form = {x: form[x] for x in form if not x.startswith("currency-")}
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)

        # Missing currency
        form = self.__get_add_form()
        key: str = [x for x in form.keys() if x.endswith("-code")][0]
        form[key] = ""
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)

        # Non-existing currency
        form = self.__get_add_form()
        key: str = [x for x in form.keys() if x.endswith("-code")][0]
        form[key] = "ZZZ"
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)

        # No debit content in a currency
        form = self.__get_add_form()
        remove_debit_in_a_currency(form)
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)

        # No credit content in a currency
        form = self.__get_add_form()
        remove_credit_in_a_currency(form)
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)

        # Non-existing account
        form = self.__get_add_form()
        key: str = [x for x in form.keys() if x.endswith("-account_code")][0]
        form[key] = "9999-999"
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)

        # Non-debit account
        form = self.__get_add_form()
        key: str = [x for x in form.keys()
                    if x.endswith("-account_code") and "-debit-" in x][0]
        form[key] = Accounts.SERVICE
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)

        # Non-credit account
        form = self.__get_add_form()
        key: str = [x for x in form.keys()
                    if x.endswith("-account_code") and "-credit-" in x][0]
        form[key] = Accounts.OFFICE
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)

        # A receivable line item cannot start from the credit side
        form = self.__get_add_form()
        key: str = [x for x in form.keys()
                    if x.endswith("-account_code") and "-credit-" in x][0]
        form[key] = Accounts.RECEIVABLE
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)

        # A payable line item cannot start from the debit side
        form = self.__get_add_form()
        key: str = [x for x in form.keys()
                    if x.endswith("-account_code") and "-debit-" in x][0]
        form[key] = Accounts.PAYABLE
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)

        # Negative amount
        form = self.__get_add_form()
        set_negative_amount(form)
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)

        # Not balanced
        form = self.__get_add_form()
        key: str = [x for x in form.keys() if x.endswith("-amount")][0]
        form[key] = str(Decimal(form[key]) + 1000)
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)

        # Success
        response = self.client.post(store_uri,
                                    data=self.__get_add_form())
        self.assertEqual(response.status_code, 302)
        voucher_id: int = match_voucher_detail(response.headers["Location"])

        with self.app.app_context():
            voucher = db.session.get(Voucher, voucher_id)
            self.assertIsNotNone(voucher)
            currencies: list[VoucherCurrency] = voucher.currencies
            self.assertEqual(len(currencies), 3)

            self.assertEqual(currencies[0].code, "JPY")
            self.assertEqual(len(currencies[0].debit), 2)
            self.assertEqual(currencies[0].debit[0].no, 1)
            self.assertEqual(currencies[0].debit[0].account.code,
                             Accounts.CASH)
            self.assertEqual(currencies[0].debit[1].no, 2)
            self.assertEqual(currencies[0].debit[1].account.code,
                             Accounts.BANK)
            self.assertEqual(len(currencies[0].credit), 2)
            self.assertEqual(currencies[0].credit[0].no, 1)
            self.assertEqual(currencies[0].credit[0].account.code,
                             Accounts.DONATION)
            self.assertEqual(currencies[0].credit[1].no, 2)
            self.assertEqual(currencies[0].credit[1].account.code,
                             Accounts.AGENCY)

            self.assertEqual(currencies[1].code, "USD")
            self.assertEqual(len(currencies[1].debit), 3)
            self.assertEqual(currencies[1].debit[0].no, 3)
            self.assertEqual(currencies[1].debit[0].account.code,
                             Accounts.BANK)
            self.assertEqual(currencies[1].debit[0].summary, "Deposit")
            self.assertEqual(currencies[1].debit[1].no, 4)
            self.assertEqual(currencies[1].debit[1].account.code,
                             Accounts.OFFICE)
            self.assertEqual(currencies[1].debit[1].summary, "Pens")
            self.assertEqual(currencies[1].debit[2].no, 5)
            self.assertEqual(currencies[1].debit[2].account.code,
                             Accounts.CASH)
            self.assertIsNone(currencies[1].debit[2].summary)
            self.assertEqual(len(currencies[1].credit), 3)
            self.assertEqual(currencies[1].credit[0].no, 3)
            self.assertEqual(currencies[1].credit[0].account.code,
                             Accounts.SERVICE)
            self.assertEqual(currencies[1].credit[1].no, 4)
            self.assertEqual(currencies[1].credit[1].account.code,
                             Accounts.SALES)
            self.assertEqual(currencies[1].credit[2].no, 5)
            self.assertEqual(currencies[1].credit[2].account.code,
                             Accounts.INTEREST)

            self.assertEqual(currencies[2].code, "TWD")
            self.assertEqual(len(currencies[2].debit), 2)
            self.assertEqual(currencies[2].debit[0].no, 6)
            self.assertEqual(currencies[2].debit[0].account.code,
                             Accounts.CASH)
            self.assertEqual(currencies[2].debit[1].no, 7)
            self.assertEqual(currencies[2].debit[1].account.code,
                             Accounts.TRAVEL)
            self.assertEqual(len(currencies[2].credit), 2)
            self.assertEqual(currencies[2].credit[0].no, 6)
            self.assertEqual(currencies[2].credit[0].account.code,
                             Accounts.RENT)
            self.assertEqual(currencies[2].credit[1].no, 7)
            self.assertEqual(currencies[2].credit[1].account.code,
                             Accounts.DONATION)

            self.assertEqual(voucher.note, NON_EMPTY_NOTE)

        # Success, with empty note
        form = self.__get_add_form()
        form["note"] = EMPTY_NOTE
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        voucher_id: int = match_voucher_detail(response.headers["Location"])

        with self.app.app_context():
            voucher = db.session.get(Voucher, voucher_id)
            self.assertIsNotNone(voucher)
            self.assertIsNone(voucher.note)

    def test_basic_update(self) -> None:
        """Tests the basic rules to update a voucher.

        :return: None.
        """
        from accounting.models import Voucher, VoucherCurrency
        voucher_id: int = add_voucher(self.client, self.__get_add_form())
        detail_uri: str = f"{PREFIX}/{voucher_id}?next=%2F_next"
        edit_uri: str = f"{PREFIX}/{voucher_id}/edit?next=%2F_next"
        update_uri: str = f"{PREFIX}/{voucher_id}/update"
        form_0: dict[str, str] = self.__get_update_form(voucher_id)

        with self.app.app_context():
            voucher = db.session.get(Voucher, voucher_id)
            self.assertIsNotNone(voucher)
            currencies0: list[VoucherCurrency] = voucher.currencies
            old_id: set[int] = set()
            for currency in currencies0:
                old_id.update({x.id for x in currency.debit})

        # No currency content
        form = form_0.copy()
        form = {x: form[x] for x in form if not x.startswith("currency-")}
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Missing currency
        form = form_0.copy()
        key: str = [x for x in form.keys() if x.endswith("-code")][0]
        form[key] = ""
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Non-existing currency
        form = form_0.copy()
        key: str = [x for x in form.keys() if x.endswith("-code")][0]
        form[key] = "ZZZ"
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # No debit content in a currency
        form = form_0.copy()
        remove_debit_in_a_currency(form)
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # No credit content in a currency
        form = form_0.copy()
        remove_credit_in_a_currency(form)
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Non-existing account
        form: dict[str, str] = form_0.copy()
        key: str = [x for x in form.keys() if x.endswith("-account_code")][0]
        form[key] = "9999-999"
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Non-debit account
        form: dict[str, str] = form_0.copy()
        key: str = [x for x in form.keys()
                    if x.endswith("-account_code") and "-debit-" in x][0]
        form[key] = Accounts.SERVICE
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Non-credit account
        form: dict[str, str] = form_0.copy()
        key: str = [x for x in form.keys()
                    if x.endswith("-account_code") and "-credit-" in x][0]
        form[key] = Accounts.OFFICE
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # A receivable line item cannot start from the credit side
        form = self.__get_add_form()
        key: str = [x for x in form.keys()
                    if x.endswith("-account_code") and "-credit-" in x][0]
        form[key] = Accounts.RECEIVABLE
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # A payable line item cannot start from the debit side
        form = self.__get_add_form()
        key: str = [x for x in form.keys()
                    if x.endswith("-account_code") and "-debit-" in x][0]
        form[key] = Accounts.PAYABLE
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Negative amount
        form: dict[str, str] = form_0.copy()
        set_negative_amount(form)
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Not balanced
        form: dict[str, str] = form_0.copy()
        key: str = [x for x in form.keys() if x.endswith("-amount")][0]
        form[key] = str(Decimal(form[key]) + 1000)
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Success
        response = self.client.post(update_uri, data=form_0)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], detail_uri)

        with self.app.app_context():
            voucher = db.session.get(Voucher, voucher_id)
            self.assertIsNotNone(voucher)
            currencies1: list[VoucherCurrency] = voucher.currencies
            self.assertEqual(len(currencies1), 3)

            self.assertEqual(currencies1[0].code, "AUD")
            self.assertEqual(len(currencies1[0].debit), 2)
            self.assertNotIn(currencies1[0].debit[0].id, old_id)
            self.assertEqual(currencies1[0].debit[0].no, 1)
            self.assertEqual(currencies1[0].debit[0].account.code,
                             Accounts.OFFICE)
            self.assertNotIn(currencies1[0].debit[1].id, old_id)
            self.assertEqual(currencies1[0].debit[1].no, 2)
            self.assertEqual(currencies1[0].debit[1].account.code,
                             Accounts.CASH)
            self.assertEqual(len(currencies1[0].credit), 2)
            self.assertNotIn(currencies1[0].credit[0].id, old_id)
            self.assertEqual(currencies1[0].credit[0].no, 1)
            self.assertEqual(currencies1[0].credit[0].account.code,
                             Accounts.DONATION)
            self.assertNotIn(currencies1[0].credit[1].id, old_id)
            self.assertEqual(currencies1[0].credit[1].no, 2)
            self.assertEqual(currencies1[0].credit[1].account.code,
                             Accounts.RENT)

            self.assertEqual(currencies1[1].code, "EUR")
            self.assertEqual(len(currencies1[1].debit), 2)
            self.assertEqual(currencies1[1].debit[0].id,
                             currencies0[2].debit[0].id)
            self.assertEqual(currencies1[1].debit[0].no, 3)
            self.assertEqual(currencies1[1].debit[0].account.code,
                             Accounts.CASH)
            self.assertIsNone(currencies1[1].debit[0].summary)
            self.assertEqual(currencies1[1].debit[1].id,
                             currencies0[2].debit[1].id)
            self.assertEqual(currencies1[1].debit[1].no, 4)
            self.assertEqual(currencies1[1].debit[1].account.code,
                             Accounts.TRAVEL)
            self.assertEqual(len(currencies1[1].credit), 2)
            self.assertEqual(currencies1[1].credit[0].id,
                             currencies0[2].credit[0].id)
            self.assertEqual(currencies1[1].credit[0].no, 3)
            self.assertEqual(currencies1[1].credit[0].account.code,
                             Accounts.RENT)
            self.assertEqual(currencies1[1].credit[1].id,
                             currencies0[2].credit[1].id)
            self.assertEqual(currencies1[1].credit[1].no, 4)
            self.assertEqual(currencies1[1].credit[1].account.code,
                             Accounts.DONATION)

            self.assertEqual(currencies1[2].code, "USD")
            self.assertEqual(len(currencies1[2].debit), 3)
            self.assertNotIn(currencies1[2].debit[0].id, old_id)
            self.assertEqual(currencies1[2].debit[0].no, 5)
            self.assertEqual(currencies1[2].debit[0].account.code,
                             Accounts.TRAVEL)
            self.assertIsNone(currencies1[2].debit[0].summary)
            self.assertEqual(currencies1[2].debit[1].id,
                             currencies0[1].debit[2].id)
            self.assertEqual(currencies1[2].debit[1].no, 6)
            self.assertEqual(currencies1[2].debit[1].account.code,
                             Accounts.CASH)
            self.assertIsNone(currencies1[2].debit[1].summary)
            self.assertEqual(currencies1[2].debit[2].id,
                             currencies0[1].debit[0].id)
            self.assertEqual(currencies1[2].debit[2].no, 7)
            self.assertEqual(currencies1[2].debit[2].account.code,
                             Accounts.BANK)
            self.assertEqual(currencies1[2].debit[2].summary, "Deposit")
            self.assertEqual(len(currencies1[2].credit), 3)
            self.assertNotIn(currencies1[2].credit[0].id, old_id)
            self.assertEqual(currencies1[2].credit[0].no, 5)
            self.assertEqual(currencies1[2].credit[0].account.code,
                             Accounts.AGENCY)
            self.assertEqual(currencies1[2].credit[1].id,
                             currencies0[1].credit[2].id)
            self.assertEqual(currencies1[2].credit[1].no, 6)
            self.assertEqual(currencies1[2].credit[1].account.code,
                             Accounts.INTEREST)
            self.assertEqual(currencies1[2].credit[2].id,
                             currencies0[1].credit[0].id)
            self.assertEqual(currencies1[2].credit[2].no, 7)
            self.assertEqual(currencies1[2].credit[2].account.code,
                             Accounts.SERVICE)

            self.assertEqual(voucher.note, NON_EMPTY_NOTE)

    def test_update_not_modified(self) -> None:
        """Tests that the data is not modified.

        :return: None.
        """
        from accounting.models import Voucher
        voucher_id: int = add_voucher(self.client, self.__get_add_form())
        detail_uri: str = f"{PREFIX}/{voucher_id}?next=%2F_next"
        update_uri: str = f"{PREFIX}/{voucher_id}/update"
        voucher: Voucher
        response: httpx.Response

        response = self.client.post(
            update_uri, data=self.__get_unchanged_update_form(voucher_id))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], detail_uri)

        with self.app.app_context():
            voucher = db.session.get(Voucher, voucher_id)
            self.assertIsNotNone(voucher)
            voucher.created_at = voucher.created_at - timedelta(seconds=5)
            voucher.updated_at = voucher.created_at
            db.session.commit()

        response = self.client.post(
            update_uri, data=self.__get_update_form(voucher_id))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], detail_uri)

        with self.app.app_context():
            voucher = db.session.get(Voucher, voucher_id)
            self.assertIsNotNone(voucher)
            self.assertLess(voucher.created_at, voucher.updated_at)

    def test_created_updated_by(self) -> None:
        """Tests the created-by and updated-by record.

        :return: None.
        """
        from accounting.models import Voucher
        voucher_id: int = add_voucher(self.client, self.__get_add_form())
        editor_username, editor2_username = "editor", "editor2"
        client, csrf_token = get_client(self.app, editor2_username)
        detail_uri: str = f"{PREFIX}/{voucher_id}?next=%2F_next"
        update_uri: str = f"{PREFIX}/{voucher_id}/update"
        voucher: Voucher
        response: httpx.Response

        with self.app.app_context():
            voucher = db.session.get(Voucher, voucher_id)
            self.assertEqual(voucher.created_by.username, editor_username)
            self.assertEqual(voucher.updated_by.username, editor_username)

        form: dict[str, str] = self.__get_update_form(voucher_id)
        form["csrf_token"] = csrf_token
        response = client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], detail_uri)

        with self.app.app_context():
            voucher = db.session.get(Voucher, voucher_id)
            self.assertEqual(voucher.created_by.username, editor_username)
            self.assertEqual(voucher.updated_by.username, editor2_username)

    def test_save_as_receipt(self) -> None:
        """Tests to save a transfer voucher as a cash receipt voucher.

        :return: None.
        """
        from accounting.models import Voucher, VoucherCurrency
        voucher_id: int = add_voucher(self.client, self.__get_add_form())
        detail_uri: str = f"{PREFIX}/{voucher_id}?next=%2F_next"
        update_uri: str = f"{PREFIX}/{voucher_id}/update?as=receipt"
        form_0: dict[str, str] = self.__get_update_form(voucher_id)
        form_0 = {x: form_0[x] for x in form_0 if "-debit-" not in x}

        with self.app.app_context():
            voucher = db.session.get(Voucher, voucher_id)
            self.assertIsNotNone(voucher)
            currencies0: list[VoucherCurrency] = voucher.currencies
            old_id: set[int] = set()
            for currency in currencies0:
                old_id.update({x.id for x in currency.debit})

        # Success
        response = self.client.post(update_uri, data=form_0)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], detail_uri)

        with self.app.app_context():
            voucher = db.session.get(Voucher, voucher_id)
            self.assertIsNotNone(voucher)
            currencies1: list[VoucherCurrency] = voucher.currencies
            self.assertEqual(len(currencies1), 3)

            self.assertEqual(currencies1[0].code, "AUD")
            self.assertEqual(len(currencies1[0].debit), 1)
            self.assertNotIn(currencies1[0].debit[0].id, old_id)
            self.assertEqual(currencies1[0].debit[0].no, 1)
            self.assertEqual(currencies1[0].debit[0].account.code,
                             Accounts.CASH)
            self.assertIsNone(currencies1[0].debit[0].summary)
            self.assertEqual(currencies1[0].debit[0].amount,
                             sum([x.amount for x in currencies1[0].credit]))
            self.assertEqual(len(currencies1[0].credit), 2)
            self.assertNotIn(currencies1[0].credit[0].id, old_id)
            self.assertEqual(currencies1[0].credit[0].no, 1)
            self.assertEqual(currencies1[0].credit[0].account.code,
                             Accounts.DONATION)
            self.assertNotIn(currencies1[0].credit[1].id, old_id)
            self.assertEqual(currencies1[0].credit[1].no, 2)
            self.assertEqual(currencies1[0].credit[1].account.code,
                             Accounts.RENT)

            self.assertEqual(currencies1[1].code, "EUR")
            self.assertEqual(len(currencies1[1].debit), 1)
            self.assertNotIn(currencies1[1].debit[0].id, old_id)
            self.assertEqual(currencies1[1].debit[0].no, 2)
            self.assertEqual(currencies1[1].debit[0].account.code,
                             Accounts.CASH)
            self.assertIsNone(currencies1[1].debit[0].summary)
            self.assertEqual(currencies1[1].debit[0].amount,
                             sum([x.amount for x in currencies1[1].credit]))
            self.assertEqual(len(currencies1[1].credit), 2)
            self.assertEqual(currencies1[1].credit[0].id,
                             currencies0[2].credit[0].id)
            self.assertEqual(currencies1[1].credit[0].no, 3)
            self.assertEqual(currencies1[1].credit[0].account.code,
                             Accounts.RENT)
            self.assertEqual(currencies1[1].credit[1].id,
                             currencies0[2].credit[1].id)
            self.assertEqual(currencies1[1].credit[1].no, 4)
            self.assertEqual(currencies1[1].credit[1].account.code,
                             Accounts.DONATION)

            self.assertEqual(currencies1[2].code, "USD")
            self.assertEqual(len(currencies1[2].debit), 1)
            self.assertEqual(currencies1[2].debit[0].id,
                             currencies0[1].debit[0].id)
            self.assertEqual(currencies1[2].debit[0].no, 3)
            self.assertEqual(currencies1[2].debit[0].account.code,
                             Accounts.CASH)
            self.assertIsNone(currencies1[2].debit[0].summary)
            self.assertEqual(currencies1[2].debit[0].amount,
                             sum([x.amount for x in currencies1[2].credit]))
            self.assertEqual(len(currencies1[2].credit), 3)
            self.assertNotIn(currencies1[2].credit[0].id, old_id)
            self.assertEqual(currencies1[2].credit[0].no, 5)
            self.assertEqual(currencies1[2].credit[0].account.code,
                             Accounts.AGENCY)
            self.assertEqual(currencies1[2].credit[1].id,
                             currencies0[1].credit[2].id)
            self.assertEqual(currencies1[2].credit[1].no, 6)
            self.assertEqual(currencies1[2].credit[1].account.code,
                             Accounts.INTEREST)
            self.assertEqual(currencies1[2].credit[2].id,
                             currencies0[1].credit[0].id)
            self.assertEqual(currencies1[2].credit[2].no, 7)
            self.assertEqual(currencies1[2].credit[2].account.code,
                             Accounts.SERVICE)

            self.assertEqual(voucher.note, NON_EMPTY_NOTE)

    def test_save_as_disbursement(self) -> None:
        """Tests to save a transfer voucher as a cash disbursement voucher.

        :return: None.
        """
        from accounting.models import Voucher, VoucherCurrency
        voucher_id: int = add_voucher(self.client, self.__get_add_form())
        detail_uri: str = f"{PREFIX}/{voucher_id}?next=%2F_next"
        update_uri: str = f"{PREFIX}/{voucher_id}/update?as=disbursement"
        form_0: dict[str, str] = self.__get_update_form(voucher_id)
        form_0 = {x: form_0[x] for x in form_0 if "-credit-" not in x}

        with self.app.app_context():
            voucher = db.session.get(Voucher, voucher_id)
            self.assertIsNotNone(voucher)
            currencies0: list[VoucherCurrency] = voucher.currencies
            old_id: set[int] = set()
            for currency in currencies0:
                old_id.update({x.id for x in currency.debit})

        # Success
        response = self.client.post(update_uri, data=form_0)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], detail_uri)

        with self.app.app_context():
            voucher = db.session.get(Voucher, voucher_id)
            self.assertIsNotNone(voucher)
            currencies1: list[VoucherCurrency] = voucher.currencies
            self.assertEqual(len(currencies1), 3)

            self.assertEqual(currencies1[0].code, "AUD")
            self.assertEqual(len(currencies1[0].debit), 2)
            self.assertNotIn(currencies1[0].debit[0].id, old_id)
            self.assertEqual(currencies1[0].debit[0].no, 1)
            self.assertEqual(currencies1[0].debit[0].account.code,
                             Accounts.OFFICE)
            self.assertNotIn(currencies1[0].debit[1].id, old_id)
            self.assertEqual(currencies1[0].debit[1].no, 2)
            self.assertEqual(currencies1[0].debit[1].account.code,
                             Accounts.CASH)
            self.assertEqual(len(currencies1[0].credit), 1)
            self.assertNotIn(currencies1[0].credit[0].id, old_id)
            self.assertEqual(currencies1[0].credit[0].no, 1)
            self.assertEqual(currencies1[0].credit[0].account.code,
                             Accounts.CASH)
            self.assertIsNone(currencies1[0].credit[0].summary)
            self.assertEqual(currencies1[0].credit[0].amount,
                             sum([x.amount for x in currencies1[0].debit]))

            self.assertEqual(currencies1[1].code, "EUR")
            self.assertEqual(len(currencies1[1].debit), 2)
            self.assertEqual(currencies1[1].debit[0].id,
                             currencies0[2].debit[0].id)
            self.assertEqual(currencies1[1].debit[0].no, 3)
            self.assertEqual(currencies1[1].debit[0].account.code,
                             Accounts.CASH)
            self.assertIsNone(currencies1[1].debit[0].summary)
            self.assertEqual(currencies1[1].debit[1].id,
                             currencies0[2].debit[1].id)
            self.assertEqual(currencies1[1].debit[1].no, 4)
            self.assertEqual(currencies1[1].debit[1].account.code,
                             Accounts.TRAVEL)
            self.assertEqual(len(currencies1[1].credit), 1)
            self.assertNotIn(currencies1[1].credit[0].id, old_id)
            self.assertEqual(currencies1[1].credit[0].no, 2)
            self.assertEqual(currencies1[1].credit[0].account.code,
                             Accounts.CASH)
            self.assertIsNone(currencies1[1].credit[0].summary)
            self.assertEqual(currencies1[1].credit[0].amount,
                             sum([x.amount for x in currencies1[1].debit]))

            self.assertEqual(currencies1[2].code, "USD")
            self.assertEqual(len(currencies1[2].debit), 3)
            self.assertNotIn(currencies1[2].debit[0].id, old_id)
            self.assertEqual(currencies1[2].debit[0].no, 5)
            self.assertEqual(currencies1[2].debit[0].account.code,
                             Accounts.TRAVEL)
            self.assertIsNone(currencies1[2].debit[0].summary)
            self.assertEqual(currencies1[2].debit[1].id,
                             currencies0[1].debit[2].id)
            self.assertEqual(currencies1[2].debit[1].no, 6)
            self.assertEqual(currencies1[2].debit[1].account.code,
                             Accounts.CASH)
            self.assertIsNone(currencies1[2].debit[1].summary)
            self.assertEqual(currencies1[2].debit[2].id,
                             currencies0[1].debit[0].id)
            self.assertEqual(currencies1[2].debit[2].no, 7)
            self.assertEqual(currencies1[2].debit[2].account.code,
                             Accounts.BANK)
            self.assertEqual(currencies1[2].debit[2].summary, "Deposit")
            self.assertEqual(len(currencies1[2].credit), 1)
            self.assertEqual(currencies1[2].credit[0].id,
                             currencies0[1].credit[0].id)
            self.assertEqual(currencies1[2].credit[0].no, 3)
            self.assertEqual(currencies1[2].credit[0].account.code,
                             Accounts.CASH)
            self.assertIsNone(currencies1[2].credit[0].summary)
            self.assertEqual(currencies1[2].credit[0].amount,
                             sum([x.amount for x in currencies1[2].debit]))

            self.assertEqual(voucher.note, NON_EMPTY_NOTE)

    def test_delete(self) -> None:
        """Tests to delete a voucher.

        :return: None.
        """
        voucher_id: int = add_voucher(self.client, self.__get_add_form())
        detail_uri: str = f"{PREFIX}/{voucher_id}?next=%2F_next"
        delete_uri: str = f"{PREFIX}/{voucher_id}/delete"
        response: httpx.Response

        response = self.client.get(detail_uri)
        self.assertEqual(response.status_code, 200)
        response = self.client.post(delete_uri,
                                    data={"csrf_token": self.csrf_token,
                                          "next": NEXT_URI})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], NEXT_URI)

        response = self.client.get(detail_uri)
        self.assertEqual(response.status_code, 404)
        response = self.client.post(delete_uri,
                                    data={"csrf_token": self.csrf_token,
                                          "next": NEXT_URI})
        self.assertEqual(response.status_code, 404)

    def __get_add_form(self) -> dict[str, str]:
        """Returns the form data to add a new voucher.

        :return: The form data to add a new voucher.
        """
        return get_add_form(self.csrf_token)

    def __get_unchanged_update_form(self, voucher_id: int) -> dict[str, str]:
        """Returns the form data to update a voucher, where the data are not
        changed.

        :param voucher_id: The voucher ID.
        :return: The form data to update the voucher, where the data are not
            changed.
        """
        return get_unchanged_update_form(voucher_id, self.app, self.csrf_token)

    def __get_update_form(self, voucher_id: int) -> dict[str, str]:
        """Returns the form data to update a voucher, where the data are
        changed.

        :param voucher_id: The voucher ID.
        :return: The form data to update the voucher, where the data are
            changed.
        """
        return get_update_form(voucher_id, self.app, self.csrf_token, None)


class VoucherReorderTestCase(unittest.TestCase):
    """The voucher reorder test case."""

    def setUp(self) -> None:
        """Sets up the test.
        This is run once per test.

        :return: None.
        """
        self.app: Flask = create_test_app()

        runner: FlaskCliRunner = self.app.test_cli_runner()
        with self.app.app_context():
            from accounting.models import BaseAccount, Voucher, \
                VoucherLineItem
            result: Result
            result = runner.invoke(args="init-db")
            self.assertEqual(result.exit_code, 0)
            if BaseAccount.query.first() is None:
                result = runner.invoke(args="accounting-init-base")
                self.assertEqual(result.exit_code, 0)
            result = runner.invoke(args=["accounting-init-currencies",
                                         "-u", "editor"])
            self.assertEqual(result.exit_code, 0)
            result = runner.invoke(args=["accounting-init-accounts",
                                         "-u", "editor"])
            self.assertEqual(result.exit_code, 0)
            Voucher.query.delete()
            VoucherLineItem.query.delete()

        self.client, self.csrf_token = get_client(self.app, "editor")

    def test_change_date(self) -> None:
        """Tests to change the date of a voucher.

        :return: None.
        """
        from accounting.models import Voucher
        response: httpx.Response

        id_1: int = add_voucher(self.client, self.__get_add_receipt_form())
        id_2: int = add_voucher(self.client,
                                self.__get_add_disbursement_form())
        id_3: int = add_voucher(self.client, self.__get_add_transfer_form())
        id_4: int = add_voucher(self.client, self.__get_add_receipt_form())
        id_5: int = add_voucher(self.client,
                                self.__get_add_disbursement_form())

        with self.app.app_context():
            voucher_1: Voucher = db.session.get(Voucher, id_1)
            voucher_date_2: date = voucher_1.date
            voucher_date_1: date = voucher_date_2 - timedelta(days=1)
            voucher_1.date = voucher_date_1
            voucher_1.no = 3
            voucher_2: Voucher = db.session.get(Voucher, id_2)
            voucher_2.date = voucher_date_1
            voucher_2.no = 5
            voucher_3: Voucher = db.session.get(Voucher, id_3)
            voucher_3.date = voucher_date_1
            voucher_3.no = 8
            voucher_4: Voucher = db.session.get(Voucher, id_4)
            voucher_4.no = 2
            voucher_5: Voucher = db.session.get(Voucher, id_5)
            voucher_5.no = 6
            db.session.commit()

        form: dict[str, str] \
            = self.__get_disbursement_unchanged_update_form(id_2)
        form["date"] = voucher_date_2.isoformat()
        response = self.client.post(f"{PREFIX}/{id_2}/update", data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"],
                         f"{PREFIX}/{id_2}?next=%2F_next")

        with self.app.app_context():
            self.assertEqual(db.session.get(Voucher, id_1).no, 1)
            self.assertEqual(db.session.get(Voucher, id_2).no, 3)
            self.assertEqual(db.session.get(Voucher, id_3).no, 2)
            self.assertEqual(db.session.get(Voucher, id_4).no, 1)
            self.assertEqual(db.session.get(Voucher, id_5).no, 2)

    def test_reorder(self) -> None:
        """Tests to reorder the vouchers in a same day.

        :return: None.
        """
        from accounting.models import Voucher
        response: httpx.Response

        id_1: int = add_voucher(self.client, self.__get_add_receipt_form())
        id_2: int = add_voucher(self.client,
                                self.__get_add_disbursement_form())
        id_3: int = add_voucher(self.client, self.__get_add_transfer_form())
        id_4: int = add_voucher(self.client, self.__get_add_receipt_form())
        id_5: int = add_voucher(self.client,
                                self.__get_add_disbursement_form())

        with self.app.app_context():
            voucher_date: date = db.session.get(Voucher, id_1).date

        response = self.client.post(
            f"{PREFIX}/dates/{voucher_date.isoformat()}",
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
            self.assertEqual(db.session.get(Voucher, id_1).no, 4)
            self.assertEqual(db.session.get(Voucher, id_2).no, 1)
            self.assertEqual(db.session.get(Voucher, id_3).no, 5)
            self.assertEqual(db.session.get(Voucher, id_4).no, 2)
            self.assertEqual(db.session.get(Voucher, id_5).no, 3)

        # Malformed orders
        with self.app.app_context():
            db.session.get(Voucher, id_1).no = 3
            db.session.get(Voucher, id_2).no = 4
            db.session.get(Voucher, id_3).no = 6
            db.session.get(Voucher, id_4).no = 8
            db.session.get(Voucher, id_5).no = 9
            db.session.commit()

        response = self.client.post(
            f"{PREFIX}/dates/{voucher_date.isoformat()}",
            data={"csrf_token": self.csrf_token,
                  "next": "/next",
                  f"{id_2}-no": "3a",
                  f"{id_3}-no": "5",
                  f"{id_4}-no": "2"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], f"/next")

        with self.app.app_context():
            self.assertEqual(db.session.get(Voucher, id_1).no, 3)
            self.assertEqual(db.session.get(Voucher, id_2).no, 4)
            self.assertEqual(db.session.get(Voucher, id_3).no, 2)
            self.assertEqual(db.session.get(Voucher, id_4).no, 1)
            self.assertEqual(db.session.get(Voucher, id_5).no, 5)

    def __get_add_receipt_form(self) -> dict[str, str]:
        """Returns the form data to add a new cash receipt voucher.

        :return: The form data to add a new cash receipt voucher.
        """
        form: dict[str, str] = get_add_form(self.csrf_token)
        form = {x: form[x] for x in form if "-debit-" not in x}
        return form

    def __get_add_disbursement_form(self) -> dict[str, str]:
        """Returns the form data to add a new cash disbursement voucher.

        :return: The form data to add a new cash disbursement voucher.
        """
        form: dict[str, str] = get_add_form(self.csrf_token)
        form = {x: form[x] for x in form if "-credit-" not in x}
        return form

    def __get_disbursement_unchanged_update_form(self, voucher_id: int) \
            -> dict[str, str]:
        """Returns the form data to update a cash disbursement voucher, where
        the data are not changed.

        :param voucher_id: The voucher ID.
        :return: The form data to update the cash disbursement voucher, where
            the data are not changed.
        """
        form: dict[str, str] = get_unchanged_update_form(
            voucher_id, self.app, self.csrf_token)
        form = {x: form[x] for x in form if "-credit-" not in x}
        return form

    def __get_add_transfer_form(self) -> dict[str, str]:
        """Returns the form data to add a new voucher.

        :return: The form data to add a new voucher.
        """
        return get_add_form(self.csrf_token)
