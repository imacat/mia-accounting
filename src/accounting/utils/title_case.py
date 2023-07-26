# The Mia! Accounting Project.
# Author: imacat@mail.imacat.idv.tw (imacat), 2023/7/29

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
"""The title case capitalization for the base account titles.
This follows the APA style title case capitalization.  See
https://apastyle.apa.org/style-grammar-guidelines/capitalization/title-case .

This module should not import any other module from the application.

"""
import re

CONJUNCTIONS: set[str] = {"and", "as", "but", "for", "if", "nor", "or", "so",
                          "yet"}
"""Short conjunctions."""
ARTICLES: set[str] = {"a", "an", "the"}
"""Articles."""
PREPOSITIONS: set[str] = {"as", "at", "by", "for", "in", "of", "on", "per",
                          "to", "up", "via"}
"""Short prepositions."""
MINOR_WORDS: set[str] \
    = CONJUNCTIONS.copy().union(ARTICLES).union(PREPOSITIONS)
"""Minor words that should be in lowercase."""
# Excludes "by" as in "1223 by-products"
MINOR_WORDS.remove("by")


def title_case(s: str) -> str:
    """Capitalize a title string for the base account titles.  Do not use it
    in other places.  This excludes "by" as in "1223 by-products".

    :param s: The title string.
    :return: The capitalized title string.
    """
    return re.sub(r"\w+", __cap_word, s)


def __cap_word(m: re.Match) -> str:
    """Capitalize a matched title word.

    :param m: The matched title word.
    :return: The capitalized title word.
    """
    if m.group(0).lower() in MINOR_WORDS:
        return m.group(0)
    return m.group(0).title()
