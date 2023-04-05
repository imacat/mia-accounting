# The Mia! Accounting Project.
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
"""The test for the journal entry management.

"""
import unittest
from datetime import date, timedelta
from decimal import Decimal

import httpx
from click.testing import Result
from flask import Flask
from flask.testing import FlaskCliRunner

from test_site import db
from testlib import NEXT_URI, Accounts, create_test_app, get_client
from testlib_journal_entry import NON_EMPTY_NOTE, EMPTY_NOTE, \
    get_add_form, get_unchanged_update_form, get_update_form, \
    match_journal_entry_detail, set_negative_amount, \
    remove_debit_in_a_currency, remove_credit_in_a_currency, add_journal_entry

PREFIX: str = "/accounting/journal-entries"
"""The URL prefix for the journal entry management."""
RETURN_TO_URI: str = "/accounting"
"""The URL to return to after the operation."""


class CashReceiptJournalEntryTestCase(unittest.TestCase):
    """The cash receipt journal entry test case."""

    def setUp(self) -> None:
        """Sets up the test.
        This is run once per test.

        :return: None.
        """
        self.app: Flask = create_test_app()

        runner: FlaskCliRunner = self.app.test_cli_runner()
        with self.app.app_context():
            from accounting.models import BaseAccount, JournalEntry, \
                JournalEntryLineItem
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
            JournalEntry.query.delete()
            JournalEntryLineItem.query.delete()

        self.client, self.csrf_token = get_client(self.app, "editor")

    def test_nobody(self) -> None:
        """Test the permission as nobody.

        :return: None.
        """
        client, csrf_token = get_client(self.app, "nobody")
        journal_entry_id: int = add_journal_entry(self.client,
                                                  self.__get_add_form())
        add_form: dict[str, str] = self.__get_add_form()
        add_form["csrf_token"] = csrf_token
        update_form: dict[str, str] = self.__get_update_form(journal_entry_id)
        update_form["csrf_token"] = csrf_token
        response: httpx.Response

        response = client.get(f"{PREFIX}/{journal_entry_id}")
        self.assertEqual(response.status_code, 403)

        response = client.get(f"{PREFIX}/create/receipt")
        self.assertEqual(response.status_code, 403)

        response = client.post(f"{PREFIX}/store/receipt", data=add_form)
        self.assertEqual(response.status_code, 403)

        response = client.get(f"{PREFIX}/{journal_entry_id}/edit")
        self.assertEqual(response.status_code, 403)

        response = client.post(f"{PREFIX}/{journal_entry_id}/update",
                               data=update_form)
        self.assertEqual(response.status_code, 403)

        response = client.post(f"{PREFIX}/{journal_entry_id}/delete",
                               data={"csrf_token": csrf_token})
        self.assertEqual(response.status_code, 403)

    def test_viewer(self) -> None:
        """Test the permission as viewer.

        :return: None.
        """
        client, csrf_token = get_client(self.app, "viewer")
        journal_entry_id: int = add_journal_entry(self.client,
                                                  self.__get_add_form())
        add_form: dict[str, str] = self.__get_add_form()
        add_form["csrf_token"] = csrf_token
        update_form: dict[str, str] = self.__get_update_form(journal_entry_id)
        update_form["csrf_token"] = csrf_token
        response: httpx.Response

        response = client.get(f"{PREFIX}/{journal_entry_id}")
        self.assertEqual(response.status_code, 200)

        response = client.get(f"{PREFIX}/create/receipt")
        self.assertEqual(response.status_code, 403)

        response = client.post(f"{PREFIX}/store/receipt", data=add_form)
        self.assertEqual(response.status_code, 403)

        response = client.get(f"{PREFIX}/{journal_entry_id}/edit")
        self.assertEqual(response.status_code, 403)

        response = client.post(f"{PREFIX}/{journal_entry_id}/update",
                               data=update_form)
        self.assertEqual(response.status_code, 403)

        response = client.post(f"{PREFIX}/{journal_entry_id}/delete",
                               data={"csrf_token": csrf_token})
        self.assertEqual(response.status_code, 403)

    def test_editor(self) -> None:
        """Test the permission as editor.

        :return: None.
        """
        journal_entry_id: int = add_journal_entry(self.client,
                                                  self.__get_add_form())
        add_form: dict[str, str] = self.__get_add_form()
        update_form: dict[str, str] = self.__get_update_form(journal_entry_id)
        response: httpx.Response

        response = self.client.get(f"{PREFIX}/{journal_entry_id}")
        self.assertEqual(response.status_code, 200)

        response = self.client.get(f"{PREFIX}/create/receipt")
        self.assertEqual(response.status_code, 200)

        response = self.client.post(f"{PREFIX}/store/receipt",
                                    data=add_form)
        self.assertEqual(response.status_code, 302)
        match_journal_entry_detail(response.headers["Location"])

        response = self.client.get(f"{PREFIX}/{journal_entry_id}/edit")
        self.assertEqual(response.status_code, 200)

        response = self.client.post(f"{PREFIX}/{journal_entry_id}/update",
                                    data=update_form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"],
                         f"{PREFIX}/{journal_entry_id}?next=%2F_next")

        response = self.client.post(f"{PREFIX}/{journal_entry_id}/delete",
                                    data={"csrf_token": self.csrf_token})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], RETURN_TO_URI)

    def test_add(self) -> None:
        """Tests to add the journal entries.

        :return: None.
        """
        from accounting.models import JournalEntry, JournalEntryCurrency
        create_uri: str = f"{PREFIX}/create/receipt?next=%2F_next"
        store_uri: str = f"{PREFIX}/store/receipt"
        response: httpx.Response
        form: dict[str, str]
        journal_entry: JournalEntry | None

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

        # A receivable line item cannot start from credit
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
        journal_entry_id: int \
            = match_journal_entry_detail(response.headers["Location"])

        with self.app.app_context():
            journal_entry = db.session.get(JournalEntry, journal_entry_id)
            self.assertIsNotNone(journal_entry)
            currencies: list[JournalEntryCurrency] = journal_entry.currencies
            self.assertEqual(len(currencies), 3)

            self.assertEqual(currencies[0].code, "JPY")
            self.assertEqual(len(currencies[0].debit), 1)
            self.assertEqual(currencies[0].debit[0].no, 1)
            self.assertEqual(currencies[0].debit[0].account.code,
                             Accounts.CASH)
            self.assertIsNone(currencies[0].debit[0].description)
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
            self.assertIsNone(currencies[1].debit[0].description)
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
            self.assertIsNone(currencies[2].debit[0].description)
            self.assertEqual(currencies[2].debit[0].amount,
                             sum([x.amount for x in currencies[2].credit]))
            self.assertEqual(len(currencies[2].credit), 2)
            self.assertEqual(currencies[2].credit[0].no, 6)
            self.assertEqual(currencies[2].credit[0].account.code,
                             Accounts.RENT_INCOME)
            self.assertEqual(currencies[2].credit[1].no, 7)
            self.assertEqual(currencies[2].credit[1].account.code,
                             Accounts.DONATION)

            self.assertEqual(journal_entry.note, NON_EMPTY_NOTE)

        # Success, with empty note
        form = self.__get_add_form()
        form["note"] = EMPTY_NOTE
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        journal_entry_id: int \
            = match_journal_entry_detail(response.headers["Location"])

        with self.app.app_context():
            journal_entry = db.session.get(JournalEntry, journal_entry_id)
            self.assertIsNotNone(journal_entry)
            self.assertIsNone(journal_entry.note)

    def test_basic_update(self) -> None:
        """Tests the basic rules to update a journal entry.

        :return: None.
        """
        from accounting.models import JournalEntry, JournalEntryCurrency
        journal_entry_id: int \
            = add_journal_entry(self.client, self.__get_add_form())
        detail_uri: str = f"{PREFIX}/{journal_entry_id}?next=%2F_next"
        edit_uri: str = f"{PREFIX}/{journal_entry_id}/edit?next=%2F_next"
        update_uri: str = f"{PREFIX}/{journal_entry_id}/update"
        form_0: dict[str, str] = self.__get_update_form(journal_entry_id)

        with self.app.app_context():
            journal_entry = db.session.get(JournalEntry, journal_entry_id)
            self.assertIsNotNone(journal_entry)
            currencies0: list[JournalEntryCurrency] = journal_entry.currencies
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

        # A receivable line item cannot start from credit
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
            journal_entry = db.session.get(JournalEntry, journal_entry_id)
            self.assertIsNotNone(journal_entry)
            currencies1: list[JournalEntryCurrency] = journal_entry.currencies
            self.assertEqual(len(currencies1), 3)

            self.assertEqual(currencies1[0].code, "AUD")
            self.assertEqual(len(currencies1[0].debit), 1)
            self.assertNotIn(currencies1[0].debit[0].id, old_id)
            self.assertEqual(currencies1[0].debit[0].no, 1)
            self.assertEqual(currencies1[0].debit[0].account.code,
                             Accounts.CASH)
            self.assertIsNone(currencies1[0].debit[0].description)
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
                             Accounts.RENT_INCOME)

            self.assertEqual(currencies1[1].code, "EUR")
            self.assertEqual(len(currencies1[1].debit), 1)
            self.assertNotIn(currencies1[1].debit[0].id, old_id)
            self.assertEqual(currencies1[1].debit[0].no, 2)
            self.assertEqual(currencies1[1].debit[0].account.code,
                             Accounts.CASH)
            self.assertIsNone(currencies1[1].debit[0].description)
            self.assertEqual(currencies1[1].debit[0].amount,
                             sum([x.amount for x in currencies1[1].credit]))
            self.assertEqual(len(currencies1[1].credit), 2)
            self.assertEqual(currencies1[1].credit[0].id,
                             currencies0[2].credit[0].id)
            self.assertEqual(currencies1[1].credit[0].no, 3)
            self.assertEqual(currencies1[1].credit[0].account.code,
                             Accounts.RENT_INCOME)
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
            self.assertIsNone(currencies1[2].debit[0].description)
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

            self.assertEqual(journal_entry.note, NON_EMPTY_NOTE)

    def test_update_not_modified(self) -> None:
        """Tests that the data is not modified.

        :return: None.
        """
        from accounting.models import JournalEntry
        journal_entry_id: int \
            = add_journal_entry(self.client, self.__get_add_form())
        detail_uri: str = f"{PREFIX}/{journal_entry_id}?next=%2F_next"
        update_uri: str = f"{PREFIX}/{journal_entry_id}/update"
        journal_entry: JournalEntry
        response: httpx.Response

        response = self.client.post(
            update_uri,
            data=self.__get_unchanged_update_form(journal_entry_id))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], detail_uri)

        with self.app.app_context():
            journal_entry = db.session.get(JournalEntry, journal_entry_id)
            self.assertIsNotNone(journal_entry)
            journal_entry.created_at \
                = journal_entry.created_at - timedelta(seconds=5)
            journal_entry.updated_at = journal_entry.created_at
            db.session.commit()

        response = self.client.post(
            update_uri, data=self.__get_update_form(journal_entry_id))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], detail_uri)

        with self.app.app_context():
            journal_entry = db.session.get(JournalEntry, journal_entry_id)
            self.assertIsNotNone(journal_entry)
            self.assertLess(journal_entry.created_at, journal_entry.updated_at)

    def test_created_updated_by(self) -> None:
        """Tests the created-by and updated-by record.

        :return: None.
        """
        from accounting.models import JournalEntry
        journal_entry_id: int \
            = add_journal_entry(self.client, self.__get_add_form())
        editor_username, admin_username = "editor", "admin"
        client, csrf_token = get_client(self.app, admin_username)
        detail_uri: str = f"{PREFIX}/{journal_entry_id}?next=%2F_next"
        update_uri: str = f"{PREFIX}/{journal_entry_id}/update"
        journal_entry: JournalEntry
        response: httpx.Response

        with self.app.app_context():
            journal_entry = db.session.get(JournalEntry, journal_entry_id)
            self.assertEqual(journal_entry.created_by.username,
                             editor_username)
            self.assertEqual(journal_entry.updated_by.username,
                             editor_username)

        form: dict[str, str] = self.__get_update_form(journal_entry_id)
        form["csrf_token"] = csrf_token
        response = client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], detail_uri)

        with self.app.app_context():
            journal_entry = db.session.get(JournalEntry, journal_entry_id)
            self.assertEqual(journal_entry.created_by.username,
                             editor_username)
            self.assertEqual(journal_entry.updated_by.username,
                             admin_username)

    def test_delete(self) -> None:
        """Tests to delete a journal entry.

        :return: None.
        """
        from accounting.models import JournalEntry, JournalEntryLineItem
        journal_entry_id_1: int \
            = add_journal_entry(self.client, self.__get_add_form())
        detail_uri: str = f"{PREFIX}/{journal_entry_id_1}?next=%2F_next"
        delete_uri: str = f"{PREFIX}/{journal_entry_id_1}/delete"
        response: httpx.Response

        form: dict[str, str] = self.__get_add_form()
        key: str = [x for x in form if x.endswith("-account_code")][0]
        form[key] = Accounts.PAYABLE
        journal_entry_id_2: int = add_journal_entry(self.client, form)
        with self.app.app_context():
            journal_entry: JournalEntry | None \
                = db.session.get(JournalEntry, journal_entry_id_2)
            self.assertIsNotNone(journal_entry)
            line_item: JournalEntryLineItem \
                = [x for x in journal_entry.line_items
                   if x.account_code == Accounts.PAYABLE][0]
        add_journal_entry(
            self.client,
            form={"csrf_token": self.csrf_token,
                  "next": NEXT_URI,
                  "date": date.today().isoformat(),
                  "currency-1-code": line_item.currency_code,
                  "currency-1-debit-1-original_line_item_id": line_item.id,
                  "currency-1-debit-1-account_code": line_item.account_code,
                  "currency-1-debit-1-amount": "1"})

        # Cannot delete the journal entry that is in use
        response = self.client.post(f"{PREFIX}/{journal_entry_id_2}/delete",
                                    data={"csrf_token": self.csrf_token,
                                          "next": NEXT_URI})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"],
                         f"{PREFIX}/{journal_entry_id_2}?next=%2F_next")

        # Success
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
        """Returns the form data to add a new journal entry.

        :return: The form data to add a new journal entry.
        """
        form: dict[str, str] = get_add_form(self.csrf_token)
        form = {x: form[x] for x in form if "-debit-" not in x}
        return form

    def __get_unchanged_update_form(self, journal_entry_id: int) \
            -> dict[str, str]:
        """Returns the form data to update a journal entry, where the data are
        not changed.

        :param journal_entry_id: The journal entry ID.
        :return: The form data to update the journal entry, where the data are
            not changed.
        """
        form: dict[str, str] = get_unchanged_update_form(
            journal_entry_id, self.app, self.csrf_token)
        form = {x: form[x] for x in form if "-debit-" not in x}
        return form

    def __get_update_form(self, journal_entry_id: int) -> dict[str, str]:
        """Returns the form data to update a journal entry, where the data are
        changed.

        :param journal_entry_id: The journal entry ID.
        :return: The form data to update the journal entry, where the data are
            changed.
        """
        form: dict[str, str] = get_update_form(
            journal_entry_id, self.app, self.csrf_token, False)
        form = {x: form[x] for x in form if "-debit-" not in x}
        return form


