# The Mia! Accounting Project.
# Author: imacat@mail.imacat.idv.tw (imacat), 2023/3/8

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
"""The base report.

"""
from abc import ABC, abstractmethod

from flask import Response


class BaseReport(ABC):
    """The base report class."""

    @abstractmethod
    def csv(self) -> Response:
        """Returns the report as CSV for download.

        :return: The response of the report for download.
        """

    @abstractmethod
    def html(self) -> str:
        """Composes and returns the report as HTML.

        :return: The report as HTML.
        """
