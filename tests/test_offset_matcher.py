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
"""The test for the offset matcher.

"""
import unittest

import httpx
from click.testing import Result
from flask import Flask
from flask.testing import FlaskCliRunner

from test_site import db
from testlib import create_test_app, get_client, Accounts
from testlib_journal_entry import match_journal_entry_detail
from testlib_offset import JournalEntryData, CurrencyData, \
    JournalEntryLineItemData

PREFIX: str = "/accounting/unmatched-offsets"
"""The URL prefix for the unmatched offset management."""


class OffsetMatcherTestCase(unittest.TestCase):
    """The offset matcher test case."""

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

    def test_different(self) -> None:
        """Tests to match against different descriptions and amounts.

        :return: None.
        """
        from accounting.models import Account, JournalEntryLineItem
        from accounting.utils.offset_matcher import OffsetMatcher
        data: DifferentTestData \
            = DifferentTestData(self.app, self.client, self.csrf_token)
        account: Account | None
        line_item: JournalEntryLineItem | None
        matcher: OffsetMatcher
        list_uri: str
        response: httpx.Response

        # The receivables
        with self.app.app_context():
            account = Account.find_by_code(Accounts.RECEIVABLE)
            assert account is not None
            matcher = OffsetMatcher(account)
            self.assertEqual({x.id for x in matcher.unapplied},
                             {data.l_r_or1d.id, data.l_r_or2d.id,
                              data.l_r_or3d.id, data.l_r_or4d.id})
            self.assertEqual({x.id for x in matcher.unmatched_offsets},
                             {data.l_r_of1c.id, data.l_r_of2c.id,
                              data.l_r_of3c.id, data.l_r_of4c.id,
                              data.l_r_of5c.id})
            self.assertEqual({(x.original_line_item.id, x.offset.id)
                              for x in matcher.matched_pairs},
                             {(data.l_r_or4d.id, data.l_r_of5c.id)})
            for line_item_id in {data.l_r_of1c.id, data.l_r_of2c.id,
                                 data.l_r_of3c.id, data.l_r_of4c.id,
                                 data.l_r_of5c.id}:
                line_item = db.session.get(JournalEntryLineItem, line_item_id)
                self.assertIsNotNone(line_item)
                self.assertIsNone(line_item.original_line_item_id)

        list_uri = f"{PREFIX}/{Accounts.RECEIVABLE}"
        response = self.client.post(list_uri,
                                    data={"csrf_token": self.csrf_token})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], list_uri)

        with self.app.app_context():
            account = Account.find_by_code(Accounts.RECEIVABLE)
            assert account is not None
            matcher = OffsetMatcher(account)
            self.assertEqual({x.id for x in matcher.unapplied},
                             {data.l_r_or1d.id, data.l_r_or2d.id,
                              data.l_r_or3d.id})
            self.assertEqual({x.id for x in matcher.unmatched_offsets},
                             {data.l_r_of1c.id, data.l_r_of2c.id,
                              data.l_r_of3c.id, data.l_r_of4c.id})
            self.assertEqual(matcher.matches, 0)
            for line_item_id in {data.l_r_of1c.id, data.l_r_of2c.id,
                                 data.l_r_of3c.id, data.l_r_of4c.id}:
                line_item = db.session.get(JournalEntryLineItem, line_item_id)
                self.assertIsNotNone(line_item)
                self.assertIsNone(line_item.original_line_item_id)
            line_item = db.session.get(JournalEntryLineItem, data.l_r_of5c.id)
            self.assertIsNotNone(line_item)
            self.assertIsNotNone(line_item.original_line_item_id)
            self.assertEqual(line_item.original_line_item_id, data.l_r_or4d.id)

        # The payables
        with self.app.app_context():
            account = Account.find_by_code(Accounts.PAYABLE)
            assert account is not None
            matcher = OffsetMatcher(account)
            self.assertEqual({x.id for x in matcher.unapplied},
                             {data.l_p_or1c.id, data.l_p_or2c.id,
                              data.l_p_or3c.id, data.l_p_or4c.id})
            self.assertEqual({x.id for x in matcher.unmatched_offsets},
                             {data.l_p_of1d.id, data.l_p_of2d.id,
                              data.l_p_of3d.id, data.l_p_of4d.id,
                              data.l_p_of5d.id})
            self.assertEqual({(x.original_line_item.id, x.offset.id)
                              for x in matcher.matched_pairs},
                             {(data.l_p_or4c.id, data.l_p_of5d.id)})
            for line_item_id in {data.l_p_of1d.id, data.l_p_of2d.id,
                                 data.l_p_of3d.id, data.l_p_of4d.id,
                                 data.l_p_of5d.id}:
                line_item = db.session.get(JournalEntryLineItem, line_item_id)
                self.assertIsNotNone(line_item)
                self.assertIsNone(line_item.original_line_item_id)

        list_uri = f"{PREFIX}/{Accounts.PAYABLE}"
        response = self.client.post(list_uri,
                                    data={"csrf_token": self.csrf_token})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], list_uri)

        with self.app.app_context():
            account = Account.find_by_code(Accounts.PAYABLE)
            assert account is not None
            matcher = OffsetMatcher(account)
            self.assertEqual({x.id for x in matcher.unapplied},
                             {data.l_p_or1c.id, data.l_p_or2c.id,
                              data.l_p_or3c.id})
            self.assertEqual({x.id for x in matcher.unmatched_offsets},
                             {data.l_p_of1d.id, data.l_p_of2d.id,
                              data.l_p_of3d.id, data.l_p_of4d.id})
            self.assertEqual(matcher.matches, 0)
            for line_item_id in {data.l_p_of1d.id, data.l_p_of2d.id,
                                 data.l_p_of3d.id, data.l_p_of4d.id}:
                line_item = db.session.get(JournalEntryLineItem, line_item_id)
                self.assertIsNotNone(line_item)
                self.assertIsNone(line_item.original_line_item_id)
            line_item = db.session.get(JournalEntryLineItem, data.l_p_of5d.id)
            self.assertIsNotNone(line_item)
            self.assertIsNotNone(line_item.original_line_item_id)
            self.assertEqual(line_item.original_line_item_id, data.l_p_or4c.id)

    def test_same(self) -> None:
        """Tests to match against same descriptions and amounts.

        :return: None.
        """
        from accounting.models import Account, JournalEntryLineItem
        from accounting.utils.offset_matcher import OffsetMatcher
        data: SameTestData \
            = SameTestData(self.app, self.client, self.csrf_token)
        account: Account | None
        line_item: JournalEntryLineItem | None
        matcher: OffsetMatcher
        list_uri: str
        response: httpx.Response

        # The receivables
        with self.app.app_context():
            account = Account.find_by_code(Accounts.RECEIVABLE)
            assert account is not None
            matcher = OffsetMatcher(account)
            self.assertEqual({x.id for x in matcher.unapplied},
                             {data.l_r_or1d.id, data.l_r_or3d.id,
                              data.l_r_or4d.id, data.l_r_or5d.id,
                              data.l_r_or6d.id})
            self.assertEqual({x.id for x in matcher.unmatched_offsets},
                             {data.l_r_of1c.id, data.l_r_of2c.id,
                              data.l_r_of4c.id, data.l_r_of5c.id,
                              data.l_r_of6c.id})
            self.assertEqual({(x.original_line_item.id, x.offset.id)
                              for x in matcher.matched_pairs},
                             {(data.l_r_or1d.id, data.l_r_of2c.id),
                              (data.l_r_or3d.id, data.l_r_of4c.id),
                              (data.l_r_or4d.id, data.l_r_of6c.id)})
            for line_item_id in {data.l_r_of1c.id, data.l_r_of2c.id,
                                 data.l_r_of4c.id, data.l_r_of5c.id,
                                 data.l_r_of6c.id}:
                line_item = db.session.get(JournalEntryLineItem, line_item_id)
                self.assertIsNotNone(line_item)
                self.assertIsNone(line_item.original_line_item_id)
            line_item = db.session.get(JournalEntryLineItem, data.l_r_of3c.id)
            self.assertIsNotNone(line_item)
            self.assertIsNotNone(line_item.original_line_item_id)
            self.assertEqual(line_item.original_line_item_id, data.l_r_or2d.id)

        list_uri = f"{PREFIX}/{Accounts.RECEIVABLE}"
        response = self.client.post(list_uri,
                                    data={"csrf_token": self.csrf_token})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], list_uri)

        with self.app.app_context():
            account = Account.find_by_code(Accounts.RECEIVABLE)
            assert account is not None
            matcher = OffsetMatcher(account)
            self.assertEqual({x.id for x in matcher.unapplied},
                             {data.l_r_or5d.id, data.l_r_or6d.id})
            self.assertEqual({x.id for x in matcher.unmatched_offsets},
                             {data.l_r_of1c.id, data.l_r_of5c.id})
            self.assertEqual(matcher.matches, 0)
            for line_item_id in {data.l_r_of1c.id, data.l_r_of5c.id}:
                line_item = db.session.get(JournalEntryLineItem, line_item_id)
                self.assertIsNotNone(line_item)
                self.assertIsNone(line_item.original_line_item_id)
            line_item = db.session.get(JournalEntryLineItem, data.l_r_of2c.id)
            self.assertIsNotNone(line_item)
            self.assertIsNotNone(line_item.original_line_item_id)
            self.assertEqual(line_item.original_line_item_id, data.l_r_or1d.id)
            line_item = db.session.get(JournalEntryLineItem, data.l_r_of3c.id)
            self.assertIsNotNone(line_item)
            self.assertIsNotNone(line_item.original_line_item_id)
            self.assertEqual(line_item.original_line_item_id, data.l_r_or2d.id)
            line_item = db.session.get(JournalEntryLineItem, data.l_r_of4c.id)
            self.assertIsNotNone(line_item)
            self.assertIsNotNone(line_item.original_line_item_id)
            self.assertEqual(line_item.original_line_item_id, data.l_r_or3d.id)
            line_item = db.session.get(JournalEntryLineItem, data.l_r_of6c.id)
            self.assertIsNotNone(line_item)
            self.assertIsNotNone(line_item.original_line_item_id)
            self.assertEqual(line_item.original_line_item_id, data.l_r_or4d.id)

        # The payables
        with self.app.app_context():
            account = Account.find_by_code(Accounts.PAYABLE)
            assert account is not None
            matcher = OffsetMatcher(account)
            self.assertEqual({x.id for x in matcher.unapplied},
                             {data.l_p_or1c.id, data.l_p_or3c.id,
                              data.l_p_or4c.id, data.l_p_or5c.id,
                              data.l_p_or6c.id})
            self.assertEqual({x.id for x in matcher.unmatched_offsets},
                             {data.l_p_of1d.id, data.l_p_of2d.id,
                              data.l_p_of4d.id, data.l_p_of5d.id,
                              data.l_p_of6d.id})
            self.assertEqual({(x.original_line_item.id, x.offset.id)
                              for x in matcher.matched_pairs},
                             {(data.l_p_or1c.id, data.l_p_of2d.id),
                              (data.l_p_or3c.id, data.l_p_of4d.id),
                              (data.l_p_or4c.id, data.l_p_of6d.id)})
            for line_item_id in {data.l_p_of1d.id, data.l_p_of2d.id,
                                 data.l_p_of4d.id, data.l_p_of5d.id,
                                 data.l_p_of6d.id}:
                line_item = db.session.get(JournalEntryLineItem, line_item_id)
                self.assertIsNotNone(line_item)
                self.assertIsNone(line_item.original_line_item_id)
            line_item = db.session.get(JournalEntryLineItem, data.l_p_of3d.id)
            self.assertIsNotNone(line_item)
            self.assertIsNotNone(line_item.original_line_item_id)
            self.assertEqual(line_item.original_line_item_id, data.l_p_or2c.id)

        list_uri = f"{PREFIX}/{Accounts.PAYABLE}"
        response = self.client.post(list_uri,
                                    data={"csrf_token": self.csrf_token})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], list_uri)

        with self.app.app_context():
            account = Account.find_by_code(Accounts.PAYABLE)
            assert account is not None
            matcher = OffsetMatcher(account)
            self.assertEqual({x.id for x in matcher.unapplied},
                             {data.l_p_or5c.id, data.l_p_or6c.id})
            self.assertEqual({x.id for x in matcher.unmatched_offsets},
                             {data.l_p_of1d.id, data.l_p_of5d.id})
            self.assertEqual(matcher.matches, 0)
            for line_item_id in {data.l_p_of1d.id, data.l_p_of5d.id}:
                line_item = db.session.get(JournalEntryLineItem, line_item_id)
                self.assertIsNotNone(line_item)
                self.assertIsNone(line_item.original_line_item_id)
            line_item = db.session.get(JournalEntryLineItem, data.l_p_of2d.id)
            self.assertIsNotNone(line_item)
            self.assertIsNotNone(line_item.original_line_item_id)
            self.assertEqual(line_item.original_line_item_id, data.l_p_or1c.id)
            line_item = db.session.get(JournalEntryLineItem, data.l_p_of3d.id)
            self.assertIsNotNone(line_item)
            self.assertIsNotNone(line_item.original_line_item_id)
            self.assertEqual(line_item.original_line_item_id, data.l_p_or2c.id)
            line_item = db.session.get(JournalEntryLineItem, data.l_p_of4d.id)
            self.assertIsNotNone(line_item)
            self.assertIsNotNone(line_item.original_line_item_id)
            self.assertEqual(line_item.original_line_item_id, data.l_p_or3c.id)
            line_item = db.session.get(JournalEntryLineItem, data.l_p_of6d.id)
            self.assertIsNotNone(line_item)
            self.assertIsNotNone(line_item.original_line_item_id)
            self.assertEqual(line_item.original_line_item_id, data.l_p_or4c.id)


