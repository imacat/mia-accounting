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
"""The period description composer.

"""
from datetime import date, timedelta

from accounting.locale import gettext


class PeriodDescription:
    """The period description composer."""

    def __init__(self, start: date | None, end: date | None):
        """Constructs the period description composer.

        :param start: The start of the period.
        :param end: The end of the period.
        """
        self.__start: date | None = start
        self.__end: date | None = end
        self.desc: str = self.__get_desc()

    def __get_desc(self) -> str:
        """Returns the period description.

        :return: The period description.
        """
        if self.__start is None and self.__end is None:
            return gettext("for all time")
        if self.__start is None:
            return self.__get_until_desc()
        if self.__end is None:
            return self.__get_since_desc()
        try:
            return self.__get_year_desc()
        except ValueError:
            pass
        try:
            return self.__get_month_desc()
        except ValueError:
            pass
        return self.__get_day_desc()

    def __get_since_desc(self) -> str:
        """Returns the description without the end day.

        :return: The description without the end day.
        """
        def get_start_desc() -> str:
            """Returns the description of the start day.

            :return: The description of the start day.
            """
            if self.__start.month == 1 and self.__start.day == 1:
                return str(self.__start.year)
            if self.__start.day == 1:
                return self.__format_month(self.__start)
            return self.__format_day(self.__start)

        return gettext("since %(start)s", start=get_start_desc())

    def __get_until_desc(self) -> str:
        """Returns the description without the start day.

        :return: The description without the start day.
        """
        def get_end_desc() -> str:
            """Returns the description of the end day.

            :return: The description of the end day.
            """
            if self.__end.month == 12 and self.__end.day == 31:
                return str(self.__end.year)
            if (self.__end + timedelta(days=1)).day == 1:
                return self.__format_month(self.__end)
            return self.__format_day(self.__end)

        return gettext("until %(end)s", end=get_end_desc())

    def __get_year_desc(self) -> str:
        """Returns the description as a year range.

        :return: The description as a year range.
        :raise ValueError: The period is not a year range.
        """
        if self.__start.month != 1 or self.__start.day != 1 \
                or self.__end.month != 12 or self.__end.day != 31:
            raise ValueError
        start: str = str(self.__start.year)
        if self.__start.year == self.__end.year:
            return self.__get_in_desc(start)
        return self.__get_from_to_desc(start, str(self.__end.year))

    def __get_month_desc(self) -> str:
        """Returns the description as a month range.

        :return: The description as a month range.
        :raise ValueError: The period is not a month range.
        """
        if self.__start.day != 1 or (self.__end + timedelta(days=1)).day != 1:
            raise ValueError
        start: str = self.__format_month(self.__start)
        if self.__start.year == self.__end.year \
                and self.__start.month == self.__end.month:
            return self.__get_in_desc(start)
        if self.__start.year == self.__end.year:
            return self.__get_from_to_desc(start, str(self.__end.month))
        return self.__get_from_to_desc(start, self.__format_month(self.__end))

    def __get_day_desc(self) -> str:
        """Returns the description as a day range.

        :return: The description as a day range.
        :raise ValueError: The period is a month or year range.
        """
        start: str = self.__format_day(self.__start)
        if self.__start == self.__end:
            return self.__get_in_desc(start)
        if self.__start.year == self.__end.year \
                and self.__start.month == self.__end.month:
            return self.__get_from_to_desc(start, str(self.__end.day))
        if self.__start.year == self.__end.year:
            end_month_day: str = f"{self.__end.month}/{self.__end.day}"
            return self.__get_from_to_desc(start, end_month_day)
        return self.__get_from_to_desc(start, self.__format_day(self.__end))

    @staticmethod
    def __format_month(month: date) -> str:
        """Formats a month.

        :param month: The month.
        :return: The formatted month.
        """
        return f"{month.year}/{month.month}"

    @staticmethod
    def __format_day(day: date) -> str:
        """Formats a day.

        :param day: The day.
        :return: The formatted day.
        """
        return f"{day.year}/{day.month}/{day.day}"

    @staticmethod
    def __get_in_desc(period: str) -> str:
        """Returns the description of a whole year, month, or day.

        :param period: The time period.
        :return: The description of a whole year, month, or day.
        """
        return gettext("in %(period)s", period=period)

    @staticmethod
    def __get_from_to_desc(start: str, end: str) -> str:
        """Returns the description of a separated start and end.

        :param start: The start.
        :param end: The end.
        :return: The description of the separated start and end.
        """
        return gettext("in %(start)s-%(end)s", start=start, end=end)
