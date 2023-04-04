# The Mia! Accounting Project.
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
"""The common test libraries.

"""
import typing as t

import httpx
from flask import Flask, render_template_string

from test_site import create_app

TEST_SERVER: str = "https://testserver"
"""The test server URI."""
NEXT_URI: str = "/_next"
"""The next URI."""


class Accounts:
    """The shortcuts to the common accounts."""
    CASH: str = "1111-001"
    PETTY_CASH: str = "1112-001"
    BANK: str = "1113-001"
    NOTES_RECEIVABLE: str = "1131-001"
    RECEIVABLE: str = "1141-001"
    PREPAID: str = "1258-001"
    NOTES_PAYABLE: str = "2131-001"
    PAYABLE: str = "2141-001"
    SALES: str = "4111-001"
    SERVICE: str = "4611-001"
    AGENCY: str = "4711-001"
    RENT_EXPENSE: str = "6252-001"
    OFFICE: str = "6253-001"
    TRAVEL: str = "6254-001"
    POSTAGE: str = "6256-001"
    UTILITIES: str = "6261-001"
    INSURANCE: str = "6262-001"
    MEAL: str = "6272-001"
    INTEREST: str = "7111-001"
    DONATION: str = "7481-001"
    RENT_INCOME: str = "7482-001"


def create_test_app() -> Flask:
    """Creates and returns the testing Flask application.

    :return: The testing Flask application.
    """
    app: Flask = create_app(is_testing=True)

    @app.get("/.csrf-token")
    def get_csrf_token_view() -> str:
        """The test view to return the CSRF token."""
        return render_template_string("{{csrf_token()}}")

    @app.get("/.errors")
    def get_errors_view() -> str:
        """The test view to return the CSRF token."""
        return render_template_string("{{get_flashed_messages()|tojson}}")

    return app


def get_csrf_token(client: httpx.Client) -> str:
    """Returns the CSRF token.

    :param client: The httpx client.
    :return: The CSRF token.
    """
    return client.get("/.csrf-token").text


def get_client(app: Flask, username: str) -> tuple[httpx.Client, str]:
    """Returns a user client.

    :param app: The Flask application.
    :param username: The username.
    :return: A tuple of the client and the CSRF token.
    """
    client: httpx.Client = httpx.Client(app=app, base_url=TEST_SERVER)
    client.headers["Referer"] = TEST_SERVER
    csrf_token: str = get_csrf_token(client)
    response: httpx.Response = client.post("/login",
                                           data={"csrf_token": csrf_token,
                                                 "username": username})
    assert response.status_code == 302
    assert response.headers["Location"] == "/"
    return client, csrf_token


def set_locale(client: httpx.Client, csrf_token: str,
               locale: t.Literal["en", "zh_Hant", "zh_Hans"]) -> None:
    """Sets the current locale.

    :param client: The test client.
    :param csrf_token: The CSRF token.
    :param locale: The locale.
    :return: None.
    """
    response: httpx.Response = client.post("/locale",
                                           data={"csrf_token": csrf_token,
                                                 "locale": locale,
                                                 "next": "/next"})
    assert response.status_code == 302
    assert response.headers["Location"] == "/next"
