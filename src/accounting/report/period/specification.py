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
"""The period specification composer.

"""
from datetime import date, timedelta


class PeriodSpecification:
    """The period specification composer."""

    def __init__(self, start: date | None, end: date | None):
        """Constructs the period specification composer.

        :param start: The start of the period.
        :param end: The end of the period.
        """
        self.__start: date | None = start
        self.__end: date | None = end
        self.spec: str = self.__get_spec()

    def __get_spec(self) -> str:
        """Returns the period specification.

        :return: The period specification.
        """
        if self.__start is None and self.__end is None:
            return "-"
        if self.__end is None:
            return self.__get_since_spec()
        if self.__start is None:
            return self.__get_until_spec()
        try:
            return self.__get_year_spec()
        except ValueError:
            pass
        try:
            return self.__get_month_spec()
        except ValueError:
            pass
        return self.__get_day_spec()

    def __get_since_spec(self) -> str:
        """Returns the period specification without the end day.

        :return: The period specification without the end day
        """
        if self.__start.month == 1 and self.__start.day == 1:
            return self.__start.strftime("%Y-")
        if self.__start.day == 1:
            return self.__start.strftime("%Y-%m-")
        return self.__start.strftime("%Y-%m-%d-")

    def __get_until_spec(self) -> str:
        """Returns the period specification without the start day.

        :return: The period specification without the start day
        """
        if self.__end.month == 12 and self.__end.day == 31:
            return self.__end.strftime("-%Y")
        if (self.__end + timedelta(days=1)).day == 1:
            return self.__end.strftime("-%Y-%m")
        return self.__end.strftime("-%Y-%m-%d")

    def __get_year_spec(self) -> str:
        """Returns the period specification as a year range.

        :return: The period specification as a year range.
        :raise ValueError: The period is not a year range.
        """
        if self.__start.month != 1 or self.__start.day != 1 \
                or self.__end.month != 12 or self.__end.day != 31:
            raise ValueError
        if self.__start.year == self.__end.year:
            return "%04d" % self.__start.year
        return "%04d-%04d" % (self.__start.year, self.__end.year)

    def __get_month_spec(self) -> str:
        """Returns the period specification as a month range.

        :return: The period specification as a month range.
        :raise ValueError: The period is not a month range.
        """
        if self.__start.day != 1 or (self.__end + timedelta(days=1)).day != 1:
            raise ValueError
        if self.__start.year == self.__end.year \
                and self.__start.month == self.__end.month:
            return "%04d-%02d" % (self.__start.year, self.__start.month)
        return "%04d-%02d-%04d-%02d" % (
            self.__start.year, self.__start.month,
            self.__end.year, self.__end.month)

    def __get_day_spec(self) -> str:
        """Returns the period specification as a day range.

        :return: The period specification as a day range.
        :raise ValueError: The period is a month or year range.
        """
        if self.__start == self.__end:
            return "%04d-%02d-%02d" % (
                self.__start.year, self.__start.month, self.__start.day)
        return "%04d-%02d-%02d-%04d-%02d-%02d" % (
            self.__start.year, self.__start.month, self.__start.day,
            self.__end.year, self.__end.month, self.__end.day)