class DifferentTestData:
    """The test data for different descriptions and amounts."""

    def __init__(self, app: Flask, client: httpx.Client, csrf_token: str):
        """Constructs the test data.

        :param app: The Flask application.
        :param client: The client.
        :param csrf_token: The CSRF token.
        """
        self.app: Flask = app
        self.client: httpx.Client = client
        self.csrf_token: str = csrf_token

        def couple(description: str, amount: str, debit: str, credit: str) \
                -> tuple[JournalEntryLineItemData, JournalEntryLineItemData]:
            """Returns a couple of debit-credit line items.

            :param description: The description.
            :param amount: The amount.
            :param debit: The debit account code.
            :param credit: The credit account code.
            :return: The debit line item and credit line item.
            """
            return JournalEntryLineItemData(debit, description, amount),\
                JournalEntryLineItemData(credit, description, amount)

        # Receivable original line items
        self.l_r_or1d, self.l_r_or1c = couple(
            "Accountant", "1200", Accounts.RECEIVABLE, Accounts.SERVICE)
        self.l_r_or2d, self.l_r_or2c = couple(
            "Toy", "600", Accounts.RECEIVABLE, Accounts.SALES)
        self.l_r_or3d, self.l_r_or3c = couple(
            "Noodles", "100", Accounts.RECEIVABLE, Accounts.SALES)
        self.l_r_or4d, self.l_r_or4c = couple(
            "Interest", "3.4", Accounts.RECEIVABLE, Accounts.INTEREST)

        # Payable original line items
        self.l_p_or1d, self.l_p_or1c = couple(
            "Airplane", "2000", Accounts.TRAVEL, Accounts.PAYABLE)
        self.l_p_or2d, self.l_p_or2c = couple(
            "Phone", "900", Accounts.OFFICE, Accounts.PAYABLE)
        self.l_p_or3d, self.l_p_or3c = couple(
            "Steak", "120", Accounts.MEAL, Accounts.PAYABLE)
        self.l_p_or4d, self.l_p_or4c = couple(
            "Envelop", "0.9", Accounts.OFFICE, Accounts.PAYABLE)

        # Original journal entries
        self.j_r_or1: JournalEntryData = JournalEntryData(
            50, [CurrencyData("USD", [self.l_r_or1d, self.l_r_or4d],
                              [self.l_r_or1c, self.l_r_or4c])])
        self.j_r_or2: JournalEntryData = JournalEntryData(
            30, [CurrencyData("USD", [self.l_r_or2d, self.l_r_or3d],
                              [self.l_r_or2c, self.l_r_or3c])])
        self.j_p_or1: JournalEntryData = JournalEntryData(
            40, [CurrencyData("USD", [self.l_p_or1d, self.l_p_or4d],
                              [self.l_p_or1c, self.l_p_or4c])])
        self.j_p_or2: JournalEntryData = JournalEntryData(
            20, [CurrencyData("USD", [self.l_p_or2d, self.l_p_or3d],
                              [self.l_p_or2c, self.l_p_or3c])])

        self.__add_journal_entry(self.j_r_or1)
        self.__add_journal_entry(self.j_r_or2)
        self.__add_journal_entry(self.j_p_or1)
        self.__add_journal_entry(self.j_p_or2)

        # Receivable offset items
        self.l_r_of1d, self.l_r_of1c = couple(
            "Accountant", "500", Accounts.CASH, Accounts.RECEIVABLE)
        self.l_r_of2d, self.l_r_of2c = couple(
            "Accountant", "200", Accounts.CASH, Accounts.RECEIVABLE)
        self.l_r_of3d, self.l_r_of3c = couple(
            "Accountant", "100", Accounts.CASH, Accounts.RECEIVABLE)
        self.l_r_of4d, self.l_r_of4c = couple(
            "Toy", "240", Accounts.CASH, Accounts.RECEIVABLE)
        self.l_r_of5d, self.l_r_of5c = couple(
            "Interest", "3.4", Accounts.CASH, Accounts.RECEIVABLE)

        # Payable offset items
        self.l_p_of1d, self.l_p_of1c = couple(
            "Airplane", "800", Accounts.PAYABLE, Accounts.CASH)
        self.l_p_of2d, self.l_p_of2c = couple(
            "Airplane", "300", Accounts.PAYABLE, Accounts.CASH)
        self.l_p_of3d, self.l_p_of3c = couple(
            "Airplane", "100", Accounts.PAYABLE, Accounts.CASH)
        self.l_p_of4d, self.l_p_of4c = couple(
            "Phone", "400", Accounts.PAYABLE, Accounts.CASH)
        self.l_p_of5d, self.l_p_of5c = couple(
            "Envelop", "0.9", Accounts.PAYABLE, Accounts.CASH)

        # Offset journal entries
        self.j_r_of1: JournalEntryData = JournalEntryData(
            25, [CurrencyData("USD", [self.l_r_of1d], [self.l_r_of1c])])
        self.j_r_of2: JournalEntryData = JournalEntryData(
            20, [CurrencyData("USD",
                              [self.l_r_of2d, self.l_r_of3d, self.l_r_of4d],
                              [self.l_r_of2c, self.l_r_of3c, self.l_r_of4c])])
        self.j_r_of3: JournalEntryData = JournalEntryData(
            15, [CurrencyData("USD", [self.l_r_of5d], [self.l_r_of5c])])
        self.j_p_of1: JournalEntryData = JournalEntryData(
            15, [CurrencyData("USD", [self.l_p_of1d], [self.l_p_of1c])])
        self.j_p_of2: JournalEntryData = JournalEntryData(
            10, [CurrencyData("USD",
                              [self.l_p_of2d, self.l_p_of3d, self.l_p_of4d],
                              [self.l_p_of2c, self.l_p_of3c, self.l_p_of4c])])
        self.j_p_of3: JournalEntryData = JournalEntryData(
            5, [CurrencyData("USD", [self.l_p_of5d], [self.l_p_of5c])])

        self.__set_is_need_offset(False)
        self.__add_journal_entry(self.j_r_of1)
        self.__add_journal_entry(self.j_r_of2)
        self.__add_journal_entry(self.j_r_of3)
        self.__add_journal_entry(self.j_p_of1)
        self.__add_journal_entry(self.j_p_of2)
        self.__add_journal_entry(self.j_p_of3)
        self.__set_is_need_offset(True)

    def __set_is_need_offset(self, is_need_offset: bool) -> None:
        """Sets whether the payables and receivables need offset.

        :param is_need_offset: True if payables and receivables need offset, or
            False otherwise.
        :return:
        """
        from accounting.models import Account
        with self.app.app_context():
            for code in {Accounts.RECEIVABLE, Accounts.PAYABLE}:
                account: Account | None = Account.find_by_code(code)
                assert account is not None
                account.is_need_offset = is_need_offset
            db.session.commit()

    def __add_journal_entry(self, journal_entry_data: JournalEntryData) \
            -> None:
        """Adds a journal entry.

        :param journal_entry_data: The journal entry data.
        :return: None.
        """
        from accounting.models import JournalEntry
        store_uri: str = "/accounting/journal-entries/store/transfer"

        response: httpx.Response = self.client.post(
            store_uri, data=journal_entry_data.new_form(self.csrf_token))
        assert response.status_code == 302
        journal_entry_id: int \
            = match_journal_entry_detail(response.headers["Location"])
        journal_entry_data.id = journal_entry_id
        with self.app.app_context():
            journal_entry: JournalEntry | None \
                = db.session.get(JournalEntry, journal_entry_id)
            assert journal_entry is not None
            for i in range(len(journal_entry.currencies)):
                for j in range(len(journal_entry.currencies[i].debit)):
                    journal_entry_data.currencies[i].debit[j].id \
                        = journal_entry.currencies[i].debit[j].id
                for j in range(len(journal_entry.currencies[i].credit)):
                    journal_entry_data.currencies[i].credit[j].id \
                        = journal_entry.currencies[i].credit[j].id


