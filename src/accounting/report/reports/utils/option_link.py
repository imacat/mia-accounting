# The Mia! Accounting Flask Project.
# Author: imacat@mail.imacat.idv.tw (imacat), 2023/3/5

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
"""The option link.

"""


class OptionLink:
    """An option link."""

    def __init__(self, title: str, url: str, is_active: bool,
                 fa_icon: str | None = None):
        """Constructs an option link.

        :param title: The title.
        :param url: The URI.
        :param is_active: True if active, or False otherwise
        """
        self.title: str = title
        self.url: str = url
        self.is_active: bool = is_active
        self.fa_icon: str | None = fa_icon
