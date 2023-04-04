# The Mia! Accounting Project.
# Author: imacat@mail.imacat.idv.tw (imacat), 2023/2/1

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
"""The text stripper for the form fields.

This module should not import any other module from the application.

"""
import re


def strip_text(s: str | None) -> str | None:
    """The filter to strip the leading and trailing white spaces of text.

    :param s: The text input string.
    :return: The filtered string.
    """
    if s is None:
        return None
    s = s.strip()
    return s if s != "" else None


def strip_multiline_text(s: str | None) -> str | None:
    """The filter to strip a piece of multi-line text.

    :param s: The text input string.
    :return: The filtered string.
    """
    if s is None:
        return None
    s = re.sub(r"^\s*\n", "", s.rstrip())
    return s if s != "" else None
