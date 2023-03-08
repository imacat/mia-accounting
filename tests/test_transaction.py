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
"""The test for the transaction management.

"""
import unittest
from datetime import date, timedelta
from decimal import Decimal

import httpx
from click.testing import Result
from flask import Flask
from flask.testing import FlaskCliRunner

from test_site import create_app, db
from testlib import get_client
from testlib_txn import Accounts, get_add_form, get_unchanged_update_form, \
    get_update_form, match_txn_detail, set_negative_amount, \
    remove_debit_in_a_currency, remove_credit_in_a_currency, NEXT_URI, \
    NON_EMPTY_NOTE, EMPTY_NOTE, add_txn

PREFIX: str = "/accounting/transactions"
"""The URL prefix for the transaction management."""
RETURN_TO_URI: str = "/accounting/reports/journal"
"""The URL to return to after the operation."""


class CashIncomeTransactionTestCase(unittest.TestCase):
    """The cash income transaction test case."""

    def setUp(self) -> None:
        """Sets up the test.
        This is run once per test.

        :return: None.
        """
        self.app: Flask = create_app(is_testing=True)

        runner: FlaskCliRunner = self.app.test_cli_runner()
        with self.app.app_context():
            from accounting.models import BaseAccount, Transaction, \
                JournalEntry
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
            Transaction.query.delete()
            JournalEntry.query.delete()

        self.client, self.csrf_token = get_client(self.app, "editor")

    def test_nobody(self) -> None:
        """Test the permission as nobody.

        :return: None.
        """
        client, csrf_token = get_client(self.app, "nobody")
        txn_id: int = add_txn(self.client, self.__get_add_form())
        add_form: dict[str, str] = self.__get_add_form()
        add_form["csrf_token"] = csrf_token
        update_form: dict[str, str] = self.__get_update_form(txn_id)
        update_form["csrf_token"] = csrf_token
        response: httpx.Response

        response = client.get(f"{PREFIX}/{txn_id}")
        self.assertEqual(response.status_code, 403)

        response = client.get(f"{PREFIX}/create/income")
        self.assertEqual(response.status_code, 403)

        response = client.post(f"{PREFIX}/store/income", data=add_form)
        self.assertEqual(response.status_code, 403)

        response = client.get(f"{PREFIX}/{txn_id}/edit")
        self.assertEqual(response.status_code, 403)

        response = client.post(f"{PREFIX}/{txn_id}/update", data=update_form)
        self.assertEqual(response.status_code, 403)

        response = client.post(f"{PREFIX}/{txn_id}/delete",
                               data={"csrf_token": csrf_token})
        self.assertEqual(response.status_code, 403)

    def test_viewer(self) -> None:
        """Test the permission as viewer.

        :return: None.
        """
        client, csrf_token = get_client(self.app, "viewer")
        txn_id: int = add_txn(self.client, self.__get_add_form())
        add_form: dict[str, str] = self.__get_add_form()
        add_form["csrf_token"] = csrf_token
        update_form: dict[str, str] = self.__get_update_form(txn_id)
        update_form["csrf_token"] = csrf_token
        response: httpx.Response

        response = client.get(f"{PREFIX}/{txn_id}")
        self.assertEqual(response.status_code, 200)

        response = client.get(f"{PREFIX}/create/income")
        self.assertEqual(response.status_code, 403)

        response = client.post(f"{PREFIX}/store/income", data=add_form)
        self.assertEqual(response.status_code, 403)

        response = client.get(f"{PREFIX}/{txn_id}/edit")
        self.assertEqual(response.status_code, 403)

        response = client.post(f"{PREFIX}/{txn_id}/update", data=update_form)
        self.assertEqual(response.status_code, 403)

        response = client.post(f"{PREFIX}/{txn_id}/delete",
                               data={"csrf_token": csrf_token})
        self.assertEqual(response.status_code, 403)

    def test_editor(self) -> None:
        """Test the permission as editor.

        :return: None.
        """
        txn_id: int = add_txn(self.client, self.__get_add_form())
        add_form: dict[str, str] = self.__get_add_form()
        update_form: dict[str, str] = self.__get_update_form(txn_id)
        response: httpx.Response

        response = self.client.get(f"{PREFIX}/{txn_id}")
        self.assertEqual(response.status_code, 200)

        response = self.client.get(f"{PREFIX}/create/income")
        self.assertEqual(response.status_code, 200)

        response = self.client.post(f"{PREFIX}/store/income",
                                    data=add_form)
        self.assertEqual(response.status_code, 302)
        match_txn_detail(response.headers["Location"])

        response = self.client.get(f"{PREFIX}/{txn_id}/edit")
        self.assertEqual(response.status_code, 200)

        response = self.client.post(f"{PREFIX}/{txn_id}/update",
                                    data=update_form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"],
                         f"{PREFIX}/{txn_id}?next=%2F_next")

        response = self.client.post(f"{PREFIX}/{txn_id}/delete",
                                    data={"csrf_token": self.csrf_token})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], RETURN_TO_URI)

    def test_add(self) -> None:
        """Tests to add the transactions.

        :return: None.
        """
        from accounting.models import Transaction, TransactionCurrency
        create_uri: str = f"{PREFIX}/create/income?next=%2F_next"
        store_uri: str = f"{PREFIX}/store/income"
        response: httpx.Response
        form: dict[str, str]
        txn: Transaction | None

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
        txn_id: int = match_txn_detail(response.headers["Location"])

        with self.app.app_context():
            txn = db.session.get(Transaction, txn_id)
            self.assertIsNotNone(txn)
            currencies: list[TransactionCurrency] = txn.currencies
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

            self.assertEqual(txn.note, NON_EMPTY_NOTE)

        # Success, with empty note
        form = self.__get_add_form()
        form["note"] = EMPTY_NOTE
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        txn_id: int = match_txn_detail(response.headers["Location"])

        with self.app.app_context():
            txn = db.session.get(Transaction, txn_id)
            self.assertIsNotNone(txn)
            self.assertIsNone(txn.note)

    def test_basic_update(self) -> None:
        """Tests the basic rules to update a transaction.

        :return: None.
        """
        from accounting.models import Transaction, TransactionCurrency
        txn_id: int = add_txn(self.client, self.__get_add_form())
        detail_uri: str = f"{PREFIX}/{txn_id}?next=%2F_next"
        edit_uri: str = f"{PREFIX}/{txn_id}/edit?next=%2F_next"
        update_uri: str = f"{PREFIX}/{txn_id}/update"
        form_0: dict[str, str] = self.__get_update_form(txn_id)

        with self.app.app_context():
            txn = db.session.get(Transaction, txn_id)
            self.assertIsNotNone(txn)
            currencies0: list[TransactionCurrency] = txn.currencies
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
            txn = db.session.get(Transaction, txn_id)
            self.assertIsNotNone(txn)
            currencies1: list[TransactionCurrency] = txn.currencies
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

            self.assertEqual(txn.note, NON_EMPTY_NOTE)

    def test_update_not_modified(self) -> None:
        """Tests that the data is not modified.

        :return: None.
        """
        from accounting.models import Transaction
        txn_id: int = add_txn(self.client, self.__get_add_form())
        detail_uri: str = f"{PREFIX}/{txn_id}?next=%2F_next"
        update_uri: str = f"{PREFIX}/{txn_id}/update"
        txn: Transaction
        response: httpx.Response

        response = self.client.post(
            update_uri, data=self.__get_unchanged_update_form(txn_id))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], detail_uri)

        with self.app.app_context():
            txn = db.session.get(Transaction, txn_id)
            self.assertIsNotNone(txn)
            txn.created_at = txn.created_at - timedelta(seconds=5)
            txn.updated_at = txn.created_at
            db.session.commit()

        response = self.client.post(
            update_uri, data=self.__get_update_form(txn_id))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], detail_uri)

        with self.app.app_context():
            txn = db.session.get(Transaction, txn_id)
            self.assertIsNotNone(txn)
            self.assertLess(txn.created_at, txn.updated_at)

    def test_created_updated_by(self) -> None:
        """Tests the created-by and updated-by record.

        :return: None.
        """
        from accounting.models import Transaction
        txn_id: int = add_txn(self.client, self.__get_add_form())
        editor_username, editor2_username = "editor", "editor2"
        client, csrf_token = get_client(self.app, editor2_username)
        detail_uri: str = f"{PREFIX}/{txn_id}?next=%2F_next"
        update_uri: str = f"{PREFIX}/{txn_id}/update"
        txn: Transaction
        response: httpx.Response

        with self.app.app_context():
            txn = db.session.get(Transaction, txn_id)
            self.assertEqual(txn.created_by.username, editor_username)
            self.assertEqual(txn.updated_by.username, editor_username)

        form: dict[str, str] = self.__get_update_form(txn_id)
        form["csrf_token"] = csrf_token
        response = client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], detail_uri)

        with self.app.app_context():
            txn = db.session.get(Transaction, txn_id)
            self.assertEqual(txn.created_by.username, editor_username)
            self.assertEqual(txn.updated_by.username, editor2_username)

    def test_delete(self) -> None:
        """Tests to delete a transaction.

        :return: None.
        """
        txn_id: int = add_txn(self.client, self.__get_add_form())
        detail_uri: str = f"{PREFIX}/{txn_id}?next=%2F_next"
        delete_uri: str = f"{PREFIX}/{txn_id}/delete"
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
        """Returns the form data to add a new transaction.

        :return: The form data to add a new transaction.
        """
        form: dict[str, str] = get_add_form(self.csrf_token)
        form = {x: form[x] for x in form if "-debit-" not in x}
        return form

    def __get_unchanged_update_form(self, txn_id: int) -> dict[str, str]:
        """Returns the form data to update a transaction, where the data are
        not changed.

        :param txn_id: The transaction ID.
        :return: The form data to update the transaction, where the data are
            not changed.
        """
        form: dict[str, str] = get_unchanged_update_form(
            txn_id, self.app, self.csrf_token)
        form = {x: form[x] for x in form if "-debit-" not in x}
        return form

    def __get_update_form(self, txn_id: int) -> dict[str, str]:
        """Returns the form data to update a transaction, where the data are
        changed.

        :param txn_id: The transaction ID.
        :return: The form data to update the transaction, where the data are
            changed.
        """
        form: dict[str, str] = get_update_form(
            txn_id, self.app, self.csrf_token, False)
        form = {x: form[x] for x in form if "-debit-" not in x}
        return form


