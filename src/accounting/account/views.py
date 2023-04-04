# The Mia! Accounting Project.
# Author: imacat@mail.imacat.idv.tw (imacat), 2023/1/30

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
"""The views for the account management.

"""
from urllib.parse import parse_qsl, urlencode

import sqlalchemy as sa
from flask import Blueprint, render_template, session, redirect, flash, \
    url_for, request
from werkzeug.datastructures import ImmutableMultiDict

from accounting import db
from accounting.locale import lazy_gettext
from accounting.models import Account, BaseAccount
from accounting.utils.cast import s
from accounting.utils.flash_errors import flash_form_errors
from accounting.utils.next_uri import inherit_next, or_next
from accounting.utils.pagination import Pagination
from accounting.utils.permission import can_view, has_permission, can_edit
from accounting.utils.user import get_current_user_pk
from .forms import AccountForm, sort_accounts_in, AccountReorderForm
from .queries import get_account_query

bp: Blueprint = Blueprint("account", __name__)
"""The view blueprint for the account management."""


@bp.get("", endpoint="list")
@has_permission(can_view)
def list_accounts() -> str:
    """Lists the accounts.

    :return: The account list.
    """
    accounts: list[BaseAccount] = get_account_query()
    pagination: Pagination = Pagination[BaseAccount](accounts)
    return render_template("accounting/account/list.html",
                           list=pagination.list, pagination=pagination)


@bp.get("/create", endpoint="create")
@has_permission(can_edit)
def show_add_account_form() -> str:
    """Shows the form to add an account.

    :return: The form to add an account.
    """
    if "form" in session:
        form = AccountForm(ImmutableMultiDict(parse_qsl(session["form"])))
        del session["form"]
        form.validate()
    else:
        form = AccountForm()
    return render_template("accounting/account/create.html",
                           form=form)


@bp.post("/store", endpoint="store")
@has_permission(can_edit)
def add_account() -> redirect:
    """Adds an account.

    :return: The redirection to the account detail on success, or the account
        creation form on error.
    """
    form = AccountForm(request.form)
    if not form.validate():
        flash_form_errors(form)
        session["form"] = urlencode(list(request.form.items()))
        return redirect(inherit_next(url_for("accounting.account.create")))
    account: Account = Account()
    form.populate_obj(account)
    db.session.add(account)
    db.session.commit()
    flash(s(lazy_gettext("The account is added successfully")), "success")
    return redirect(inherit_next(__get_detail_uri(account)))


@bp.get("/<account:account>", endpoint="detail")
@has_permission(can_view)
def show_account_detail(account: Account) -> str:
    """Shows the account detail.

    :param account: The account.
    :return: The detail.
    """
    return render_template("accounting/account/detail.html", obj=account)


@bp.get("/<account:account>/edit", endpoint="edit")
@has_permission(can_edit)
def show_account_edit_form(account: Account) -> str:
    """Shows the form to edit an account.

    :param account: The account.
    :return: The form to edit the account.
    """
    form: AccountForm
    if "form" in session:
        form = AccountForm(ImmutableMultiDict(parse_qsl(session["form"])))
        del session["form"]
        form.validate()
    else:
        form = AccountForm(obj=account)
    return render_template("accounting/account/edit.html",
                           account=account, form=form)


@bp.post("/<account:account>/update", endpoint="update")
@has_permission(can_edit)
def update_account(account: Account) -> redirect:
    """Updates an account.

    :param account: The account.
    :return: The redirection to the account detail on success, or the account
        edit form on error.
    """
    form = AccountForm(request.form)
    if not form.validate():
        flash_form_errors(form)
        session["form"] = urlencode(list(request.form.items()))
        return redirect(inherit_next(url_for("accounting.account.edit",
                                             account=account)))
    with db.session.no_autoflush:
        form.populate_obj(account)
    if not account.is_modified:
        flash(s(lazy_gettext("The account was not modified.")), "success")
        return redirect(inherit_next(__get_detail_uri(account)))
    account.updated_by_id = get_current_user_pk()
    account.updated_at = sa.func.now()
    db.session.commit()
    flash(s(lazy_gettext("The account is updated successfully.")), "success")
    return redirect(inherit_next(__get_detail_uri(account)))


@bp.post("/<account:account>/delete", endpoint="delete")
@has_permission(can_edit)
def delete_account(account: Account) -> redirect:
    """Deletes an account.

    :param account: The account.
    :return: The redirection to the account list on success, or the account
        detail on error.
    """
    if not account.can_delete:
        flash(s(lazy_gettext("The account cannot be deleted.")), "error")
        return redirect(inherit_next(__get_detail_uri(account)))
    account.delete()
    sort_accounts_in(account.base_code, account.id)
    db.session.commit()
    flash(s(lazy_gettext("The account is deleted successfully.")), "success")
    return redirect(or_next(__get_list_uri()))


@bp.get("/bases/<baseAccount:base>", endpoint="order")
@has_permission(can_view)
def show_account_order(base: BaseAccount) -> str:
    """Shows the order of the accounts under a same base account.

    :param base: The base account.
    :return: The order of the accounts under the base account.
    """
    return render_template("accounting/account/order.html", base=base)


@bp.post("/bases/<baseAccount:base>", endpoint="sort")
@has_permission(can_edit)
def sort_accounts(base: BaseAccount) -> redirect:
    """Reorders the accounts under a base account.

    :param base: The base account.
    :return: The redirection to the incoming account or the account list.  The
        reordering operation does not fail.
    """
    form: AccountReorderForm = AccountReorderForm(base)
    form.save_order()
    if not form.is_modified:
        flash(s(lazy_gettext("The order was not modified.")), "success")
        return redirect(or_next(__get_list_uri()))
    db.session.commit()
    flash(s(lazy_gettext("The order is updated successfully.")), "success")
    return redirect(or_next(__get_list_uri()))


def __get_detail_uri(account: Account) -> str:
    """Returns the detail URI of an account.

    :param account: The account.
    :return: The detail URI of the account.
    """
    return url_for("accounting.account.detail", account=account)


def __get_list_uri() -> str:
    """Returns the account list URI.

    :return: The account list URI.
    """
    return url_for("accounting.account.list")
