# The Mia! Accounting Project.
# Author: imacat@mail.imacat.idv.tw (imacat), 2024/6/4

#  Copyright (c) 2024 imacat.
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
"""The timezone utility.

This module should not import any other module from the application.

"""

import datetime as dt

import pytz
from flask import request


def get_tz_today() -> dt.date:
    """Returns today in the client timezone.

    :return: today in the client timezone.
    """
    tz_name: str | None = request.cookies.get("accounting-tz")
    if tz_name is None:
        return dt.date.today()
    return dt.datetime.now(tz=pytz.timezone(tz_name)).date()
