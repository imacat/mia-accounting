#! env python3
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
"""The sample data generation.

"""
import csv
import typing as t
from datetime import date, timedelta
from pathlib import Path

import click

from testlib import Accounts, create_test_app, JournalEntryLineItemData, \
    JournalEntryCurrencyData, JournalEntryData, \
    BaseTestData


@click.command()
def main() -> None:
    """Creates the sample data and output to a file."""
    data: SampleData = SampleData(create_test_app(), "editor")
    data_dir: Path = Path(__file__).parent / "test_site" / "data"
    data.write_journal_entries(data_dir / "sample-journal_entries.csv")
    data.write_line_items(data_dir / "sample-journal_entry_line_items.csv")


class SampleData(BaseTestData):
    """The sample data."""

    def _init_data(self) -> None:
        self.__add_recurring()
        self.__add_offsets()
        self.__add_meals()

    def __add_recurring(self) -> None:
        """Adds the recurring data.

        :return: None.
        """
        self.__add_usd_recurring()
        self.__add_twd_recurring()

    def __add_usd_recurring(self) -> None:
        """Adds the recurring data in USD.

        :return: None.
        """
        today: date = date.today()
        days: int
        year: int
        month: int

        # Recurring in USD
        j_date: date = date(today.year - 5, today.month, today.day)
        j_date = j_date + timedelta(days=(4 - j_date.weekday()))
        days = (today - j_date).days
        while True:
            if days < 0:
                break
            self.__add_journal_entry(
                days, "USD", "2600",
                Accounts.BANK, "Transfer", Accounts.SERVICE, "Payroll")

            days = days - 1
            if days < 0:
                break
            self.__add_journal_entry(
                days, "USD", "1200",
                Accounts.CASH, None, Accounts.BANK, "Withdraw")
            days = days - 13

        year = today.year - 5
        month = today.month
        while True:
            month = month + 1
            if month > 12:
                year = year + 1
                month = 1
            days = (today - date(year, month, 1)).days
            if days < 0:
                break
            self.__add_journal_entry(
                days, "USD", "1800",
                Accounts.RENT_EXPENSE, "Rent", Accounts.BANK, "Transfer")

    def __add_twd_recurring(self) -> None:
        """Adds the recurring data in TWD.

        :return: None.
        """
        today: date = date.today()

        year: int = today.year - 5
        month: int = today.month
        while True:
            days: int = (today - date(year, month, 5)).days
            if days < 0:
                break
            self.__add_journal_entry(
                days, "TWD", "50000",
                Accounts.BANK, "薪資轉帳", Accounts.SERVICE, "薪水")

            days = days - 1
            if days < 0:
                break
            self.__add_journal_entry(
                days, "TWD", "25000",
                Accounts.CASH, None, Accounts.BANK, "提款")

            days = days - 4
            if days < 0:
                break
            self.__add_journal_entry(
                days, "TWD", "18000",
                Accounts.RENT_EXPENSE, "房租", Accounts.BANK, "轉帳")

            month = month + 1
            if month > 12:
                year = year + 1
                month = 1

    def __add_offsets(self) -> None:
        """Adds the offset data.

        :return: None.
        """
        days: int
        year: int
        month: int
        description: str
        line_item_or: JournalEntryLineItemData
        line_item_of: JournalEntryLineItemData

        # Full offset and unmatched in USD
        description = "Speaking—Institute"
        line_item_or = JournalEntryLineItemData(
            Accounts.RECEIVABLE, description, "120")
        self._add_journal_entry(JournalEntryData(
            40, [JournalEntryCurrencyData(
                "USD", [line_item_or], [JournalEntryLineItemData(
                    Accounts.SERVICE, description, "120")])]))
        line_item_of = JournalEntryLineItemData(
            Accounts.RECEIVABLE, description, "120",
            original_line_item=line_item_or)
        self._add_journal_entry(JournalEntryData(
            5, [JournalEntryCurrencyData(
                "USD", [JournalEntryLineItemData(
                    Accounts.BANK, description, "120")],
                [line_item_of])]))
        self.__add_journal_entry(
            30, "USD", "120",
            Accounts.BANK, description, Accounts.SERVICE, description)

        # Partial offset in USD
        line_item_or = JournalEntryLineItemData(
            Accounts.PAYABLE, "Computer", "1600")
        self._add_journal_entry(JournalEntryData(
            60, [JournalEntryCurrencyData(
                "USD", [JournalEntryLineItemData(
                    Accounts.MACHINERY, "Computer", "1600")],
                [line_item_or])]))
        line_item_of = JournalEntryLineItemData(
            Accounts.PAYABLE, "Computer", "800",
            original_line_item=line_item_or)
        self._add_journal_entry(JournalEntryData(
            35, [JournalEntryCurrencyData(
                "USD", [line_item_of], [JournalEntryLineItemData(
                    Accounts.BANK, "Computer", "800")])]))
        line_item_of = JournalEntryLineItemData(
            Accounts.PAYABLE, "Computer", "400",
            original_line_item=line_item_or)
        self._add_journal_entry(JournalEntryData(
            10, [JournalEntryCurrencyData(
                "USD", [line_item_of], [JournalEntryLineItemData(
                    Accounts.CASH, "Computer", "400")])]))

        # Full offset and unmatched in TWD
        description = "演講費—母校"
        line_item_or = JournalEntryLineItemData(
            Accounts.RECEIVABLE, description, "3000")
        self._add_journal_entry(JournalEntryData(
            45, [JournalEntryCurrencyData(
                "TWD", [line_item_or], [JournalEntryLineItemData(
                    Accounts.SERVICE, description, "3000")])]))
        line_item_of = JournalEntryLineItemData(
            Accounts.RECEIVABLE, description, "3000",
            original_line_item=line_item_or)
        self._add_journal_entry(JournalEntryData(
            6, [JournalEntryCurrencyData(
                "TWD", [JournalEntryLineItemData(
                    Accounts.BANK, description, "3000")],
                [line_item_of])]))
        self.__add_journal_entry(
            25, "TWD", "3000",
            Accounts.BANK, description, Accounts.SERVICE, description)

        # Partial offset in TWD
        line_item_or = JournalEntryLineItemData(
            Accounts.PAYABLE, "手機", "30000")
        self._add_journal_entry(JournalEntryData(
            55, [JournalEntryCurrencyData(
                "TWD", [JournalEntryLineItemData(
                    Accounts.MACHINERY, "手機", "30000")],
                [line_item_or])]))
        line_item_of = JournalEntryLineItemData(
            Accounts.PAYABLE, "手機", "16000",
            original_line_item=line_item_or)
        self._add_journal_entry(JournalEntryData(
            27, [JournalEntryCurrencyData(
                "TWD", [line_item_of], [JournalEntryLineItemData(
                    Accounts.BANK, "手機", "16000")])]))
        line_item_of = JournalEntryLineItemData(
            Accounts.PAYABLE, "手機", "6000",
            original_line_item=line_item_or)
        self._add_journal_entry(JournalEntryData(
            8, [JournalEntryCurrencyData(
                "TWD", [line_item_of], [JournalEntryLineItemData(
                    Accounts.CASH, "手機", "6000")])]))

    def __add_meals(self) -> None:
        """Adds the meal data.

        :return: None.
        """
        days = 60
        while days >= 0:
            # Meals in USD
            if days % 4 == 2:
                self.__add_journal_entry(
                    days, "USD", "2.9",
                    Accounts.MEAL, "Lunch—Coffee", Accounts.CASH, None)
            else:
                self.__add_journal_entry(
                    days, "USD", "3.9",
                    Accounts.MEAL, "Lunch—Coffee", Accounts.CASH, None)

            if days % 15 == 3:
                self.__add_journal_entry(
                    days, "USD", "5.45",
                    Accounts.MEAL, "Dinner—Pizza",
                    Accounts.PAYABLE, "Dinner—Pizza")
            else:
                self.__add_journal_entry(
                    days, "USD", "5.9",
                    Accounts.MEAL, "Dinner—Pasta", Accounts.CASH, None)

            # Meals in TWD
            if days % 5 == 3:
                self.__add_journal_entry(
                    days, "TWD", "125",
                    Accounts.MEAL, "午餐—鄰家咖啡", Accounts.CASH, None)
            else:
                self.__add_journal_entry(
                    days, "TWD", "80",
                    Accounts.MEAL, "午餐—便當", Accounts.CASH, None)

            if days % 15 == 3:
                self.__add_journal_entry(
                    days, "TWD", "320",
                    Accounts.MEAL, "晚餐—牛排", Accounts.PAYABLE, "晚餐—牛排")
            else:
                self.__add_journal_entry(
                    days, "TWD", "100",
                    Accounts.MEAL, "晚餐—自助餐", Accounts.CASH, None)

            days = days - 1

    def __add_journal_entry(
            self, days: int, currency: str, amount: str,
            debit_account: str, debit_description: str | None,
            credit_account: str, credit_description: str | None) -> None:
        """Adds a simple journal entry.

        :param days: The number of days before today.
        :param currency: The currency code.
        :param amount: The amount.
        :param debit_account: The debit account code.
        :param debit_description: The debit description.
        :param credit_account: The credit account code.
        :param credit_description: The credit description.
        :return: None.
        """
        self._add_journal_entry(JournalEntryData(
            days,
            [JournalEntryCurrencyData(
                currency,
                [JournalEntryLineItemData(
                    debit_account, debit_description, amount)],
                [JournalEntryLineItemData(
                    credit_account, credit_description, amount)])]))

    def write_journal_entries(self, file: Path) -> None:
        """Writes the journal entries to the CSV file.

        :param file: The CSV file.
        :return: None.
        """
        today: date = date.today()

        def filter_data(data: dict[str, t.Any]) -> dict[str, t.Any]:
            """Filters the journal entry data for JSON encoding.

            :param data: The journal entry data.
            :return: The journal entry data for JSON encoding.
            """
            data = data.copy()
            data["date"] = (today - data["date"]).days
            del data["created_by_id"]
            del data["updated_by_id"]
            return data

        with open(file, "wt") as fp:
            writer: csv.DictWriter = csv.DictWriter(
                fp, fieldnames=["id", "date", "no", "note"])
            writer.writeheader()
            writer.writerows([filter_data(x) for x in self._journal_entries])

    def write_line_items(self, file: Path) -> None:
        """Writes the journal entries to the CSV file.

        :param file: The CSV file.
        :return: None.
        """
        from accounting import db
        from accounting.models import Account

        def filter_data(data: dict[str, t.Any]) -> dict[str, t.Any]:
            """Filters the journal entry line item data for JSON encoding.

            :param data: The journal entry line item data.
            :return: The journal entry line item data for JSON encoding.
            """
            data = data.copy()
            with self._app.app_context():
                data["account_id"] \
                    = db.session.get(Account, data["account_id"]).code
            if "original_line_item_id" not in data:
                data["original_line_item_id"] = None
            data["is_debit"] = "1" if data["is_debit"] else ""
            return data

        with open(file, "wt") as fp:
            writer: csv.DictWriter = csv.DictWriter(
                fp, fieldnames=["id", "journal_entry_id",
                                "original_line_item_id", "is_debit", "no",
                                "account_id", "currency_code", "description",
                                "amount"])
            writer.writeheader()
            writer.writerows([filter_data(x) for x in self._line_items])


if __name__ == "__main__":
    main()
