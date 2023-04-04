# The Mia! Accounting Project.
# Author: imacat@mail.imacat.idv.tw (imacat), 2023/2/28

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
"""The test for the description editor.

"""
import unittest
from datetime import date

from click.testing import Result
from flask import Flask
from flask.testing import FlaskCliRunner

from testlib import NEXT_URI, Accounts, create_test_app, get_client
from testlib_journal_entry import add_journal_entry


class DescriptionEditorTestCase(unittest.TestCase):
    """The description editor test case."""

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

    def test_description_editor(self) -> None:
        """Test the description editor.

        :return: None.
        """
        from accounting.journal_entry.utils.description_editor import \
            DescriptionEditor
        for form in get_form_data(self.csrf_token):
            add_journal_entry(self.client, form)
        with self.app.app_context():
            editor: DescriptionEditor = DescriptionEditor()

        # Debit-General
        self.assertEqual(len(editor.debit.general.tags), 2)
        self.assertEqual(editor.debit.general.tags[0].name, "Lunch")
        self.assertEqual(len(editor.debit.general.tags[0].accounts), 2)
        self.assertEqual(editor.debit.general.tags[0].accounts[0].code,
                         Accounts.MEAL)
        self.assertEqual(editor.debit.general.tags[0].accounts[1].code,
                         Accounts.PETTY_CASH)
        self.assertEqual(editor.debit.general.tags[1].name, "Dinner")
        self.assertEqual(len(editor.debit.general.tags[1].accounts), 2)
        self.assertEqual(editor.debit.general.tags[1].accounts[0].code,
                         Accounts.MEAL)
        self.assertEqual(editor.debit.general.tags[1].accounts[1].code,
                         Accounts.PETTY_CASH)

        # Debit-Travel
        self.assertEqual(len(editor.debit.travel.tags), 3)
        self.assertEqual(editor.debit.travel.tags[0].name, "Bike")
        self.assertEqual(len(editor.debit.travel.tags[0].accounts), 1)
        self.assertEqual(editor.debit.travel.tags[0].accounts[0].code,
                         Accounts.TRAVEL)
        self.assertEqual(editor.debit.travel.tags[1].name, "Taxi")
        self.assertEqual(len(editor.debit.travel.tags[1].accounts), 1)
        self.assertEqual(editor.debit.travel.tags[1].accounts[0].code,
                         Accounts.TRAVEL)
        self.assertEqual(editor.debit.travel.tags[2].name, "Airplane")
        self.assertEqual(len(editor.debit.travel.tags[2].accounts), 1)
        self.assertEqual(editor.debit.travel.tags[2].accounts[0].code,
                         Accounts.TRAVEL)

        # Debit-Bus
        self.assertEqual(len(editor.debit.bus.tags), 2)
        self.assertEqual(editor.debit.bus.tags[0].name, "Train")
        self.assertEqual(len(editor.debit.bus.tags[0].accounts), 1)
        self.assertEqual(editor.debit.bus.tags[0].accounts[0].code,
                         Accounts.TRAVEL)
        self.assertEqual(editor.debit.bus.tags[1].name, "Bus")
        self.assertEqual(len(editor.debit.bus.tags[1].accounts), 1)
        self.assertEqual(editor.debit.bus.tags[1].accounts[0].code,
                         Accounts.TRAVEL)

        # Credit-General
        self.assertEqual(len(editor.credit.general.tags), 2)
        self.assertEqual(editor.credit.general.tags[0].name, "Lunch")
        self.assertEqual(len(editor.credit.general.tags[0].accounts), 3)
        self.assertEqual(editor.credit.general.tags[0].accounts[0].code,
                         Accounts.PETTY_CASH)
        self.assertEqual(editor.credit.general.tags[0].accounts[1].code,
                         Accounts.BANK)
        self.assertEqual(editor.credit.general.tags[0].accounts[2].code,
                         Accounts.CASH)
        self.assertEqual(editor.credit.general.tags[1].name, "Dinner")
        self.assertEqual(len(editor.credit.general.tags[1].accounts), 2)
        self.assertEqual(editor.credit.general.tags[1].accounts[0].code,
                         Accounts.BANK)
        self.assertEqual(editor.credit.general.tags[1].accounts[1].code,
                         Accounts.PETTY_CASH)

        # Credit-Travel
        self.assertEqual(len(editor.credit.travel.tags), 2)
        self.assertEqual(editor.credit.travel.tags[0].name, "Bike")
        self.assertEqual(len(editor.credit.travel.tags[0].accounts), 2)
        self.assertEqual(editor.credit.travel.tags[0].accounts[0].code,
                         Accounts.PETTY_CASH)
        self.assertEqual(editor.credit.travel.tags[0].accounts[1].code,
                         Accounts.PREPAID)
        self.assertEqual(editor.credit.travel.tags[1].name, "Taxi")
        self.assertEqual(len(editor.credit.travel.tags[1].accounts), 2)
        self.assertEqual(editor.credit.travel.tags[1].accounts[0].code,
                         Accounts.PETTY_CASH)
        self.assertEqual(editor.credit.travel.tags[1].accounts[1].code,
                         Accounts.CASH)

        # Credit-Bus
        self.assertEqual(len(editor.credit.bus.tags), 2)
        self.assertEqual(editor.credit.bus.tags[0].name, "Train")
        self.assertEqual(len(editor.credit.bus.tags[0].accounts), 2)
        self.assertEqual(editor.credit.bus.tags[0].accounts[0].code,
                         Accounts.PREPAID)
        self.assertEqual(editor.credit.bus.tags[0].accounts[1].code,
                         Accounts.PETTY_CASH)
        self.assertEqual(editor.credit.bus.tags[1].name, "Bus")
        self.assertEqual(len(editor.credit.bus.tags[1].accounts), 1)
        self.assertEqual(editor.credit.bus.tags[1].accounts[0].code,
                         Accounts.PREPAID)


