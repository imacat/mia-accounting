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
"""The query keyword parser.

This module should not import any other module from the application.

"""
import re


def parse_query_keywords(q: str | None) -> list[str]:
    """Returns the query keywords by the query parameter.

    :param q: The query parameter.
    :return: The query keywords.
    """
    if q is None:
        return []
    q = q.strip()
    if q == "":
        return []
    keywords: list[str] = []
    while q is not None:
        m: re.Match = re.match(r"(?:\"([^\"]+)\"|(\S+))(?:\s+(.+)|)$", q)
        if m.group(1) is not None:
            keywords.append(m.group(1))
        else:
            keywords.append(m.group(2))
        q = m.group(3)
    return keywords
