# The Mia! Accounting Flask Project.
# Author: imacat@mail.imacat.idv.tw (imacat), 2023/1/25

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

"""The database instance factory for the base account management.

This is to overcome the problem that the database instance needs to be
initialized at compile time, but as a submodule it is only available at run
time.

"""

from flask_sqlalchemy import SQLAlchemy

from accounting import AbstractUserUtils

db: SQLAlchemy
"""The database instance."""
user_utils: AbstractUserUtils
"""The user utilities."""


def set_db(new_db: SQLAlchemy, new_user_utils: AbstractUserUtils) -> None:
    """Sets the database instance.

    :param new_db: The database instance.
    :param new_user_utils: The user utilities.
    :return: None.
    """
    global db, user_utils
    db = new_db
    user_utils = new_user_utils
