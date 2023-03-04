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
"""The report chooser.

This file is largely taken from the NanoParma ERP project, first written in
2021/9/16 by imacat (imacat@nanoparma.com).

"""
import typing as t

from flask import url_for
from flask_babel import LazyString

from accounting import db
from accounting.locale import gettext
from accounting.models import Currency
from accounting.template_globals import default_currency_code
from .period import Period
from .report_type import ReportType


class ReportLink:
    """A link of a report."""

    def __init__(self, name: str | LazyString, url: str):
        """Constructs a report.

        :param name: The report name.
        :param url: The URL.
        """
        self.name: str | LazyString = name
        """The report name."""
        self.url: str = url
        """The URL."""
        self.is_active: bool = False
        """Whether the report is the current report."""


class ReportChooser:
    """The report chooser."""

    def __init__(self, active_report: ReportType,
                 period: Period | None = None,
                 currency: Currency | None = None):
        """Constructs the report chooser.

        :param active_report: The active report.
        :param period: The period.
        :param currency: The currency.
        """
        self.__active_report: ReportType = active_report
        """The currently active report."""
        self.__period: Period = Period.get_instance() if period is None \
            else period
        """The period."""
        self.__currency: Currency = db.session.get(
            Currency, default_currency_code()) \
            if currency is None else currency
        """The currency."""
        self.__reports: list[ReportLink] = []
        """The links to the reports."""
        self.__reports.append(self.__journal)
        self.current_report: str | LazyString = ""
        """The name of the current report."""
        for report in self.__reports:
            if report.is_active:
                self.current_report = report.name

    @property
    def __journal(self) -> ReportLink:
        """Returns the journal.

        :return: The journal.
        """
        url: str = url_for("accounting.report.journal-default") \
            if self.__period.is_default \
            else url_for("accounting.report.journal", period=self.__period)
        report = ReportLink(gettext("Journal"), url)
        if self.__active_report == ReportType.JOURNAL:
            report.is_active = True
        return report

    def __iter__(self) -> t.Iterator[ReportLink]:
        """Returns the iteration of the reports.

        :return: The iteration of the reports.
        """
        return iter(self.__reports)
