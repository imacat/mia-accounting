# The Mia! Accounting Project.
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
from __future__ import annotations

import unittest
from decimal import Decimal

import httpx
from flask import Flask

from test_site import db
from testlib import Accounts, create_test_app, get_client, \
    match_journal_entry_detail, JournalEntryLineItemData, \
    JournalEntryCurrencyData, JournalEntryData, BaseTestData

PREFIX: str = "/accounting/journal-entries"
"""The URL prefix for the journal entry management."""


class OffsetTestCase(unittest.TestCase):
    """The offset test case."""

    def setUp(self) -> None:
        """Sets up the test.
        This is run once per test.

        :return: None.
        """
        self.app: Flask = create_test_app()

        with self.app.app_context():
            from accounting.models import JournalEntry, JournalEntryLineItem
            JournalEntry.query.delete()
            JournalEntryLineItem.query.delete()

        self.client, self.csrf_token = get_client(self.app, "editor")
        self.data: OffsetTestData = OffsetTestData(
            self.app, self.client, self.csrf_token)

    def test_add_receivable_offset(self) -> None:
        """Tests to add the receivable offset.

        :return: None.
        """
        from accounting.models import Account, JournalEntry
        create_uri: str = f"{PREFIX}/create/receipt?next=%2F_next"
        store_uri: str = f"{PREFIX}/store/receipt"
        form: dict[str, str]
        old_amount: Decimal
        response: httpx.Response

        journal_entry_data: JournalEntryData = JournalEntryData(
            self.data.l_r_or3d.journal_entry.days, [JournalEntryCurrencyData(
                "USD",
                [],
                [JournalEntryLineItemData(
                    Accounts.RECEIVABLE,
                    self.data.l_r_or1d.description, "300",
                    original_line_item=self.data.l_r_or1d),
                 JournalEntryLineItemData(
                     Accounts.RECEIVABLE,
                     self.data.l_r_or1d.description, "100",
                     original_line_item=self.data.l_r_or1d),
                 JournalEntryLineItemData(
                     Accounts.RECEIVABLE,
                     self.data.l_r_or3d.description, "100",
                     original_line_item=self.data.l_r_or3d)])])

        # Non-existing original line item ID
        form = journal_entry_data.new_form(self.csrf_token)
        form["currency-1-credit-1-original_line_item_id"] = "9999"
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)

        # The same debit or credit
        form = journal_entry_data.new_form(self.csrf_token)
        form["currency-1-credit-1-original_line_item_id"] \
            = str(self.data.l_p_or1c.id)
        form["currency-1-credit-1-account_code"] = self.data.l_p_or1c.account
        form["currency-1-credit-1-amount"] = "100"
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)

        # The original line item does not need offset
        with self.app.app_context():
            account = Account.find_by_code(Accounts.RECEIVABLE)
            account.is_need_offset = False
            db.session.commit()
        response = self.client.post(
            store_uri, data=journal_entry_data.new_form(self.csrf_token))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)
        with self.app.app_context():
            account = Account.find_by_code(Accounts.RECEIVABLE)
            account.is_need_offset = True
            db.session.commit()

        # The original line item is also an offset
        form = journal_entry_data.new_form(self.csrf_token)
        form["currency-1-credit-1-original_line_item_id"] \
            = str(self.data.l_p_of1d.id)
        form["currency-1-credit-1-account_code"] = self.data.l_p_of1d.account
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)

        # Not the same currency
        form = journal_entry_data.new_form(self.csrf_token)
        form["currency-1-code"] = "EUR"
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)

        # Not the same account
        form = journal_entry_data.new_form(self.csrf_token)
        form["currency-1-credit-1-account_code"] = Accounts.NOTES_RECEIVABLE
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)

        # Not exceeding net balance - partially offset
        form = journal_entry_data.new_form(self.csrf_token)
        form["currency-1-credit-1-amount"] \
            = str(journal_entry_data.currencies[0].credit[0].amount
                  + Decimal("0.01"))
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)

        # Not exceeding net balance - unmatched
        form = journal_entry_data.new_form(self.csrf_token)
        form["currency-1-credit-3-amount"] \
            = str(journal_entry_data.currencies[0].credit[2].amount
                  + Decimal("0.01"))
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)

        # Not before the original line items
        old_days = journal_entry_data.days
        journal_entry_data.days = old_days + 1
        form = journal_entry_data.new_form(self.csrf_token)
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)
        journal_entry_data.days = old_days

        # Success
        form = journal_entry_data.new_form(self.csrf_token)
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        journal_entry_id: int \
            = match_journal_entry_detail(response.headers["Location"])
        with self.app.app_context():
            journal_entry = db.session.get(JournalEntry, journal_entry_id)
            for offset in journal_entry.currencies[0].credit:
                self.assertIsNotNone(offset.original_line_item_id)

    def test_edit_receivable_offset(self) -> None:
        """Tests to edit the receivable offset.

        :return: None.
        """
        from accounting.models import Account
        journal_entry_data: JournalEntryData = self.data.j_r_of2
        edit_uri: str = f"{PREFIX}/{journal_entry_data.id}/edit?next=%2F_next"
        update_uri: str = f"{PREFIX}/{journal_entry_data.id}/update"
        form: dict[str, str]
        response: httpx.Response

        journal_entry_data.days = self.data.j_r_or2.days
        journal_entry_data.currencies[0].debit[0].amount = Decimal("600")
        journal_entry_data.currencies[0].credit[0].amount = Decimal("600")
        journal_entry_data.currencies[0].debit[2].amount = Decimal("600")
        journal_entry_data.currencies[0].credit[2].amount = Decimal("600")

        # Non-existing original line item ID
        form = journal_entry_data.update_form(self.csrf_token)
        form["currency-1-credit-1-original_line_item_id"] = "9999"
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # The same debit or credit
        form = journal_entry_data.update_form(self.csrf_token)
        form["currency-1-credit-1-original_line_item_id"] \
            = str(self.data.l_p_or1c.id)
        form["currency-1-credit-1-account_code"] = self.data.l_p_or1c.account
        form["currency-1-debit-1-amount"] = "100"
        form["currency-1-credit-1-amount"] = "100"
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # The original line item does not need offset
        with self.app.app_context():
            account = Account.find_by_code(Accounts.RECEIVABLE)
            account.is_need_offset = False
            db.session.commit()
        response = self.client.post(
            update_uri, data=journal_entry_data.update_form(self.csrf_token))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)
        with self.app.app_context():
            account = Account.find_by_code(Accounts.RECEIVABLE)
            account.is_need_offset = True
            db.session.commit()

        # The original line item is also an offset
        form = journal_entry_data.update_form(self.csrf_token)
        form["currency-1-credit-1-original_line_item_id"] \
            = str(self.data.l_p_of1d.id)
        form["currency-1-credit-1-account_code"] = self.data.l_p_of1d.account
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Not the same currency
        form = journal_entry_data.update_form(self.csrf_token)
        form["currency-1-code"] = "EUR"
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Not the same account
        form = journal_entry_data.update_form(self.csrf_token)
        form["currency-1-credit-1-account_code"] = Accounts.NOTES_RECEIVABLE
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Not exceeding net balance - partially offset
        form = journal_entry_data.update_form(self.csrf_token)
        form["currency-1-debit-1-amount"] \
            = str(journal_entry_data.currencies[0].debit[0].amount
                  + Decimal("0.01"))
        form["currency-1-credit-1-amount"] \
            = str(journal_entry_data.currencies[0].credit[0].amount
                  + Decimal("0.01"))
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Not exceeding net balance - unmatched
        form = journal_entry_data.update_form(self.csrf_token)
        form["currency-1-debit-3-amount"] \
            = str(journal_entry_data.currencies[0].debit[2].amount
                  + Decimal("0.01"))
        form["currency-1-credit-3-amount"] \
            = str(journal_entry_data.currencies[0].credit[2].amount
                  + Decimal("0.01"))
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Not before the original line items
        old_days: int = journal_entry_data.days
        journal_entry_data.days = old_days + 1
        form = journal_entry_data.update_form(self.csrf_token)
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)
        journal_entry_data.days = old_days

        # Success
        form = journal_entry_data.update_form(self.csrf_token)
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"],
                         f"{PREFIX}/{journal_entry_data.id}?next=%2F_next")

    def test_edit_receivable_original_line_item(self) -> None:
        """Tests to edit the receivable original line item.

        :return: None.
        """
        from accounting.models import JournalEntry
        journal_entry_data: JournalEntryData = self.data.j_r_or1
        edit_uri: str = f"{PREFIX}/{journal_entry_data.id}/edit?next=%2F_next"
        update_uri: str = f"{PREFIX}/{journal_entry_data.id}/update"
        form: dict[str, str]
        response: httpx.Response

        journal_entry_data.days = self.data.j_r_of1.days
        journal_entry_data.currencies[0].debit[0].amount = Decimal("800")
        journal_entry_data.currencies[0].credit[0].amount = Decimal("800")
        journal_entry_data.currencies[0].debit[1].amount = Decimal("3.4")
        journal_entry_data.currencies[0].credit[1].amount = Decimal("3.4")

        # Not the same currency
        form = journal_entry_data.update_form(self.csrf_token)
        form["currency-1-code"] = "EUR"
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Not the same account
        form = journal_entry_data.update_form(self.csrf_token)
        form["currency-1-debit-1-account_code"] = Accounts.NOTES_RECEIVABLE
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Not less than offset total - partially offset
        form = journal_entry_data.update_form(self.csrf_token)
        form["currency-1-debit-1-amount"] \
            = str(journal_entry_data.currencies[0].debit[0].amount
                  - Decimal("0.01"))
        form["currency-1-credit-1-amount"] \
            = str(journal_entry_data.currencies[0].credit[0].amount
                  - Decimal("0.01"))
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Not less than offset total - fully offset
        form = journal_entry_data.update_form(self.csrf_token)
        form["currency-1-debit-2-amount"] \
            = str(journal_entry_data.currencies[0].debit[1].amount
                  - Decimal("0.01"))
        form["currency-1-credit-2-amount"] \
            = str(journal_entry_data.currencies[0].credit[1].amount
                  - Decimal("0.01"))
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Not after the offset items
        old_days: int = journal_entry_data.days
        journal_entry_data.days = old_days - 1
        form = journal_entry_data.update_form(self.csrf_token)
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)
        journal_entry_data.days = old_days

        # Not deleting matched original line items
        form = journal_entry_data.update_form(self.csrf_token)
        del form["currency-1-debit-1-id"]
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Success
        form = journal_entry_data.update_form(self.csrf_token)
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"],
                         f"{PREFIX}/{journal_entry_data.id}?next=%2F_next")

        # The original line item is always before the offset item, even when
        # they happen in the same day.
        with self.app.app_context():
            journal_entry_or: JournalEntry | None = db.session.get(
                JournalEntry, journal_entry_data.id)
            self.assertIsNotNone(journal_entry_or)
            journal_entry_of: JournalEntry | None = db.session.get(
                JournalEntry, self.data.j_r_of1.id)
            self.assertIsNotNone(journal_entry_of)
            self.assertEqual(journal_entry_or.date, journal_entry_of.date)
            self.assertLess(journal_entry_or.no, journal_entry_of.no)

    def test_add_payable_offset(self) -> None:
        """Tests to add the payable offset.

        :return: None.
        """
        from accounting.models import Account, JournalEntry
        create_uri: str = f"{PREFIX}/create/disbursement?next=%2F_next"
        store_uri: str = f"{PREFIX}/store/disbursement"
        form: dict[str, str]
        response: httpx.Response

        journal_entry_data: JournalEntryData = JournalEntryData(
            self.data.l_p_or3c.journal_entry.days, [JournalEntryCurrencyData(
                "USD",
                [JournalEntryLineItemData(
                    Accounts.PAYABLE,
                    self.data.l_p_or1c.description, "500",
                    original_line_item=self.data.l_p_or1c),
                 JournalEntryLineItemData(
                     Accounts.PAYABLE,
                     self.data.l_p_or1c.description, "300",
                     original_line_item=self.data.l_p_or1c),
                 JournalEntryLineItemData(
                     Accounts.PAYABLE,
                     self.data.l_p_or3c.description, "120",
                     original_line_item=self.data.l_p_or3c)],
                [])])

        # Non-existing original line item ID
        form = journal_entry_data.new_form(self.csrf_token)
        form["currency-1-debit-1-original_line_item_id"] = "9999"
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)

        # The same debit or credit
        form = journal_entry_data.new_form(self.csrf_token)
        form["currency-1-debit-1-original_line_item_id"] \
            = str(self.data.l_r_or1d.id)
        form["currency-1-debit-1-account_code"] = self.data.l_r_or1d.account
        form["currency-1-debit-1-amount"] = "100"
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)

        # The original line item does not need offset
        with self.app.app_context():
            account = Account.find_by_code(Accounts.PAYABLE)
            account.is_need_offset = False
            db.session.commit()
        response = self.client.post(
            store_uri, data=journal_entry_data.new_form(self.csrf_token))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)
        with self.app.app_context():
            account = Account.find_by_code(Accounts.PAYABLE)
            account.is_need_offset = True
            db.session.commit()

        # The original line item is also an offset
        form = journal_entry_data.new_form(self.csrf_token)
        form["currency-1-debit-1-original_line_item_id"] \
            = str(self.data.l_r_of1c.id)
        form["currency-1-debit-1-account_code"] = self.data.l_r_of1c.account
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)

        # Not the same currency
        form = journal_entry_data.new_form(self.csrf_token)
        form["currency-1-code"] = "EUR"
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)

        # Not the same account
        form = journal_entry_data.new_form(self.csrf_token)
        form["currency-1-debit-1-account_code"] = Accounts.NOTES_PAYABLE
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)

        # Not exceeding net balance - partially offset
        form = journal_entry_data.new_form(self.csrf_token)
        form["currency-1-debit-1-amount"] \
            = str(journal_entry_data.currencies[0].debit[0].amount
                  + Decimal("0.01"))
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)

        # Not exceeding net balance - unmatched
        form = journal_entry_data.new_form(self.csrf_token)
        form["currency-1-debit-3-amount"] \
            = str(journal_entry_data.currencies[0].debit[2].amount
                  + Decimal("0.01"))
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)

        # Not before the original line items
        old_days: int = journal_entry_data.days
        journal_entry_data.days = old_days + 1
        form = journal_entry_data.new_form(self.csrf_token)
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], create_uri)
        journal_entry_data.days = old_days

        # Success
        form = journal_entry_data.new_form(self.csrf_token)
        response = self.client.post(store_uri, data=form)
        self.assertEqual(response.status_code, 302)
        journal_entry_id: int \
            = match_journal_entry_detail(response.headers["Location"])
        with self.app.app_context():
            journal_entry = db.session.get(JournalEntry, journal_entry_id)
            for offset in journal_entry.currencies[0].debit:
                self.assertIsNotNone(offset.original_line_item_id)

    def test_edit_payable_offset(self) -> None:
        """Tests to edit the payable offset.

        :return: None.
        """
        from accounting.models import Account, JournalEntry
        journal_entry_data: JournalEntryData = self.data.j_p_of2
        edit_uri: str = f"{PREFIX}/{journal_entry_data.id}/edit?next=%2F_next"
        update_uri: str = f"{PREFIX}/{journal_entry_data.id}/update"
        form: dict[str, str]
        response: httpx.Response

        journal_entry_data.days = self.data.j_p_or2.days
        journal_entry_data.currencies[0].debit[0].amount = Decimal("1100")
        journal_entry_data.currencies[0].credit[0].amount = Decimal("1100")
        journal_entry_data.currencies[0].debit[2].amount = Decimal("900")
        journal_entry_data.currencies[0].credit[2].amount = Decimal("900")

        # Non-existing original line item ID
        form = journal_entry_data.update_form(self.csrf_token)
        form["currency-1-debit-1-original_line_item_id"] = "9999"
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # The same debit or credit
        form = journal_entry_data.update_form(self.csrf_token)
        form["currency-1-debit-1-original_line_item_id"] \
            = str(self.data.l_r_or1d.id)
        form["currency-1-debit-1-account_code"] = self.data.l_r_or1d.account
        form["currency-1-debit-1-amount"] = "100"
        form["currency-1-credit-1-amount"] = "100"
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # The original line item does not need offset
        with self.app.app_context():
            account = Account.find_by_code(Accounts.PAYABLE)
            account.is_need_offset = False
            db.session.commit()
        response = self.client.post(
            update_uri, data=journal_entry_data.update_form(self.csrf_token))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)
        with self.app.app_context():
            account = Account.find_by_code(Accounts.PAYABLE)
            account.is_need_offset = True
            db.session.commit()

        # The original line item is also an offset
        form = journal_entry_data.update_form(self.csrf_token)
        form["currency-1-debit-1-original_line_item_id"] \
            = str(self.data.l_r_of1c.id)
        form["currency-1-debit-1-account_code"] = self.data.l_r_of1c.account
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Not the same currency
        form = journal_entry_data.update_form(self.csrf_token)
        form["currency-1-code"] = "EUR"
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Not the same account
        form = journal_entry_data.update_form(self.csrf_token)
        form["currency-1-debit-1-account_code"] = Accounts.NOTES_PAYABLE
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Not exceeding net balance - partially offset
        form = journal_entry_data.update_form(self.csrf_token)
        form["currency-1-debit-1-amount"] \
            = str(journal_entry_data.currencies[0].debit[0].amount
                  + Decimal("0.01"))
        form["currency-1-credit-1-amount"] \
            = str(journal_entry_data.currencies[0].credit[0].amount
                  + Decimal("0.01"))
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Not exceeding net balance - unmatched
        form = journal_entry_data.update_form(self.csrf_token)
        form["currency-1-debit-3-amount"] \
            = str(journal_entry_data.currencies[0].debit[2].amount
                  + Decimal("0.01"))
        form["currency-1-credit-3-amount"] \
            = str(journal_entry_data.currencies[0].credit[2].amount
                  + Decimal("0.01"))
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Not before the original line items
        old_days: int = journal_entry_data.days
        journal_entry_data.days = old_days + 1
        form = journal_entry_data.update_form(self.csrf_token)
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)
        journal_entry_data.days = old_days

        # Success
        form = journal_entry_data.update_form(self.csrf_token)
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        journal_entry_id: int \
            = match_journal_entry_detail(response.headers["Location"])
        with self.app.app_context():
            journal_entry = db.session.get(JournalEntry, journal_entry_id)
            for offset in journal_entry.currencies[0].debit:
                self.assertIsNotNone(offset.original_line_item_id)

    def test_edit_payable_original_line_item(self) -> None:
        """Tests to edit the payable original line item.

        :return: None.
        """
        from accounting.models import JournalEntry
        journal_entry_data: JournalEntryData = self.data.j_p_or1
        edit_uri: str = f"{PREFIX}/{journal_entry_data.id}/edit?next=%2F_next"
        update_uri: str = f"{PREFIX}/{journal_entry_data.id}/update"
        form: dict[str, str]
        response: httpx.Response

        journal_entry_data.days = self.data.j_p_of1.days
        journal_entry_data.currencies[0].debit[0].amount = Decimal("1200")
        journal_entry_data.currencies[0].credit[0].amount = Decimal("1200")
        journal_entry_data.currencies[0].debit[1].amount = Decimal("0.9")
        journal_entry_data.currencies[0].credit[1].amount = Decimal("0.9")

        # Not the same currency
        form = journal_entry_data.update_form(self.csrf_token)
        form["currency-1-code"] = "EUR"
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Not the same account
        form = journal_entry_data.update_form(self.csrf_token)
        form["currency-1-credit-1-account_code"] = Accounts.NOTES_PAYABLE
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Not less than offset total - partially offset
        form = journal_entry_data.update_form(self.csrf_token)
        form["currency-1-debit-1-amount"] \
            = str(journal_entry_data.currencies[0].debit[0].amount
                  - Decimal("0.01"))
        form["currency-1-credit-1-amount"] \
            = str(journal_entry_data.currencies[0].credit[0].amount
                  - Decimal("0.01"))
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Not less than offset total - fully offset
        form = journal_entry_data.update_form(self.csrf_token)
        form["currency-1-debit-2-amount"] \
            = str(journal_entry_data.currencies[0].debit[1].amount
                  - Decimal("0.01"))
        form["currency-1-credit-2-amount"] \
            = str(journal_entry_data.currencies[0].credit[1].amount
                  - Decimal("0.01"))
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Not after the offset items
        old_days: int = journal_entry_data.days
        journal_entry_data.days = old_days - 1
        form = journal_entry_data.update_form(self.csrf_token)
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)
        journal_entry_data.days = old_days

        # Not deleting matched original line items
        form = journal_entry_data.update_form(self.csrf_token)
        del form["currency-1-credit-1-id"]
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], edit_uri)

        # Success
        form = journal_entry_data.update_form(self.csrf_token)
        response = self.client.post(update_uri, data=form)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"],
                         f"{PREFIX}/{journal_entry_data.id}?next=%2F_next")

        # The original line item is always before the offset item, even when
        # they happen in the same day
        with self.app.app_context():
            journal_entry_or: JournalEntry | None = db.session.get(
                JournalEntry, journal_entry_data.id)
            self.assertIsNotNone(journal_entry_or)
            journal_entry_of: JournalEntry | None = db.session.get(
                JournalEntry, self.data.j_p_of1.id)
            self.assertIsNotNone(journal_entry_of)
            self.assertEqual(journal_entry_or.date, journal_entry_of.date)
            self.assertLess(journal_entry_or.no, journal_entry_of.no)


