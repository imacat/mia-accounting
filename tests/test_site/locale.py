# The Mia! Accounting Demonstration Website.
# Author: imacat@mail.imacat.idv.tw (imacat), 2023/1/2

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
"""The localization for the Mia! Accounting demonstration website.

"""
from babel import Locale
from flask import request, session, current_app, Blueprint, Response, \
    redirect, url_for, Flask
from flask_babel import Babel
from werkzeug.datastructures import LanguageAccept

bp: Blueprint = Blueprint("locale", __name__, url_prefix="/")


def get_locale():
    """Returns the locale of the user

    :return: The locale of the user.
    """
    all_linguas: dict[str, str] = get_all_linguas()
    if "locale" in session and session["locale"] in all_linguas:
        return session["locale"]
    return __fix_accept_language(request.accept_languages)\
        .best_match(all_linguas.keys())


def __fix_accept_language(accept: LanguageAccept) -> LanguageAccept:
    """Fixes the accept-language so that territory variants may be matched to
    script variants.  For example, zh_TW, zh_HK to zh_Hant, and zh_CN, zh_SG to
    zh_Hans.  This is to solve the issue that Flask only recognizes the script
    variants, like zh_Hant and zh_Hans.

    :param accept: The original HTTP accept languages.
    :return: The fixed HTTP accept languages
    """
    accept_list: list[tuple[str, float]] = list(accept)
    to_add: list[tuple[str, float]] = []
    for pair in accept_list:
        locale: Locale = Locale.parse(pair[0].replace("-", "_"))
        if locale.script is not None:
            tag: str = f"{locale.language}-{locale.script}"
            if tag not in accept:
                to_add.append((tag, pair[1]))
    accept_list.extend(to_add)
    return LanguageAccept(accept_list)


@bp.post("/locale", endpoint="set-locale")
def set_locale() -> Response:
    """Sets the locale for the user.

    :return: The response.
    """
    all_linguas: dict[str, str] = get_all_linguas()
    if "locale" in request.form and request.form["locale"] in all_linguas:
        session["locale"] = request.form["locale"]
    if "next" in request.form:
        return redirect(request.form["next"])
    return redirect(url_for("home.home"))


def get_all_linguas() -> dict[str, str]:
    """Returns all the available languages.

    :return: All the available languages, as a dictionary of the language code
        and their local names.
    """
    return {y[0]: y[1] for y in
            [x.split("|") for x in
             current_app.config["ALL_LINGUAS"].split(",")]}


def init_app(app: Flask) -> None:
    """Initialize the localization.

    :param app: The Flask application.
    :return: None.
    """
    babel = Babel()
    babel.init_app(app, locale_selector=get_locale)
    app.register_blueprint(bp)
    app.jinja_env.globals["get_locale"] = get_locale
    app.jinja_env.globals["get_all_linguas"] = get_all_linguas
