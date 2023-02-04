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
"""The pagination utilities.

This module should not import any other module from the application.

"""
import typing as t
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse, \
    ParseResult

from flask import request
from werkzeug.routing import RequestRedirect

from accounting.locale import gettext


class Link:
    """A link."""

    def __init__(self, text: str, uri: str | None = None,
                 is_current: bool = False, is_for_mobile: bool = False):
        """Constructs the link.

        :param text: The link text.
        :param uri: The link URI, or None if there is no link.
        :param is_current: True if the page is the current page, or False
            otherwise.
        :param is_for_mobile: True if the page should be shown on small
            screens, or False otherwise.
        """
        self.text: str = text
        """The link text"""
        self.uri: str | None = uri
        """The link URI, or None if there is no link."""
        self.is_current: bool = is_current
        """Whether the link is the current page."""
        self.is_for_mobile: bool = is_for_mobile
        """Whether the link should be shown on mobile screens."""


class Redirection(RequestRedirect):
    """The redirection."""
    code = 302
    """The HTTP code."""


T = t.TypeVar("T")


class Pagination(t.Generic[T]):
    """The pagination utilities"""
    AVAILABLE_PAGE_SIZES: list[int] = [10, 100, 200]
    """The available page sizes."""
    DEFAULT_PAGE_SIZE: int = 10
    """The default page size."""

    def __init__(self, items: list[T], is_reversed: bool = False):
        """Constructs the pagination.

        :param items: The items.
        :param is_reversed: True if the default page is the last page, or False
            otherwise.
        """
        self.__current_uri: str = request.full_path if request.query_string \
            else request.path
        """The current URI."""
        self.__items: list[T] = items
        """All the items."""
        self.__is_reversed: bool = is_reversed
        """Whether the default page is the last page."""
        self.page_size: int = self.__get_page_size()
        """The number of items in a page."""
        self.__total_pages: int = 0 if len(items) == 0 \
            else int((len(items) - 1) / self.page_size) + 1
        """The total number of pages."""
        self.is_paged: bool = self.__total_pages > 1
        """Whether there should be pagination."""
        self.__default_page_no: int = 0
        """The default page number."""
        self.page_no: int = 0
        """The current page number."""
        self.list: list[T] = []
        """The items shown in the list"""
        if self.__total_pages > 0:
            self.__set_list()
        """The base URI parameters."""
        self.page_links: list[Link] = self.__get_page_links()
        """The pagination links."""
        self.page_sizes: list[Link] = self.__get_page_sizes()
        """The links to switch the number of items in a page."""

    def __get_page_size(self) -> int:
        """Returns the page size.

        :return: The page size.
        :raise Redirection: When the page size is malformed.
        """
        if "page-size" not in request.args:
            return self.DEFAULT_PAGE_SIZE
        try:
            page_size: int = int(request.args["page-size"])
        except ValueError:
            raise Redirection(self.__uri_set("page-size", None))
        if page_size == self.DEFAULT_PAGE_SIZE:
            raise Redirection(self.__uri_set("page-size", None))
        return page_size

    def __set_list(self) -> None:
        """Sets the items to show in the list.

        :return: None.
        """
        self.__default_page_no = self.__total_pages if self.__is_reversed \
            else 1
        self.page_no = self.__get_page_no()
        if self.page_no < 1:
            self.page_no = 1
        if self.page_no > self.__total_pages:
            self.page_no = self.__total_pages
        lower_bound: int = (self.page_no - 1) * self.page_size
        upper_bound: int = lower_bound + self.page_size
        if upper_bound > len(self.__items):
            upper_bound = len(self.__items)
        self.list = self.__items[lower_bound:upper_bound]

    def __get_page_no(self) -> int:
        """Returns the page number.

        :return: The page number.
        :raise Redirection: When the page number is malformed.
        """
        if "page-no" not in request.args:
            return self.__default_page_no
        try:
            page_no: int = int(request.args["page-no"])
        except ValueError:
            raise Redirection(self.__uri_set("page-no", None))
        if page_no == self.__default_page_no:
            raise Redirection(self.__uri_set("page-no", None))
        if page_no < 1:
            if not self.__is_reversed:
                raise Redirection(self.__uri_set("page-no", None))
            raise Redirection(self.__uri_set("page-no", "1"))
        if page_no > self.__total_pages:
            if self.__is_reversed:
                raise Redirection(self.__uri_set("page-no", None))
            raise Redirection(self.__uri_set("page-no",
                                             str(self.__total_pages)))
        return page_no

    def __get_page_links(self) -> list[Link]:
        """Returns the page links in the pagination navigation.

        :return: The page links in the pagination navigation.
        """
        if self.__total_pages < 2:
            return []
        uri: str | None
        links: list[Link] = []

        # The previous page.
        uri = None if self.page_no == 1 else self.__uri_page(self.page_no - 1)
        links.append(Link(gettext("Previous"), uri, is_for_mobile=True))

        # The first page.
        if self.page_no > 1:
            links.append(Link("1", self.__uri_page(1)))

        # The eclipse of the previous pages.
        if self.page_no - 3 == 2:
            links.append(Link(str(self.page_no - 3),
                              self.__uri_page(self.page_no - 3)))
        elif self.page_no - 3 > 2:
            links.append(Link("…"))

        # The previous two pages.
        if self.page_no - 2 > 1:
            links.append(Link(str(self.page_no - 2),
                              self.__uri_page(self.page_no - 2)))
        if self.page_no - 1 > 1:
            links.append(Link(str(self.page_no - 1),
                              self.__uri_page(self.page_no - 1)))

        # The current page.
        links.append(Link(str(self.page_no), self.__uri_page(self.page_no),
                          is_current=True))

        # The next two pages.
        if self.page_no + 1 < self.__total_pages:
            links.append(Link(str(self.page_no + 1),
                              self.__uri_page(self.page_no + 1)))
        if self.page_no + 2 < self.__total_pages:
            links.append(Link(str(self.page_no + 2),
                              self.__uri_page(self.page_no + 2)))

        # The eclipse of the next pages.
        if self.page_no + 3 == self.__total_pages - 1:
            links.append(Link(str(self.page_no + 3),
                              self.__uri_page(self.page_no + 3)))
        elif self.page_no + 3 < self.__total_pages - 1:
            links.append(Link("…"))

        # The last page.
        if self.page_no < self.__total_pages:
            links.append(Link(str(self.__total_pages),
                              self.__uri_page(self.__total_pages)))

        # The next page.
        uri = None if self.page_no == self.__total_pages \
            else self.__uri_page(self.page_no + 1)
        links.append(Link(gettext("Next"), uri, is_for_mobile=True))

        return links

    def __uri_page(self, page_no: int) -> str:
        """Returns the URI of a page.

        :param page_no: The page number.
        :return: The URI of the page.
        """
        if page_no == self.page_no:
            return self.__current_uri
        if page_no == self.__default_page_no:
            return self.__uri_set("page-no", None)
        return self.__uri_set("page-no", str(page_no))

    def __get_page_sizes(self) -> list[Link]:
        """Returns the available page sizes.

        :return: The available page sizes.
        """
        return [Link(str(x), self.__uri_size(x),
                     is_current=x == self.page_size)
                for x in self.AVAILABLE_PAGE_SIZES]

    def __uri_size(self, page_size: int) -> str:
        """Returns the URI of a page size.

        :param page_size: The page size.
        :return: The URI of the page size.
        """
        if page_size == self.page_size:
            return self.__current_uri
        if page_size == self.DEFAULT_PAGE_SIZE:
            return self.__uri_set("page-size", None)
        return self.__uri_set("page-size", str(page_size))

    def __uri_set(self, name: str, value: str | None) -> str:
        """Raises current URI with a parameter set.

        :param name: The name of the parameter.
        :param value: The value, or None to remove the parameter.
        :return: The URI with the parameter set.
        """
        uri_p: ParseResult = urlparse(self.__current_uri)
        params: list[tuple[str, str]] = parse_qsl(uri_p.query)

        # Try to keep the position of the parameter.
        i: int = 0
        is_found: bool = False
        while i < len(params):
            if params[i][0] == name:
                if is_found or value is None:
                    params = params[:i] + params[i + 1:]
                    continue
                params[i] = (name, value)
            i = i + 1

        parts: list[str] = list(uri_p)
        parts[4] = urlencode(params)
        return urlunparse(parts)
