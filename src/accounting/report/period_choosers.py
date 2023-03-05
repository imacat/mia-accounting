# The Mia! Accounting Flask Project.
# Author: imacat@mail.imacat.idv.tw (imacat), 2023/3/4

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
"""The period choosers.

This file is largely taken from the NanoParma ERP project, first written in
2021/9/16 by imacat (imacat@nanoparma.com).

"""
import typing as t
from abc import ABC, abstractmethod
from datetime import date

from flask import url_for

from accounting.models import Currency, Account, Transaction
from .period import YearPeriod, Period, ThisMonth, LastMonth, SinceLastMonth, \
    ThisYear, LastYear, Today, Yesterday, TemplatePeriod


class PeriodChooser(ABC):
    """The period chooser."""

    def __init__(self, start: date | None):
        """Constructs a period chooser.

        :param start: The start of the period.
        """

        # Shortcut periods
        self.this_month_url: str = self._url_for(ThisMonth())
        """The URL for this month."""
        self.last_month_url: str = self._url_for(LastMonth())
        """The URL for last month."""
        self.since_last_month_url: str = self._url_for(SinceLastMonth())
        """The URL since last mint."""
        self.this_year_url: str = self._url_for(ThisYear())
        """The URL for this year."""
        self.last_year_url: str = self._url_for(LastYear())
        """The URL for last year."""
        self.today_url: str = self._url_for(Today())
        """The URL for today."""
        self.yesterday_url: str = self._url_for(Yesterday())
        """The URL for yesterday."""
        self.all_url: str = self._url_for(Period(None, None))
        """The URL for all period."""
        self.url_template: str = self._url_for(TemplatePeriod())
        """The URL template."""

        # Attributes
        self.data_start: date | None = start
        """The start of the data."""
        self.has_data: bool = start is not None
        """Whether there is any data."""
        self.has_last_month: bool = False
        """Where there is data in last month."""
        self.has_last_year: bool = False
        """Whether there is data in last year."""
        self.has_yesterday: bool = False
        """Whether there is data in yesterday."""
        self.available_years: t.Iterator[int] = []
        """The available years."""

        if self.has_data is not None:
            today: date = date.today()
            self.has_last_month = start < date(today.year, today.month, 1)
            self.has_last_year = start.year < today.year
            self.has_yesterday = start < today
            self.available_years: t.Iterator[int] = []
            if start.year < today.year - 1:
                self.available_years \
                    = reversed(range(start.year, today.year - 1))

    @abstractmethod
    def _url_for(self, period: Period) -> str:
        """Returns the URL for a period.

        :param period: The period.
        :return: The URL for the period.
        """
        pass

    def year_url(self, year: int) -> str:
        """Returns the period URL of a year.

        :param year: The year
        :return: The period URL of the year.
        """
        return self._url_for(YearPeriod(year))


class JournalPeriodChooser(PeriodChooser):
    """The journal period chooser."""

    def __init__(self):
        """Constructs the journal period chooser."""
        first: Transaction | None \
            = Transaction.query.order_by(Transaction.date).first()
        super(JournalPeriodChooser, self).__init__(
            None if first is None else first.date)

    def _url_for(self, period: Period) -> str:
        if period.is_default:
            return url_for("accounting.report.journal-default")
        return url_for("accounting.report.journal", period=period)


class LedgerPeriodChooser(PeriodChooser):
    """The ledger period chooser."""

    def __init__(self, currency: Currency, account: Account):
        """Constructs the ledger period chooser."""
        self.currency: Currency = currency
        """The currency."""
        self.account: Account = account
        """The account."""
        first: Transaction | None \
            = Transaction.query.order_by(Transaction.date).first()
        super(LedgerPeriodChooser, self).__init__(
            None if first is None else first.date)

    def _url_for(self, period: Period) -> str:
        if period.is_default:
            return url_for("accounting.report.ledger-default",
                           currency=self.currency, account=self.account)
        return url_for("accounting.report.ledger",
                       currency=self.currency, account=self.account,
                       period=period)


class IncomeExpensesPeriodChooser(PeriodChooser):
    """The income-expenses period chooser."""

    def __init__(self, currency: Currency, account: Account):
        """Constructs the income-expenses period chooser."""
        self.currency: Currency = currency
        """The currency."""
        self.account: Account = account
        """The account."""
        first: Transaction | None \
            = Transaction.query.order_by(Transaction.date).first()
        super(IncomeExpensesPeriodChooser, self).__init__(
            None if first is None else first.date)

    def _url_for(self, period: Period) -> str:
        if period.is_default:
            return url_for("accounting.report.income-expenses-default",
                           currency=self.currency, account=self.account)
        return url_for("accounting.report.income-expenses",
                       currency=self.currency, account=self.account,
                       period=period)
