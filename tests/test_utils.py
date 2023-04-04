# The Mia! Accounting Project.
# Author: imacat@mail.imacat.idv.tw (imacat), 2023/2/3

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
"""The test for the independent utilities.

"""
import unittest
from urllib.parse import quote_plus

import httpx
from flask import Flask, request

from accounting.utils.next_uri import append_next, inherit_next, or_next
from accounting.utils.pagination import Pagination, DEFAULT_PAGE_SIZE
from accounting.utils.query import parse_query_keywords
from testlib import TEST_SERVER, create_test_app, get_csrf_token


class NextUriTestCase(unittest.TestCase):
    """The test case for the next URI utilities."""
    TARGET: str = "/target"

    def setUp(self) -> None:
        """Sets up the test.
        This is run once per test.

        :return: None.
        """
        self.app: Flask = create_test_app()

    def test_next_uri(self) -> None:
        """Tests the next URI utilities with the next URI.

        :return: None.
        """
        def test_next_uri_view() -> str:
            """The test view with the next URI."""
            current_uri: str = request.full_path if request.query_string \
                else request.path
            self.assertEqual(append_next(self.TARGET),
                             f"{self.TARGET}?next={quote_plus(current_uri)}")
            next_uri: str = request.form["next"] if request.method == "POST" \
                else request.args["next"]
            self.assertEqual(inherit_next(self.TARGET),
                             f"{self.TARGET}?next={quote_plus(next_uri)}")
            self.assertEqual(or_next(self.TARGET), next_uri)
            return ""

        self.app.add_url_rule("/test-next", view_func=test_next_uri_view,
                              methods=["GET", "POST"])
        client: httpx.Client = httpx.Client(app=self.app, base_url=TEST_SERVER)
        client.headers["Referer"] = TEST_SERVER
        csrf_token: str = get_csrf_token(client)
        response: httpx.Response

        response = client.get("/test-next?next=/next&q=abc&page-no=4")
        self.assertEqual(response.status_code, 200)
        response = client.post("/test-next", data={"csrf_token": csrf_token,
                                                   "next": "/next",
                                                   "name": "viewer"})
        self.assertEqual(response.status_code, 200)

    def test_no_next_uri(self) -> None:
        """Tests the next URI utilities without the next URI.

        :return: None.
        """
        def test_no_next_uri_view() -> str:
            """The test view without the next URI."""
            current_uri: str = request.full_path if request.query_string \
                else request.path
            self.assertEqual(append_next(self.TARGET),
                             f"{self.TARGET}?next={quote_plus(current_uri)}")
            self.assertEqual(inherit_next(self.TARGET), self.TARGET)
            self.assertEqual(or_next(self.TARGET), self.TARGET)
            return ""

        self.app.add_url_rule("/test-no-next", view_func=test_no_next_uri_view,
                              methods=["GET", "POST"])
        client: httpx.Client = httpx.Client(app=self.app, base_url=TEST_SERVER)
        client.headers["Referer"] = TEST_SERVER
        csrf_token: str = get_csrf_token(client)
        response: httpx.Response

        response = client.get("/test-no-next?q=abc&page-no=4")
        self.assertEqual(response.status_code, 200)
        response = client.post("/test-no-next", data={"csrf_token": csrf_token,
                                                      "name": "viewer"})
        self.assertEqual(response.status_code, 200)


class QueryKeywordParserTestCase(unittest.TestCase):
    """The test case for the query keyword parser."""

    def test_default(self) -> None:
        """Tests the query keyword parser.

        :return: None.
        """
        self.assertEqual(parse_query_keywords("coffee"), ["coffee"])
        self.assertEqual(parse_query_keywords("coffee tea"), ["coffee", "tea"])
        self.assertEqual(parse_query_keywords("\"coffee\" \"tea cake\""),
                         ["coffee", "tea cake"])
        self.assertEqual(parse_query_keywords("\"coffee tea\" cheese "
                                              "\"cake candy\" sugar"),
                         ["coffee tea", "cheese", "cake candy", "sugar"])

    def test_malformed(self) -> None:
        """Tests the malformed query.

        :return: None.
        """
        self.assertEqual(parse_query_keywords("coffee \"tea cake"),
                         ["coffee", "tea cake"])
        self.assertEqual(parse_query_keywords("coffee te\"a ca\"ke"),
                         ["coffee", "te\"a", "ca\"ke"])
        self.assertEqual(parse_query_keywords("coffee\" tea cake\""),
                         ["coffee\"", "tea", "cake\""])

    def test_empty(self) -> None:
        """Tests the empty query.

        :return: None.
        """
        self.assertEqual(parse_query_keywords(None), [])
        self.assertEqual(parse_query_keywords(""), [])