class CashDisbursementJournalEntryTestCase(unittest.TestCase):
    """The cash disbursement journal entry test case."""

    def setUp(self) -> None:
        """Sets up the test.
        This is run once per test.

        :return: None.
        """
        self.app: Flask = create_test_app()

        runner: FlaskCliRunner = self.app.test_cli_runner()
        with self.app.app_context():
            from accounting.models import BaseAccount, JournalEntry, \
                JournalEntryLineItem
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
            JournalEntry.query.delete()
            JournalEntryLineItem.query.delete()

        self.client, self.csrf_token = get_client(self.app, "editor")

    def test_nobody(self) -> None:
        """Test the permission as nobody.

        :return: None.
        """
        client, csrf_token = get_client(self.app, "nobody")
        journal_entry_id: int \
            = add_journal_entry(self.client, self.__get_add_form())
        add_form: dict[str, str] = self.__get_add_form()
        add_form["csrf_token"] = csrf_token
        update_form: dict[str, str] = self.__get_update_form(journal_entry_id)
        update_form["csrf_token"] = csrf_token
        response: httpx.Response

        response = client.get(f"{PREFIX}/{journal_entry_id}")
        self.assertEqual(response.status_code, 403)

        response = client.get(f"{PREFIX}/create/disbursement")
        self.assertEqual(response.status_code, 403)

        response = client.post(f"{PREFIX}/store/disbursement", data=add_form)
        self.assertEqual(response.status_code, 403)

        response = client.get(f"{PREFIX}/{journal_entry_id}/edit")
        self.assertEqual(response.status_code, 403)

        response = client.post(f"{PREFIX}/{journal_entry_id}/update",
                               data=update_form)
        self.assertEqual(response.status_code, 403)

        response = client.post(f"{PREFIX}/{journal_entry_id}/delete",
                               data={"csrf_token": csrf_token})
        self.assertEqual(response.status_code, 403)

    def test_viewer(self) -> None:
        """Test the permission as viewer.

        :return: None.
        """
        client, csrf_token = get_client(self.app, "viewer")
        journal_entry_id: int \
            = add_journal_entry(self.client, self.__get_add_form())
        add_form: dict[str, str] = self.__get_add_form()
        add_form["csrf_token"] = csrf_token
        update_form: dict[str, str] = self.__get_update_form(journal_entry_id)
        update_form["csrf_token"] = csrf_token
        response: httpx.Response

        response = client.get(f"{PREFIX}/{journal_entry_id}")
        self.assertEqual(response.status_code, 200)

        response = client.get(f"{PREFIX}/create/disbursement")
        self.assertEqual(response.status_code, 403)

        response = client.post(f"{PREFIX}/store/disbursement", data=add_form)
        self.assertEqual(response.status_code, 403)

        response = client.get(f"{PREFIX}/{journal_entry_id}/edit")
        self.assertEqual(response.status_code, 403)

        response = client.post(f"{PREFIX}/{journal_entry_id}/update",
                               data=update_form)
        self.assertEqual(response.status_code, 403)

        response = client.post(f"{PREFIX}/{journal_entry_id}/delete",
                               data={"csrf_token": csrf_token})
        self.assertEqual(response.status_code, 403)

    def test_editor(self) -> None:
        """Test the permission as editor.

        :return: None.
        """
        journal_entry_id: int \
            = add_journal_entry(self.client, self.__get_add_form())
        add_form: dict[str, str] = self.__get_add_form()
        update_form: dict[str, str] = self.__get_update_form(journal_entry_id)
        response: httpx.Response

        response = self.client.get(f"{PREFIX}/{journal_entry_id}")
        self.assertEqual(response.status_code, 200)

        response = self.client.get(f"{PREFIX}/create/disbursement")
        self.assertEqual(response.status_code, 200)

        response = self.client.post(f"{PREFIX}/store/disbursement",
                                    data=add_form)
        self.assertEqual(response.status_code, 302)
        match_journal_entry_detail(response.headers["Location"])

        response = self.client.get(f"{PREFIX}/{journal_entry_id}/edit")
        self.assertEqual(response.status_code, 200)

        response = self.client.post(f"{PREFIX}/{journal_entry_id}/update",
                                    data=update_form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"],
                         f"{PREFIX}/{journal_entry_id}?next=%2F_next")

        response = self.client.post(f"{PREFIX}/{journal_entry_id}/delete",
                                    data={"csrf_token": self.csrf_token})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], RETURN_TO_URI)

    def test_add(self) -> None:
        """Tests to add the journal entries.

        :return: None.
        """
        from accounting.models import JournalEntry, JournalEntryCurrency
        create_uri: str = f"{PREFIX}/create/disbursement?next=%2F_next"
        store_uri: str = f"{PREFIX}/store/disbursement"
        response: httpx.Response
        form: dict[str, str]
        journal_entry: JournalEntry | None

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

        # A payable line item cannot start from debit
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
        journal_entry_id: int \
            = match_journal_entry_detail(response.headers["Location"])

        with self.app.app_context():
            journal_entry = db.session.get(JournalEntry, journal_entry_id)
            self.assertIsNotNone(journal_entry)
            currencies: list[JournalEntryCurrency] = journal_entry.currencies
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
            self.assertIsNone(currencies[0].credit[0].description)
            self.assertEqual(currencies[0].credit[0].amount,
                             sum([x.amount for x in currencies[0].debit]))

            self.assertEqual(currencies[1].code, "USD")
            self.assertEqual(len(currencies[1].debit), 3)
            self.assertEqual(currencies[1].debit[0].no, 3)
            self.assertEqual(currencies[1].debit[0].account.code,
                             Accounts.BANK)
            self.assertEqual(currencies[1].debit[0].description, "Deposit")
            self.assertEqual(currencies[1].debit[1].no, 4)
            self.assertEqual(currencies[1].debit[1].account.code,
                             Accounts.OFFICE)
            self.assertEqual(currencies[1].debit[1].description, "Pens")
            self.assertEqual(currencies[1].debit[2].no, 5)
            self.assertEqual(currencies[1].debit[2].account.code,
                             Accounts.CASH)
            self.assertIsNone(currencies[1].debit[2].description)
            self.assertEqual(len(currencies[1].credit), 1)
            self.assertEqual(currencies[1].credit[0].no, 2)
            self.assertEqual(currencies[1].credit[0].account.code,
                             Accounts.CASH)
            self.assertIsNone(currencies[1].credit[0].description)
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
            self.assertIsNone(currencies[2].credit[0].description)
            self.assertEqual(currencies[2].credit[0].amount,
                             sum([x.amount for x in currencies[2].debit]))

            self.assertEqual(journal_entry.note, NON_EMPTY_NOTE)

        # Success, with empty note
        form = self.__get_add_form()
        form["note"] = EMPTY_NOTE
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        journal_entry_id: int \
            = match_journal_entry_detail(response.headers["Location"])

        with self.app.app_context():
            journal_entry = db.session.get(JournalEntry, journal_entry_id)
            self.assertIsNotNone(journal_entry)
            self.assertIsNone(journal_entry.note)

    def test_basic_update(self) -> None:
        """Tests the basic rules to update a journal entry.

        :return: None.
        """
        from accounting.models import JournalEntry, JournalEntryCurrency
        journal_entry_id: int \
            = add_journal_entry(self.client, self.__get_add_form())
        detail_uri: str = f"{PREFIX}/{journal_entry_id}?next=%2F_next"
        edit_uri: str = f"{PREFIX}/{journal_entry_id}/edit?next=%2F_next"
        update_uri: str = f"{PREFIX}/{journal_entry_id}/update"
        form_0: dict[str, str] = self.__get_update_form(journal_entry_id)

        with self.app.app_context():
            journal_entry = db.session.get(JournalEntry, journal_entry_id)
            self.assertIsNotNone(journal_entry)
            currencies0: list[JournalEntryCurrency] = journal_entry.currencies
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

        # A payable line item cannot start from debit
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
            journal_entry = db.session.get(JournalEntry, journal_entry_id)
            self.assertIsNotNone(journal_entry)
            currencies1: list[JournalEntryCurrency] = journal_entry.currencies
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
            self.assertIsNone(currencies1[0].credit[0].description)
            self.assertEqual(currencies1[0].credit[0].amount,
                             sum([x.amount for x in currencies1[0].debit]))

            self.assertEqual(currencies1[1].code, "EUR")
            self.assertEqual(len(currencies1[1].debit), 2)
            self.assertEqual(currencies1[1].debit[0].id,
                             currencies0[2].debit[0].id)
            self.assertEqual(currencies1[1].debit[0].no, 3)
            self.assertEqual(currencies1[1].debit[0].account.code,
                             Accounts.CASH)
            self.assertIsNone(currencies1[1].debit[0].description)
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
            self.assertIsNone(currencies1[1].credit[0].description)
            self.assertEqual(currencies1[1].credit[0].amount,
                             sum([x.amount for x in currencies1[1].debit]))

            self.assertEqual(currencies1[2].code, "USD")
            self.assertEqual(len(currencies1[2].debit), 3)
            self.assertNotIn(currencies1[2].debit[0].id, old_id)
            self.assertEqual(currencies1[2].debit[0].no, 5)
            self.assertEqual(currencies1[2].debit[0].account.code,
                             Accounts.TRAVEL)
            self.assertIsNone(currencies1[2].debit[0].description)
            self.assertEqual(currencies1[2].debit[1].id,
                             currencies0[1].debit[2].id)
            self.assertEqual(currencies1[2].debit[1].no, 6)
            self.assertEqual(currencies1[2].debit[1].account.code,
                             Accounts.CASH)
            self.assertIsNone(currencies1[2].debit[1].description)
            self.assertEqual(currencies1[2].debit[2].id,
                             currencies0[1].debit[0].id)
            self.assertEqual(currencies1[2].debit[2].no, 7)
            self.assertEqual(currencies1[2].debit[2].account.code,
                             Accounts.BANK)
            self.assertEqual(currencies1[2].debit[2].description, "Deposit")
            self.assertEqual(len(currencies1[2].credit), 1)
            self.assertEqual(currencies1[2].credit[0].id,
                             currencies0[1].credit[0].id)
            self.assertEqual(currencies1[2].credit[0].no, 3)
            self.assertEqual(currencies1[2].credit[0].account.code,
                             Accounts.CASH)
            self.assertIsNone(currencies1[2].credit[0].description)
            self.assertEqual(currencies1[2].credit[0].amount,
                             sum([x.amount for x in currencies1[2].debit]))

            self.assertEqual(journal_entry.note, NON_EMPTY_NOTE)

    def test_update_not_modified(self) -> None:
        """Tests that the data is not modified.

        :return: None.
        """
        from accounting.models import JournalEntry
        journal_entry_id: int \
            = add_journal_entry(self.client, self.__get_add_form())
        detail_uri: str = f"{PREFIX}/{journal_entry_id}?next=%2F_next"
        update_uri: str = f"{PREFIX}/{journal_entry_id}/update"
        journal_entry: JournalEntry
        response: httpx.Response

        response = self.client.post(
            update_uri,
            data=self.__get_unchanged_update_form(journal_entry_id))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], detail_uri)

        with self.app.app_context():
            journal_entry = db.session.get(JournalEntry, journal_entry_id)
            self.assertIsNotNone(journal_entry)
            journal_entry.created_at \
                = journal_entry.created_at - timedelta(seconds=5)
            journal_entry.updated_at = journal_entry.created_at
            db.session.commit()

        response = self.client.post(
            update_uri, data=self.__get_update_form(journal_entry_id))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], detail_uri)

        with self.app.app_context():
            journal_entry = db.session.get(JournalEntry, journal_entry_id)
            self.assertIsNotNone(journal_entry)
            self.assertLess(journal_entry.created_at, journal_entry.updated_at)

    def test_created_updated_by(self) -> None:
        """Tests the created-by and updated-by record.

        :return: None.
        """
        from accounting.models import JournalEntry
        journal_entry_id: int \
            = add_journal_entry(self.client, self.__get_add_form())
        editor_username, admin_username = "editor", "admin"
        client, csrf_token = get_client(self.app, admin_username)
        detail_uri: str = f"{PREFIX}/{journal_entry_id}?next=%2F_next"
        update_uri: str = f"{PREFIX}/{journal_entry_id}/update"
        journal_entry: JournalEntry
        response: httpx.Response

        with self.app.app_context():
            journal_entry = db.session.get(JournalEntry, journal_entry_id)
            self.assertEqual(journal_entry.created_by.username,
                             editor_username)
            self.assertEqual(journal_entry.updated_by.username,
                             editor_username)

        form: dict[str, str] = self.__get_update_form(journal_entry_id)
        form["csrf_token"] = csrf_token
        response = client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], detail_uri)

        with self.app.app_context():
            journal_entry = db.session.get(JournalEntry, journal_entry_id)
            self.assertEqual(journal_entry.created_by.username,
                             editor_username)
            self.assertEqual(journal_entry.updated_by.username,
                             admin_username)

    def test_delete(self) -> None:
        """Tests to delete a journal entry.

        :return: None.
        """
        journal_entry_id: int \
            = add_journal_entry(self.client, self.__get_add_form())
        detail_uri: str = f"{PREFIX}/{journal_entry_id}?next=%2F_next"
        delete_uri: str = f"{PREFIX}/{journal_entry_id}/delete"
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
        """Returns the form data to add a new journal entry.

        :return: The form data to add a new journal entry.
        """
        form: dict[str, str] = get_add_form(self.csrf_token)
        form = {x: form[x] for x in form if "-credit-" not in x}
        return form

    def __get_unchanged_update_form(self, journal_entry_id: int) \
            -> dict[str, str]:
        """Returns the form data to update a journal entry, where the data are
        not changed.

        :param journal_entry_id: The journal entry ID.
        :return: The form data to update the journal entry, where the data are
            not changed.
        """
        form: dict[str, str] = get_unchanged_update_form(
            journal_entry_id, self.app, self.csrf_token)
        form = {x: form[x] for x in form if "-credit-" not in x}
        return form

    def __get_update_form(self, journal_entry_id: int) -> dict[str, str]:
        """Returns the form data to update a journal entry, where the data are
        changed.

        :param journal_entry_id: The journal entry ID.
        :return: The form data to update the journal entry, where the data are
            changed.
        """
        form: dict[str, str] = get_update_form(
            journal_entry_id, self.app, self.csrf_token, True)
        form = {x: form[x] for x in form if "-credit-" not in x}
        return form


