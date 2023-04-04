# The Mia! Accounting Project.
# Author: imacat@mail.imacat.idv.tw (imacat), 2023/3/7

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
"""The utilities to export the report as CSV for download.

"""
import csv
from abc import ABC, abstractmethod
from datetime import timedelta, date
from decimal import Decimal
from io import StringIO

from flask import Response

from accounting.report.period import Period


class BaseCSVRow(ABC):
    """The base CSV row."""

    @property
    @abstractmethod
    def values(self) -> list[str | Decimal | None]:
        """Returns the values of the row.

        :return: The values of the row.
        """


def csv_download(filename: str, rows: list[BaseCSVRow]) -> Response:
    """Exports the data rows as a CSV file for download.

    :param filename: The download file name.
    :param rows: The data rows.
    :return: The response for download the CSV file.
    """
    with StringIO() as fp:
        writer = csv.writer(fp)
        writer.writerows([x.values for x in rows])
        fp.seek(0)
        response: Response = Response(fp.read(), mimetype="text/csv")
        response.headers["Content-Disposition"] \
            = f"attachment; filename={filename}"
        return response


def period_spec(period: Period) -> str:
    """Constructs the period specification to be used in the filename.

    :param period: The period.
    :return: The period specification to be used in the filename.
    """
    start: str | None = __get_start_str(period.start)
    end: str | None = __get_end_str(period.end)
    if period.start is None and period.end is None:
        return "all-time"
    if start == end:
        return start
    if period.start is None:
        return f"until-{end}"
    if period.end is None:
        return f"since-{start}"
    return f"{start}-{end}"


def __get_start_str(start: date | None) -> str | None:
    """Returns the string representation of the start date.

    :param start: The start date.
    :return: The string representation of the start date, or None if the start
        date is None.
    """
    if start is None:
        return None
    if start.month == 1 and start.day == 1:
        return str(start.year)
    if start.day == 1:
        return start.strftime("%Y%m")
    return start.strftime("%Y%m%d")


def __get_end_str(end: date | None) -> str | None:
    """Returns the string representation of the end date.

    :param end: The end date.
    :return: The string representation of the end date, or None if the end
        date is None.
    """
    if end is None:
        return None
    if end.month == 12 and end.day == 31:
        return str(end.year)
    if (end + timedelta(days=1)).day == 1:
        return end.strftime("%Y%m")
    return end.strftime("%Y%m%d")
