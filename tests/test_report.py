# The Mia! Accounting Project.
# Author: imacat@mail.imacat.idv.tw (imacat), 2023/4/9

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
"""The test for the reports.

"""
import datetime as dt
import unittest

import httpx
from flask import Flask

from test_site.lib import BaseTestData
from testlib import create_test_app, get_client, get_csrf_token, Accounts

PREFIX: str = "/accounting"
"""The URL prefix for the reports."""
CSV_MIME: str = "text/csv; charset=utf-8"
"""The MIME type of the downloaded CSV files."""


class ReportTestCase(unittest.TestCase):
    """The report test case."""

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

        self.__client: httpx.Client = get_client(self.__app, "editor")
        """The user client."""
        self.__csrf_token: str = get_csrf_token(self.__client)
        """The CSRF token."""

    def test_nobody(self) -> None:
        """Test the permission as nobody.

        :return: None.
        """
        client: httpx.Client = get_client(self.__app, "nobody")
        ReportTestData(self.__app, "editor").populate()
        response: httpx.Response

        response = client.get(PREFIX)
        self.assertEqual(response.status_code, 403)

        response = client.get(f"{PREFIX}?as=csv")
        self.assertEqual(response.status_code, 403)

        response = client.get(f"{PREFIX}/journal")
        self.assertEqual(response.status_code, 403)

        response = client.get(f"{PREFIX}/journal?as=csv")
        self.assertEqual(response.status_code, 403)

        response = client.get(f"{PREFIX}/ledger")
        self.assertEqual(response.status_code, 403)

        response = client.get(f"{PREFIX}/ledger?as=csv")
        self.assertEqual(response.status_code, 403)

        response = client.get(f"{PREFIX}/income-expenses")
        self.assertEqual(response.status_code, 403)

        response = client.get(f"{PREFIX}/income-expenses?as=csv")
        self.assertEqual(response.status_code, 403)

        response = client.get(f"{PREFIX}/trial-balance")
        self.assertEqual(response.status_code, 403)

        response = client.get(f"{PREFIX}/trial-balance?as=csv")
        self.assertEqual(response.status_code, 403)

        response = client.get(f"{PREFIX}/income-statement")
        self.assertEqual(response.status_code, 403)

        response = client.get(f"{PREFIX}/income-statement?as=csv")
        self.assertEqual(response.status_code, 403)

        response = client.get(f"{PREFIX}/balance-sheet")
        self.assertEqual(response.status_code, 403)

        response = client.get(f"{PREFIX}/balance-sheet?as=csv")
        self.assertEqual(response.status_code, 403)

        response = client.get(f"{PREFIX}/unapplied")
        self.assertEqual(response.status_code, 403)

        response = client.get(f"{PREFIX}/unapplied?as=csv")
        self.assertEqual(response.status_code, 403)

        response = client.get(
            f"{PREFIX}/unapplied/USD/{Accounts.PAYABLE}")
        self.assertEqual(response.status_code, 403)

        response = client.get(
            f"{PREFIX}/unapplied/USD/{Accounts.PAYABLE}?as=csv")
        self.assertEqual(response.status_code, 403)

        response = client.get(f"{PREFIX}/unmatched")
        self.assertEqual(response.status_code, 403)

        response = client.get(f"{PREFIX}/unmatched?as=csv")
        self.assertEqual(response.status_code, 403)

        response = client.get(
            f"{PREFIX}/unmatched/USD/{Accounts.PAYABLE}")
        self.assertEqual(response.status_code, 403)

        response = client.get(
            f"{PREFIX}/unmatched/USD/{Accounts.PAYABLE}?as=csv")
        self.assertEqual(response.status_code, 403)

        response = client.get(f"{PREFIX}/search?q=Salary")
        self.assertEqual(response.status_code, 403)

        response = client.get(f"{PREFIX}/search?q=Salary&as=csv")
        self.assertEqual(response.status_code, 403)

        response = client.get(f"{PREFIX}/search?q=薪水")
        self.assertEqual(response.status_code, 403)

        response = client.get(f"{PREFIX}/search?q=薪水&as=csv")
        self.assertEqual(response.status_code, 403)

    def test_viewer(self) -> None:
        """Test the permission as viewer.

        :return: None.
        """
        client: httpx.Client = get_client(self.__app, "viewer")
        ReportTestData(self.__app, "editor").populate()
        response: httpx.Response

        response = client.get(PREFIX)
        self.assertEqual(response.status_code, 200)

        response = client.get(f"{PREFIX}?as=csv")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], CSV_MIME)

        response = client.get(f"{PREFIX}/journal")
        self.assertEqual(response.status_code, 200)

        response = client.get(f"{PREFIX}/journal?as=csv")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], CSV_MIME)

        response = client.get(f"{PREFIX}/ledger")
        self.assertEqual(response.status_code, 200)

        response = client.get(f"{PREFIX}/ledger?as=csv")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], CSV_MIME)

        response = client.get(f"{PREFIX}/income-expenses")
        self.assertEqual(response.status_code, 200)

        response = client.get(f"{PREFIX}/income-expenses?as=csv")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], CSV_MIME)

        response = client.get(f"{PREFIX}/trial-balance")
        self.assertEqual(response.status_code, 200)

        response = client.get(f"{PREFIX}/trial-balance?as=csv")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], CSV_MIME)

        response = client.get(f"{PREFIX}/income-statement")
        self.assertEqual(response.status_code, 200)

        response = client.get(f"{PREFIX}/income-statement?as=csv")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], CSV_MIME)

        response = client.get(f"{PREFIX}/balance-sheet")
        self.assertEqual(response.status_code, 200)

        response = client.get(f"{PREFIX}/balance-sheet?as=csv")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], CSV_MIME)

        response = client.get(f"{PREFIX}/unapplied")
        self.assertEqual(response.status_code, 200)

        response = client.get(f"{PREFIX}/unapplied?as=csv")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], CSV_MIME)

        response = client.get(
            f"{PREFIX}/unapplied/USD/{Accounts.PAYABLE}")
        self.assertEqual(response.status_code, 200)

        response = client.get(
            f"{PREFIX}/unapplied/USD/{Accounts.PAYABLE}?as=csv")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], CSV_MIME)

        response = client.get(f"{PREFIX}/unmatched")
        self.assertEqual(response.status_code, 403)

        response = client.get(f"{PREFIX}/unmatched?as=csv")
        self.assertEqual(response.status_code, 403)

        response = client.get(
            f"{PREFIX}/unmatched/USD/{Accounts.PAYABLE}")
        self.assertEqual(response.status_code, 403)

        response = client.get(
            f"{PREFIX}/unmatched/USD/{Accounts.PAYABLE}?as=csv")
        self.assertEqual(response.status_code, 403)

        response = client.get(f"{PREFIX}/search?q=Salary")
        self.assertEqual(response.status_code, 200)

        response = client.get(f"{PREFIX}/search?q=Salary&as=csv")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], CSV_MIME)

        response = client.get(f"{PREFIX}/search?q=薪水")
        self.assertEqual(response.status_code, 200)

        response = client.get(f"{PREFIX}/search?q=薪水&as=csv")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], CSV_MIME)

    def test_editor(self) -> None:
        """Test the permission as editor.

        :return: None.
        """
        ReportTestData(self.__app, "editor").populate()
        response: httpx.Response

        response = self.__client.get(PREFIX)
        self.assertEqual(response.status_code, 200)

        response = self.__client.get(f"{PREFIX}?as=csv")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], CSV_MIME)

        response = self.__client.get(f"{PREFIX}/journal")
        self.assertEqual(response.status_code, 200)

        response = self.__client.get(f"{PREFIX}/journal?as=csv")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], CSV_MIME)

        response = self.__client.get(f"{PREFIX}/ledger")
        self.assertEqual(response.status_code, 200)

        response = self.__client.get(f"{PREFIX}/ledger?as=csv")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], CSV_MIME)

        response = self.__client.get(f"{PREFIX}/income-expenses")
        self.assertEqual(response.status_code, 200)

        response = self.__client.get(f"{PREFIX}/income-expenses?as=csv")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], CSV_MIME)

        response = self.__client.get(f"{PREFIX}/trial-balance")
        self.assertEqual(response.status_code, 200)

        response = self.__client.get(f"{PREFIX}/trial-balance?as=csv")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], CSV_MIME)

        response = self.__client.get(f"{PREFIX}/income-statement")
        self.assertEqual(response.status_code, 200)

        response = self.__client.get(f"{PREFIX}/income-statement?as=csv")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], CSV_MIME)

        response = self.__client.get(f"{PREFIX}/balance-sheet")
        self.assertEqual(response.status_code, 200)

        response = self.__client.get(f"{PREFIX}/balance-sheet?as=csv")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], CSV_MIME)

        response = self.__client.get(f"{PREFIX}/unapplied")
        self.assertEqual(response.status_code, 200)

        response = self.__client.get(f"{PREFIX}/unapplied?as=csv")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], CSV_MIME)

        response = self.__client.get(
            f"{PREFIX}/unapplied/USD/{Accounts.PAYABLE}")
        self.assertEqual(response.status_code, 200)

        response = self.__client.get(
            f"{PREFIX}/unapplied/USD/{Accounts.PAYABLE}?as=csv")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], CSV_MIME)

        response = self.__client.get(f"{PREFIX}/unmatched")
        self.assertEqual(response.status_code, 200)

        response = self.__client.get(f"{PREFIX}/unmatched?as=csv")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], CSV_MIME)

        response = self.__client.get(
            f"{PREFIX}/unmatched/USD/{Accounts.PAYABLE}")
        self.assertEqual(response.status_code, 200)

        response = self.__client.get(
            f"{PREFIX}/unmatched/USD/{Accounts.PAYABLE}?as=csv")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], CSV_MIME)

        response = self.__client.get(f"{PREFIX}/search?q=Salary")
        self.assertEqual(response.status_code, 200)

        response = self.__client.get(f"{PREFIX}/search?q=Salary&as=csv")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], CSV_MIME)

        response = self.__client.get(f"{PREFIX}/search?q=薪水")
        self.assertEqual(response.status_code, 200)

        response = self.__client.get(f"{PREFIX}/search?q=薪水&as=csv")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], CSV_MIME)

    def test_empty_db(self) -> None:
        """Tests the empty database.

        :return: None.
        """
        response: httpx.Response

        response = self.__client.get(PREFIX)
        self.assertEqual(response.status_code, 200)

        response = self.__client.get(f"{PREFIX}?as=csv")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], CSV_MIME)

        response = self.__client.get(f"{PREFIX}/journal")
        self.assertEqual(response.status_code, 200)

        response = self.__client.get(f"{PREFIX}/journal?as=csv")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], CSV_MIME)

        response = self.__client.get(f"{PREFIX}/ledger")
        self.assertEqual(response.status_code, 200)

        response = self.__client.get(f"{PREFIX}/ledger?as=csv")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], CSV_MIME)

        response = self.__client.get(f"{PREFIX}/income-expenses")
        self.assertEqual(response.status_code, 200)

        response = self.__client.get(f"{PREFIX}/income-expenses?as=csv")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], CSV_MIME)

        response = self.__client.get(f"{PREFIX}/trial-balance")
        self.assertEqual(response.status_code, 200)

        response = self.__client.get(f"{PREFIX}/trial-balance?as=csv")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], CSV_MIME)

        response = self.__client.get(f"{PREFIX}/income-statement")
        self.assertEqual(response.status_code, 200)

        response = self.__client.get(f"{PREFIX}/income-statement?as=csv")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], CSV_MIME)

        response = self.__client.get(f"{PREFIX}/balance-sheet")
        self.assertEqual(response.status_code, 200)

        response = self.__client.get(f"{PREFIX}/balance-sheet?as=csv")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], CSV_MIME)

        response = self.__client.get(f"{PREFIX}/unapplied")
        self.assertEqual(response.status_code, 200)

        response = self.__client.get(f"{PREFIX}/unapplied?as=csv")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], CSV_MIME)

        response = self.__client.get(
            f"{PREFIX}/unapplied/USD/{Accounts.PAYABLE}")
        self.assertEqual(response.status_code, 200)

        response = self.__client.get(
            f"{PREFIX}/unapplied/USD/{Accounts.PAYABLE}?as=csv")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], CSV_MIME)

        response = self.__client.get(f"{PREFIX}/unmatched")
        self.assertEqual(response.status_code, 200)

        response = self.__client.get(f"{PREFIX}/unmatched?as=csv")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], CSV_MIME)

        response = self.__client.get(
            f"{PREFIX}/unmatched/USD/{Accounts.PAYABLE}")
        self.assertEqual(response.status_code, 200)

        response = self.__client.get(
            f"{PREFIX}/unmatched/USD/{Accounts.PAYABLE}?as=csv")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], CSV_MIME)

        response = self.__client.get(f"{PREFIX}/search?q=Salary")
        self.assertEqual(response.status_code, 200)

        response = self.__client.get(f"{PREFIX}/search?q=Salary&as=csv")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], CSV_MIME)


class ReportTestData(BaseTestData):
    """The report test data."""

    def _init_data(self) -> None:
        today: dt.date = dt.date.today()
        year: int = today.year - 5
        month: int = today.month
        while True:
            date: dt.date = dt.date(year, month, 5)
            if date > today:
                break
            self._add_simple_journal_entry(
                (date - today).days, "USD",
                "Salary薪水", "1200", Accounts.BANK, Accounts.SERVICE)
            month = month + 1
            if month > 12:
                year = year + 1
                month = 1
        self._add_simple_journal_entry(
            1, "USD", "Withdraw領錢", "1000", Accounts.CASH, Accounts.BANK)
        self._add_simple_journal_entry(
            0, "USD", "Dinner晚餐", "40", Accounts.MEAL, Accounts.CASH)
