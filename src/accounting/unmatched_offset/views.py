# The Mia! Accounting Project.
# Author: imacat@mail.imacat.idv.tw (imacat), 2023/4/8

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
"""The views for the unmatched offset management.

"""
from flask import Blueprint, render_template, redirect, url_for, flash

from accounting import db
from accounting.locale import lazy_gettext
from accounting.models import JournalEntryLineItem, Account
from accounting.utils.cast import s
from accounting.utils.offset_matcher import OffsetMatcher
from accounting.utils.pagination import Pagination
from accounting.utils.permission import has_permission, can_admin
from .queries import get_accounts_with_unmatched_offsets

bp: Blueprint = Blueprint("unmatched-offset", __name__)
"""The view blueprint for the unmatched offset management."""


@bp.get("", endpoint="dashboard")
@has_permission(can_admin)
def show_offset_dashboard() -> str:
    """Shows the dashboard about offsets.

    :return: The dashboard about offsets.
    """
    return render_template("accounting/unmatched-offset/dashboard.html",
                           list=get_accounts_with_unmatched_offsets())


@bp.get("<needOffsetAccount:account>", endpoint="list")
@has_permission(can_admin)
def show_unmatched_offsets(account: Account) -> str:
    """Shows the unmatched offsets in an account.

    :return: The unmatched offsets in an account.
    """
    matcher: OffsetMatcher = OffsetMatcher(account)
    pagination: Pagination \
        = Pagination[JournalEntryLineItem](matcher.unmatched_offsets,
                                           is_reversed=True)
    return render_template("accounting/unmatched-offset/list.html",
                           matcher=matcher,
                           list=pagination.list, pagination=pagination)


@bp.post("<needOffsetAccount:account>", endpoint="match")
@has_permission(can_admin)
def match_offsets(account: Account) -> redirect:
    """Matches the original line items with their offsets.

    :return: Redirection to the view of the unmatched offsets.
    """
    matcher: OffsetMatcher = OffsetMatcher(account)
    if not matcher.is_having_matches:
        flash(s(lazy_gettext("No more offset to match automatically.")),
              "success")
        return redirect(url_for("accounting.unmatched-offset.list",
                                account=account))
    matcher.match()
    db.session.commit()
    flash(s(lazy_gettext(
        "Matches %(matches)s from %(total)s unapplied line items.",
        matches=matcher.matches, total=matcher.total)), "success")
    return redirect(url_for("accounting.unmatched-offset.list",
                            account=account))