class CashExpenseTransactionTestCase(unittest.TestCase):
    """The cash expense transaction test case."""

    def setUp(self) -> None:
        """Sets up the test.
        This is run once per test.

        :return: None.
        """
        self.app: Flask = create_app(is_testing=True)

        runner: FlaskCliRunner = self.app.test_cli_runner()
        with self.app.app_context():
            from accounting.models import BaseAccount, Transaction, \
                JournalEntry
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
            Transaction.query.delete()
            JournalEntry.query.delete()

        self.client, self.csrf_token = get_client(self.app, "editor")

    def test_nobody(self) -> None:
        """Test the permission as nobody.

        :return: None.
        """
        client, csrf_token = get_client(self.app, "nobody")
        txn_id: int = add_txn(self.client, self.__get_add_form())
        add_form: dict[str, str] = self.__get_add_form()
        add_form["csrf_token"] = csrf_token
        update_form: dict[str, str] = self.__get_update_form(txn_id)
        update_form["csrf_token"] = csrf_token
        response: httpx.Response

        response = client.get(f"{PREFIX}/{txn_id}")
        self.assertEqual(response.status_code, 403)

        response = client.get(f"{PREFIX}/create/expense")
        self.assertEqual(response.status_code, 403)

        response = client.post(f"{PREFIX}/store/expense", data=add_form)
        self.assertEqual(response.status_code, 403)

        response = client.get(f"{PREFIX}/{txn_id}/edit")
        self.assertEqual(response.status_code, 403)

        response = client.post(f"{PREFIX}/{txn_id}/update", data=update_form)
        self.assertEqual(response.status_code, 403)

        response = client.post(f"{PREFIX}/{txn_id}/delete",
                               data={"csrf_token": csrf_token})
        self.assertEqual(response.status_code, 403)

    def test_viewer(self) -> None:
        """Test the permission as viewer.

        :return: None.
        """
        client, csrf_token = get_client(self.app, "viewer")
        txn_id: int = add_txn(self.client, self.__get_add_form())
        add_form: dict[str, str] = self.__get_add_form()
        add_form["csrf_token"] = csrf_token
        update_form: dict[str, str] = self.__get_update_form(txn_id)
        update_form["csrf_token"] = csrf_token
        response: httpx.Response

        response = client.get(f"{PREFIX}/{txn_id}")
        self.assertEqual(response.status_code, 200)

        response = client.get(f"{PREFIX}/create/expense")
        self.assertEqual(response.status_code, 403)

        response = client.post(f"{PREFIX}/store/expense", data=add_form)
        self.assertEqual(response.status_code, 403)

        response = client.get(f"{PREFIX}/{txn_id}/edit")
        self.assertEqual(response.status_code, 403)

        response = client.post(f"{PREFIX}/{txn_id}/update", data=update_form)
        self.assertEqual(response.status_code, 403)

        response = client.post(f"{PREFIX}/{txn_id}/delete",
                               data={"csrf_token": csrf_token})
        self.assertEqual(response.status_code, 403)

    def test_editor(self) -> None:
        """Test the permission as editor.

        :return: None.
        """
        txn_id: int = add_txn(self.client, self.__get_add_form())
        add_form: dict[str, str] = self.__get_add_form()
        update_form: dict[str, str] = self.__get_update_form(txn_id)
        response: httpx.Response

        response = self.client.get(f"{PREFIX}/{txn_id}")
        self.assertEqual(response.status_code, 200)

        response = self.client.get(f"{PREFIX}/create/expense")
        self.assertEqual(response.status_code, 200)

        response = self.client.post(f"{PREFIX}/store/expense",
                                    data=add_form)
        self.assertEqual(response.status_code, 302)
        match_txn_detail(response.headers["Location"])

        response = self.client.get(f"{PREFIX}/{txn_id}/edit")
        self.assertEqual(response.status_code, 200)

        response = self.client.post(f"{PREFIX}/{txn_id}/update",
                                    data=update_form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"],
                         f"{PREFIX}/{txn_id}?next=%2F_next")

        response = self.client.post(f"{PREFIX}/{txn_id}/delete",
                                    data={"csrf_token": self.csrf_token})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], RETURN_TO_URI)

    def test_add(self) -> None:
        """Tests to add the transactions.

        :return: None.
        """
        from accounting.models import Transaction, TransactionCurrency
        create_uri: str = f"{PREFIX}/create/expense?next=%2F_next"
        store_uri: str = f"{PREFIX}/store/expense"
        response: httpx.Response
        form: dict[str, str]
        txn: Transaction | None

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
        txn_id: int = match_txn_detail(response.headers["Location"])

        with self.app.app_context():
            txn = db.session.get(Transaction, txn_id)
            self.assertIsNotNone(txn)
            currencies: list[TransactionCurrency] = txn.currencies
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

            self.assertEqual(txn.note, NON_EMPTY_NOTE)

        # Success, with empty note
        form = self.__get_add_form()
        form["note"] = EMPTY_NOTE
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        txn_id: int = match_txn_detail(response.headers["Location"])

        with self.app.app_context():
            txn = db.session.get(Transaction, txn_id)
            self.assertIsNotNone(txn)
            self.assertIsNone(txn.note)

    def test_basic_update(self) -> None:
        """Tests the basic rules to update a transaction.

        :return: None.
        """
        from accounting.models import Transaction, TransactionCurrency
        txn_id: int = add_txn(self.client, self.__get_add_form())
        detail_uri: str = f"{PREFIX}/{txn_id}?next=%2F_next"
        edit_uri: str = f"{PREFIX}/{txn_id}/edit?next=%2F_next"
        update_uri: str = f"{PREFIX}/{txn_id}/update"
        form_0: dict[str, str] = self.__get_update_form(txn_id)

        with self.app.app_context():
            txn = db.session.get(Transaction, txn_id)
            self.assertIsNotNone(txn)
            currencies0: list[TransactionCurrency] = txn.currencies
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
            txn = db.session.get(Transaction, txn_id)
            self.assertIsNotNone(txn)
            currencies1: list[TransactionCurrency] = txn.currencies
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

            self.assertEqual(txn.note, NON_EMPTY_NOTE)

    def test_update_not_modified(self) -> None:
        """Tests that the data is not modified.

        :return: None.
        """
        from accounting.models import Transaction
        txn_id: int = add_txn(self.client, self.__get_add_form())
        detail_uri: str = f"{PREFIX}/{txn_id}?next=%2F_next"
        update_uri: str = f"{PREFIX}/{txn_id}/update"
        txn: Transaction
        response: httpx.Response

        response = self.client.post(
            update_uri, data=self.__get_unchanged_update_form(txn_id))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], detail_uri)

        with self.app.app_context():
            txn = db.session.get(Transaction, txn_id)
            self.assertIsNotNone(txn)
            txn.created_at = txn.created_at - timedelta(seconds=5)
            txn.updated_at = txn.created_at
            db.session.commit()

        response = self.client.post(
            update_uri, data=self.__get_update_form(txn_id))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], detail_uri)

        with self.app.app_context():
            txn = db.session.get(Transaction, txn_id)
            self.assertIsNotNone(txn)
            self.assertLess(txn.created_at, txn.updated_at)

    def test_created_updated_by(self) -> None:
        """Tests the created-by and updated-by record.

        :return: None.
        """
        from accounting.models import Transaction
        txn_id: int = add_txn(self.client, self.__get_add_form())
        editor_username, editor2_username = "editor", "editor2"
        client, csrf_token = get_client(self.app, editor2_username)
        detail_uri: str = f"{PREFIX}/{txn_id}?next=%2F_next"
        update_uri: str = f"{PREFIX}/{txn_id}/update"
        txn: Transaction
        response: httpx.Response

        with self.app.app_context():
            txn = db.session.get(Transaction, txn_id)
            self.assertEqual(txn.created_by.username, editor_username)
            self.assertEqual(txn.updated_by.username, editor_username)

        form: dict[str, str] = self.__get_update_form(txn_id)
        form["csrf_token"] = csrf_token
        response = client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], detail_uri)

        with self.app.app_context():
            txn = db.session.get(Transaction, txn_id)
            self.assertEqual(txn.created_by.username, editor_username)
            self.assertEqual(txn.updated_by.username, editor2_username)

    def test_delete(self) -> None:
        """Tests to delete a transaction.

        :return: None.
        """
        txn_id: int = add_txn(self.client, self.__get_add_form())
        detail_uri: str = f"{PREFIX}/{txn_id}?next=%2F_next"
        delete_uri: str = f"{PREFIX}/{txn_id}/delete"
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
        """Returns the form data to add a new transaction.

        :return: The form data to add a new transaction.
        """
        form: dict[str, str] = get_add_form(self.csrf_token)
        form = {x: form[x] for x in form if "-credit-" not in x}
        return form

    def __get_unchanged_update_form(self, txn_id: int) -> dict[str, str]:
        """Returns the form data to update a transaction, where the data are
        not changed.

        :param txn_id: The transaction ID.
        :return: The form data to update the transaction, where the data are
            not changed.
        """
        form: dict[str, str] = get_unchanged_update_form(
            txn_id, self.app, self.csrf_token)
        form = {x: form[x] for x in form if "-credit-" not in x}
        return form

    def __get_update_form(self, txn_id: int) -> dict[str, str]:
        """Returns the form data to update a transaction, where the data are
        changed.

        :param txn_id: The transaction ID.
        :return: The form data to update the transaction, where the data are
            changed.
        """
        form: dict[str, str] = get_update_form(
            txn_id, self.app, self.csrf_token, True)
        form = {x: form[x] for x in form if "-credit-" not in x}
        return form


