# The Mia! Accounting Project.
# Author: imacat@mail.imacat.idv.tw (imacat), 2023/2/1

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
"""The user utilities.

This module should not import any other module from the application.

"""
import typing as t
from abc import ABC, abstractmethod

import sqlalchemy as sa
from flask import g, Response
from flask_sqlalchemy.model import Model

T = t.TypeVar("T", bound=Model)


class UserUtilityInterface(t.Generic[T], ABC):
    """The interface for the user utilities."""

    @abstractmethod
    def can_view(self) -> bool:
        """Returns whether the currently logged-in user can view the accounting
        data.

        :return: True if the currently logged-in user can view the accounting
            data, or False otherwise.
        """

    @abstractmethod
    def can_edit(self) -> bool:
        """Returns whether the currently logged-in user can edit the accounting
        data.

        :return: True if the currently logged-in user can edit the accounting
            data, or False otherwise.
        """

    @abstractmethod
    def can_admin(self) -> bool:
        """Returns whether the currently logged-in user can administrate the
        accounting settings.

        :return: True if the currently logged-in user can administrate the
            accounting settings, or False otherwise.
        """

    @abstractmethod
    def unauthorized(self) -> Response | None:
        """Returns the response to require the user to log in.

        This may be a redirection to the login page, or an HTTP 401
        Unauthorized response for HTTP Authentication.  If this returns None,
        an HTTP 403 Forbidden response is return to the user.

        :return: The response to require the user to log in.
        """

    @property
    @abstractmethod
    def cls(self) -> t.Type[T]:
        """Returns the class of the user data model.

        :return: The class of the user data model.
        """

    @property
    @abstractmethod
    def pk_column(self) -> sa.Column:
        """Returns the primary key column.

        :return: The primary key column.
        """

    @property
    @abstractmethod
    def current_user(self) -> T | None:
        """Returns the currently logged-in user.

        :return: The currently logged-in user, or None if the user has not
            logged in
        """

    @abstractmethod
    def get_by_username(self, username: str) -> T | None:
        """Returns the user by her username.

        :return: The user by her username, or None if the user was not found.
        """

    @abstractmethod
    def get_pk(self, user: T) -> int:
        """Returns the primary key of the user, as an integer.

        :return: The primary key of the user, as an integer.
        """


__user_utils: UserUtilityInterface
"""The user utilities."""
user_cls: t.Type[Model] = Model
"""The user class."""
user_pk_column: sa.Column = sa.Column(sa.Integer)
"""The primary key column of the user class."""


def init_user_utils(utils: UserUtilityInterface) -> None:
    """Initializes the user utilities.

    :param utils: The user utilities.
    :return: None.
    """
    global __user_utils, user_cls, user_pk_column
    __user_utils = utils
    user_cls = utils.cls
    user_pk_column = utils.pk_column


def get_current_user_pk() -> int:
    """Returns the primary key value of the currently logged-in user.

    :return: The primary key value of the currently logged-in user.
    """
    return __user_utils.get_pk(get_current_user())


def has_user(username: str) -> bool:
    """Returns whether a user by the username exists.

    :param username: The username.
    :return: True if the user by the username exists, or False otherwise.
    """
    return __user_utils.get_by_username(username) is not None


def get_user_pk(username: str) -> int:
    """Returns the primary key value of the user by the username.

    :param username: The username.
    :return: The primary key value of the user by the username.
    """
    return __user_utils.get_pk(__user_utils.get_by_username(username))


def get_current_user() -> user_cls | None:
    """Returns the currently logged-in user.  The result is cached in the
    current request.

    :return: The currently logged-in user.
    """
    if not hasattr(g, "_accounting_user"):
        setattr(g, "_accounting_user", __user_utils.current_user)
    return getattr(g, "_accounting_user")