class TransferJournalEntryTestCase(unittest.TestCase):
    """The transfer journal entry test case."""

    def setUp(self) -> None:
        """Sets up the test.
        This is run once per test.

        :return: None.
        """
        self.app: Flask = create_test_app()

        runner: FlaskCliRunner = self.app.test_cli_runner()
        with self.app.app_context():
            from accounting.models import BaseAccount, JournalEntry, \
                JournalEntryLineItem
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
            JournalEntry.query.delete()
            JournalEntryLineItem.query.delete()

        self.client, self.csrf_token = get_client(self.app, "editor")

    def test_nobody(self) -> None:
        """Test the permission as nobody.

        :return: None.
        """
        client, csrf_token = get_client(self.app, "nobody")
        journal_entry_id: int \
            = add_journal_entry(self.client, self.__get_add_form())
        add_form: dict[str, str] = self.__get_add_form()
        add_form["csrf_token"] = csrf_token
        update_form: dict[str, str] = self.__get_update_form(journal_entry_id)
        update_form["csrf_token"] = csrf_token
        response: httpx.Response

        response = client.get(f"{PREFIX}/{journal_entry_id}")
        self.assertEqual(response.status_code, 403)

        response = client.get(f"{PREFIX}/create/transfer")
        self.assertEqual(response.status_code, 403)

        response = client.post(f"{PREFIX}/store/transfer", data=add_form)
        self.assertEqual(response.status_code, 403)

        response = client.get(f"{PREFIX}/{journal_entry_id}/edit")
        self.assertEqual(response.status_code, 403)

        response = client.post(f"{PREFIX}/{journal_entry_id}/update",
                               data=update_form)
        self.assertEqual(response.status_code, 403)

        response = client.post(f"{PREFIX}/{journal_entry_id}/delete",
                               data={"csrf_token": csrf_token})
        self.assertEqual(response.status_code, 403)

    def test_viewer(self) -> None:
        """Test the permission as viewer.

        :return: None.
        """
        client, csrf_token = get_client(self.app, "viewer")
        journal_entry_id: int \
            = add_journal_entry(self.client, self.__get_add_form())
        add_form: dict[str, str] = self.__get_add_form()
        add_form["csrf_token"] = csrf_token
        update_form: dict[str, str] = self.__get_update_form(journal_entry_id)
        update_form["csrf_token"] = csrf_token
        response: httpx.Response

        response = client.get(f"{PREFIX}/{journal_entry_id}")
        self.assertEqual(response.status_code, 200)

        response = client.get(f"{PREFIX}/create/transfer")
        self.assertEqual(response.status_code, 403)

        response = client.post(f"{PREFIX}/store/transfer", data=add_form)
        self.assertEqual(response.status_code, 403)

        response = client.get(f"{PREFIX}/{journal_entry_id}/edit")
        self.assertEqual(response.status_code, 403)

        response = client.post(f"{PREFIX}/{journal_entry_id}/update",
                               data=update_form)
        self.assertEqual(response.status_code, 403)

        response = client.post(f"{PREFIX}/{journal_entry_id}/delete",
                               data={"csrf_token": csrf_token})
        self.assertEqual(response.status_code, 403)

    def test_editor(self) -> None:
        """Test the permission as editor.

        :return: None.
        """
        journal_entry_id: int \
            = add_journal_entry(self.client, self.__get_add_form())
        add_form: dict[str, str] = self.__get_add_form()
        update_form: dict[str, str] = self.__get_update_form(journal_entry_id)
        response: httpx.Response

        response = self.client.get(f"{PREFIX}/{journal_entry_id}")
        self.assertEqual(response.status_code, 200)

        response = self.client.get(f"{PREFIX}/create/transfer")
        self.assertEqual(response.status_code, 200)

        response = self.client.post(f"{PREFIX}/store/transfer",
                                    data=add_form)
        self.assertEqual(response.status_code, 302)
        match_journal_entry_detail(response.headers["Location"])

        response = self.client.get(f"{PREFIX}/{journal_entry_id}/edit")
        self.assertEqual(response.status_code, 200)

        response = self.client.post(f"{PREFIX}/{journal_entry_id}/update",
                                    data=update_form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"],
                         f"{PREFIX}/{journal_entry_id}?next=%2F_next")

        response = self.client.post(f"{PREFIX}/{journal_entry_id}/delete",
                                    data={"csrf_token": self.csrf_token})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], RETURN_TO_URI)

    def test_add(self) -> None:
        """Tests to add the journal entries.

        :return: None.
        """
        from accounting.models import JournalEntry, JournalEntryCurrency
        create_uri: str = f"{PREFIX}/create/transfer?next=%2F_next"
        store_uri: str = f"{PREFIX}/store/transfer"
        response: httpx.Response
        form: dict[str, str]
        journal_entry: JournalEntry | None

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

        # A receivable line item cannot start from credit
        form = self.__get_add_form()
        key: str = [x for x in form.keys()
                    if x.endswith("-account_code") and "-credit-" in x][0]
        form[key] = Accounts.RECEIVABLE
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)

        # A payable line item cannot start from debit
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
        journal_entry_id: int \
            = match_journal_entry_detail(response.headers["Location"])

        with self.app.app_context():
            journal_entry = db.session.get(JournalEntry, journal_entry_id)
            self.assertIsNotNone(journal_entry)
            currencies: list[JournalEntryCurrency] = journal_entry.currencies
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
            self.assertEqual(currencies[1].debit[0].description, "Deposit")
            self.assertEqual(currencies[1].debit[1].no, 4)
            self.assertEqual(currencies[1].debit[1].account.code,
                             Accounts.OFFICE)
            self.assertEqual(currencies[1].debit[1].description, "Pens")
            self.assertEqual(currencies[1].debit[2].no, 5)
            self.assertEqual(currencies[1].debit[2].account.code,
                             Accounts.CASH)
            self.assertIsNone(currencies[1].debit[2].description)
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
                             Accounts.RENT_INCOME)
            self.assertEqual(currencies[2].credit[1].no, 7)
            self.assertEqual(currencies[2].credit[1].account.code,
                             Accounts.DONATION)

            self.assertEqual(journal_entry.note, NON_EMPTY_NOTE)

        # Success, with empty note
        form = self.__get_add_form()
        form["note"] = EMPTY_NOTE
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        journal_entry_id: int \
            = match_journal_entry_detail(response.headers["Location"])

        with self.app.app_context():
            journal_entry = db.session.get(JournalEntry, journal_entry_id)
            self.assertIsNotNone(journal_entry)
            self.assertIsNone(journal_entry.note)

    def test_basic_update(self) -> None:
        """Tests the basic rules to update a journal entry.

        :return: None.
        """
        from accounting.models import JournalEntry, JournalEntryCurrency
        journal_entry_id: int \
            = add_journal_entry(self.client, self.__get_add_form())
        detail_uri: str = f"{PREFIX}/{journal_entry_id}?next=%2F_next"
        edit_uri: str = f"{PREFIX}/{journal_entry_id}/edit?next=%2F_next"
        update_uri: str = f"{PREFIX}/{journal_entry_id}/update"
        form_0: dict[str, str] = self.__get_update_form(journal_entry_id)

        with self.app.app_context():
            journal_entry = db.session.get(JournalEntry, journal_entry_id)
            self.assertIsNotNone(journal_entry)
            currencies0: list[JournalEntryCurrency] = journal_entry.currencies
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

        # A receivable line item cannot start from credit
        form = self.__get_add_form()
        key: str = [x for x in form.keys()
                    if x.endswith("-account_code") and "-credit-" in x][0]
        form[key] = Accounts.RECEIVABLE
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # A payable line item cannot start from debit
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
            journal_entry = db.session.get(JournalEntry, journal_entry_id)
            self.assertIsNotNone(journal_entry)
            currencies1: list[JournalEntryCurrency] = journal_entry.currencies
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
                             Accounts.RENT_INCOME)

            self.assertEqual(currencies1[1].code, "EUR")
            self.assertEqual(len(currencies1[1].debit), 2)
            self.assertEqual(currencies1[1].debit[0].id,
                             currencies0[2].debit[0].id)
            self.assertEqual(currencies1[1].debit[0].no, 3)
            self.assertEqual(currencies1[1].debit[0].account.code,
                             Accounts.CASH)
            self.assertIsNone(currencies1[1].debit[0].description)
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
                             Accounts.RENT_INCOME)
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
            self.assertIsNone(currencies1[2].debit[0].description)
            self.assertEqual(currencies1[2].debit[1].id,
                             currencies0[1].debit[2].id)
            self.assertEqual(currencies1[2].debit[1].no, 6)
            self.assertEqual(currencies1[2].debit[1].account.code,
                             Accounts.CASH)
            self.assertIsNone(currencies1[2].debit[1].description)
            self.assertEqual(currencies1[2].debit[2].id,
                             currencies0[1].debit[0].id)
            self.assertEqual(currencies1[2].debit[2].no, 7)
            self.assertEqual(currencies1[2].debit[2].account.code,
                             Accounts.BANK)
            self.assertEqual(currencies1[2].debit[2].description, "Deposit")
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

            self.assertEqual(journal_entry.note, NON_EMPTY_NOTE)

    def test_update_not_modified(self) -> None:
        """Tests that the data is not modified.

        :return: None.
        """
        from accounting.models import JournalEntry
        journal_entry_id: int \
            = add_journal_entry(self.client, self.__get_add_form())
        detail_uri: str = f"{PREFIX}/{journal_entry_id}?next=%2F_next"
        update_uri: str = f"{PREFIX}/{journal_entry_id}/update"
        journal_entry: JournalEntry
        response: httpx.Response

        response = self.client.post(
            update_uri,
            data=self.__get_unchanged_update_form(journal_entry_id))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], detail_uri)

        with self.app.app_context():
            journal_entry = db.session.get(JournalEntry, journal_entry_id)
            self.assertIsNotNone(journal_entry)
            journal_entry.created_at \
                = journal_entry.created_at - timedelta(seconds=5)
            journal_entry.updated_at = journal_entry.created_at
            db.session.commit()

        response = self.client.post(
            update_uri, data=self.__get_update_form(journal_entry_id))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], detail_uri)

        with self.app.app_context():
            journal_entry = db.session.get(JournalEntry, journal_entry_id)
            self.assertIsNotNone(journal_entry)
            self.assertLess(journal_entry.created_at, journal_entry.updated_at)

    def test_created_updated_by(self) -> None:
        """Tests the created-by and updated-by record.

        :return: None.
        """
        from accounting.models import JournalEntry
        journal_entry_id: int \
            = add_journal_entry(self.client, self.__get_add_form())
        editor_username, admin_username = "editor", "admin"
        client, csrf_token = get_client(self.app, admin_username)
        detail_uri: str = f"{PREFIX}/{journal_entry_id}?next=%2F_next"
        update_uri: str = f"{PREFIX}/{journal_entry_id}/update"
        journal_entry: JournalEntry
        response: httpx.Response

        with self.app.app_context():
            journal_entry = db.session.get(JournalEntry, journal_entry_id)
            self.assertEqual(journal_entry.created_by.username,
                             editor_username)
            self.assertEqual(journal_entry.updated_by.username,
                             editor_username)

        form: dict[str, str] = self.__get_update_form(journal_entry_id)
        form["csrf_token"] = csrf_token
        response = client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], detail_uri)

        with self.app.app_context():
            journal_entry = db.session.get(JournalEntry, journal_entry_id)
            self.assertEqual(journal_entry.created_by.username,
                             editor_username)
            self.assertEqual(journal_entry.updated_by.username,
                             admin_username)

    def test_save_as_receipt(self) -> None:
        """Tests to save a transfer journal entry as a cash receipt journal
        entry.

        :return: None.
        """
        from accounting.models import JournalEntry, JournalEntryCurrency
        journal_entry_id: int \
            = add_journal_entry(self.client, self.__get_add_form())
        detail_uri: str = f"{PREFIX}/{journal_entry_id}?next=%2F_next"
        update_uri: str = f"{PREFIX}/{journal_entry_id}/update?as=receipt"
        form_0: dict[str, str] = self.__get_update_form(journal_entry_id)
        form_0 = {x: form_0[x] for x in form_0 if "-debit-" not in x}

        with self.app.app_context():
            journal_entry = db.session.get(JournalEntry, journal_entry_id)
            self.assertIsNotNone(journal_entry)
            currencies0: list[JournalEntryCurrency] = journal_entry.currencies
            old_id: set[int] = set()
            for currency in currencies0:
                old_id.update({x.id for x in currency.debit})

        # Success
        response = self.client.post(update_uri, data=form_0)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], detail_uri)

        with self.app.app_context():
            journal_entry = db.session.get(JournalEntry, journal_entry_id)
            self.assertIsNotNone(journal_entry)
            currencies1: list[JournalEntryCurrency] = journal_entry.currencies
            self.assertEqual(len(currencies1), 3)

            self.assertEqual(currencies1[0].code, "AUD")
            self.assertEqual(len(currencies1[0].debit), 1)
            self.assertNotIn(currencies1[0].debit[0].id, old_id)
            self.assertEqual(currencies1[0].debit[0].no, 1)
            self.assertEqual(currencies1[0].debit[0].account.code,
                             Accounts.CASH)
            self.assertIsNone(currencies1[0].debit[0].description)
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
                             Accounts.RENT_INCOME)

            self.assertEqual(currencies1[1].code, "EUR")
            self.assertEqual(len(currencies1[1].debit), 1)
            self.assertNotIn(currencies1[1].debit[0].id, old_id)
            self.assertEqual(currencies1[1].debit[0].no, 2)
            self.assertEqual(currencies1[1].debit[0].account.code,
                             Accounts.CASH)
            self.assertIsNone(currencies1[1].debit[0].description)
            self.assertEqual(currencies1[1].debit[0].amount,
                             sum([x.amount for x in currencies1[1].credit]))
            self.assertEqual(len(currencies1[1].credit), 2)
            self.assertEqual(currencies1[1].credit[0].id,
                             currencies0[2].credit[0].id)
            self.assertEqual(currencies1[1].credit[0].no, 3)
            self.assertEqual(currencies1[1].credit[0].account.code,
                             Accounts.RENT_INCOME)
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
            self.assertIsNone(currencies1[2].debit[0].description)
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

            self.assertEqual(journal_entry.note, NON_EMPTY_NOTE)

    def test_save_as_disbursement(self) -> None:
        """Tests to save a transfer journal entry as a cash disbursement
        journal entry.

        :return: None.
        """
        from accounting.models import JournalEntry, JournalEntryCurrency
        journal_entry_id: int \
            = add_journal_entry(self.client, self.__get_add_form())
        detail_uri: str = f"{PREFIX}/{journal_entry_id}?next=%2F_next"
        update_uri: str = f"{PREFIX}/{journal_entry_id}/update?as=disbursement"
        form_0: dict[str, str] = self.__get_update_form(journal_entry_id)
        form_0 = {x: form_0[x] for x in form_0 if "-credit-" not in x}

        with self.app.app_context():
            journal_entry = db.session.get(JournalEntry, journal_entry_id)
            self.assertIsNotNone(journal_entry)
            currencies0: list[JournalEntryCurrency] = journal_entry.currencies
            old_id: set[int] = set()
            for currency in currencies0:
                old_id.update({x.id for x in currency.debit})

        # Success
        response = self.client.post(update_uri, data=form_0)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], detail_uri)

        with self.app.app_context():
            journal_entry = db.session.get(JournalEntry, journal_entry_id)
            self.assertIsNotNone(journal_entry)
            currencies1: list[JournalEntryCurrency] = journal_entry.currencies
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
            self.assertIsNone(currencies1[0].credit[0].description)
            self.assertEqual(currencies1[0].credit[0].amount,
                             sum([x.amount for x in currencies1[0].debit]))

            self.assertEqual(currencies1[1].code, "EUR")
            self.assertEqual(len(currencies1[1].debit), 2)
            self.assertEqual(currencies1[1].debit[0].id,
                             currencies0[2].debit[0].id)
            self.assertEqual(currencies1[1].debit[0].no, 3)
            self.assertEqual(currencies1[1].debit[0].account.code,
                             Accounts.CASH)
            self.assertIsNone(currencies1[1].debit[0].description)
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
            self.assertIsNone(currencies1[1].credit[0].description)
            self.assertEqual(currencies1[1].credit[0].amount,
                             sum([x.amount for x in currencies1[1].debit]))

            self.assertEqual(currencies1[2].code, "USD")
            self.assertEqual(len(currencies1[2].debit), 3)
            self.assertNotIn(currencies1[2].debit[0].id, old_id)
            self.assertEqual(currencies1[2].debit[0].no, 5)
            self.assertEqual(currencies1[2].debit[0].account.code,
                             Accounts.TRAVEL)
            self.assertIsNone(currencies1[2].debit[0].description)
            self.assertEqual(currencies1[2].debit[1].id,
                             currencies0[1].debit[2].id)
            self.assertEqual(currencies1[2].debit[1].no, 6)
            self.assertEqual(currencies1[2].debit[1].account.code,
                             Accounts.CASH)
            self.assertIsNone(currencies1[2].debit[1].description)
            self.assertEqual(currencies1[2].debit[2].id,
                             currencies0[1].debit[0].id)
            self.assertEqual(currencies1[2].debit[2].no, 7)
            self.assertEqual(currencies1[2].debit[2].account.code,
                             Accounts.BANK)
            self.assertEqual(currencies1[2].debit[2].description, "Deposit")
            self.assertEqual(len(currencies1[2].credit), 1)
            self.assertEqual(currencies1[2].credit[0].id,
                             currencies0[1].credit[0].id)
            self.assertEqual(currencies1[2].credit[0].no, 3)
            self.assertEqual(currencies1[2].credit[0].account.code,
                             Accounts.CASH)
            self.assertIsNone(currencies1[2].credit[0].description)
            self.assertEqual(currencies1[2].credit[0].amount,
                             sum([x.amount for x in currencies1[2].debit]))

            self.assertEqual(journal_entry.note, NON_EMPTY_NOTE)

    def test_delete(self) -> None:
        """Tests to delete a journal entry.

        :return: None.
        """
        journal_entry_id: int \
            = add_journal_entry(self.client, self.__get_add_form())
        detail_uri: str = f"{PREFIX}/{journal_entry_id}?next=%2F_next"
        delete_uri: str = f"{PREFIX}/{journal_entry_id}/delete"
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
        """Returns the form data to add a new journal entry.

        :return: The form data to add a new journal entry.
        """
        return get_add_form(self.csrf_token)

    def __get_unchanged_update_form(self, journal_entry_id: int) \
            -> dict[str, str]:
        """Returns the form data to update a journal entry, where the data are
        not changed.

        :param journal_entry_id: The journal entry ID.
        :return: The form data to update the journal entry, where the data are
            not changed.
        """
        return get_unchanged_update_form(
            journal_entry_id, self.app, self.csrf_token)

    def __get_update_form(self, journal_entry_id: int) -> dict[str, str]:
        """Returns the form data to update a journal entry, where the data are
        changed.

        :param journal_entry_id: The journal entry ID.
        :return: The form data to update the journal entry, where the data are
            changed.
        """
        return get_update_form(journal_entry_id,
                               self.app, self.csrf_token, None)