class SameTestData:
    """The test data with same descriptions and amounts."""

    def __init__(self, app: Flask, client: httpx.Client, csrf_token: str):
        """Constructs the test data.

        :param app: The Flask application.
        :param client: The client.
        :param csrf_token: The CSRF token.
        """
        self.app: Flask = app
        self.client: httpx.Client = client
        self.csrf_token: str = csrf_token

        def couple(description: str, amount: str, debit: str, credit: str) \
                -> tuple[JournalEntryLineItemData, JournalEntryLineItemData]:
            """Returns a couple of debit-credit line items.

            :param description: The description.
            :param amount: The amount.
            :param debit: The debit account code.
            :param credit: The credit account code.
            :return: The debit line item and credit line item.
            """
            return JournalEntryLineItemData(debit, description, amount),\
                JournalEntryLineItemData(credit, description, amount)

        # Receivable original line items
        self.l_r_or1d, self.l_r_or1c = couple(
            "Noodles", "100", Accounts.RECEIVABLE, Accounts.SALES)
        self.l_r_or2d, self.l_r_or2c = couple(
            "Noodles", "100", Accounts.RECEIVABLE, Accounts.SALES)
        self.l_r_or3d, self.l_r_or3c = couple(
            "Noodles", "100", Accounts.RECEIVABLE, Accounts.SALES)
        self.l_r_or4d, self.l_r_or4c = couple(
            "Noodles", "100", Accounts.RECEIVABLE, Accounts.SALES)
        self.l_r_or5d, self.l_r_or5c = couple(
            "Noodles", "100", Accounts.RECEIVABLE, Accounts.SALES)
        self.l_r_or6d, self.l_r_or6c = couple(
            "Noodles", "100", Accounts.RECEIVABLE, Accounts.SALES)

        # Payable original line items
        self.l_p_or1d, self.l_p_or1c = couple(
            "Steak", "120", Accounts.MEAL, Accounts.PAYABLE)
        self.l_p_or2d, self.l_p_or2c = couple(
            "Steak", "120", Accounts.MEAL, Accounts.PAYABLE)
        self.l_p_or3d, self.l_p_or3c = couple(
            "Steak", "120", Accounts.MEAL, Accounts.PAYABLE)
        self.l_p_or4d, self.l_p_or4c = couple(
            "Steak", "120", Accounts.MEAL, Accounts.PAYABLE)
        self.l_p_or5d, self.l_p_or5c = couple(
            "Steak", "120", Accounts.MEAL, Accounts.PAYABLE)
        self.l_p_or6d, self.l_p_or6c = couple(
            "Steak", "120", Accounts.MEAL, Accounts.PAYABLE)

        # Original journal entries
        self.j_r_or1: JournalEntryData = JournalEntryData(
            60, [CurrencyData("USD", [self.l_r_or1d], [self.l_r_or1c])])
        self.j_r_or2: JournalEntryData = JournalEntryData(
            50, [CurrencyData("USD", [self.l_r_or2d], [self.l_r_or2c])])
        self.j_r_or3: JournalEntryData = JournalEntryData(
            40, [CurrencyData("USD", [self.l_r_or3d], [self.l_r_or3c])])
        self.j_r_or4: JournalEntryData = JournalEntryData(
            30, [CurrencyData("USD", [self.l_r_or4d], [self.l_r_or4c])])
        self.j_r_or5: JournalEntryData = JournalEntryData(
            20, [CurrencyData("USD", [self.l_r_or5d], [self.l_r_or5c])])
        self.j_r_or6: JournalEntryData = JournalEntryData(
            10, [CurrencyData("USD", [self.l_r_or6d], [self.l_r_or6c])])
        self.j_p_or1: JournalEntryData = JournalEntryData(
            60, [CurrencyData("USD", [self.l_p_or1d], [self.l_p_or1c])])
        self.j_p_or2: JournalEntryData = JournalEntryData(
            50, [CurrencyData("USD", [self.l_p_or2d], [self.l_p_or2c])])
        self.j_p_or3: JournalEntryData = JournalEntryData(
            40, [CurrencyData("USD", [self.l_p_or3d], [self.l_p_or3c])])
        self.j_p_or4: JournalEntryData = JournalEntryData(
            30, [CurrencyData("USD", [self.l_p_or4d], [self.l_p_or4c])])
        self.j_p_or5: JournalEntryData = JournalEntryData(
            20, [CurrencyData("USD", [self.l_p_or5d], [self.l_p_or5c])])
        self.j_p_or6: JournalEntryData = JournalEntryData(
            10, [CurrencyData("USD", [self.l_p_or6d], [self.l_p_or6c])])

        self.__add_journal_entry(self.j_r_or1)
        self.__add_journal_entry(self.j_r_or2)
        self.__add_journal_entry(self.j_r_or3)
        self.__add_journal_entry(self.j_r_or4)
        self.__add_journal_entry(self.j_r_or5)
        self.__add_journal_entry(self.j_r_or6)
        self.__add_journal_entry(self.j_p_or1)
        self.__add_journal_entry(self.j_p_or2)
        self.__add_journal_entry(self.j_p_or3)
        self.__add_journal_entry(self.j_p_or4)
        self.__add_journal_entry(self.j_p_or5)
        self.__add_journal_entry(self.j_p_or6)

        # Receivable offset items
        self.l_r_of1d, self.l_r_of1c = couple(
            "Noodles", "100", Accounts.CASH, Accounts.RECEIVABLE)
        self.l_r_of2d, self.l_r_of2c = couple(
            "Noodles", "100", Accounts.CASH, Accounts.RECEIVABLE)
        self.l_r_of3d, self.l_r_of3c = couple(
            "Noodles", "100", Accounts.CASH, Accounts.RECEIVABLE)
        self.l_r_of3c.original_line_item = self.l_r_or2d
        self.l_r_of4d, self.l_r_of4c = couple(
            "Noodles", "100", Accounts.CASH, Accounts.RECEIVABLE)
        self.l_r_of5d, self.l_r_of5c = couple(
            "Noodles", "100", Accounts.CASH, Accounts.RECEIVABLE)
        self.l_r_of6d, self.l_r_of6c = couple(
            "Noodles", "100", Accounts.CASH, Accounts.RECEIVABLE)

        # Payable offset items
        self.l_p_of1d, self.l_p_of1c = couple(
            "Steak", "120", Accounts.PAYABLE, Accounts.CASH)
        self.l_p_of2d, self.l_p_of2c = couple(
            "Steak", "120", Accounts.PAYABLE, Accounts.CASH)
        self.l_p_of3d, self.l_p_of3c = couple(
            "Steak", "120", Accounts.PAYABLE, Accounts.CASH)
        self.l_p_of3d.original_line_item = self.l_p_or2c
        self.l_p_of4d, self.l_p_of4c = couple(
            "Steak", "120", Accounts.PAYABLE, Accounts.CASH)
        self.l_p_of5d, self.l_p_of5c = couple(
            "Steak", "120", Accounts.PAYABLE, Accounts.CASH)
        self.l_p_of6d, self.l_p_of6c = couple(
            "Steak", "120", Accounts.PAYABLE, Accounts.CASH)

        # Offset journal entries
        self.j_r_of1: JournalEntryData = JournalEntryData(
            65, [CurrencyData("USD", [self.l_r_of1d], [self.l_r_of1c])])
        self.j_r_of2: JournalEntryData = JournalEntryData(
            35, [CurrencyData("USD", [self.l_r_of2d], [self.l_r_of2c])])
        self.j_r_of3: JournalEntryData = JournalEntryData(
            35, [CurrencyData("USD", [self.l_r_of3d], [self.l_r_of3c])])
        self.j_r_of4: JournalEntryData = JournalEntryData(
            35, [CurrencyData("USD", [self.l_r_of4d], [self.l_r_of4c])])
        self.j_r_of5: JournalEntryData = JournalEntryData(
            35, [CurrencyData("USD", [self.l_r_of5d], [self.l_r_of5c])])
        self.j_r_of6: JournalEntryData = JournalEntryData(
            15, [CurrencyData("USD", [self.l_r_of6d], [self.l_r_of6c])])
        self.j_p_of1: JournalEntryData = JournalEntryData(
            65, [CurrencyData("USD", [self.l_p_of1d], [self.l_p_of1c])])
        self.j_p_of2: JournalEntryData = JournalEntryData(
            35, [CurrencyData("USD", [self.l_p_of2d], [self.l_p_of2c])])
        self.j_p_of3: JournalEntryData = JournalEntryData(
            35, [CurrencyData("USD", [self.l_p_of3d], [self.l_p_of3c])])
        self.j_p_of4: JournalEntryData = JournalEntryData(
            35, [CurrencyData("USD", [self.l_p_of4d], [self.l_p_of4c])])
        self.j_p_of5: JournalEntryData = JournalEntryData(
            35, [CurrencyData("USD", [self.l_p_of5d], [self.l_p_of5c])])
        self.j_p_of6: JournalEntryData = JournalEntryData(
            15, [CurrencyData("USD", [self.l_p_of6d], [self.l_p_of6c])])

        self.__set_is_need_offset(False)
        self.__add_journal_entry(self.j_r_of1)
        self.__add_journal_entry(self.j_r_of2)
        self.__add_journal_entry(self.j_r_of4)
        self.__add_journal_entry(self.j_r_of5)
        self.__add_journal_entry(self.j_r_of6)
        self.__add_journal_entry(self.j_p_of1)
        self.__add_journal_entry(self.j_p_of2)
        self.__add_journal_entry(self.j_p_of4)
        self.__add_journal_entry(self.j_p_of5)
        self.__add_journal_entry(self.j_p_of6)
        self.__set_is_need_offset(True)
        self.__add_journal_entry(self.j_r_of3)
        self.__add_journal_entry(self.j_p_of3)

    def __set_is_need_offset(self, is_need_offset: bool) -> None:
        """Sets whether the payables and receivables need offset.

        :param is_need_offset: True if payables and receivables need offset, or
            False otherwise.
        :return:
        """
        from accounting.models import Account
        with self.app.app_context():
            for code in {Accounts.RECEIVABLE, Accounts.PAYABLE}:
                account: Account | None = Account.find_by_code(code)
                assert account is not None
                account.is_need_offset = is_need_offset
            db.session.commit()

    def __add_journal_entry(self, journal_entry_data: JournalEntryData) \
            -> None:
        """Adds a journal entry.

        :param journal_entry_data: The journal entry data.
        :return: None.
        """
        from accounting.models import JournalEntry
        store_uri: str = "/accounting/journal-entries/store/transfer"

        response: httpx.Response = self.client.post(
            store_uri, data=journal_entry_data.new_form(self.csrf_token))
        assert response.status_code == 302
        journal_entry_id: int \
            = match_journal_entry_detail(response.headers["Location"])
        journal_entry_data.id = journal_entry_id
        with self.app.app_context():
            journal_entry: JournalEntry | None \
                = db.session.get(JournalEntry, journal_entry_id)
            assert journal_entry is not None
            for i in range(len(journal_entry.currencies)):
                for j in range(len(journal_entry.currencies[i].debit)):
                    journal_entry_data.currencies[i].debit[j].id \
                        = journal_entry.currencies[i].debit[j].id
                for j in range(len(journal_entry.currencies[i].credit)):
                    journal_entry_data.currencies[i].credit[j].id \
                        = journal_entry.currencies[i].credit[j].id
