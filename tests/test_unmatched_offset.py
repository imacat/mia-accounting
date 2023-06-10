# The Mia! Accounting Project.
# Author: imacat@mail.imacat.idv.tw (imacat), 2023/4/8

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
"""The test for the unmatched offsets.

"""
import unittest

import httpx
from flask import Flask

from accounting.utils.next_uri import encode_next
from test_site import db
from test_site.lib import JournalEntryCurrencyData, JournalEntryData, \
    BaseTestData
from testlib import NEXT_URI, create_test_app, get_client, get_csrf_token, \
    Accounts

PREFIX: str = "/accounting/match-offsets/USD"
"""The URL prefix for the unmatched offset management."""


class UnmatchedOffsetTestCase(unittest.TestCase):
    """The unmatched offset test case."""

    def setUp(self) -> None:
        """Sets up the test.
        This is run once per test.

        :return: None.
        """
        self.__app: Flask = create_test_app()
        """The Flask application."""

        with self.__app.app_context():
            from accounting.models import JournalEntry, JournalEntryLineItem
            JournalEntry.query.delete()
            JournalEntryLineItem.query.delete()
            self.__encoded_next_uri: str = encode_next(NEXT_URI)
            """The encoded next URI."""

        self.__client: httpx.Client = get_client(self.__app, "editor")
        """The user client."""
        self.__csrf_token: str = get_csrf_token(self.__client)
        """The CSRF token."""

    def test_nobody(self) -> None:
        """Test the permission as nobody.

        :return: None.
        """
        client: httpx.Client = get_client(self.__app, "nobody")
        csrf_token: str = get_csrf_token(client)
        DifferentTestData(self.__app, "nobody").populate()
        response: httpx.Response

        response = client.post(f"{PREFIX}/{Accounts.PAYABLE}",
                               data={"csrf_token": csrf_token,
                                     "next": self.__encoded_next_uri})
        self.assertEqual(response.status_code, 403)

    def test_viewer(self) -> None:
        """Test the permission as viewer.

        :return: None.
        """
        client: httpx.Client = get_client(self.__app, "viewer")
        csrf_token: str = get_csrf_token(client)
        DifferentTestData(self.__app, "viewer").populate()
        response: httpx.Response

        response = client.post(f"{PREFIX}/{Accounts.PAYABLE}",
                               data={"csrf_token": csrf_token,
                                     "next": self.__encoded_next_uri})
        self.assertEqual(response.status_code, 403)

    def test_editor(self) -> None:
        """Test the permission as editor.

        :return: None.
        """
        DifferentTestData(self.__app, "editor").populate()
        response: httpx.Response

        response = self.__client.post(f"{PREFIX}/{Accounts.PAYABLE}",
                                      data={"csrf_token": self.__csrf_token,
                                            "next": self.__encoded_next_uri})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], NEXT_URI)

    def test_empty_db(self) -> None:
        """Test the empty database.

        :return: None.
        """
        response: httpx.Response

        response = self.__client.post(f"{PREFIX}/{Accounts.PAYABLE}",
                                      data={"csrf_token": self.__csrf_token,
                                            "next": self.__encoded_next_uri})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], NEXT_URI)

    def test_different(self) -> None:
        """Tests to match against different descriptions and amounts.

        :return: None.
        """
        from accounting.models import Currency, Account, JournalEntryLineItem
        from accounting.report.utils.offset_matcher import OffsetMatcher
        from accounting.template_globals import default_currency_code
        data: DifferentTestData = DifferentTestData(self.__app, "editor")
        data.populate()
        account: Account | None
        line_item: JournalEntryLineItem | None
        matcher: OffsetMatcher
        match_uri: str
        response: httpx.Response

        with self.__app.app_context():
            currency: Currency | None \
                = db.session.get(Currency, default_currency_code())
            assert currency is not None

        # The receivables
        with self.__app.app_context():
            account = Account.find_by_code(Accounts.RECEIVABLE)
            assert account is not None
            matcher = OffsetMatcher(currency, account)
            self.assertEqual({x.id for x in matcher.unapplied},
                             {data.l_r_or1d.id, data.l_r_or2d.id,
                              data.l_r_or3d.id, data.l_r_or4d.id})
            self.assertEqual({x.id for x in matcher.unmatched},
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

        match_uri = f"{PREFIX}/{Accounts.RECEIVABLE}"
        response = self.__client.post(match_uri,
                                      data={"csrf_token": self.__csrf_token,
                                            "next": self.__encoded_next_uri})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], NEXT_URI)

        with self.__app.app_context():
            account = Account.find_by_code(Accounts.RECEIVABLE)
            assert account is not None
            matcher = OffsetMatcher(currency, account)
            self.assertEqual({x.id for x in matcher.unapplied},
                             {data.l_r_or1d.id, data.l_r_or2d.id,
                              data.l_r_or3d.id})
            self.assertEqual({x.id for x in matcher.unmatched},
                             {data.l_r_of1c.id, data.l_r_of2c.id,
                              data.l_r_of3c.id, data.l_r_of4c.id})
            self.assertEqual(len(matcher.matched_pairs), 0)
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
        with self.__app.app_context():
            account = Account.find_by_code(Accounts.PAYABLE)
            assert account is not None
            matcher = OffsetMatcher(currency, account)
            self.assertEqual({x.id for x in matcher.unapplied},
                             {data.l_p_or1c.id, data.l_p_or2c.id,
                              data.l_p_or3c.id, data.l_p_or4c.id})
            self.assertEqual({x.id for x in matcher.unmatched},
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

        match_uri = f"{PREFIX}/{Accounts.PAYABLE}"
        response = self.__client.post(match_uri,
                                      data={"csrf_token": self.__csrf_token,
                                            "next": self.__encoded_next_uri})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], NEXT_URI)

        with self.__app.app_context():
            account = Account.find_by_code(Accounts.PAYABLE)
            assert account is not None
            matcher = OffsetMatcher(currency, account)
            self.assertEqual({x.id for x in matcher.unapplied},
                             {data.l_p_or1c.id, data.l_p_or2c.id,
                              data.l_p_or3c.id})
            self.assertEqual({x.id for x in matcher.unmatched},
                             {data.l_p_of1d.id, data.l_p_of2d.id,
                              data.l_p_of3d.id, data.l_p_of4d.id})
            self.assertEqual(len(matcher.matched_pairs), 0)
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
        from accounting.models import Currency, Account, JournalEntryLineItem
        from accounting.report.utils.offset_matcher import OffsetMatcher
        from accounting.template_globals import default_currency_code
        data: SameTestData = SameTestData(self.__app, "editor")
        data.populate()
        account: Account | None
        line_item: JournalEntryLineItem | None
        matcher: OffsetMatcher
        match_uri: str
        response: httpx.Response

        with self.__app.app_context():
            currency: Currency | None \
                = db.session.get(Currency, default_currency_code())
            assert currency is not None

        # The receivables
        with self.__app.app_context():
            account = Account.find_by_code(Accounts.RECEIVABLE)
            assert account is not None
            matcher = OffsetMatcher(currency, account)
            self.assertEqual({x.id for x in matcher.unapplied},
                             {data.l_r_or1d.id, data.l_r_or3d.id,
                              data.l_r_or4d.id, data.l_r_or5d.id,
                              data.l_r_or6d.id})
            self.assertEqual({x.id for x in matcher.unmatched},
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

        match_uri = f"{PREFIX}/{Accounts.RECEIVABLE}"
        response = self.__client.post(match_uri,
                                      data={"csrf_token": self.__csrf_token,
                                            "next": self.__encoded_next_uri})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], NEXT_URI)

        with self.__app.app_context():
            account = Account.find_by_code(Accounts.RECEIVABLE)
            assert account is not None
            matcher = OffsetMatcher(currency, account)
            self.assertEqual({x.id for x in matcher.unapplied},
                             {data.l_r_or5d.id, data.l_r_or6d.id})
            self.assertEqual({x.id for x in matcher.unmatched},
                             {data.l_r_of1c.id, data.l_r_of5c.id})
            self.assertEqual(len(matcher.matched_pairs), 0)
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
        with self.__app.app_context():
            account = Account.find_by_code(Accounts.PAYABLE)
            assert account is not None
            matcher = OffsetMatcher(currency, account)
            self.assertEqual({x.id for x in matcher.unapplied},
                             {data.l_p_or1c.id, data.l_p_or3c.id,
                              data.l_p_or4c.id, data.l_p_or5c.id,
                              data.l_p_or6c.id})
            self.assertEqual({x.id for x in matcher.unmatched},
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

        match_uri = f"{PREFIX}/{Accounts.PAYABLE}"
        response = self.__client.post(match_uri,
                                      data={"csrf_token": self.__csrf_token,
                                            "next": self.__encoded_next_uri})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], NEXT_URI)

        with self.__app.app_context():
            account = Account.find_by_code(Accounts.PAYABLE)
            assert account is not None
            matcher = OffsetMatcher(currency, account)
            self.assertEqual({x.id for x in matcher.unapplied},
                             {data.l_p_or5c.id, data.l_p_or6c.id})
            self.assertEqual({x.id for x in matcher.unmatched},
                             {data.l_p_of1d.id, data.l_p_of5d.id})
            self.assertEqual(len(matcher.matched_pairs), 0)
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


