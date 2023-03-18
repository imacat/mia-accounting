# The Mia! Accounting Flask Project.
# Author: imacat@mail.imacat.idv.tw (imacat), 2023/3/11

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
"""The test for the offset.

"""
import unittest
from decimal import Decimal

import httpx
from click.testing import Result
from flask import Flask
from flask.testing import FlaskCliRunner

from test_site import db
from testlib import create_test_app, get_client
from testlib_offset import TestData, JournalEntryData, TransactionData, \
    CurrencyData
from testlib_txn import Accounts, match_txn_detail

PREFIX: str = "/accounting/transactions"
"""The URL prefix for the transaction management."""


class OffsetTestCase(unittest.TestCase):
    """The offset test case."""

    def setUp(self) -> None:
        """Sets up the test.
        This is run once per test.

        :return: None.
        """
        self.app: Flask = create_test_app()

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
        self.data: TestData = TestData(self.app, self.client, self.csrf_token)

    def test_add_receivable_offset(self) -> None:
        """Tests to add the receivable offset.

        :return: None.
        """
        from accounting.models import Account, Transaction
        create_uri: str = f"{PREFIX}/create/income?next=%2F_next"
        store_uri: str = f"{PREFIX}/store/income"
        form: dict[str, str]
        old_amount: Decimal
        response: httpx.Response

        txn_data: TransactionData = TransactionData(
            self.data.e_r_or3d.txn.days, [CurrencyData(
                "USD",
                [],
                [JournalEntryData(Accounts.RECEIVABLE,
                                  self.data.e_r_or1d.summary, "300",
                                  original_entry=self.data.e_r_or1d),
                 JournalEntryData(Accounts.RECEIVABLE,
                                  self.data.e_r_or1d.summary, "100",
                                  original_entry=self.data.e_r_or1d),
                 JournalEntryData(Accounts.RECEIVABLE,
                                  self.data.e_r_or3d.summary, "100",
                                  original_entry=self.data.e_r_or3d)])])

        # Non-existing original entry ID
        form = txn_data.new_form(self.csrf_token)
        form["currency-1-credit-1-original_entry_id"] = "9999"
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)

        # The same side
        form = txn_data.new_form(self.csrf_token)
        form["currency-1-credit-1-original_entry_id"] = self.data.e_p_or1c.id
        form["currency-1-credit-1-account_code"] = self.data.e_p_or1c.account
        form["currency-1-credit-1-amount"] = "100"
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)

        # The original entry does not need offset
        with self.app.app_context():
            account = Account.find_by_code(Accounts.RECEIVABLE)
            account.is_need_offset = False
            db.session.commit()
        response = self.client.post(store_uri,
                                    data=txn_data.new_form(self.csrf_token))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)
        with self.app.app_context():
            account = Account.find_by_code(Accounts.RECEIVABLE)
            account.is_need_offset = True
            db.session.commit()

        # The original entry is also an offset
        form = txn_data.new_form(self.csrf_token)
        form["currency-1-credit-1-original_entry_id"] = self.data.e_p_of1d.id
        form["currency-1-credit-1-account_code"] = self.data.e_p_of1d.account
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)

        # Not the same currency
        form = txn_data.new_form(self.csrf_token)
        form["currency-1-code"] = "EUR"
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)

        # Not the same account
        form = txn_data.new_form(self.csrf_token)
        form["currency-1-credit-1-account_code"] = Accounts.NOTES_RECEIVABLE
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)

        # Not exceeding net balance - partially offset
        form = txn_data.new_form(self.csrf_token)
        form["currency-1-credit-1-amount"] \
            = str(txn_data.currencies[0].credit[0].amount + Decimal("0.01"))
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)

        # Not exceeding net balance - unmatched
        form = txn_data.new_form(self.csrf_token)
        form["currency-1-credit-3-amount"] \
            = str(txn_data.currencies[0].credit[2].amount + Decimal("0.01"))
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)

        # Not before the original entries
        old_days = txn_data.days
        txn_data.days = old_days + 1
        form = txn_data.new_form(self.csrf_token)
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)
        txn_data.days = old_days

        # Success
        form = txn_data.new_form(self.csrf_token)
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        txn_id: int = match_txn_detail(response.headers["Location"])
        with self.app.app_context():
            txn = db.session.get(Transaction, txn_id)
            for offset in txn.currencies[0].credit:
                self.assertIsNotNone(offset.original_entry_id)

    def test_edit_receivable_offset(self) -> None:
        """Tests to edit the receivable offset.

        :return: None.
        """
        from accounting.models import Account
        txn_data: TransactionData = self.data.t_r_of2
        edit_uri: str = f"{PREFIX}/{txn_data.id}/edit?next=%2F_next"
        update_uri: str = f"{PREFIX}/{txn_data.id}/update"
        form: dict[str, str]
        response: httpx.Response

        txn_data.days = self.data.t_r_or2.days
        txn_data.currencies[0].debit[0].amount = Decimal("600")
        txn_data.currencies[0].credit[0].amount = Decimal("600")
        txn_data.currencies[0].debit[2].amount = Decimal("600")
        txn_data.currencies[0].credit[2].amount = Decimal("600")

        # Non-existing original entry ID
        form = txn_data.update_form(self.csrf_token)
        form["currency-1-credit-1-original_entry_id"] = "9999"
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # The same side
        form = txn_data.update_form(self.csrf_token)
        form["currency-1-credit-1-original_entry_id"] = self.data.e_p_or1c.id
        form["currency-1-credit-1-account_code"] = self.data.e_p_or1c.account
        form["currency-1-debit-1-amount"] = "100"
        form["currency-1-credit-1-amount"] = "100"
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # The original entry does not need offset
        with self.app.app_context():
            account = Account.find_by_code(Accounts.RECEIVABLE)
            account.is_need_offset = False
            db.session.commit()
        response = self.client.post(update_uri,
                                    data=txn_data.update_form(self.csrf_token))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)
        with self.app.app_context():
            account = Account.find_by_code(Accounts.RECEIVABLE)
            account.is_need_offset = True
            db.session.commit()

        # The original entry is also an offset
        form = txn_data.update_form(self.csrf_token)
        form["currency-1-credit-1-original_entry_id"] = self.data.e_p_of1d.id
        form["currency-1-credit-1-account_code"] = self.data.e_p_of1d.account
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Not the same currency
        form = txn_data.update_form(self.csrf_token)
        form["currency-1-code"] = "EUR"
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Not the same account
        form = txn_data.update_form(self.csrf_token)
        form["currency-1-credit-1-account_code"] = Accounts.NOTES_RECEIVABLE
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Not exceeding net balance - partially offset
        form = txn_data.update_form(self.csrf_token)
        form["currency-1-debit-1-amount"] \
            = str(txn_data.currencies[0].debit[0].amount + Decimal("0.01"))
        form["currency-1-credit-1-amount"] \
            = str(txn_data.currencies[0].credit[0].amount + Decimal("0.01"))
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Not exceeding net balance - unmatched
        form = txn_data.update_form(self.csrf_token)
        form["currency-1-debit-3-amount"] \
            = str(txn_data.currencies[0].debit[2].amount + Decimal("0.01"))
        form["currency-1-credit-3-amount"] \
            = str(txn_data.currencies[0].credit[2].amount + Decimal("0.01"))
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Not before the original entries
        old_days: int = txn_data.days
        txn_data.days = old_days + 1
        form = txn_data.update_form(self.csrf_token)
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)
        txn_data.days = old_days

        # Success
        form = txn_data.update_form(self.csrf_token)
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"],
                         f"{PREFIX}/{txn_data.id}?next=%2F_next")

    def test_edit_receivable_original_entry(self) -> None:
        """Tests to edit the receivable original entry.

        :return: None.
        """
        from accounting.models import Transaction
        txn_data: TransactionData = self.data.t_r_or1
        edit_uri: str = f"{PREFIX}/{txn_data.id}/edit?next=%2F_next"
        update_uri: str = f"{PREFIX}/{txn_data.id}/update"
        form: dict[str, str]
        response: httpx.Response

        txn_data.days = self.data.t_r_of1.days
        txn_data.currencies[0].debit[0].amount = Decimal("800")
        txn_data.currencies[0].credit[0].amount = Decimal("800")
        txn_data.currencies[0].debit[1].amount = Decimal("3.4")
        txn_data.currencies[0].credit[1].amount = Decimal("3.4")

        # Not the same currency
        form = txn_data.update_form(self.csrf_token)
        form["currency-1-code"] = "EUR"
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Not the same account
        form = txn_data.update_form(self.csrf_token)
        form["currency-1-debit-1-account_code"] = Accounts.NOTES_RECEIVABLE
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Not less than offset total - partially offset
        form = txn_data.update_form(self.csrf_token)
        form["currency-1-debit-1-amount"] \
            = str(txn_data.currencies[0].debit[0].amount - Decimal("0.01"))
        form["currency-1-credit-1-amount"] \
            = str(txn_data.currencies[0].credit[0].amount - Decimal("0.01"))
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Not less than offset total - fully offset
        form = txn_data.update_form(self.csrf_token)
        form["currency-1-debit-2-amount"] \
            = str(txn_data.currencies[0].debit[1].amount - Decimal("0.01"))
        form["currency-1-credit-2-amount"] \
            = str(txn_data.currencies[0].credit[1].amount - Decimal("0.01"))
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Not after the offset entries
        old_days: int = txn_data.days
        txn_data.days = old_days - 1
        form = txn_data.update_form(self.csrf_token)
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)
        txn_data.days = old_days

        # Not deleting matched original entries
        form = txn_data.update_form(self.csrf_token)
        del form["currency-1-debit-1-eid"]
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Success
        form = txn_data.update_form(self.csrf_token)
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"],
                         f"{PREFIX}/{txn_data.id}?next=%2F_next")

        # The original entry is always before the offset entry, even when they
        # happen in the same day.
        with self.app.app_context():
            txn_or: Transaction | None = db.session.get(
                Transaction, txn_data.id)
            self.assertIsNotNone(txn_or)
            txn_of: Transaction | None = db.session.get(
                Transaction, self.data.t_r_of1.id)
            self.assertIsNotNone(txn_of)
            self.assertEqual(txn_or.date, txn_of.date)
            self.assertLess(txn_or.no, txn_of.no)

    def test_add_payable_offset(self) -> None:
        """Tests to add the payable offset.

        :return: None.
        """
        from accounting.models import Account, Transaction
        create_uri: str = f"{PREFIX}/create/expense?next=%2F_next"
        store_uri: str = f"{PREFIX}/store/expense"
        form: dict[str, str]
        response: httpx.Response

        txn_data: TransactionData = TransactionData(
            self.data.e_p_or3c.txn.days, [CurrencyData(
                "USD",
                [JournalEntryData(Accounts.PAYABLE,
                                  self.data.e_p_or1c.summary, "500",
                                  original_entry=self.data.e_p_or1c),
                 JournalEntryData(Accounts.PAYABLE,
                                  self.data.e_p_or1c.summary, "300",
                                  original_entry=self.data.e_p_or1c),
                 JournalEntryData(Accounts.PAYABLE,
                                  self.data.e_p_or3c.summary, "120",
                                  original_entry=self.data.e_p_or3c)],
                [])])

        # Non-existing original entry ID
        form = txn_data.new_form(self.csrf_token)
        form["currency-1-debit-1-original_entry_id"] = "9999"
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)

        # The same side
        form = txn_data.new_form(self.csrf_token)
        form["currency-1-debit-1-original_entry_id"] = self.data.e_r_or1d.id
        form["currency-1-debit-1-account_code"] = self.data.e_r_or1d.account
        form["currency-1-debit-1-amount"] = "100"
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)

        # The original entry does not need offset
        with self.app.app_context():
            account = Account.find_by_code(Accounts.PAYABLE)
            account.is_need_offset = False
            db.session.commit()
        response = self.client.post(store_uri,
                                    data=txn_data.new_form(self.csrf_token))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)
        with self.app.app_context():
            account = Account.find_by_code(Accounts.PAYABLE)
            account.is_need_offset = True
            db.session.commit()

        # The original entry is also an offset
        form = txn_data.new_form(self.csrf_token)
        form["currency-1-debit-1-original_entry_id"] = self.data.e_r_of1c.id
        form["currency-1-debit-1-account_code"] = self.data.e_r_of1c.account
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)

        # Not the same currency
        form = txn_data.new_form(self.csrf_token)
        form["currency-1-code"] = "EUR"
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)

        # Not the same account
        form = txn_data.new_form(self.csrf_token)
        form["currency-1-debit-1-account_code"] = Accounts.NOTES_PAYABLE
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)

        # Not exceeding net balance - partially offset
        form = txn_data.new_form(self.csrf_token)
        form["currency-1-debit-1-amount"] \
            = str(txn_data.currencies[0].debit[0].amount + Decimal("0.01"))
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)

        # Not exceeding net balance - unmatched
        form = txn_data.new_form(self.csrf_token)
        form["currency-1-debit-3-amount"] \
            = str(txn_data.currencies[0].debit[2].amount + Decimal("0.01"))
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)

        # Not before the original entries
        old_days: int = txn_data.days
        txn_data.days = old_days + 1
        form = txn_data.new_form(self.csrf_token)
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)
        txn_data.days = old_days

        # Success
        form = txn_data.new_form(self.csrf_token)
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        txn_id: int = match_txn_detail(response.headers["Location"])
        with self.app.app_context():
            txn = db.session.get(Transaction, txn_id)
            for offset in txn.currencies[0].debit:
                self.assertIsNotNone(offset.original_entry_id)

    def test_edit_payable_offset(self) -> None:
        """Tests to edit the payable offset.

        :return: None.
        """
        from accounting.models import Account, Transaction
        txn_data: TransactionData = self.data.t_p_of2
        edit_uri: str = f"{PREFIX}/{txn_data.id}/edit?next=%2F_next"
        update_uri: str = f"{PREFIX}/{txn_data.id}/update"
        form: dict[str, str]
        response: httpx.Response

        txn_data.days = self.data.t_p_or2.days
        txn_data.currencies[0].debit[0].amount = Decimal("1100")
        txn_data.currencies[0].credit[0].amount = Decimal("1100")
        txn_data.currencies[0].debit[2].amount = Decimal("900")
        txn_data.currencies[0].credit[2].amount = Decimal("900")

        # Non-existing original entry ID
        form = txn_data.update_form(self.csrf_token)
        form["currency-1-debit-1-original_entry_id"] = "9999"
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # The same side
        form = txn_data.update_form(self.csrf_token)
        form["currency-1-debit-1-original_entry_id"] = self.data.e_r_or1d.id
        form["currency-1-debit-1-account_code"] = self.data.e_r_or1d.account
        form["currency-1-debit-1-amount"] = "100"
        form["currency-1-credit-1-amount"] = "100"
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # The original entry does not need offset
        with self.app.app_context():
            account = Account.find_by_code(Accounts.PAYABLE)
            account.is_need_offset = False
            db.session.commit()
        response = self.client.post(update_uri,
                                    data=txn_data.update_form(self.csrf_token))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)
        with self.app.app_context():
            account = Account.find_by_code(Accounts.PAYABLE)
            account.is_need_offset = True
            db.session.commit()

        # The original entry is also an offset
        form = txn_data.update_form(self.csrf_token)
        form["currency-1-debit-1-original_entry_id"] = self.data.e_r_of1c.id
        form["currency-1-debit-1-account_code"] = self.data.e_r_of1c.account
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Not the same currency
        form = txn_data.update_form(self.csrf_token)
        form["currency-1-code"] = "EUR"
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Not the same account
        form = txn_data.update_form(self.csrf_token)
        form["currency-1-debit-1-account_code"] = Accounts.NOTES_PAYABLE
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Not exceeding net balance - partially offset
        form = txn_data.update_form(self.csrf_token)
        form["currency-1-debit-1-amount"] \
            = str(txn_data.currencies[0].debit[0].amount + Decimal("0.01"))
        form["currency-1-credit-1-amount"] \
            = str(txn_data.currencies[0].credit[0].amount + Decimal("0.01"))
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Not exceeding net balance - unmatched
        form = txn_data.update_form(self.csrf_token)
        form["currency-1-debit-3-amount"] \
            = str(txn_data.currencies[0].debit[2].amount + Decimal("0.01"))
        form["currency-1-credit-3-amount"] \
            = str(txn_data.currencies[0].credit[2].amount + Decimal("0.01"))
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Not before the original entries
        old_days: int = txn_data.days
        txn_data.days = old_days + 1
        form = txn_data.update_form(self.csrf_token)
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)
        txn_data.days = old_days

        # Success
        form = txn_data.update_form(self.csrf_token)
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        txn_id: int = match_txn_detail(response.headers["Location"])
        with self.app.app_context():
            txn = db.session.get(Transaction, txn_id)
            for offset in txn.currencies[0].debit:
                self.assertIsNotNone(offset.original_entry_id)

    def test_edit_payable_original_entry(self) -> None:
        """Tests to edit the payable original entry.

        :return: None.
        """
        from accounting.models import Transaction
        txn_data: TransactionData = self.data.t_p_or1
        edit_uri: str = f"{PREFIX}/{txn_data.id}/edit?next=%2F_next"
        update_uri: str = f"{PREFIX}/{txn_data.id}/update"
        form: dict[str, str]
        response: httpx.Response

        txn_data.days = self.data.t_p_of1.days
        txn_data.currencies[0].debit[0].amount = Decimal("1200")
        txn_data.currencies[0].credit[0].amount = Decimal("1200")
        txn_data.currencies[0].debit[1].amount = Decimal("0.9")
        txn_data.currencies[0].credit[1].amount = Decimal("0.9")

        # Not the same currency
        form = txn_data.update_form(self.csrf_token)
        form["currency-1-code"] = "EUR"
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Not the same account
        form = txn_data.update_form(self.csrf_token)
        form["currency-1-credit-1-account_code"] = Accounts.NOTES_PAYABLE
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Not less than offset total - partially offset
        form = txn_data.update_form(self.csrf_token)
        form["currency-1-debit-1-amount"] \
            = str(txn_data.currencies[0].debit[0].amount - Decimal("0.01"))
        form["currency-1-credit-1-amount"] \
            = str(txn_data.currencies[0].credit[0].amount - Decimal("0.01"))
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Not less than offset total - fully offset
        form = txn_data.update_form(self.csrf_token)
        form["currency-1-debit-2-amount"] \
            = str(txn_data.currencies[0].debit[1].amount - Decimal("0.01"))
        form["currency-1-credit-2-amount"] \
            = str(txn_data.currencies[0].credit[1].amount - Decimal("0.01"))
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Not after the offset entries
        old_days: int = txn_data.days
        txn_data.days = old_days - 1
        form = txn_data.update_form(self.csrf_token)
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)
        txn_data.days = old_days

        # Not deleting matched original entries
        form = txn_data.update_form(self.csrf_token)
        del form["currency-1-credit-1-eid"]
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Success
        form = txn_data.update_form(self.csrf_token)
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"],
                         f"{PREFIX}/{txn_data.id}?next=%2F_next")

        # The original entry is always before the offset entry, even when they
        # happen in the same day
        with self.app.app_context():
            txn_or: Transaction | None = db.session.get(
                Transaction, txn_data.id)
            self.assertIsNotNone(txn_or)
            txn_of: Transaction | None = db.session.get(
                Transaction, self.data.t_p_of1.id)
            self.assertIsNotNone(txn_of)
            self.assertEqual(txn_or.date, txn_of.date)
            self.assertLess(txn_or.no, txn_of.no)
