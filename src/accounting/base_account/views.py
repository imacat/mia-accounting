# The Mia! Accounting Project.
# Author: imacat@mail.imacat.idv.tw (imacat), 2023/1/26

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
"""The views for the base account management.

"""
from flask import Blueprint, render_template

from accounting.models import BaseAccount
from accounting.utils.pagination import Pagination
from accounting.utils.permission import has_permission, can_view

bp: Blueprint = Blueprint("base-account", __name__)
"""The view blueprint for the base account management."""


@bp.get("", endpoint="list")
@has_permission(can_view)
def list_accounts() -> str:
    """Lists the base accounts.

    :return: The account list.
    """
    from .queries import get_base_account_query
    accounts: list[BaseAccount] = get_base_account_query()
    pagination: Pagination = Pagination[BaseAccount](accounts)
    return render_template("accounting/base-account/list.html",
                           list=pagination.list, pagination=pagination)


@bp.get("/<baseAccount:account>", endpoint="detail")
@has_permission(can_view)
def show_account_detail(account: BaseAccount) -> str:
    """Shows the account detail.

    :param account: The account.
    :return: The detail.
    """
    return render_template("accounting/base-account/detail.html", obj=account)

