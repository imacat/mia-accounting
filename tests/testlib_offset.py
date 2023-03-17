# The Mia! Accounting Flask Project.
# Author: imacat@mail.imacat.idv.tw (imacat), 2023/2/27

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
"""The common test libraries for the offset test cases.

"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import httpx
from flask import Flask

from test_site import db
from testlib_txn import Accounts, match_txn_detail, NEXT_URI


class JournalEntryData:
    """The journal entry data."""

    def __init__(self, account: str, summary: str, amount: str,
                 original_entry: JournalEntryData | None = None):
        """Constructs the journal entry data.

        :param account: The account code.
        :param summary: The summary.
        :param amount: The amount.
        :param original_entry: The original entry.
        """
        self.txn: TransactionData | None = None
        self.id: int = -1
        self.no: int = -1
        self.original_entry: JournalEntryData | None = original_entry
        self.account: str = account
        self.summary: str = summary
        self.amount: Decimal = Decimal(amount)

    def form(self, prefix: str, entry_type: str, index: int, is_update: bool) \
            -> dict[str, str]:
        """Returns the journal entry as form data.

        :param prefix: The prefix of the form fields.
        :param entry_type: The entry type, either "debit" or "credit".
        :param index: The entry index.
        :param is_update: True for an update operation, or False otherwise
        :return: The form data.
        """
        prefix = f"{prefix}-{entry_type}-{index}"
        form: dict[str, str] = {f"{prefix}-account_code": self.account,
                                f"{prefix}-summary": self.summary,
                                f"{prefix}-amount": str(self.amount)}
        if is_update and self.id != -1:
            form[f"{prefix}-eid"] = str(self.id)
        form[f"{prefix}-no"] = str(index) if self.no == -1 else str(self.no)
        if self.original_entry is not None:
            assert self.original_entry.id != -1
            form[f"{prefix}-original_entry_id"] = str(self.original_entry.id)
        return form


class CurrencyData:
    """The transaction currency data."""

    def __init__(self, currency: str, debit: list[JournalEntryData],
                 credit: list[JournalEntryData]):
        """Constructs the transaction currency data.

        :param currency: The currency code.
        :param debit: The debit journal entries.
        :param credit: The credit journal entries.
        """
        self.code: str = currency
        self.debit: list[JournalEntryData] = debit
        self.credit: list[JournalEntryData] = credit

    def form(self, index: int, is_update: bool) -> dict[str, str]:
        """Returns the currency as form data.

        :param index: The currency index.
        :param is_update: True for an update operation, or False otherwise
        :return: The form data.
        """
        prefix: str = f"currency-{index}"
        form: dict[str, str] = {f"{prefix}-code": self.code}
        for i in range(len(self.debit)):
            form.update(self.debit[i].form(prefix, "debit", i + 1, is_update))
        for i in range(len(self.credit)):
            form.update(self.credit[i].form(prefix, "credit", i + 1,
                                            is_update))
        return form


class TransactionData:
    """The transaction data."""

    def __init__(self, days: int, currencies: list[CurrencyData]):
        """Constructs a transaction.

        :param days: The number of days before today.
        :param currencies: The transaction currency data.
        """
        self.id: int = -1
        self.days: int = days
        self.currencies: list[CurrencyData] = currencies
        self.note: str | None = None
        for currency in self.currencies:
            for entry in currency.debit:
                entry.txn = self
            for entry in currency.credit:
                entry.txn = self

    def new_form(self, csrf_token: str) -> dict[str, str]:
        """Returns the transaction as a form.

        :param csrf_token: The CSRF token.
        :return: The transaction as a form.
        """
        return self.__form(csrf_token, is_update=False)

    def update_form(self, csrf_token: str) -> dict[str, str]:
        """Returns the transaction as a form.

        :param csrf_token: The CSRF token.
        :return: The transaction as a form.
        """
        return self.__form(csrf_token, is_update=True)

    def __form(self, csrf_token: str, is_update: bool = False) \
            -> dict[str, str]:
        """Returns the transaction as a form.

        :param csrf_token: The CSRF token.
        :param is_update: True for an update operation, or False otherwise
        :return: The transaction as a form.
        """
        txn_date: date = date.today() - timedelta(days=self.days)
        form: dict[str, str] = {"csrf_token": csrf_token,
                                "next": NEXT_URI,
                                "date": txn_date.isoformat()}
        for i in range(len(self.currencies)):
            form.update(self.currencies[i].form(i + 1, is_update))
        if self.note is not None:
            form["note"] = self.note
        return form


class TestData:
    """The test data."""

    def __init__(self, app: Flask, client: httpx.Client, csrf_token: str):
        """Constructs the test data.

        :param app: The Flask application.
        :param client: The client.
        :param csrf_token: The CSRF token.
        """
        self.app: Flask = app
        self.client: httpx.Client = client
        self.csrf_token: str = csrf_token

        def couple(summary: str, amount: str, debit: str, credit: str) \
                -> tuple[JournalEntryData, JournalEntryData]:
            """Returns a couple of debit-credit journal entries.

            :param summary: The summary.
            :param amount: The amount.
            :param debit: The debit account code.
            :param credit: The credit account code.
            :return: The debit journal entry and credit journal entry.
            """
            return JournalEntryData(debit, summary, amount),\
                JournalEntryData(credit, summary, amount)

        # Receivable original entries
        self.e_r_or1d, self.e_r_or1c = couple(
            "Accountant", "1200", Accounts.RECEIVABLE, Accounts.SERVICE)
        self.e_r_or2d, self.e_r_or2c = couple(
            "Toy", "600", Accounts.RECEIVABLE, Accounts.SALES)
        self.e_r_or3d, self.e_r_or3c = couple(
            "Noodles", "100", Accounts.RECEIVABLE, Accounts.SALES)
        self.e_r_or4d, self.e_r_or4c = couple(
            "Interest", "3.4", Accounts.RECEIVABLE, Accounts.INTEREST)

        # Payable original entries
        self.e_p_or1d, self.e_p_or1c = couple(
            "Airplane ticket", "2000", Accounts.TRAVEL, Accounts.PAYABLE)
        self.e_p_or2d, self.e_p_or2c = couple(
            "Phone", "900", Accounts.OFFICE, Accounts.PAYABLE)
        self.e_p_or3d, self.e_p_or3c = couple(
            "Steak", "120", Accounts.MEAL, Accounts.PAYABLE)
        self.e_p_or4d, self.e_p_or4c = couple(
            "Envelop", "0.9", Accounts.OFFICE, Accounts.PAYABLE)

        # Original transactions
        self.t_r_or1: TransactionData = TransactionData(
            50, [CurrencyData("USD", [self.e_r_or1d, self.e_r_or4d],
                              [self.e_r_or1c, self.e_r_or4c])])
        self.t_r_or2: TransactionData = TransactionData(
            30, [CurrencyData("USD", [self.e_r_or2d, self.e_r_or3d],
                              [self.e_r_or2c, self.e_r_or3c])])
        self.t_p_or1: TransactionData = TransactionData(
            40, [CurrencyData("USD", [self.e_p_or1d, self.e_p_or4d],
                              [self.e_p_or1c, self.e_p_or4c])])
        self.t_p_or2: TransactionData = TransactionData(
            20, [CurrencyData("USD", [self.e_p_or2d, self.e_p_or3d],
                              [self.e_p_or2c, self.e_p_or3c])])

        self.__add_txn(self.t_r_or1)
        self.__add_txn(self.t_r_or2)
        self.__add_txn(self.t_p_or1)
        self.__add_txn(self.t_p_or2)

        # Receivable offset entries
        self.e_r_of1d, self.e_r_of1c = couple(
            "Accountant", "500", Accounts.CASH, Accounts.RECEIVABLE)
        self.e_r_of1c.original_entry = self.e_r_or1d
        self.e_r_of2d, self.e_r_of2c = couple(
            "Accountant", "200", Accounts.CASH, Accounts.RECEIVABLE)
        self.e_r_of2c.original_entry = self.e_r_or1d
        self.e_r_of3d, self.e_r_of3c = couple(
            "Accountant", "100", Accounts.CASH, Accounts.RECEIVABLE)
        self.e_r_of3c.original_entry = self.e_r_or1d
        self.e_r_of4d, self.e_r_of4c = couple(
            "Toy", "240", Accounts.CASH, Accounts.RECEIVABLE)
        self.e_r_of4c.original_entry = self.e_r_or2d
        self.e_r_of5d, self.e_r_of5c = couple(
            "Interest", "3.4", Accounts.CASH, Accounts.RECEIVABLE)
        self.e_r_of5c.original_entry = self.e_r_or4d

        # Payable offset entries
        self.e_p_of1d, self.e_p_of1c = couple(
            "Airplane ticket", "800", Accounts.PAYABLE, Accounts.CASH)
        self.e_p_of1d.original_entry = self.e_p_or1c
        self.e_p_of2d, self.e_p_of2c = couple(
            "Airplane ticket", "300", Accounts.PAYABLE, Accounts.CASH)
        self.e_p_of2d.original_entry = self.e_p_or1c
        self.e_p_of3d, self.e_p_of3c = couple(
            "Airplane ticket", "100", Accounts.PAYABLE, Accounts.CASH)
        self.e_p_of3d.original_entry = self.e_p_or1c
        self.e_p_of4d, self.e_p_of4c = couple(
            "Phone", "400", Accounts.PAYABLE, Accounts.CASH)
        self.e_p_of4d.original_entry = self.e_p_or2c
        self.e_p_of5d, self.e_p_of5c = couple(
            "Envelop", "0.9", Accounts.PAYABLE, Accounts.CASH)
        self.e_p_of5d.original_entry = self.e_p_or4c

        # Offset transactions
        self.t_r_of1: TransactionData = TransactionData(
            25, [CurrencyData("USD", [self.e_r_of1d], [self.e_r_of1c])])
        self.t_r_of2: TransactionData = TransactionData(
            20, [CurrencyData("USD",
                              [self.e_r_of2d, self.e_r_of3d, self.e_r_of4d],
                              [self.e_r_of2c, self.e_r_of3c, self.e_r_of4c])])
        self.t_r_of3: TransactionData = TransactionData(
            15, [CurrencyData("USD", [self.e_r_of5d], [self.e_r_of5c])])
        self.t_p_of1: TransactionData = TransactionData(
            15, [CurrencyData("USD", [self.e_p_of1d], [self.e_p_of1c])])
        self.t_p_of2: TransactionData = TransactionData(
            10, [CurrencyData("USD",
                              [self.e_p_of2d, self.e_p_of3d, self.e_p_of4d],
                              [self.e_p_of2c, self.e_p_of3c, self.e_p_of4c])])
        self.t_p_of3: TransactionData = TransactionData(
            5, [CurrencyData("USD", [self.e_p_of5d], [self.e_p_of5c])])

        self.__add_txn(self.t_r_of1)
        self.__add_txn(self.t_r_of2)
        self.__add_txn(self.t_r_of3)
        self.__add_txn(self.t_p_of1)
        self.__add_txn(self.t_p_of2)
        self.__add_txn(self.t_p_of3)

    def __add_txn(self, txn_data: TransactionData) -> None:
        """Adds a transaction.

        :param txn_data: The transaction data.
        :return: None.
        """
        from accounting.models import Transaction
        store_uri: str = "/accounting/transactions/store/transfer"

        response: httpx.Response = self.client.post(
            store_uri, data=txn_data.new_form(self.csrf_token))
        assert response.status_code == 302
        txn_id: int = match_txn_detail(response.headers["Location"])
        txn_data.id = txn_id
        with self.app.app_context():
            txn: Transaction | None = db.session.get(Transaction, txn_id)
            assert txn is not None
            for i in range(len(txn.currencies)):
                for j in range(len(txn.currencies[i].debit)):
                    txn_data.currencies[i].debit[j].id \
                        = txn.currencies[i].debit[j].id
                for j in range(len(txn.currencies[i].credit)):
                    txn_data.currencies[i].credit[j].id \
                        = txn.currencies[i].credit[j].id
