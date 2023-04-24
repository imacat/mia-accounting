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
"""The authentication for the Mia! Accounting demonstration website.

"""
import typing as t

from flask import Blueprint, render_template, Flask, redirect, url_for, \
    session, request, g, Response, abort
from sqlalchemy.orm import Mapped, mapped_column

from . import db

bp: Blueprint = Blueprint("auth", __name__, url_prefix="/")
"""The authentication blueprint."""


class User(db.Model):
    """A user."""
    __tablename__ = "users"
    """The table name."""
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    """The ID."""
    username: Mapped[str] = mapped_column(unique=True)
    """The username."""

    def __str__(self) -> str:
        """Returns the string representation of the user.

        :return: The string representation of the user.
        """
        return self.username


@bp.get("login", endpoint="login-form")
def show_login_form() -> str | Response:
    """Shows the login form.

    :return: The login form.
    """
    if "user" in session:
        return redirect(url_for("accounting-report.default"))
    return render_template("login.html")


@bp.post("login", endpoint="login")
def login() -> redirect:
    """Logs in the user.

    :return: The redirection to the home page.
    """
    from accounting.utils.next_uri import inherit_next, or_next
    if request.form.get("username") not in {"viewer", "editor", "admin",
                                            "nobody"}:
        return redirect(inherit_next(url_for("auth.login")))
    session["user"] = request.form.get("username")
    return redirect(or_next(url_for("accounting-report.default")))


@bp.post("logout", endpoint="logout")
def logout() -> redirect:
    """Logs out the user.

    :return: The redirection to the home page.
    """
    if "user" in session:
        del session["user"]
    return redirect(url_for("home.home"))


def current_user() -> User | None:
    """Returns the current user.

    :return: The current user, or None if the user did not log in.
    """
    if not hasattr(g, "user"):
        if "user" not in session:
            g.user = None
        else:
            g.user = User.query.filter(
                User.username == session["user"]).first()
    return g.user


def admin_required(view: t.Callable) -> t.Callable:
    """The view decorator to require the user to be an administrator.

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
        from accounting.utils.next_uri import append_next
        if "user" not in session:
            return redirect(append_next(url_for("auth.login")))
        if session["user"] != "admin":
            abort(403)
        return view(*args, **kwargs)

    return decorated_view


def init_app(app: Flask) -> None:
    """Initialize the localization.

    :param app: The Flask application.
    :return: None.
    """
    app.register_blueprint(bp)
    app.jinja_env.globals["current_user"] = current_user
