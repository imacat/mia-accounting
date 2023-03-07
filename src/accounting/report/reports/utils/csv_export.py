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
from decimal import Decimal
from io import StringIO

from flask import Response


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
