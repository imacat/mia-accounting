# The Mia! Accounting Project.
# Author: imacat@mail.imacat.idv.tw (imacat), 2023/3/15

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
"""The utilities to cast values into desired types, to avoid IDE warnings.

This module should not import any other module from the application.

"""
from typing import Any


def s(message: Any) -> str:
    """Casts the LazyString message to the string type.

    :param message: The message.
    :return: The binary expression itself.
    """
    return message
