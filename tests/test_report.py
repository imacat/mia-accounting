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
import unittest

import httpx
from click.testing import Result
from flask import Flask
from flask.testing import FlaskCliRunner

from testlib import create_test_app, get_client, Accounts
from testlib_offset import TestData

PREFIX: str = "/accounting"
"""The URL prefix for the reports."""


class ReportTestCase(unittest.TestCase):
    """The report test case."""

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
        TestData(self.app, self.client, self.csrf_token)
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

        response = client.get(f"{PREFIX}/unapplied/{Accounts.PAYABLE}")
        self.assertEqual(response.status_code, 403)

        response = client.get(f"{PREFIX}/unapplied/{Accounts.PAYABLE}?as=csv")
        self.assertEqual(response.status_code, 403)

    def test_viewer(self) -> None:
        """Test the permission as viewer.

        :return: None.
        """
        client, csrf_token = get_client(self.app, "viewer")
        TestData(self.app, self.client, self.csrf_token)
        response: httpx.Response

        response = client.get(PREFIX)
        self.assertEqual(response.status_code, 200)

        response = client.get(f"{PREFIX}?as=csv")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"],
                         "text/csv; charset=utf-8")

        response = client.get(f"{PREFIX}/journal")
        self.assertEqual(response.status_code, 200)

        response = client.get(f"{PREFIX}/journal?as=csv")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"],
                         "text/csv; charset=utf-8")

        response = client.get(f"{PREFIX}/ledger")
        self.assertEqual(response.status_code, 200)

        response = client.get(f"{PREFIX}/ledger?as=csv")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"],
                         "text/csv; charset=utf-8")

        response = client.get(f"{PREFIX}/income-expenses")
        self.assertEqual(response.status_code, 200)

        response = client.get(f"{PREFIX}/income-expenses?as=csv")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"],
                         "text/csv; charset=utf-8")

        response = client.get(f"{PREFIX}/trial-balance")
        self.assertEqual(response.status_code, 200)

        response = client.get(f"{PREFIX}/trial-balance?as=csv")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"],
                         "text/csv; charset=utf-8")

        response = client.get(f"{PREFIX}/income-statement")
        self.assertEqual(response.status_code, 200)

        response = client.get(f"{PREFIX}/income-statement?as=csv")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"],
                         "text/csv; charset=utf-8")

        response = client.get(f"{PREFIX}/balance-sheet")
        self.assertEqual(response.status_code, 200)

        response = client.get(f"{PREFIX}/balance-sheet?as=csv")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"],
                         "text/csv; charset=utf-8")

        response = client.get(f"{PREFIX}/unapplied")
        self.assertEqual(response.status_code, 200)

        response = client.get(f"{PREFIX}/unapplied?as=csv")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"],
                         "text/csv; charset=utf-8")

        response = client.get(f"{PREFIX}/unapplied/{Accounts.PAYABLE}")
        self.assertEqual(response.status_code, 200)

        response = client.get(f"{PREFIX}/unapplied/{Accounts.PAYABLE}?as=csv")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"],
                         "text/csv; charset=utf-8")

    def test_editor(self) -> None:
        """Test the permission as editor.

        :return: None.
        """
        TestData(self.app, self.client, self.csrf_token)
        response: httpx.Response

        response = self.client.get(PREFIX)
        self.assertEqual(response.status_code, 200)

        response = self.client.get(f"{PREFIX}?as=csv")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"],
                         "text/csv; charset=utf-8")

        response = self.client.get(f"{PREFIX}/journal")
        self.assertEqual(response.status_code, 200)

        response = self.client.get(f"{PREFIX}/journal?as=csv")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"],
                         "text/csv; charset=utf-8")

        response = self.client.get(f"{PREFIX}/ledger")
        self.assertEqual(response.status_code, 200)

        response = self.client.get(f"{PREFIX}/ledger?as=csv")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"],
                         "text/csv; charset=utf-8")

        response = self.client.get(f"{PREFIX}/income-expenses")
        self.assertEqual(response.status_code, 200)

        response = self.client.get(f"{PREFIX}/income-expenses?as=csv")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"],
                         "text/csv; charset=utf-8")

        response = self.client.get(f"{PREFIX}/trial-balance")
        self.assertEqual(response.status_code, 200)

        response = self.client.get(f"{PREFIX}/trial-balance?as=csv")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"],
                         "text/csv; charset=utf-8")

        response = self.client.get(f"{PREFIX}/income-statement")
        self.assertEqual(response.status_code, 200)

        response = self.client.get(f"{PREFIX}/income-statement?as=csv")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"],
                         "text/csv; charset=utf-8")

        response = self.client.get(f"{PREFIX}/balance-sheet")
        self.assertEqual(response.status_code, 200)

        response = self.client.get(f"{PREFIX}/balance-sheet?as=csv")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"],
                         "text/csv; charset=utf-8")

        response = self.client.get(f"{PREFIX}/unapplied")
        self.assertEqual(response.status_code, 200)

        response = self.client.get(f"{PREFIX}/unapplied?as=csv")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"],
                         "text/csv; charset=utf-8")

        response = self.client.get(f"{PREFIX}/unapplied/{Accounts.PAYABLE}")
        self.assertEqual(response.status_code, 200)

        response = self.client.get(
            f"{PREFIX}/unapplied/{Accounts.PAYABLE}?as=csv")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"],
                         "text/csv; charset=utf-8")

    def test_empty_db(self) -> None:
        """Tests the empty database.

        :return: None.
        """
        response: httpx.Response

        response = self.client.get(PREFIX)
        self.assertEqual(response.status_code, 200)

        response = self.client.get(f"{PREFIX}?as=csv")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"],
                         "text/csv; charset=utf-8")

        response = self.client.get(f"{PREFIX}/journal")
        self.assertEqual(response.status_code, 200)

        response = self.client.get(f"{PREFIX}/journal?as=csv")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"],
                         "text/csv; charset=utf-8")

        response = self.client.get(f"{PREFIX}/ledger")
        self.assertEqual(response.status_code, 200)

        response = self.client.get(f"{PREFIX}/ledger?as=csv")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"],
                         "text/csv; charset=utf-8")

        response = self.client.get(f"{PREFIX}/income-expenses")
        self.assertEqual(response.status_code, 200)

        response = self.client.get(f"{PREFIX}/income-expenses?as=csv")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"],
                         "text/csv; charset=utf-8")

        response = self.client.get(f"{PREFIX}/trial-balance")
        self.assertEqual(response.status_code, 200)

        response = self.client.get(f"{PREFIX}/trial-balance?as=csv")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"],
                         "text/csv; charset=utf-8")

        response = self.client.get(f"{PREFIX}/income-statement")
        self.assertEqual(response.status_code, 200)

        response = self.client.get(f"{PREFIX}/income-statement?as=csv")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"],
                         "text/csv; charset=utf-8")

        response = self.client.get(f"{PREFIX}/balance-sheet")
        self.assertEqual(response.status_code, 200)

        response = self.client.get(f"{PREFIX}/balance-sheet?as=csv")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"],
                         "text/csv; charset=utf-8")

        response = self.client.get(f"{PREFIX}/unapplied")
        self.assertEqual(response.status_code, 200)

        response = self.client.get(f"{PREFIX}/unapplied?as=csv")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"],
                         "text/csv; charset=utf-8")

        response = self.client.get(f"{PREFIX}/unapplied/{Accounts.PAYABLE}")
        self.assertEqual(response.status_code, 200)

        response = self.client.get(
            f"{PREFIX}/unapplied/{Accounts.PAYABLE}?as=csv")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"],
                         "text/csv; charset=utf-8")
