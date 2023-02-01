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
"""The accounting application.

"""
import typing as t
from abc import ABC, abstractmethod

import sqlalchemy as sa
from flask import Flask, Blueprint
from flask_sqlalchemy.model import Model

T = t.TypeVar("T", bound=Model)


class AbstractUserUtils(t.Generic[T], ABC):
    """The abstract user utilities."""

    @property
    @abstractmethod
    def cls(self) -> t.Type[T]:
        """Returns the user class.

        :return: The user class.
        """

    @property
    @abstractmethod
    def pk_column(self) -> sa.Column:
        """Returns the primary key column.

        :return: The primary key column.
        """

    @property
    @abstractmethod
    def current_user(self) -> T:
        """Returns the current user.

        :return: The current user.
        """

    @abstractmethod
    def get_by_username(self, username: str) -> T | None:
        """Returns the user by her username.

        :return: The user by her username, or None if the user was not found.
        """

    @abstractmethod
    def get_pk(self, user: T) -> int:
        """Returns the primary key of the user.

        :return: The primary key of the user.
        """


def init_app(app: Flask, user_utils: AbstractUserUtils,
             url_prefix: str = "/accounting",
             can_view_func: t.Callable[[], bool] | None = None,
             can_edit_func: t.Callable[[], bool] | None = None) -> None:
    """Initialize the application.

    :param app: The Flask application.
    :param user_utils: The user utilities.
    :param url_prefix: The URL prefix of the accounting application.
    :param can_view_func: A callback that returns whether the current user can
        view the accounting data.
    :param can_edit_func: A callback that returns whether the current user can
        edit the accounting data.
    :return: None.
    """
    # The database instance must be set before loading everything
    # in the application.
    from .database import set_db
    set_db(app.extensions["sqlalchemy"], user_utils)

    bp: Blueprint = Blueprint("accounting", __name__,
                              url_prefix=url_prefix,
                              template_folder="templates",
                              static_folder="static")

    from . import locale
    locale.init_app(app, bp)

    from .utils import permission
    permission.init_app(app, can_view_func, can_edit_func)

    from . import base_account
    base_account.init_app(app, bp)

    from . import account
    account.init_app(app, bp)

    app.register_blueprint(bp)
