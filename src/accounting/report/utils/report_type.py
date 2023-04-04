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
"""The report types.

"""
from enum import Enum


class ReportType(Enum):
    """The report types."""
    JOURNAL: str = "journal"
    """The journal."""
    LEDGER: str = "ledger"
    """The ledger."""
    INCOME_EXPENSES: str = "income-expenses"
    """The income and expenses log."""
    TRIAL_BALANCE: str = "trial-balance"
    """The trial balance."""
    INCOME_STATEMENT: str = "income-statement"
    """The income statement."""
    BALANCE_SHEET: str = "balance-sheet"
    """The balance sheet."""
    SEARCH: str = "search"
    """The search."""
