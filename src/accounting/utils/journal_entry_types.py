# The Mia! Accounting Project.
# Author: imacat@mail.imacat.idv.tw (imacat), 2023/3/4

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
"""The journal entry types.

"""
from enum import Enum


class JournalEntryType(Enum):
    """The journal entry types."""
    CASH_RECEIPT: str = "receipt"
    """The cash receipt journal entry."""
    CASH_DISBURSEMENT: str = "disbursement"
    """The cash disbursement journal entry."""
    TRANSFER: str = "transfer"
    """The transfer journal entry."""
