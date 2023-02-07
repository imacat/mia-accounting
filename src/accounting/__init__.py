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

from flask import Flask, Blueprint

from accounting.utils.user import AbstractUserUtils


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
    set_db(app.extensions["sqlalchemy"])
    from .utils.user import init_user_utils
    init_user_utils(user_utils)

    bp: Blueprint = Blueprint("accounting", __name__,
                              url_prefix=url_prefix,
                              template_folder="templates",
                              static_folder="static")

    from . import locale
    locale.init_app(app, bp)

    from .utils import permission
    permission.init_app(bp, can_view_func, can_edit_func)

    from . import base_account
    base_account.init_app(app, bp)

    from . import account
    account.init_app(app, bp)

    from . import currency
    currency.init_app(app, bp)

    from .utils import next_url
    next_url.init_app(bp)

    app.register_blueprint(bp)