class TransferTransactionTestCase(unittest.TestCase):
    """The transfer transaction test case."""

    def setUp(self) -> None:
        """Sets up the test.
        This is run once per test.

        :return: None.
        """
        self.app: Flask = create_app(is_testing=True)

        runner: FlaskCliRunner = self.app.test_cli_runner()
        with self.app.app_context():
            from accounting.models import BaseAccount, Transaction, \
                JournalEntry
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
            Transaction.query.delete()
            JournalEntry.query.delete()

        self.client, self.csrf_token = get_client(self.app, "editor")

    def test_nobody(self) -> None:
        """Test the permission as nobody.

        :return: None.
        """
        client, csrf_token = get_client(self.app, "nobody")
        txn_id: int = add_txn(self.client, self.__get_add_form())
        add_form: dict[str, str] = self.__get_add_form()
        add_form["csrf_token"] = csrf_token
        update_form: dict[str, str] = self.__get_update_form(txn_id)
        update_form["csrf_token"] = csrf_token
        response: httpx.Response

        response = client.get(f"{PREFIX}/{txn_id}")
        self.assertEqual(response.status_code, 403)

        response = client.get(f"{PREFIX}/create/transfer")
        self.assertEqual(response.status_code, 403)

        response = client.post(f"{PREFIX}/store/transfer", data=add_form)
        self.assertEqual(response.status_code, 403)

        response = client.get(f"{PREFIX}/{txn_id}/edit")
        self.assertEqual(response.status_code, 403)

        response = client.post(f"{PREFIX}/{txn_id}/update", data=update_form)
        self.assertEqual(response.status_code, 403)

        response = client.post(f"{PREFIX}/{txn_id}/delete",
                               data={"csrf_token": csrf_token})
        self.assertEqual(response.status_code, 403)

    def test_viewer(self) -> None:
        """Test the permission as viewer.

        :return: None.
        """
        client, csrf_token = get_client(self.app, "viewer")
        txn_id: int = add_txn(self.client, self.__get_add_form())
        add_form: dict[str, str] = self.__get_add_form()
        add_form["csrf_token"] = csrf_token
        update_form: dict[str, str] = self.__get_update_form(txn_id)
        update_form["csrf_token"] = csrf_token
        response: httpx.Response

        response = client.get(f"{PREFIX}/{txn_id}")
        self.assertEqual(response.status_code, 200)

        response = client.get(f"{PREFIX}/create/transfer")
        self.assertEqual(response.status_code, 403)

        response = client.post(f"{PREFIX}/store/transfer", data=add_form)
        self.assertEqual(response.status_code, 403)

        response = client.get(f"{PREFIX}/{txn_id}/edit")
        self.assertEqual(response.status_code, 403)

        response = client.post(f"{PREFIX}/{txn_id}/update", data=update_form)
        self.assertEqual(response.status_code, 403)

        response = client.post(f"{PREFIX}/{txn_id}/delete",
                               data={"csrf_token": csrf_token})
        self.assertEqual(response.status_code, 403)

    def test_editor(self) -> None:
        """Test the permission as editor.

        :return: None.
        """
        txn_id: int = add_txn(self.client, self.__get_add_form())
        add_form: dict[str, str] = self.__get_add_form()
        update_form: dict[str, str] = self.__get_update_form(txn_id)
        response: httpx.Response

        response = self.client.get(f"{PREFIX}/{txn_id}")
        self.assertEqual(response.status_code, 200)

        response = self.client.get(f"{PREFIX}/create/transfer")
        self.assertEqual(response.status_code, 200)

        response = self.client.post(f"{PREFIX}/store/transfer",
                                    data=add_form)
        self.assertEqual(response.status_code, 302)
        match_txn_detail(response.headers["Location"])

        response = self.client.get(f"{PREFIX}/{txn_id}/edit")
        self.assertEqual(response.status_code, 200)

        response = self.client.post(f"{PREFIX}/{txn_id}/update",
                                    data=update_form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"],
                         f"{PREFIX}/{txn_id}?next=%2F_next")

        response = self.client.post(f"{PREFIX}/{txn_id}/delete",
                                    data={"csrf_token": self.csrf_token})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], RETURN_TO_URI)

    def test_add(self) -> None:
        """Tests to add the transactions.

        :return: None.
        """
        from accounting.models import Transaction, TransactionCurrency
        create_uri: str = f"{PREFIX}/create/transfer?next=%2F_next"
        store_uri: str = f"{PREFIX}/store/transfer"
        response: httpx.Response
        form: dict[str, str]
        txn: Transaction | None

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
        txn_id: int = match_txn_detail(response.headers["Location"])

        with self.app.app_context():
            txn = db.session.get(Transaction, txn_id)
            self.assertIsNotNone(txn)
            currencies: list[TransactionCurrency] = txn.currencies
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

            self.assertEqual(txn.note, NON_EMPTY_NOTE)

        # Success, with empty note
        form = self.__get_add_form()
        form["note"] = EMPTY_NOTE
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        txn_id: int = match_txn_detail(response.headers["Location"])

        with self.app.app_context():
            txn = db.session.get(Transaction, txn_id)
            self.assertIsNotNone(txn)
            self.assertIsNone(txn.note)

    def test_basic_update(self) -> None:
        """Tests the basic rules to update a transaction.

        :return: None.
        """
        from accounting.models import Transaction, TransactionCurrency
        txn_id: int = add_txn(self.client, self.__get_add_form())
        detail_uri: str = f"{PREFIX}/{txn_id}?next=%2F_next"
        edit_uri: str = f"{PREFIX}/{txn_id}/edit?next=%2F_next"
        update_uri: str = f"{PREFIX}/{txn_id}/update"
        form_0: dict[str, str] = self.__get_update_form(txn_id)

        with self.app.app_context():
            txn = db.session.get(Transaction, txn_id)
            self.assertIsNotNone(txn)
            currencies0: list[TransactionCurrency] = txn.currencies
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
            txn = db.session.get(Transaction, txn_id)
            self.assertIsNotNone(txn)
            currencies1: list[TransactionCurrency] = txn.currencies
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

            self.assertEqual(txn.note, NON_EMPTY_NOTE)

    def test_update_not_modified(self) -> None:
        """Tests that the data is not modified.

        :return: None.
        """
        from accounting.models import Transaction
        txn_id: int = add_txn(self.client, self.__get_add_form())
        detail_uri: str = f"{PREFIX}/{txn_id}?next=%2F_next"
        update_uri: str = f"{PREFIX}/{txn_id}/update"
        txn: Transaction
        response: httpx.Response

        response = self.client.post(
            update_uri, data=self.__get_unchanged_update_form(txn_id))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], detail_uri)

        with self.app.app_context():
            txn = db.session.get(Transaction, txn_id)
            self.assertIsNotNone(txn)
            txn.created_at = txn.created_at - timedelta(seconds=5)
            txn.updated_at = txn.created_at
            db.session.commit()

        response = self.client.post(
            update_uri, data=self.__get_update_form(txn_id))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], detail_uri)

        with self.app.app_context():
            txn = db.session.get(Transaction, txn_id)
            self.assertIsNotNone(txn)
            self.assertLess(txn.created_at, txn.updated_at)

    def test_created_updated_by(self) -> None:
        """Tests the created-by and updated-by record.

        :return: None.
        """
        from accounting.models import Transaction
        txn_id: int = add_txn(self.client, self.__get_add_form())
        editor_username, editor2_username = "editor", "editor2"
        client, csrf_token = get_client(self.app, editor2_username)
        detail_uri: str = f"{PREFIX}/{txn_id}?next=%2F_next"
        update_uri: str = f"{PREFIX}/{txn_id}/update"
        txn: Transaction
        response: httpx.Response

        with self.app.app_context():
            txn = db.session.get(Transaction, txn_id)
            self.assertEqual(txn.created_by.username, editor_username)
            self.assertEqual(txn.updated_by.username, editor_username)

        form: dict[str, str] = self.__get_update_form(txn_id)
        form["csrf_token"] = csrf_token
        response = client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], detail_uri)

        with self.app.app_context():
            txn = db.session.get(Transaction, txn_id)
            self.assertEqual(txn.created_by.username, editor_username)
            self.assertEqual(txn.updated_by.username, editor2_username)

    def test_save_as_income(self) -> None:
        """Tests to save a transfer transaction as a cash income transaction.

        :return: None.
        """
        from accounting.models import Transaction, TransactionCurrency
        txn_id: int = add_txn(self.client, self.__get_add_form())
        detail_uri: str = f"{PREFIX}/{txn_id}?next=%2F_next"
        update_uri: str = f"{PREFIX}/{txn_id}/update?as=income"
        form_0: dict[str, str] = self.__get_update_form(txn_id)
        form_0 = {x: form_0[x] for x in form_0 if "-debit-" not in x}

        with self.app.app_context():
            txn = db.session.get(Transaction, txn_id)
            self.assertIsNotNone(txn)
            currencies0: list[TransactionCurrency] = txn.currencies
            old_id: set[int] = set()
            for currency in currencies0:
                old_id.update({x.id for x in currency.debit})

        # Success
        response = self.client.post(update_uri, data=form_0)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], detail_uri)

        with self.app.app_context():
            txn = db.session.get(Transaction, txn_id)
            self.assertIsNotNone(txn)
            currencies1: list[TransactionCurrency] = txn.currencies
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

            self.assertEqual(txn.note, NON_EMPTY_NOTE)

    def test_save_as_expense(self) -> None:
        """Tests to save a transfer transaction as a cash expense transaction.

        :return: None.
        """
        from accounting.models import Transaction, TransactionCurrency
        txn_id: int = add_txn(self.client, self.__get_add_form())
        detail_uri: str = f"{PREFIX}/{txn_id}?next=%2F_next"
        update_uri: str = f"{PREFIX}/{txn_id}/update?as=expense"
        form_0: dict[str, str] = self.__get_update_form(txn_id)
        form_0 = {x: form_0[x] for x in form_0 if "-credit-" not in x}

        with self.app.app_context():
            txn = db.session.get(Transaction, txn_id)
            self.assertIsNotNone(txn)
            currencies0: list[TransactionCurrency] = txn.currencies
            old_id: set[int] = set()
            for currency in currencies0:
                old_id.update({x.id for x in currency.debit})

        # Success
        response = self.client.post(update_uri, data=form_0)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], detail_uri)

        with self.app.app_context():
            txn = db.session.get(Transaction, txn_id)
            self.assertIsNotNone(txn)
            currencies1: list[TransactionCurrency] = txn.currencies
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

            self.assertEqual(txn.note, NON_EMPTY_NOTE)

    def test_delete(self) -> None:
        """Tests to delete a transaction.

        :return: None.
        """
        txn_id: int = add_txn(self.client, self.__get_add_form())
        detail_uri: str = f"{PREFIX}/{txn_id}?next=%2F_next"
        delete_uri: str = f"{PREFIX}/{txn_id}/delete"
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
        """Returns the form data to add a new transaction.

        :return: The form data to add a new transaction.
        """
        return get_add_form(self.csrf_token)

    def __get_unchanged_update_form(self, txn_id: int) -> dict[str, str]:
        """Returns the form data to update a transaction, where the data are
        not changed.

        :param txn_id: The transaction ID.
        :return: The form data to update the transaction, where the data are
            not changed.
        """
        return get_unchanged_update_form(txn_id, self.app, self.csrf_token)

    def __get_update_form(self, txn_id: int) -> dict[str, str]:
        """Returns the form data to update a transaction, where the data are
        changed.

        :param txn_id: The transaction ID.
        :return: The form data to update the transaction, where the data are
            changed.
        """
        return get_update_form(txn_id, self.app, self.csrf_token, None)


