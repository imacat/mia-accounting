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
"""The pagination utilities.

This module should not import any other module from the application.

"""
import typing as t
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse, \
    ParseResult

from flask import request
from werkzeug.routing import RequestRedirect

from accounting.locale import pgettext


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


DEFAULT_PAGE_SIZE: int = 10
"""The default page size."""

T = t.TypeVar("T")


class Pagination(t.Generic[T]):
    """The pagination utility."""

    def __init__(self, items: list[T], is_reversed: bool = False):
        """Constructs the pagination.

        :param items: The items.
        :param is_reversed: True if the default page is the last page, or False
            otherwise.
        :raise Redirection: When the pagination parameters are malformed.
        """
        pagination: AbstractPagination[T] = EmptyPagination[T]() \
            if len(items) == 0 \
            else NonEmptyPagination[T](items, is_reversed)
        self.is_paged: bool = pagination.is_paged
        """Whether there should be pagination."""
        self.list: list[T] = pagination.list
        """The items shown in the list"""
        self.pages: list[Link] = pagination.pages
        """The pages."""
        self.page_size: int = pagination.page_size
        """The number of items in a page."""
        self.page_size_options: list[Link] = pagination.page_size_options
        """The options to the number of items in a page."""


class AbstractPagination(t.Generic[T]):
    """An abstract pagination."""

    def __init__(self):
        """Constructs an empty pagination."""
        self.page_size: int = DEFAULT_PAGE_SIZE
        """The number of items in a page."""
        self.is_paged: bool = False
        """Whether there should be pagination."""
        self.list: list[T] = []
        """The items shown in the list"""
        self.pages: list[Link] = []
        """The pages."""
        self.page_size_options: list[Link] = []
        """The options to the number of items in a page."""


class EmptyPagination(AbstractPagination[T]):
    """The pagination from empty data."""
    pass


class NonEmptyPagination(AbstractPagination[T]):
    """The pagination with real data."""
    PAGE_SIZE_OPTION_VALUES: list[int] = [10, 100, 200]
    """The page size options."""

    def __init__(self, items: list[T], is_reversed: bool = False):
        """Constructs the pagination.

        :param items: The items.
        :param is_reversed: True if the default page is the last page, or False
            otherwise.
        :raise Redirection: When the pagination parameters are malformed.
        """
        super().__init__()
        self.__current_uri: str = request.full_path if request.query_string \
            else request.path
        """The current URI."""
        self.__is_reversed: bool = is_reversed
        """Whether the default page is the last page."""
        self.page_size = self.__get_page_size()
        self.__total_pages: int = int((len(items) - 1) / self.page_size) + 1
        """The total number of pages."""
        self.is_paged = self.__total_pages > 1
        self.__default_page_no: int = self.__total_pages \
            if self.__is_reversed else 1
        """The default page number."""
        self.__page_no: int = self.__get_page_no()
        """The current page number."""
        lower_bound: int = (self.__page_no - 1) * self.page_size
        upper_bound: int = lower_bound + self.page_size
        if upper_bound > len(items):
            upper_bound = len(items)
        self.list = items[lower_bound:upper_bound]
        self.pages = self.__get_pages()
        self.page_size_options = self.__get_page_size_options()

    def __get_page_size(self) -> int:
        """Returns the page size.

        :return: The page size.
        :raise Redirection: When the page size is malformed.
        """
        if "page-size" not in request.args:
            return DEFAULT_PAGE_SIZE
        try:
            page_size: int = int(request.args["page-size"])
        except ValueError:
            raise Redirection(self.__uri_set("page-size", None))
        if page_size == DEFAULT_PAGE_SIZE or page_size < 1:
            raise Redirection(self.__uri_set("page-size", None))
        return page_size

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

    def __get_pages(self) -> list[Link]:
        """Returns the page links in the pagination navigation.

        :return: The page links in the pagination navigation.
        """
        if not self.is_paged:
            return []
        uri: str | None
        links: list[Link] = []

        # The previous page.
        uri = None if self.__page_no == 1 \
            else self.__uri_page(self.__page_no - 1)
        links.append(Link(pgettext("Pagination|", "Previous"), uri,
                          is_for_mobile=True))

        # The first page.
        if self.__page_no > 1:
            links.append(Link("1", self.__uri_page(1)))

        # The eclipse of the previous pages.
        if self.__page_no - 3 == 2:
            links.append(Link(str(self.__page_no - 3),
                              self.__uri_page(self.__page_no - 3)))
        elif self.__page_no - 3 > 2:
            links.append(Link("…"))

        # The previous two pages.
        if self.__page_no - 2 > 1:
            links.append(Link(str(self.__page_no - 2),
                              self.__uri_page(self.__page_no - 2)))
        if self.__page_no - 1 > 1:
            links.append(Link(str(self.__page_no - 1),
                              self.__uri_page(self.__page_no - 1)))

        # The current page.
        links.append(Link(str(self.__page_no), self.__uri_page(self.__page_no),
                          is_current=True))

        # The next two pages.
        if self.__page_no + 1 < self.__total_pages:
            links.append(Link(str(self.__page_no + 1),
                              self.__uri_page(self.__page_no + 1)))
        if self.__page_no + 2 < self.__total_pages:
            links.append(Link(str(self.__page_no + 2),
                              self.__uri_page(self.__page_no + 2)))

        # The eclipse of the next pages.
        if self.__page_no + 3 == self.__total_pages - 1:
            links.append(Link(str(self.__page_no + 3),
                              self.__uri_page(self.__page_no + 3)))
        elif self.__page_no + 3 < self.__total_pages - 1:
            links.append(Link("…"))

        # The last page.
        if self.__page_no < self.__total_pages:
            links.append(Link(str(self.__total_pages),
                              self.__uri_page(self.__total_pages)))

        # The next page.
        uri = None if self.__page_no == self.__total_pages \
            else self.__uri_page(self.__page_no + 1)
        links.append(Link(pgettext("Pagination|", "Next"), uri,
                          is_for_mobile=True))

        return links

    def __uri_page(self, page_no: int) -> str:
        """Returns the URI of a page.

        :param page_no: The page number.
        :return: The URI of the page.
        """
        if page_no == self.__page_no:
            return self.__current_uri
        if page_no == self.__default_page_no:
            return self.__uri_set("page-no", None)
        return self.__uri_set("page-no", str(page_no))

    def __get_page_size_options(self) -> list[Link]:
        """Returns the page size options.

        :return: The page size options.
        """
        if not self.is_paged:
            return []
        return [Link(str(x), self.__uri_size(x),
                     is_current=x == self.page_size)
                for x in self.PAGE_SIZE_OPTION_VALUES]

    def __uri_size(self, page_size: int) -> str:
        """Returns the URI of a page size.

        :param page_size: The page size.
        :return: The URI of the page size.
        """
        if page_size == self.page_size:
            return self.__current_uri
        if page_size == DEFAULT_PAGE_SIZE:
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
                is_found = True
            i = i + 1
        if not is_found and value is not None:
            params.append((name, value))

        parts: list[str] = list(uri_p)
        parts[4] = urlencode(params)
        return urlunparse(parts)
