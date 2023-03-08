# The Mia! Accounting Flask Project.
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
"""The utility to export the report as CSV for download.

"""
import csv
from abc import ABC, abstractmethod
from datetime import timedelta
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
    start: str | None = None
    if period.start is not None:
        if period.start.month == 1 and period.start.day == 1:
            start = str(period.start.year)
        elif period.start.day == 1:
            start = period.start.strftime("%Y%m")
        else:
            start = period.start.strftime("%Y%m%d")
    end: str | None = None
    if period.end is not None:
        if period.end.month == 12 and period.end.day == 31:
            end = str(period.end.year)
        elif (period.end + timedelta(days=1)).day == 1:
            end = period.end.strftime("%Y%m")
        else:
            end = period.end.strftime("%Y%m%d")
    if start == end:
        return start
    if period.start is None and period.end is None:
        return "all-time"
    if period.start is None:
        return f"until-{end}"
    if period.end is None:
        return f"since-{start}"
    return f"{start}-{end}"
