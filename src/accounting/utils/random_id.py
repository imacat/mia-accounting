# The Mia! Accounting Project.
# Author: imacat@mail.imacat.idv.tw (imacat), 2023/1/30

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
"""The random ID mixin for the data models.

This module should not import any other module from the application.

"""
import typing as t
from secrets import randbelow

from accounting import db


def new_id(cls: t.Type):
    """Returns a new random ID for the data model.

    :param cls: The data model.
    :return: The generated new random ID.
    """
    while True:
        obj_id: int = 100000000 + randbelow(900000000)
        if db.session.get(cls, obj_id) is None:
            return obj_id