class PaginationTestCase(unittest.TestCase):
    """The test case for pagination."""

    class Params:
        """The testing parameters."""

        def __init__(self, items: list[int], is_reversed: bool | None,
                     result: list[int], is_paged: bool):
            """Constructs the expected pagination.

            :param items: All the items in the list.
            :param is_reversed: Whether the default page is the last page.
            :param result: The expected items on the page.
            :param is_paged: Whether we need pagination.
            """
            self.items: list[int] = items
            self.is_reversed: bool | None = is_reversed
            self.result: list[int] = result
            self.is_paged: bool = is_paged

    def setUp(self) -> None:
        """Sets up the test.
        This is run once per test.

        :return: None.
        """
        self.app: Flask = create_test_app()
        self.params = self.Params([], None, [], True)

        @self.app.get("/test-pagination")
        def test_pagination_view() -> str:
            """The test view with the pagination."""
            pagination: Pagination
            if self.params.is_reversed is not None:
                pagination = Pagination[int](
                    self.params.items, is_reversed=self.params.is_reversed)
            else:
                pagination = Pagination[int](self.params.items)
            self.assertEqual(pagination.is_paged, self.params.is_paged)
            self.assertEqual(pagination.list, self.params.result)
            return ""

        self.client = httpx.Client(app=self.app, base_url=TEST_SERVER)
        self.client.headers["Referer"] = TEST_SERVER

    def __test_success(self, query: str, items: range,
                       result: range, is_paged: bool = True,
                       is_reversed: bool | None = None) -> None:
        """Tests the pagination.

        :param query: The query string.
        :param items: The original items.
        :param result: The expected page content.
        :param is_paged: Whether we need pagination.
        :param is_reversed: Whether the list is reversed.
        :return: None.
        """
        target: str = "/test-pagination"
        if query != "":
            target = f"{target}?{query}"
        self.params = self.Params(list(items), is_reversed,
                                  list(result), is_paged)
        response: httpx.Response = self.client.get(target)
        self.assertEqual(response.status_code, 200)

    def __test_malformed(self, query: str, items: range, redirect_to: str,
                         is_reversed: bool | None = None) -> None:
        """Tests the pagination.

        :param query: The query string.
        :param items: The original items.
        :param redirect_to: The expected target query of the redirection.
        :param is_reversed: Whether the list is reversed.
        :return: None.
        """
        target: str = "/test-pagination"
        self.params = self.Params(list(items), is_reversed, [], True)
        response: httpx.Response = self.client.get(f"{target}?{query}")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"],
                         f"{target}?{redirect_to}")

    def test_default(self) -> None:
        """Tests the default pagination.

        :return: None.
        """
        # The default first page
        self.__test_success("", range(1, 687), range(1, 11))
        # Some page in the middle
        self.__test_success("page-no=37", range(1, 687), range(361, 371))
        # The last page
        self.__test_success("page-no=69", range(1, 687), range(681, 687))

    def test_page_size(self) -> None:
        """Tests the pagination with a different page size.

        :return: None.
        """
        # The default page with a different page size
        self.__test_success("page-size=15", range(1, 687), range(1, 16))
        # Some page with a different page size
        self.__test_success("page-no=37&page-size=15", range(1, 687),
                            range(541, 556))
        # The last page with a different page size.
        self.__test_success("page-no=46&page-size=15", range(1, 687),
                            range(676, 687))

    def test_not_need(self) -> None:
        """Tests that the data does not need pagination.

        :return: None.
        """
        # Empty list
        self.__test_success("", range(0, 0), range(0, 0), is_paged=False)
        # A list that fits in one page
        self.__test_success("", range(1, 4), range(1, 4), is_paged=False)
        # A large page size that fits in everything
        self.__test_success("page-size=1000", range(1, 687), range(1, 687),
                            is_paged=False)

    def test_reversed(self) -> None:
        """Tests the default page on a reversed list.

        :return: None.
        """
        # The default page
        self.__test_success("", range(1, 687), range(681, 687),
                            is_reversed=True)
        # The default page with a different page size
        self.__test_success("page-size=15", range(1, 687), range(676, 687),
                            is_reversed=True)

    def test_last_page(self) -> None:
        """Tests the calculation of the items on the last page.

        :return: None.
        """
        # The last page that fits in one page
        self.__test_success("page-no=69", range(1, 691), range(681, 691))
        # A danging item in the last page
        self.__test_success("page-no=70", range(1, 692), range(691, 692))

    def test_malformed(self) -> None:
        """Tests the malformed pagination parameters.

        :return: None.
        """
        page_37: str = "q=word&page-no=37&next=%2F"
        page_size_15_default: str = "q=word&page-size=15&next=%2F"

        # A malformed page size
        self.__test_malformed("q=word&page-size=100a&page-no=37&next=%2F",
                              range(1, 691), page_37)
        # A default page size
        self.__test_malformed(f"q=word&page-size={DEFAULT_PAGE_SIZE}"
                              "&page-no=37&next=%2F",
                              range(1, 691), page_37)
        # An invalid page size
        self.__test_malformed("q=word&page-size=0&page-no=37&next=%2F",
                              range(1, 691), page_37)
        # A malformed page number
        self.__test_malformed("q=word&page-size=15&page-no=37a&next=%2F",
                              range(1, 691), page_size_15_default)
        # A default page number
        self.__test_malformed("q=word&page-size=15&page-no=1&next=%2F",
                              range(1, 691), page_size_15_default)
        # A default page number, on a reversed list
        self.__test_malformed("q=word&page-size=15&page-no=46&next=%2F",
                              range(1, 691), page_size_15_default,
                              is_reversed=True)
        # A page number beyond the last page
        self.__test_malformed("q=word&page-size=15&page-no=100&next=%2F",
                              range(1, 691),
                              "q=word&page-size=15&page-no=46&next=%2F")
        # A page number beyond the last page, on a reversed list
        self.__test_malformed("q=word&page-size=15&page-no=100&next=%2F",
                              range(1, 691),
                              page_size_15_default, is_reversed=True)
        # A page number before the first page
        self.__test_malformed("q=word&page-size=15&page-no=0&next=%2F",
                              range(1, 691),
                              page_size_15_default)
        # A page number before the first page, on a reversed list
        self.__test_malformed("q=word&page-size=15&page-no=0&next=%2F",
                              range(1, 691),
                              "q=word&page-size=15&page-no=1&next=%2F",
                              is_reversed=True)
