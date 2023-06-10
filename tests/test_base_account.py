# The Mia! Accounting Project.
# Author: imacat@mail.imacat.idv.tw (imacat), 2023/1/26

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
"""The test for the base account management.

"""
import unittest

import httpx
from flask import Flask

from testlib import create_test_app, get_client

LIST_URI: str = "/accounting/base-accounts"
"""The list URI."""
DETAIL_URI: str = "/accounting/base-accounts/1111"
"""The detail URI."""


class BaseAccountTestCase(unittest.TestCase):
    """The base account test case."""

    def setUp(self) -> None:
        """Sets up the test.
        This is run once per test.

        :return: None.
        """
        self.__app: Flask = create_test_app()
        """The Flask application."""

    def test_nobody(self) -> None:
        """Test the permission as nobody.

        :return: None.
        """
        client: httpx.Client = get_client(self.__app, "nobody")
        response: httpx.Response

        response = client.get(LIST_URI)
        self.assertEqual(response.status_code, 403)

        response = client.get(DETAIL_URI)
        self.assertEqual(response.status_code, 403)

    def test_viewer(self) -> None:
        """Test the permission as viewer.

        :return: None.
        """
        client: httpx.Client = get_client(self.__app, "viewer")
        response: httpx.Response

        response = client.get(LIST_URI)
        self.assertEqual(response.status_code, 200)

        response = client.get(DETAIL_URI)
        self.assertEqual(response.status_code, 200)

    def test_editor(self) -> None:
        """Test the permission as editor.

        :return: None.
        """
        client: httpx.Client = get_client(self.__app, "editor")
        response: httpx.Response

        response = client.get(LIST_URI)
        self.assertEqual(response.status_code, 200)

        response = client.get(DETAIL_URI)
        self.assertEqual(response.status_code, 200)