class TransactionReorderTestCase(unittest.TestCase):
    """The transaction reorder test case."""

    def setUp(self) -> None:
        """Sets up the test.
        This is run once per test.

        :return: None.
        """
        self.app: Flask = create_app(is_testing=True)

        runner: FlaskCliRunner = self.app.test_cli_runner()
        with self.app.app_context():
            from accounting.models import BaseAccount, Transaction, \
                JournalEntry
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
            Transaction.query.delete()
            JournalEntry.query.delete()

        self.client, self.csrf_token = get_client(self.app, "editor")

    def test_change_date(self) -> None:
        """Tests to change the date of a transaction.

        :return: None.
        """
        from accounting.models import Transaction
        response: httpx.Response

        id_1: int = add_txn(self.client, self.__get_add_income_form())
        id_2: int = add_txn(self.client, self.__get_add_expense_form())
        id_3: int = add_txn(self.client, self.__get_add_transfer_form())
        id_4: int = add_txn(self.client, self.__get_add_income_form())
        id_5: int = add_txn(self.client, self.__get_add_expense_form())

        with self.app.app_context():
            txn_1: Transaction = db.session.get(Transaction, id_1)
            txn_date_2: date = txn_1.date
            txn_date_1: date = txn_date_2 - timedelta(days=1)
            txn_1.date = txn_date_1
            txn_1.no = 3
            txn_2: Transaction = db.session.get(Transaction, id_2)
            txn_2.date = txn_date_1
            txn_2.no = 5
            txn_3: Transaction = db.session.get(Transaction, id_3)
            txn_3.date = txn_date_1
            txn_3.no = 8
            txn_4: Transaction = db.session.get(Transaction, id_4)
            txn_4.no = 2
            txn_5: Transaction = db.session.get(Transaction, id_5)
            txn_5.no = 6
            db.session.commit()

        form: dict[str, str] = self.__get_expense_unchanged_update_form(id_2)
        form["date"] = txn_date_2.isoformat()
        response = self.client.post(f"{PREFIX}/{id_2}/update", data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"],
                         f"{PREFIX}/{id_2}?next=%2F_next")

        with self.app.app_context():
            self.assertEqual(db.session.get(Transaction, id_1).no, 1)
            self.assertEqual(db.session.get(Transaction, id_2).no, 3)
            self.assertEqual(db.session.get(Transaction, id_3).no, 2)
            self.assertEqual(db.session.get(Transaction, id_4).no, 1)
            self.assertEqual(db.session.get(Transaction, id_5).no, 2)

    def test_reorder(self) -> None:
        """Tests to reorder the transactions in a same day.

        :return: None.
        """
        from accounting.models import Transaction
        response: httpx.Response

        id_1: int = add_txn(self.client, self.__get_add_income_form())
        id_2: int = add_txn(self.client, self.__get_add_expense_form())
        id_3: int = add_txn(self.client, self.__get_add_transfer_form())
        id_4: int = add_txn(self.client, self.__get_add_income_form())
        id_5: int = add_txn(self.client, self.__get_add_expense_form())

        with self.app.app_context():
            txn_date: date = db.session.get(Transaction, id_1).date

        response = self.client.post(f"{PREFIX}/dates/{txn_date.isoformat()}",
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
            self.assertEqual(db.session.get(Transaction, id_1).no, 4)
            self.assertEqual(db.session.get(Transaction, id_2).no, 1)
            self.assertEqual(db.session.get(Transaction, id_3).no, 5)
            self.assertEqual(db.session.get(Transaction, id_4).no, 2)
            self.assertEqual(db.session.get(Transaction, id_5).no, 3)

        # Malformed orders
        with self.app.app_context():
            db.session.get(Transaction, id_1).no = 3
            db.session.get(Transaction, id_2).no = 4
            db.session.get(Transaction, id_3).no = 6
            db.session.get(Transaction, id_4).no = 8
            db.session.get(Transaction, id_5).no = 9
            db.session.commit()

        response = self.client.post(f"{PREFIX}/dates/{txn_date.isoformat()}",
                                    data={"csrf_token": self.csrf_token,
                                          "next": "/next",
                                          f"{id_2}-no": "3a",
                                          f"{id_3}-no": "5",
                                          f"{id_4}-no": "2"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], f"/next")

        with self.app.app_context():
            self.assertEqual(db.session.get(Transaction, id_1).no, 3)
            self.assertEqual(db.session.get(Transaction, id_2).no, 4)
            self.assertEqual(db.session.get(Transaction, id_3).no, 2)
            self.assertEqual(db.session.get(Transaction, id_4).no, 1)
            self.assertEqual(db.session.get(Transaction, id_5).no, 5)

    def __get_add_income_form(self) -> dict[str, str]:
        """Returns the form data to add a new transaction.

        :return: The form data to add a new transaction.
        """
        form: dict[str, str] = get_add_form(self.csrf_token)
        form = {x: form[x] for x in form if "-debit-" not in x}
        return form

    def __get_add_expense_form(self) -> dict[str, str]:
        """Returns the form data to add a new transaction.

        :return: The form data to add a new transaction.
        """
        form: dict[str, str] = get_add_form(self.csrf_token)
        form = {x: form[x] for x in form if "-credit-" not in x}
        return form

    def __get_expense_unchanged_update_form(self, txn_id: int) \
            -> dict[str, str]:
        """Returns the form data to update a cash expense transaction, where
        the data are not changed.

        :param txn_id: The transaction ID.
        :return: The form data to update the cash expense transaction, where
            the data are not changed.
        """
        form: dict[str, str] = get_unchanged_update_form(
            txn_id, self.app, self.csrf_token)
        form = {x: form[x] for x in form if "-credit-" not in x}
        return form

    def __get_add_transfer_form(self) -> dict[str, str]:
        """Returns the form data to add a new transaction.

        :return: The form data to add a new transaction.
        """
        return get_add_form(self.csrf_token)
