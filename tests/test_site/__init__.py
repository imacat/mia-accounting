# The Mia! Accounting Demonstration Website.
# Author: imacat@mail.imacat.idv.tw (imacat), 2023/1/27

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
"""The Mia! Accounting demonstration website.

"""
import os
from secrets import token_urlsafe
from typing import Type

from click.testing import Result
from flask import Flask, Blueprint, render_template, redirect, Response, \
    url_for
from flask.testing import FlaskCliRunner
from flask_babel_js import BabelJS
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from sqlalchemy import Column

bp: Blueprint = Blueprint("home", __name__)
"""The global blueprint."""
babel_js: BabelJS = BabelJS()
"""The Babel JavaScript instance."""
csrf: CSRFProtect = CSRFProtect()
"""The CSRF protector."""
db: SQLAlchemy = SQLAlchemy()
"""The database instance."""


def create_app(is_testing: bool = False) -> Flask:
    """Create and configure the application.

    :param is_testing: True if we are running for testing, or False otherwise.
    :return: The application.
    """
    import accounting

    app: Flask = Flask(__name__)
    db_uri: str = "sqlite:///" if is_testing else "sqlite:///local.sqlite"
    app.config.from_mapping({
        "SECRET_KEY": os.environ.get("SECRET_KEY", token_urlsafe(32)),
        "SESSION_COOKIE_SAMESITE": "Lax",
        "SESSION_COOKIE_SECURE": True,
        "SQLALCHEMY_DATABASE_URI": db_uri,
        "BABEL_DEFAULT_LOCALE": "en",
        "ALL_LINGUAS": "zh_Hant|正體中文,en|English,zh_Hans|简体中文",
    })
    if is_testing:
        app.config["TESTING"] = True

    babel_js.init_app(app)
    csrf.init_app(app)
    db.init_app(app)

    app.register_blueprint(bp, url_prefix="/")

    from . import locale
    locale.init_app(app)

    from . import auth
    auth.init_app(app)

    from . import reset
    reset.init_app(app)

    class UserUtilities(accounting.UserUtilityInterface[auth.User]):

        def can_view(self) -> bool:
            return auth.current_user() is not None \
                and auth.current_user().username in ["viewer", "editor",
                                                     "admin"]

        def can_edit(self) -> bool:
            return auth.current_user() is not None \
                and auth.current_user().username in ["editor", "admin"]

        def can_admin(self) -> bool:
            return auth.current_user() is not None \
                and auth.current_user().username == "admin"

        def unauthorized(self) -> Response:
            from accounting.utils.next_uri import append_next
            return redirect(append_next(url_for("auth.login-form")))

        @property
        def cls(self) -> Type[auth.User]:
            return auth.User

        @property
        def pk_column(self) -> Column:
            return auth.User.id

        @property
        def current_user(self) -> auth.User | None:
            return auth.current_user()

        def get_by_username(self, username: str) -> auth.User | None:
            return auth.User.query\
                .filter(auth.User.username == username).first()

        def get_pk(self, user: auth.User) -> int:
            return user.id

    accounting.init_app(app, user_utils=UserUtilities())

    with app.app_context():
        init_db(app)

    return app


def init_db(app: Flask) -> None:
    """Initializes the database.

    :param app: The Flask application.
    :return: None.
    """
    db.create_all()
    from .auth import User
    for username in ["viewer", "editor", "admin", "nobody"]:
        if User.query.filter(User.username == username).first() is None:
            db.session.add(User(username=username))
    db.session.commit()
    runner: FlaskCliRunner = app.test_cli_runner()
    result: Result = runner.invoke(args=["accounting-init-db", "-u", "editor"])
    assert result.exit_code == 0, result.output + str(result.exception)


@bp.get("/", endpoint="home")
def get_home() -> str:
    """Returns the home page.

    :return: The home page.
    """
    return render_template("home.html")