class OffsetTestData(BaseTestData):
    """The offset test data."""

    def _init_data(self) -> None:
        # Receivable original line items
        self.l_r_or1d, self.l_r_or1c = self._couple(
            "Accountant", "1200", Accounts.RECEIVABLE, Accounts.SERVICE)
        self.l_r_or2d, self.l_r_or2c = self._couple(
            "Toy", "600", Accounts.RECEIVABLE, Accounts.SALES)
        self.l_r_or3d, self.l_r_or3c = self._couple(
            "Noodles", "100", Accounts.RECEIVABLE, Accounts.SALES)
        self.l_r_or4d, self.l_r_or4c = self._couple(
            "Interest", "3.4", Accounts.RECEIVABLE, Accounts.INTEREST)

        # Payable original line items
        self.l_p_or1d, self.l_p_or1c = self._couple(
            "Airplane", "2000", Accounts.TRAVEL, Accounts.PAYABLE)
        self.l_p_or2d, self.l_p_or2c = self._couple(
            "Phone", "900", Accounts.OFFICE, Accounts.PAYABLE)
        self.l_p_or3d, self.l_p_or3c = self._couple(
            "Steak", "120", Accounts.MEAL, Accounts.PAYABLE)
        self.l_p_or4d, self.l_p_or4c = self._couple(
            "Envelop", "0.9", Accounts.OFFICE, Accounts.PAYABLE)

        # Original journal entries
        self.j_r_or1: JournalEntryData = JournalEntryData(
            50, [JournalEntryCurrencyData(
                "USD", [self.l_r_or1d, self.l_r_or4d],
                [self.l_r_or1c, self.l_r_or4c])])
        self.j_r_or2: JournalEntryData = JournalEntryData(
            30, [JournalEntryCurrencyData(
                "USD", [self.l_r_or2d, self.l_r_or3d],
                [self.l_r_or2c, self.l_r_or3c])])
        self.j_p_or1: JournalEntryData = JournalEntryData(
            40, [JournalEntryCurrencyData(
                "USD", [self.l_p_or1d, self.l_p_or4d],
                [self.l_p_or1c, self.l_p_or4c])])
        self.j_p_or2: JournalEntryData = JournalEntryData(
            20, [JournalEntryCurrencyData(
                "USD", [self.l_p_or2d, self.l_p_or3d],
                [self.l_p_or2c, self.l_p_or3c])])

        self._add_journal_entry(self.j_r_or1)
        self._add_journal_entry(self.j_r_or2)
        self._add_journal_entry(self.j_p_or1)
        self._add_journal_entry(self.j_p_or2)

        # Receivable offset items
        self.l_r_of1d, self.l_r_of1c = self._couple(
            "Accountant", "500", Accounts.CASH, Accounts.RECEIVABLE)
        self.l_r_of1c.original_line_item = self.l_r_or1d
        self.l_r_of2d, self.l_r_of2c = self._couple(
            "Accountant", "200", Accounts.CASH, Accounts.RECEIVABLE)
        self.l_r_of2c.original_line_item = self.l_r_or1d
        self.l_r_of3d, self.l_r_of3c = self._couple(
            "Accountant", "100", Accounts.CASH, Accounts.RECEIVABLE)
        self.l_r_of3c.original_line_item = self.l_r_or1d
        self.l_r_of4d, self.l_r_of4c = self._couple(
            "Toy", "240", Accounts.CASH, Accounts.RECEIVABLE)
        self.l_r_of4c.original_line_item = self.l_r_or2d
        self.l_r_of5d, self.l_r_of5c = self._couple(
            "Interest", "3.4", Accounts.CASH, Accounts.RECEIVABLE)
        self.l_r_of5c.original_line_item = self.l_r_or4d

        # Payable offset items
        self.l_p_of1d, self.l_p_of1c = self._couple(
            "Airplane", "800", Accounts.PAYABLE, Accounts.CASH)
        self.l_p_of1d.original_line_item = self.l_p_or1c
        self.l_p_of2d, self.l_p_of2c = self._couple(
            "Airplane", "300", Accounts.PAYABLE, Accounts.CASH)
        self.l_p_of2d.original_line_item = self.l_p_or1c
        self.l_p_of3d, self.l_p_of3c = self._couple(
            "Airplane", "100", Accounts.PAYABLE, Accounts.CASH)
        self.l_p_of3d.original_line_item = self.l_p_or1c
        self.l_p_of4d, self.l_p_of4c = self._couple(
            "Phone", "400", Accounts.PAYABLE, Accounts.CASH)
        self.l_p_of4d.original_line_item = self.l_p_or2c
        self.l_p_of5d, self.l_p_of5c = self._couple(
            "Envelop", "0.9", Accounts.PAYABLE, Accounts.CASH)
        self.l_p_of5d.original_line_item = self.l_p_or4c

        # Offset journal entries
        self.j_r_of1: JournalEntryData = JournalEntryData(
            25, [JournalEntryCurrencyData(
                "USD", [self.l_r_of1d], [self.l_r_of1c])])
        self.j_r_of2: JournalEntryData = JournalEntryData(
            20, [JournalEntryCurrencyData(
                "USD", [self.l_r_of2d, self.l_r_of3d, self.l_r_of4d],
                [self.l_r_of2c, self.l_r_of3c, self.l_r_of4c])])
        self.j_r_of3: JournalEntryData = JournalEntryData(
            15, [JournalEntryCurrencyData(
                "USD", [self.l_r_of5d], [self.l_r_of5c])])
        self.j_p_of1: JournalEntryData = JournalEntryData(
            15, [JournalEntryCurrencyData(
                "USD", [self.l_p_of1d], [self.l_p_of1c])])
        self.j_p_of2: JournalEntryData = JournalEntryData(
            10, [JournalEntryCurrencyData(
                "USD", [self.l_p_of2d, self.l_p_of3d, self.l_p_of4d],
                [self.l_p_of2c, self.l_p_of3c, self.l_p_of4c])])
        self.j_p_of3: JournalEntryData = JournalEntryData(
            5, [JournalEntryCurrencyData(
                "USD", [self.l_p_of5d], [self.l_p_of5c])])

        self._add_journal_entry(self.j_r_of1)
        self._add_journal_entry(self.j_r_of2)
        self._add_journal_entry(self.j_r_of3)
        self._add_journal_entry(self.j_p_of1)
        self._add_journal_entry(self.j_p_of2)
        self._add_journal_entry(self.j_p_of3)
