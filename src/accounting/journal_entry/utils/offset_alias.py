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
"""The SQLAlchemy alias for the offset items.

"""
import typing as t

import sqlalchemy as sa

from accounting.models import JournalEntryLineItem


def offset_alias() -> sa.Alias:
    """Returns the SQLAlchemy alias for the offset items.

    :return: The SQLAlchemy alias for the offset items.
    """

    def as_from(model_cls: t.Any) -> sa.FromClause:
        return model_cls

    def as_alias(alias: t.Any) -> sa.Alias:
        return alias

    return as_alias(sa.alias(as_from(JournalEntryLineItem), name="offset"))
