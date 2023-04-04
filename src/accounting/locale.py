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
"""The localization for the accounting application.

"""
import json
from pathlib import Path

from flask import Flask, Response, Blueprint
from flask_babel import LazyString, Domain
from flask_babel_js import JAVASCRIPT, c2js

translation_dir: Path = Path(__file__).parent / "translations"
domain: Domain = Domain(translation_directories=[translation_dir],
                        domain="accounting")


def gettext(string, **variables) -> str:
    """A replacement of the Babel gettext() function..

    :param string: The message to translate.
    :param variables: The variable substitution.
    :return: The translated message.
    """
    return domain.gettext(string, **variables)


def pgettext(context, string, **variables) -> str:
    """A replacement of the Babel gettext() function..

    :param context: The context.
    :param string: The message to translate.
    :param variables: The variable substitution.
    :return: The translated message.
    """
    return domain.pgettext(context, string, **variables)


def lazy_gettext(string, **variables) -> LazyString:
    """A replacement of the Babel lazy_gettext() function..

    :param string: The message to translate.
    :param variables: The variable substitution.
    :return: The translated message.
    """
    return domain.lazy_gettext(string, **variables)


def __babel_js_catalog_view() -> Response:
    """A tweaked view taken from Flask-Babel-JS that returns the messages and
    with the A_() function instead of _().

    :return: The response.
    """
    js = [
            """"use strict";

(function() {
    var babel = {};
    babel.catalog = """
    ]

    translations = domain.get_translations()
    # Here used to be an isinstance check for NullTranslations, but the
    # translation object that is "merged" by flask-babel is seen as an
    # instance of NullTranslations.
    catalog = translations._catalog.copy()

    # copy()ing the catalog here because we're modifying the original copy.
    for key, value in catalog.copy().items():
        if isinstance(key, tuple):
            text, plural = key
            if text not in catalog:
                catalog[text] = {}

            catalog[text][plural] = value
            del catalog[key]

    js.append(json.dumps(catalog, indent=4))

    js.append(";\n")
    js.append(JAVASCRIPT)

    metadata = translations.gettext("")
    if metadata:
        for m in metadata.splitlines():
            if m.lower().startswith("plural-forms:"):
                js.append("    babel.plural = ")
                js.append(c2js(m.lower().split("plural=")[1].rstrip(';')))

    js.append("""

    window.A_ = babel.gettext;
})();
""")

    resp = Response("".join(js))
    resp.headers["Content-Type"] = "text/javascript"
    return resp


def init_app(app: Flask, bp: Blueprint) -> None:
    """Initializes the application.

    :param app: The Flask application.
    :param bp: The blueprint of the accounting application.
    :return: None.
    """
    bp.add_url_rule("/_jstrans.js", "babel_catalog",
                    __babel_js_catalog_view)
    app.jinja_env.globals["A_"] = domain.gettext
