# The Mia! Accounting Flask Project.
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
from html.parser import HTMLParser
from unittest import TestCase

import httpx
from flask import Flask


class UserClient:
    """A user client."""

    def __init__(self, client: httpx.Client, csrf_token: str):
        """Constructs a user client.

        :param client: The client.
        :param csrf_token: The CSRF token.
        """
        self.client: httpx.Client = client
        self.csrf_token: str = csrf_token


def get_user_client(test_case: TestCase, app: Flask, username: str) \
        -> UserClient:
    """Returns a user client.

    :param test_case: The test case.
    :param app: The Flask application.
    :param username: The username.
    :return: The user client.
    """
    client: httpx.Client = httpx.Client(app=app, base_url="https://testserver")
    client.headers["Referer"] = "https://testserver"
    csrf_token: str = get_csrf_token(test_case, client, "/login")
    response: httpx.Response = client.post("/login",
                                           data={"csrf_token": csrf_token,
                                                 "username": username})
    test_case.assertEqual(response.status_code, 302)
    test_case.assertEqual(response.headers["Location"], "/")
    return UserClient(client, csrf_token)


def get_csrf_token(test_case: TestCase, client: httpx.Client, uri: str) -> str:
    """Returns the CSRF token from a form in a URI.

    :param test_case: The test case.
    :param client: The httpx client.
    :param uri: The URI.
    :return: The CSRF token.
    """

    class CsrfParser(HTMLParser):
        """The CSRF token parser."""

        def __init__(self):
            """Constructs the CSRF token parser."""
            super().__init__()
            self.csrf_token: str | None = None
            """The CSRF token."""

        def handle_starttag(self, tag: str,
                            attrs: list[tuple[str, str | None]]) -> None:
            """Handles when a start tag is found."""
            attrs_dict: dict[str, str] = dict(attrs)
            if attrs_dict.get("name") == "csrf_token":
                self.csrf_token = attrs_dict["value"]

    response: httpx.Response = client.get(uri)
    test_case.assertEqual(response.status_code, 200)
    parser: CsrfParser = CsrfParser()
    parser.feed(response.text)
    test_case.assertIsNotNone(parser.csrf_token)
    return parser.csrf_token