class DifferentTestData(BaseTestData):
    """The test data for different descriptions and amounts."""

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
        """The receivable original journal entry #1."""
        self.j_r_or2: JournalEntryData = JournalEntryData(
            30, [JournalEntryCurrencyData(
                "USD", [self.l_r_or2d, self.l_r_or3d],
                [self.l_r_or2c, self.l_r_or3c])])
        """The receivable original journal entry #2"""
        self.j_p_or1: JournalEntryData = JournalEntryData(
            40, [JournalEntryCurrencyData(
                "USD", [self.l_p_or1d, self.l_p_or4d],
                [self.l_p_or1c, self.l_p_or4c])])
        """The payable original journal entry #1."""
        self.j_p_or2: JournalEntryData = JournalEntryData(
            20, [JournalEntryCurrencyData(
                "USD", [self.l_p_or2d, self.l_p_or3d],
                [self.l_p_or2c, self.l_p_or3c])])
        """The payable original journal entry #2."""

        self._add_journal_entry(self.j_r_or1)
        self._add_journal_entry(self.j_r_or2)
        self._add_journal_entry(self.j_p_or1)
        self._add_journal_entry(self.j_p_or2)

        # Receivable offset items
        self.l_r_of1d, self.l_r_of1c = self._couple(
            "Accountant", "500", Accounts.CASH, Accounts.RECEIVABLE)
        self.l_r_of2d, self.l_r_of2c = self._couple(
            "Accountant", "200", Accounts.CASH, Accounts.RECEIVABLE)
        self.l_r_of3d, self.l_r_of3c = self._couple(
            "Accountant", "100", Accounts.CASH, Accounts.RECEIVABLE)
        self.l_r_of4d, self.l_r_of4c = self._couple(
            "Toy", "240", Accounts.CASH, Accounts.RECEIVABLE)
        self.l_r_of5d, self.l_r_of5c = self._couple(
            "Interest", "3.4", Accounts.CASH, Accounts.RECEIVABLE)

        # Payable offset items
        self.l_p_of1d, self.l_p_of1c = self._couple(
            "Airplane", "800", Accounts.PAYABLE, Accounts.CASH)
        self.l_p_of2d, self.l_p_of2c = self._couple(
            "Airplane", "300", Accounts.PAYABLE, Accounts.CASH)
        self.l_p_of3d, self.l_p_of3c = self._couple(
            "Airplane", "100", Accounts.PAYABLE, Accounts.CASH)
        self.l_p_of4d, self.l_p_of4c = self._couple(
            "Phone", "400", Accounts.PAYABLE, Accounts.CASH)
        self.l_p_of5d, self.l_p_of5c = self._couple(
            "Envelop", "0.9", Accounts.PAYABLE, Accounts.CASH)

        # Offset journal entries
        self.j_r_of1: JournalEntryData = JournalEntryData(
            25, [JournalEntryCurrencyData(
                "USD", [self.l_r_of1d], [self.l_r_of1c])])
        """The offset journal entry to the receivable #1."""
        self.j_r_of2: JournalEntryData = JournalEntryData(
            20, [JournalEntryCurrencyData(
                "USD", [self.l_r_of2d, self.l_r_of3d, self.l_r_of4d],
                [self.l_r_of2c, self.l_r_of3c, self.l_r_of4c])])
        """The offset journal entry to the receivable #2."""
        self.j_r_of3: JournalEntryData = JournalEntryData(
            15, [JournalEntryCurrencyData(
                "USD", [self.l_r_of5d], [self.l_r_of5c])])
        """The offset journal entry to the receivable #3."""
        self.j_p_of1: JournalEntryData = JournalEntryData(
            15, [JournalEntryCurrencyData(
                "USD", [self.l_p_of1d], [self.l_p_of1c])])
        """The offset journal entry to the payable #1."""
        self.j_p_of2: JournalEntryData = JournalEntryData(
            10, [JournalEntryCurrencyData(
                "USD", [self.l_p_of2d, self.l_p_of3d, self.l_p_of4d],
                [self.l_p_of2c, self.l_p_of3c, self.l_p_of4c])])
        """The offset journal entry to the payable #2."""
        self.j_p_of3: JournalEntryData = JournalEntryData(
            5, [JournalEntryCurrencyData(
                "USD", [self.l_p_of5d], [self.l_p_of5c])])
        """The offset journal entry to the payable #3."""

        self._add_journal_entry(self.j_r_of1)
        self._add_journal_entry(self.j_r_of2)
        self._add_journal_entry(self.j_r_of3)
        self._add_journal_entry(self.j_p_of1)
        self._add_journal_entry(self.j_p_of2)
        self._add_journal_entry(self.j_p_of3)


