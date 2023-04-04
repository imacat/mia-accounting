# The Mia! Accounting Project.
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
"""The utility to return the end of a month.

"""
import calendar
from datetime import date


def month_end(day: date) -> date:
    """Returns the end day of month for a date.

    :param day: The date.
    :return: The end day of the month of that day.
    """
    last_day: int = calendar.monthrange(day.year, day.month)[1]
    return date(day.year, day.month, last_day)