class JournalEntryReorderTestCase(unittest.TestCase):
    """The journal entry reorder test case."""

    def setUp(self) -> None:
        """Sets up the test.
        This is run once per test.

        :return: None.
        """
        self.app: Flask = create_test_app()

        runner: FlaskCliRunner = self.app.test_cli_runner()
        with self.app.app_context():
            from accounting.models import BaseAccount, JournalEntry, \
                JournalEntryLineItem
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
            JournalEntry.query.delete()
            JournalEntryLineItem.query.delete()

        self.client, self.csrf_token = get_client(self.app, "editor")

    def test_change_date(self) -> None:
        """Tests to change the date of a journal entry.

        :return: None.
        """
        from accounting.models import JournalEntry
        response: httpx.Response

        id_1: int = add_journal_entry(self.client,
                                      self.__get_add_receipt_form())
        id_2: int = add_journal_entry(self.client,
                                      self.__get_add_disbursement_form())
        id_3: int = add_journal_entry(self.client,
                                      self.__get_add_transfer_form())
        id_4: int = add_journal_entry(self.client,
                                      self.__get_add_receipt_form())
        id_5: int = add_journal_entry(self.client,
                                      self.__get_add_disbursement_form())

        with self.app.app_context():
            journal_entry_1: JournalEntry = db.session.get(JournalEntry, id_1)
            journal_entry_date_2: date = journal_entry_1.date
            journal_entry_date_1: date \
                = journal_entry_date_2 - timedelta(days=1)
            journal_entry_1.date = journal_entry_date_1
            journal_entry_1.no = 3
            journal_entry_2: JournalEntry = db.session.get(JournalEntry, id_2)
            journal_entry_2.date = journal_entry_date_1
            journal_entry_2.no = 5
            journal_entry_3: JournalEntry = db.session.get(JournalEntry, id_3)
            journal_entry_3.date = journal_entry_date_1
            journal_entry_3.no = 8
            journal_entry_4: JournalEntry = db.session.get(JournalEntry, id_4)
            journal_entry_4.no = 2
            journal_entry_5: JournalEntry = db.session.get(JournalEntry, id_5)
            journal_entry_5.no = 6
            db.session.commit()

        form: dict[str, str] \
            = self.__get_disbursement_unchanged_update_form(id_2)
        form["date"] = journal_entry_date_2.isoformat()
        response = self.client.post(f"{PREFIX}/{id_2}/update", data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"],
                         f"{PREFIX}/{id_2}?next=%2F_next")

        with self.app.app_context():
            self.assertEqual(db.session.get(JournalEntry, id_1).no, 1)
            self.assertEqual(db.session.get(JournalEntry, id_2).no, 3)
            self.assertEqual(db.session.get(JournalEntry, id_3).no, 2)
            self.assertEqual(db.session.get(JournalEntry, id_4).no, 1)
            self.assertEqual(db.session.get(JournalEntry, id_5).no, 2)

    def test_reorder(self) -> None:
        """Tests to reorder the journal entries in a same day.

        :return: None.
        """
        from accounting.models import JournalEntry
        response: httpx.Response

        id_1: int = add_journal_entry(self.client,
                                      self.__get_add_receipt_form())
        id_2: int = add_journal_entry(self.client,
                                      self.__get_add_disbursement_form())
        id_3: int = add_journal_entry(self.client,
                                      self.__get_add_transfer_form())
        id_4: int = add_journal_entry(self.client,
                                      self.__get_add_receipt_form())
        id_5: int = add_journal_entry(self.client,
                                      self.__get_add_disbursement_form())

        with self.app.app_context():
            journal_entry_date: date = db.session.get(JournalEntry, id_1).date

        response = self.client.post(
            f"{PREFIX}/dates/{journal_entry_date.isoformat()}",
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
            self.assertEqual(db.session.get(JournalEntry, id_1).no, 4)
            self.assertEqual(db.session.get(JournalEntry, id_2).no, 1)
            self.assertEqual(db.session.get(JournalEntry, id_3).no, 5)
            self.assertEqual(db.session.get(JournalEntry, id_4).no, 2)
            self.assertEqual(db.session.get(JournalEntry, id_5).no, 3)

        # Malformed orders
        with self.app.app_context():
            db.session.get(JournalEntry, id_1).no = 3
            db.session.get(JournalEntry, id_2).no = 4
            db.session.get(JournalEntry, id_3).no = 6
            db.session.get(JournalEntry, id_4).no = 8
            db.session.get(JournalEntry, id_5).no = 9
            db.session.commit()

        response = self.client.post(
            f"{PREFIX}/dates/{journal_entry_date.isoformat()}",
            data={"csrf_token": self.csrf_token,
                  "next": "/next",
                  f"{id_2}-no": "3a",
                  f"{id_3}-no": "5",
                  f"{id_4}-no": "2"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], f"/next")

        with self.app.app_context():
            self.assertEqual(db.session.get(JournalEntry, id_1).no, 3)
            self.assertEqual(db.session.get(JournalEntry, id_2).no, 4)
            self.assertEqual(db.session.get(JournalEntry, id_3).no, 2)
            self.assertEqual(db.session.get(JournalEntry, id_4).no, 1)
            self.assertEqual(db.session.get(JournalEntry, id_5).no, 5)

    def __get_add_receipt_form(self) -> dict[str, str]:
        """Returns the form data to add a new cash receipt journal entry.

        :return: The form data to add a new cash receipt journal entry.
        """
        form: dict[str, str] = get_add_form(self.csrf_token)
        form = {x: form[x] for x in form if "-debit-" not in x}
        return form

    def __get_add_disbursement_form(self) -> dict[str, str]:
        """Returns the form data to add a new cash disbursement journal entry.

        :return: The form data to add a new cash disbursement journal entry.
        """
        form: dict[str, str] = get_add_form(self.csrf_token)
        form = {x: form[x] for x in form if "-credit-" not in x}
        return form

    def __get_disbursement_unchanged_update_form(self, journal_entry_id: int) \
            -> dict[str, str]:
        """Returns the form data to update a cash disbursement journal entry,
        where the data are not changed.

        :param journal_entry_id: The journal entry ID.
        :return: The form data to update the cash disbursement journal entry,
            where the data are not changed.
        """
        form: dict[str, str] = get_unchanged_update_form(
            journal_entry_id, self.app, self.csrf_token)
        form = {x: form[x] for x in form if "-credit-" not in x}
        return form

    def __get_add_transfer_form(self) -> dict[str, str]:
        """Returns the form data to add a new journal entry.

        :return: The form data to add a new journal entry.
        """
        return get_add_form(self.csrf_token)