class SameTestData(BaseTestData):
    """The test data with same descriptions and amounts."""

    def _init_data(self) -> None:
        # Receivable original line items
        self.l_r_or1d, self.l_r_or1c = self._add_simple_journal_entry(
            60, "USD", "Noodles", "100", Accounts.RECEIVABLE, Accounts.SALES)
        self.l_r_or2d, self.l_r_or2c = self._add_simple_journal_entry(
            50, "USD", "Noodles", "100", Accounts.RECEIVABLE, Accounts.SALES)
        self.l_r_or3d, self.l_r_or3c = self._add_simple_journal_entry(
            40, "USD", "Noodles", "100", Accounts.RECEIVABLE, Accounts.SALES)
        self.l_r_or4d, self.l_r_or4c = self._add_simple_journal_entry(
            30, "USD", "Noodles", "100", Accounts.RECEIVABLE, Accounts.SALES)
        self.l_r_or5d, self.l_r_or5c = self._add_simple_journal_entry(
            20, "USD", "Noodles", "100", Accounts.RECEIVABLE, Accounts.SALES)
        self.l_r_or6d, self.l_r_or6c = self._add_simple_journal_entry(
            10, "USD", "Noodles", "100", Accounts.RECEIVABLE, Accounts.SALES)

        # Payable original line items
        self.l_p_or1d, self.l_p_or1c = self._add_simple_journal_entry(
            60, "USD", "Steak", "120", Accounts.MEAL, Accounts.PAYABLE)
        self.l_p_or2d, self.l_p_or2c = self._add_simple_journal_entry(
            50, "USD", "Steak", "120", Accounts.MEAL, Accounts.PAYABLE)
        self.l_p_or3d, self.l_p_or3c = self._add_simple_journal_entry(
            40, "USD", "Steak", "120", Accounts.MEAL, Accounts.PAYABLE)
        self.l_p_or4d, self.l_p_or4c = self._add_simple_journal_entry(
            30, "USD", "Steak", "120", Accounts.MEAL, Accounts.PAYABLE)
        self.l_p_or5d, self.l_p_or5c = self._add_simple_journal_entry(
            20, "USD", "Steak", "120", Accounts.MEAL, Accounts.PAYABLE)
        self.l_p_or6d, self.l_p_or6c = self._add_simple_journal_entry(
            10, "USD", "Steak", "120", Accounts.MEAL, Accounts.PAYABLE)

        # Receivable offset items
        self.l_r_of1d, self.l_r_of1c = self._add_simple_journal_entry(
            65, "USD", "Noodles", "100", Accounts.CASH, Accounts.RECEIVABLE)
        self.l_r_of2d, self.l_r_of2c = self._add_simple_journal_entry(
            35, "USD", "Noodles", "100", Accounts.CASH, Accounts.RECEIVABLE)
        self.l_r_of3d, self.l_r_of3c = self._couple(
            "Noodles", "100", Accounts.CASH, Accounts.RECEIVABLE)
        self.l_r_of3c.original_line_item = self.l_r_or2d
        j_r_of3: JournalEntryData = JournalEntryData(
            35, [JournalEntryCurrencyData(
                "USD", [self.l_r_of3d], [self.l_r_of3c])])
        self.l_r_of4d, self.l_r_of4c = self._add_simple_journal_entry(
            35, "USD", "Noodles", "100", Accounts.CASH, Accounts.RECEIVABLE)
        self.l_r_of5d, self.l_r_of5c = self._add_simple_journal_entry(
            35, "USD", "Noodles", "100", Accounts.CASH, Accounts.RECEIVABLE)
        self.l_r_of6d, self.l_r_of6c = self._add_simple_journal_entry(
            15, "USD", "Noodles", "100", Accounts.CASH, Accounts.RECEIVABLE)

        # Payable offset items
        self.l_p_of1d, self.l_p_of1c = self._add_simple_journal_entry(
            65, "USD", "Steak", "120", Accounts.PAYABLE, Accounts.CASH)
        self.l_p_of2d, self.l_p_of2c = self._add_simple_journal_entry(
            35, "USD", "Steak", "120", Accounts.PAYABLE, Accounts.CASH)
        self.l_p_of3d, self.l_p_of3c = self._couple(
            "Steak", "120", Accounts.PAYABLE, Accounts.CASH)
        self.l_p_of3d.original_line_item = self.l_p_or2c
        j_p_of3: JournalEntryData = JournalEntryData(
            35, [JournalEntryCurrencyData(
                "USD", [self.l_p_of3d], [self.l_p_of3c])])
        self.l_p_of4d, self.l_p_of4c = self._add_simple_journal_entry(
            35, "USD", "Steak", "120", Accounts.PAYABLE, Accounts.CASH)
        self.l_p_of5d, self.l_p_of5c = self._add_simple_journal_entry(
            35, "USD", "Steak", "120", Accounts.PAYABLE, Accounts.CASH)
        self.l_p_of6d, self.l_p_of6c = self._add_simple_journal_entry(
            15, "USD", "Steak", "120", Accounts.PAYABLE, Accounts.CASH)

        self._add_journal_entry(j_r_of3)
        self._add_journal_entry(j_p_of3)