def get_form_data(csrf_token: str) -> list[dict[str, str]]:
    """Returns the form data for multiple journal entry forms.

    :param csrf_token: The CSRF token.
    :return: A list of the form data.
    """
    journal_entry_date: str = date.today().isoformat()
    return [{"csrf_token": csrf_token,
             "next": NEXT_URI,
             "date": journal_entry_date,
             "currency-0-code": "USD",
             "currency-0-credit-0-account_code": Accounts.SERVICE,
             "currency-0-credit-0-description": " Salary ",
             "currency-0-credit-0-amount": "2500"},
            {"csrf_token": csrf_token,
             "next": NEXT_URI,
             "date": journal_entry_date,
             "currency-0-code": "USD",
             "currency-0-debit-0-account_code": Accounts.MEAL,
             "currency-0-debit-0-description": " Lunch—Fish ",
             "currency-0-debit-0-amount": "4.7",
             "currency-0-credit-0-account_code": Accounts.BANK,
             "currency-0-credit-0-description": " Lunch—Fish ",
             "currency-0-credit-0-amount": "4.7",
             "currency-0-debit-1-account_code": Accounts.MEAL,
             "currency-0-debit-1-description": " Lunch—Fries ",
             "currency-0-debit-1-amount": "2.15",
             "currency-0-credit-1-account_code": Accounts.PETTY_CASH,
             "currency-0-credit-1-description": " Lunch—Fries ",
             "currency-0-credit-1-amount": "2.15",
             "currency-0-debit-2-account_code": Accounts.MEAL,
             "currency-0-debit-2-description": " Dinner—Hamburger ",
             "currency-0-debit-2-amount": "4.25",
             "currency-0-credit-2-account_code": Accounts.BANK,
             "currency-0-credit-2-description": " Dinner—Hamburger ",
             "currency-0-credit-2-amount": "4.25"},
            {"csrf_token": csrf_token,
             "next": NEXT_URI,
             "date": journal_entry_date,
             "currency-0-code": "USD",
             "currency-0-debit-0-account_code": Accounts.MEAL,
             "currency-0-debit-0-description": " Lunch—Salad ",
             "currency-0-debit-0-amount": "4.99",
             "currency-0-credit-0-account_code": Accounts.CASH,
             "currency-0-credit-0-description": " Lunch—Salad ",
             "currency-0-credit-0-amount": "4.99",
             "currency-0-debit-1-account_code": Accounts.MEAL,
             "currency-0-debit-1-description": " Dinner—Steak  ",
             "currency-0-debit-1-amount": "8.28",
             "currency-0-credit-1-account_code": Accounts.PETTY_CASH,
             "currency-0-credit-1-description": " Dinner—Steak ",
             "currency-0-credit-1-amount": "8.28"},
            {"csrf_token": csrf_token,
             "next": NEXT_URI,
             "date": journal_entry_date,
             "currency-0-code": "USD",
             "currency-0-debit-0-account_code": Accounts.MEAL,
             "currency-0-debit-0-description": " Lunch—Pizza  ",
             "currency-0-debit-0-amount": "5.49",
             "currency-0-credit-0-account_code": Accounts.PETTY_CASH,
             "currency-0-credit-0-description": " Lunch—Pizza ",
             "currency-0-credit-0-amount": "5.49",
             "currency-0-debit-1-account_code": Accounts.MEAL,
             "currency-0-debit-1-description": " Lunch—Noodles ",
             "currency-0-debit-1-amount": "7.47",
             "currency-0-credit-1-account_code": Accounts.PETTY_CASH,
             "currency-0-credit-1-description": " Lunch—Noodles ",
             "currency-0-credit-1-amount": "7.47"},
            {"csrf_token": csrf_token,
             "next": NEXT_URI,
             "date": journal_entry_date,
             "currency-0-code": "USD",
             "currency-0-debit-0-account_code": Accounts.TRAVEL,
             "currency-0-debit-0-description": " Airplane—Lake City↔Hill Town",
             "currency-0-debit-0-amount": "800"},
            {"csrf_token": csrf_token,
             "next": NEXT_URI,
             "date": journal_entry_date,
             "currency-0-code": "USD",
             "currency-0-debit-0-account_code": Accounts.TRAVEL,
             "currency-0-debit-0-description": " Bus—323—Downtown→Museum ",
             "currency-0-debit-0-amount": "2.5",
             "currency-0-credit-0-account_code": Accounts.PREPAID,
             "currency-0-credit-0-description": " Bus—323—Downtown→Museum ",
             "currency-0-credit-0-amount": "2.5",
             "currency-0-debit-1-account_code": Accounts.TRAVEL,
             "currency-0-debit-1-description": " Train—Blue—Museum→Central ",
             "currency-0-debit-1-amount": "3.2",
             "currency-0-credit-1-account_code": Accounts.PREPAID,
             "currency-0-credit-1-description": " Train—Blue—Museum→Central ",
             "currency-0-credit-1-amount": "3.2",
             "currency-0-debit-2-account_code": Accounts.TRAVEL,
             "currency-0-debit-2-description": " Train—Green—Central→Mall ",
             "currency-0-debit-2-amount": "3.2",
             "currency-0-credit-2-account_code": Accounts.PREPAID,
             "currency-0-credit-2-description": " Train—Green—Central→Mall ",
             "currency-0-credit-2-amount": "3.2",
             "currency-0-debit-3-account_code": Accounts.TRAVEL,
             "currency-0-debit-3-description": " Train—Red—Mall→Museum ",
             "currency-0-debit-3-amount": "4.4",
             "currency-0-credit-3-account_code": Accounts.PETTY_CASH,
             "currency-0-credit-3-description": " Train—Red—Mall→Museum ",
             "currency-0-credit-3-amount": "4.4"},
            {"csrf_token": csrf_token,
             "next": NEXT_URI,
             "date": journal_entry_date,
             "currency-0-code": "USD",
             "currency-0-debit-0-account_code": Accounts.TRAVEL,
             "currency-0-debit-0-description": " Taxi—Museum→Office ",
             "currency-0-debit-0-amount": "15.5",
             "currency-0-credit-0-account_code": Accounts.CASH,
             "currency-0-credit-0-description": " Taxi—Museum→Office ",
             "currency-0-credit-0-amount": "15.5",
             "currency-0-debit-1-account_code": Accounts.TRAVEL,
             "currency-0-debit-1-description": " Taxi—Office→Restaurant ",
             "currency-0-debit-1-amount": "12",
             "currency-0-credit-1-account_code": Accounts.PETTY_CASH,
             "currency-0-credit-1-description": " Taxi—Office→Restaurant ",
             "currency-0-credit-1-amount": "12",
             "currency-0-debit-2-account_code": Accounts.TRAVEL,
             "currency-0-debit-2-description": " Taxi—Restaurant→City Hall ",
             "currency-0-debit-2-amount": "8",
             "currency-0-credit-2-account_code": Accounts.PETTY_CASH,
             "currency-0-credit-2-description": " Taxi—Restaurant→City Hall ",
             "currency-0-credit-2-amount": "8",
             "currency-0-debit-3-account_code": Accounts.TRAVEL,
             "currency-0-debit-3-description": " Bike—City Hall→Office ",
             "currency-0-debit-3-amount": "3.5",
             "currency-0-credit-3-account_code": Accounts.PETTY_CASH,
             "currency-0-credit-3-description": " Bike—City Hall→Office ",
             "currency-0-credit-3-amount": "3.5",
             "currency-0-debit-4-account_code": Accounts.TRAVEL,
             "currency-0-debit-4-description": " Bike—Restaurant→Office ",
             "currency-0-debit-4-amount": "4",
             "currency-0-credit-4-account_code": Accounts.PETTY_CASH,
             "currency-0-credit-4-description": " Bike—Restaurant→Office ",
             "currency-0-credit-4-amount": "4",
             "currency-0-debit-5-account_code": Accounts.TRAVEL,
             "currency-0-debit-5-description": " Bike—Office→Theatre ",
             "currency-0-debit-5-amount": "1.5",
             "currency-0-credit-5-account_code": Accounts.PETTY_CASH,
             "currency-0-credit-5-description": " Bike—Office→Theatre ",
             "currency-0-credit-5-amount": "1.5",
             "currency-0-debit-6-account_code": Accounts.TRAVEL,
             "currency-0-debit-6-description": " Bike—Theatre→Home ",
             "currency-0-debit-6-amount": "5.5",
             "currency-0-credit-6-account_code": Accounts.PREPAID,
             "currency-0-credit-6-description": " Bike—Theatre→Home ",
             "currency-0-credit-6-amount": "5.5"},
            {"csrf_token": csrf_token,
             "next": NEXT_URI,
             "date": journal_entry_date,
             "currency-0-code": "USD",
             "currency-0-debit-0-account_code": Accounts.PETTY_CASH,
             "currency-0-debit-0-description": " Dinner—Steak  ",
             "currency-0-debit-0-amount": "8.28",
             "currency-0-credit-0-account_code": Accounts.BANK,
             "currency-0-credit-0-description": " Dinner—Steak ",
             "currency-0-credit-0-amount": "8.28",
             "currency-0-debit-1-account_code": Accounts.PETTY_CASH,
             "currency-0-debit-1-description": " Lunch—Pizza ",
             "currency-0-debit-1-amount": "5.49",
             "currency-0-credit-1-account_code": Accounts.BANK,
             "currency-0-credit-1-description": " Lunch—Pizza  ",
             "currency-0-credit-1-amount": "5.49"}]
