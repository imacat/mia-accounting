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
from testlib_offset import TestData, JournalEntryData, VoucherData, \
    CurrencyData
from testlib_voucher import Accounts, match_voucher_detail

PREFIX: str = "/accounting/vouchers"
"""The URL prefix for the voucher management."""


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
            from accounting.models import BaseAccount, Voucher, \
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
            Voucher.query.delete()
            JournalEntry.query.delete()

        self.client, self.csrf_token = get_client(self.app, "editor")
        self.data: TestData = TestData(self.app, self.client, self.csrf_token)

    def test_add_receivable_offset(self) -> None:
        """Tests to add the receivable offset.

        :return: None.
        """
        from accounting.models import Account, Voucher
        create_uri: str = f"{PREFIX}/create/receipt?next=%2F_next"
        store_uri: str = f"{PREFIX}/store/receipt"
        form: dict[str, str]
        old_amount: Decimal
        response: httpx.Response

        voucher_data: VoucherData = VoucherData(
            self.data.e_r_or3d.voucher.days, [CurrencyData(
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
        form = voucher_data.new_form(self.csrf_token)
        form["currency-1-credit-1-original_entry_id"] = "9999"
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)

        # The same side
        form = voucher_data.new_form(self.csrf_token)
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
        response = self.client.post(
            store_uri, data=voucher_data.new_form(self.csrf_token))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)
        with self.app.app_context():
            account = Account.find_by_code(Accounts.RECEIVABLE)
            account.is_need_offset = True
            db.session.commit()

        # The original entry is also an offset
        form = voucher_data.new_form(self.csrf_token)
        form["currency-1-credit-1-original_entry_id"] = self.data.e_p_of1d.id
        form["currency-1-credit-1-account_code"] = self.data.e_p_of1d.account
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)

        # Not the same currency
        form = voucher_data.new_form(self.csrf_token)
        form["currency-1-code"] = "EUR"
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)

        # Not the same account
        form = voucher_data.new_form(self.csrf_token)
        form["currency-1-credit-1-account_code"] = Accounts.NOTES_RECEIVABLE
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)

        # Not exceeding net balance - partially offset
        form = voucher_data.new_form(self.csrf_token)
        form["currency-1-credit-1-amount"] \
            = str(voucher_data.currencies[0].credit[0].amount
                  + Decimal("0.01"))
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)

        # Not exceeding net balance - unmatched
        form = voucher_data.new_form(self.csrf_token)
        form["currency-1-credit-3-amount"] \
            = str(voucher_data.currencies[0].credit[2].amount
                  + Decimal("0.01"))
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)

        # Not before the original entries
        old_days = voucher_data.days
        voucher_data.days = old_days + 1
        form = voucher_data.new_form(self.csrf_token)
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)
        voucher_data.days = old_days

        # Success
        form = voucher_data.new_form(self.csrf_token)
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        voucher_id: int = match_voucher_detail(response.headers["Location"])
        with self.app.app_context():
            voucher = db.session.get(Voucher, voucher_id)
            for offset in voucher.currencies[0].credit:
                self.assertIsNotNone(offset.original_entry_id)

    def test_edit_receivable_offset(self) -> None:
        """Tests to edit the receivable offset.

        :return: None.
        """
        from accounting.models import Account
        voucher_data: VoucherData = self.data.v_r_of2
        edit_uri: str = f"{PREFIX}/{voucher_data.id}/edit?next=%2F_next"
        update_uri: str = f"{PREFIX}/{voucher_data.id}/update"
        form: dict[str, str]
        response: httpx.Response

        voucher_data.days = self.data.v_r_or2.days
        voucher_data.currencies[0].debit[0].amount = Decimal("600")
        voucher_data.currencies[0].credit[0].amount = Decimal("600")
        voucher_data.currencies[0].debit[2].amount = Decimal("600")
        voucher_data.currencies[0].credit[2].amount = Decimal("600")

        # Non-existing original entry ID
        form = voucher_data.update_form(self.csrf_token)
        form["currency-1-credit-1-original_entry_id"] = "9999"
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # The same side
        form = voucher_data.update_form(self.csrf_token)
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
        response = self.client.post(
            update_uri, data=voucher_data.update_form(self.csrf_token))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)
        with self.app.app_context():
            account = Account.find_by_code(Accounts.RECEIVABLE)
            account.is_need_offset = True
            db.session.commit()

        # The original entry is also an offset
        form = voucher_data.update_form(self.csrf_token)
        form["currency-1-credit-1-original_entry_id"] = self.data.e_p_of1d.id
        form["currency-1-credit-1-account_code"] = self.data.e_p_of1d.account
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Not the same currency
        form = voucher_data.update_form(self.csrf_token)
        form["currency-1-code"] = "EUR"
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Not the same account
        form = voucher_data.update_form(self.csrf_token)
        form["currency-1-credit-1-account_code"] = Accounts.NOTES_RECEIVABLE
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Not exceeding net balance - partially offset
        form = voucher_data.update_form(self.csrf_token)
        form["currency-1-debit-1-amount"] \
            = str(voucher_data.currencies[0].debit[0].amount + Decimal("0.01"))
        form["currency-1-credit-1-amount"] \
            = str(voucher_data.currencies[0].credit[0].amount
                  + Decimal("0.01"))
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Not exceeding net balance - unmatched
        form = voucher_data.update_form(self.csrf_token)
        form["currency-1-debit-3-amount"] \
            = str(voucher_data.currencies[0].debit[2].amount + Decimal("0.01"))
        form["currency-1-credit-3-amount"] \
            = str(voucher_data.currencies[0].credit[2].amount
                  + Decimal("0.01"))
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Not before the original entries
        old_days: int = voucher_data.days
        voucher_data.days = old_days + 1
        form = voucher_data.update_form(self.csrf_token)
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)
        voucher_data.days = old_days

        # Success
        form = voucher_data.update_form(self.csrf_token)
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"],
                         f"{PREFIX}/{voucher_data.id}?next=%2F_next")

    def test_edit_receivable_original_entry(self) -> None:
        """Tests to edit the receivable original entry.

        :return: None.
        """
        from accounting.models import Voucher
        voucher_data: VoucherData = self.data.v_r_or1
        edit_uri: str = f"{PREFIX}/{voucher_data.id}/edit?next=%2F_next"
        update_uri: str = f"{PREFIX}/{voucher_data.id}/update"
        form: dict[str, str]
        response: httpx.Response

        voucher_data.days = self.data.v_r_of1.days
        voucher_data.currencies[0].debit[0].amount = Decimal("800")
        voucher_data.currencies[0].credit[0].amount = Decimal("800")
        voucher_data.currencies[0].debit[1].amount = Decimal("3.4")
        voucher_data.currencies[0].credit[1].amount = Decimal("3.4")

        # Not the same currency
        form = voucher_data.update_form(self.csrf_token)
        form["currency-1-code"] = "EUR"
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Not the same account
        form = voucher_data.update_form(self.csrf_token)
        form["currency-1-debit-1-account_code"] = Accounts.NOTES_RECEIVABLE
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Not less than offset total - partially offset
        form = voucher_data.update_form(self.csrf_token)
        form["currency-1-debit-1-amount"] \
            = str(voucher_data.currencies[0].debit[0].amount - Decimal("0.01"))
        form["currency-1-credit-1-amount"] \
            = str(voucher_data.currencies[0].credit[0].amount
                  - Decimal("0.01"))
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Not less than offset total - fully offset
        form = voucher_data.update_form(self.csrf_token)
        form["currency-1-debit-2-amount"] \
            = str(voucher_data.currencies[0].debit[1].amount - Decimal("0.01"))
        form["currency-1-credit-2-amount"] \
            = str(voucher_data.currencies[0].credit[1].amount
                  - Decimal("0.01"))
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Not after the offset entries
        old_days: int = voucher_data.days
        voucher_data.days = old_days - 1
        form = voucher_data.update_form(self.csrf_token)
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)
        voucher_data.days = old_days

        # Not deleting matched original entries
        form = voucher_data.update_form(self.csrf_token)
        del form["currency-1-debit-1-eid"]
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Success
        form = voucher_data.update_form(self.csrf_token)
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"],
                         f"{PREFIX}/{voucher_data.id}?next=%2F_next")

        # The original entry is always before the offset entry, even when they
        # happen in the same day.
        with self.app.app_context():
            voucher_or: Voucher | None = db.session.get(
                Voucher, voucher_data.id)
            self.assertIsNotNone(voucher_or)
            voucher_of: Voucher | None = db.session.get(
                Voucher, self.data.v_r_of1.id)
            self.assertIsNotNone(voucher_of)
            self.assertEqual(voucher_or.date, voucher_of.date)
            self.assertLess(voucher_or.no, voucher_of.no)

    def test_add_payable_offset(self) -> None:
        """Tests to add the payable offset.

        :return: None.
        """
        from accounting.models import Account, Voucher
        create_uri: str = f"{PREFIX}/create/disbursement?next=%2F_next"
        store_uri: str = f"{PREFIX}/store/disbursement"
        form: dict[str, str]
        response: httpx.Response

        voucher_data: VoucherData = VoucherData(
            self.data.e_p_or3c.voucher.days, [CurrencyData(
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
        form = voucher_data.new_form(self.csrf_token)
        form["currency-1-debit-1-original_entry_id"] = "9999"
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)

        # The same side
        form = voucher_data.new_form(self.csrf_token)
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
        response = self.client.post(
            store_uri, data=voucher_data.new_form(self.csrf_token))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)
        with self.app.app_context():
            account = Account.find_by_code(Accounts.PAYABLE)
            account.is_need_offset = True
            db.session.commit()

        # The original entry is also an offset
        form = voucher_data.new_form(self.csrf_token)
        form["currency-1-debit-1-original_entry_id"] = self.data.e_r_of1c.id
        form["currency-1-debit-1-account_code"] = self.data.e_r_of1c.account
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)

        # Not the same currency
        form = voucher_data.new_form(self.csrf_token)
        form["currency-1-code"] = "EUR"
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)

        # Not the same account
        form = voucher_data.new_form(self.csrf_token)
        form["currency-1-debit-1-account_code"] = Accounts.NOTES_PAYABLE
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)

        # Not exceeding net balance - partially offset
        form = voucher_data.new_form(self.csrf_token)
        form["currency-1-debit-1-amount"] \
            = str(voucher_data.currencies[0].debit[0].amount + Decimal("0.01"))
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)

        # Not exceeding net balance - unmatched
        form = voucher_data.new_form(self.csrf_token)
        form["currency-1-debit-3-amount"] \
            = str(voucher_data.currencies[0].debit[2].amount + Decimal("0.01"))
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)

        # Not before the original entries
        old_days: int = voucher_data.days
        voucher_data.days = old_days + 1
        form = voucher_data.new_form(self.csrf_token)
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)
        voucher_data.days = old_days

        # Success
        form = voucher_data.new_form(self.csrf_token)
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        voucher_id: int = match_voucher_detail(response.headers["Location"])
        with self.app.app_context():
            voucher = db.session.get(Voucher, voucher_id)
            for offset in voucher.currencies[0].debit:
                self.assertIsNotNone(offset.original_entry_id)

    def test_edit_payable_offset(self) -> None:
        """Tests to edit the payable offset.

        :return: None.
        """
        from accounting.models import Account, Voucher
        voucher_data: VoucherData = self.data.v_p_of2
        edit_uri: str = f"{PREFIX}/{voucher_data.id}/edit?next=%2F_next"
        update_uri: str = f"{PREFIX}/{voucher_data.id}/update"
        form: dict[str, str]
        response: httpx.Response

        voucher_data.days = self.data.v_p_or2.days
        voucher_data.currencies[0].debit[0].amount = Decimal("1100")
        voucher_data.currencies[0].credit[0].amount = Decimal("1100")
        voucher_data.currencies[0].debit[2].amount = Decimal("900")
        voucher_data.currencies[0].credit[2].amount = Decimal("900")

        # Non-existing original entry ID
        form = voucher_data.update_form(self.csrf_token)
        form["currency-1-debit-1-original_entry_id"] = "9999"
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # The same side
        form = voucher_data.update_form(self.csrf_token)
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
        response = self.client.post(
            update_uri, data=voucher_data.update_form(self.csrf_token))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)
        with self.app.app_context():
            account = Account.find_by_code(Accounts.PAYABLE)
            account.is_need_offset = True
            db.session.commit()

        # The original entry is also an offset
        form = voucher_data.update_form(self.csrf_token)
        form["currency-1-debit-1-original_entry_id"] = self.data.e_r_of1c.id
        form["currency-1-debit-1-account_code"] = self.data.e_r_of1c.account
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Not the same currency
        form = voucher_data.update_form(self.csrf_token)
        form["currency-1-code"] = "EUR"
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Not the same account
        form = voucher_data.update_form(self.csrf_token)
        form["currency-1-debit-1-account_code"] = Accounts.NOTES_PAYABLE
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Not exceeding net balance - partially offset
        form = voucher_data.update_form(self.csrf_token)
        form["currency-1-debit-1-amount"] \
            = str(voucher_data.currencies[0].debit[0].amount + Decimal("0.01"))
        form["currency-1-credit-1-amount"] \
            = str(voucher_data.currencies[0].credit[0].amount
                  + Decimal("0.01"))
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Not exceeding net balance - unmatched
        form = voucher_data.update_form(self.csrf_token)
        form["currency-1-debit-3-amount"] \
            = str(voucher_data.currencies[0].debit[2].amount + Decimal("0.01"))
        form["currency-1-credit-3-amount"] \
            = str(voucher_data.currencies[0].credit[2].amount
                  + Decimal("0.01"))
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Not before the original entries
        old_days: int = voucher_data.days
        voucher_data.days = old_days + 1
        form = voucher_data.update_form(self.csrf_token)
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)
        voucher_data.days = old_days

        # Success
        form = voucher_data.update_form(self.csrf_token)
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        voucher_id: int = match_voucher_detail(response.headers["Location"])
        with self.app.app_context():
            voucher = db.session.get(Voucher, voucher_id)
            for offset in voucher.currencies[0].debit:
                self.assertIsNotNone(offset.original_entry_id)

    def test_edit_payable_original_entry(self) -> None:
        """Tests to edit the payable original entry.

        :return: None.
        """
        from accounting.models import Voucher
        voucher_data: VoucherData = self.data.v_p_or1
        edit_uri: str = f"{PREFIX}/{voucher_data.id}/edit?next=%2F_next"
        update_uri: str = f"{PREFIX}/{voucher_data.id}/update"
        form: dict[str, str]
        response: httpx.Response

        voucher_data.days = self.data.v_p_of1.days
        voucher_data.currencies[0].debit[0].amount = Decimal("1200")
        voucher_data.currencies[0].credit[0].amount = Decimal("1200")
        voucher_data.currencies[0].debit[1].amount = Decimal("0.9")
        voucher_data.currencies[0].credit[1].amount = Decimal("0.9")

        # Not the same currency
        form = voucher_data.update_form(self.csrf_token)
        form["currency-1-code"] = "EUR"
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Not the same account
        form = voucher_data.update_form(self.csrf_token)
        form["currency-1-credit-1-account_code"] = Accounts.NOTES_PAYABLE
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Not less than offset total - partially offset
        form = voucher_data.update_form(self.csrf_token)
        form["currency-1-debit-1-amount"] \
            = str(voucher_data.currencies[0].debit[0].amount - Decimal("0.01"))
        form["currency-1-credit-1-amount"] \
            = str(voucher_data.currencies[0].credit[0].amount
                  - Decimal("0.01"))
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Not less than offset total - fully offset
        form = voucher_data.update_form(self.csrf_token)
        form["currency-1-debit-2-amount"] \
            = str(voucher_data.currencies[0].debit[1].amount - Decimal("0.01"))
        form["currency-1-credit-2-amount"] \
            = str(voucher_data.currencies[0].credit[1].amount
                  - Decimal("0.01"))
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Not after the offset entries
        old_days: int = voucher_data.days
        voucher_data.days = old_days - 1
        form = voucher_data.update_form(self.csrf_token)
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)
        voucher_data.days = old_days

        # Not deleting matched original entries
        form = voucher_data.update_form(self.csrf_token)
        del form["currency-1-credit-1-eid"]
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Success
        form = voucher_data.update_form(self.csrf_token)
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"],
                         f"{PREFIX}/{voucher_data.id}?next=%2F_next")

        # The original entry is always before the offset entry, even when they
        # happen in the same day
        with self.app.app_context():
            voucher_or: Voucher | None = db.session.get(
                Voucher, voucher_data.id)
            self.assertIsNotNone(voucher_or)
            voucher_of: Voucher | None = db.session.get(
                Voucher, self.data.v_p_of1.id)
            self.assertIsNotNone(voucher_of)
            self.assertEqual(voucher_or.date, voucher_of.date)
            self.assertLess(voucher_or.no, voucher_of.no)
