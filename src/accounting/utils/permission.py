# The Mia! Accounting Project.
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
"""The permissions.

This module should not import any other module from the application.

"""
import typing as t

from flask import abort, Blueprint, Response

from accounting.utils.user import get_current_user, UserUtilityInterface


def has_permission(rule: t.Callable[[], bool]) -> t.Callable:
    """The permission decorator to check whether the current user is allowed.

    :param rule: The permission rule.
    :return: The view decorator.
    """

    def decorator(view: t.Callable) -> t.Callable:
        """The view decorator to decorate a view with permission tests.

        :param view: The view.
        :return: The decorated view.
        """

        def decorated_view(*args, **kwargs):
            """The decorated view that tests against a permission rule.

            :param args: The arguments of the view.
            :param kwargs: The keyword arguments of the view.
            :return: The response of the view.
            :raise Forbidden: When the user is denied.
            """
            if not rule():
                if get_current_user() is None:
                    response: Response | None = _unauthorized_func()
                    if response is not None:
                        return response
                abort(403)
            return view(*args, **kwargs)

        return decorated_view

    return decorator


__can_view_func: t.Callable[[], bool] = lambda: True
"""The callback that returns whether the current user can view the accounting
data."""
__can_edit_func: t.Callable[[], bool] = lambda: True
"""The callback that returns whether the current user can edit the accounting
data."""
__can_admin_func: t.Callable[[], bool] = lambda: True
"""The callback that returns whether the current user can administrate the
accounting settings."""
_unauthorized_func: t.Callable[[], Response | None] \
    = lambda: Response(status=403)
"""The callback that returns the response to require the user to log in."""


def can_view() -> bool:
    """Returns whether the current user can view the accounting data.

    :return: True if the current user can view the accounting data, or False
        otherwise.
    """
    return __can_view_func()


def can_edit() -> bool:
    """Returns whether the current user can edit the accounting data.

    The user has to log in.

    :return: True if the current user can edit the accounting data, or False
        otherwise.
    """
    if get_current_user() is None:
        return False
    return __can_edit_func()


def can_admin() -> bool:
    """Returns whether the current user can administrate the accounting
    settings.

    The user has to log in.

    :return: True if the current user can administrate the accounting settings,
        or False otherwise.
    """
    if get_current_user() is None:
        return False
    return __can_admin_func()


def init_app(bp: Blueprint, user_utils: UserUtilityInterface) -> None:
    """Initializes the application.

    :param bp: The blueprint of the accounting application.
    :param user_utils: The user utilities.
    :return: None.
    """
    global __can_view_func, __can_edit_func, __can_admin_func, \
        _unauthorized_func
    __can_view_func = user_utils.can_view
    __can_edit_func = user_utils.can_edit
    __can_admin_func = user_utils.can_admin
    _unauthorized_func = user_utils.unauthorized
    bp.add_app_template_global(user_utils.can_view, "accounting_can_view")
    bp.add_app_template_global(user_utils.can_edit, "accounting_can_edit")
    bp.add_app_template_global(user_utils.can_admin, "accounting_can_admin")
