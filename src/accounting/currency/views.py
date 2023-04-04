# The Mia! Accounting Project.
# Author: imacat@mail.imacat.idv.tw (imacat), 2023/2/6

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
"""The views for the currency management.

"""
from urllib.parse import urlencode, parse_qsl

import sqlalchemy as sa
from flask import Blueprint, render_template, redirect, session, request, \
    flash, url_for
from werkzeug.datastructures import ImmutableMultiDict

from accounting import db
from accounting.locale import lazy_gettext
from accounting.models import Currency
from accounting.utils.cast import s
from accounting.utils.flash_errors import flash_form_errors
from accounting.utils.next_uri import inherit_next, or_next
from accounting.utils.pagination import Pagination
from accounting.utils.permission import has_permission, can_view, can_edit
from accounting.utils.user import get_current_user_pk
from .forms import CurrencyForm

bp: Blueprint = Blueprint("currency", __name__)
"""The view blueprint for the currency management."""
api_bp: Blueprint = Blueprint("currency-api", __name__)
"""The view blueprint for the currency management API."""


@bp.get("", endpoint="list")
@has_permission(can_view)
def list_currencies() -> str:
    """Lists the currencies.

    :return: The currency list.
    """
    from .queries import get_currency_query
    currencies: list[Currency] = get_currency_query()
    pagination: Pagination = Pagination[Currency](currencies)
    return render_template("accounting/currency/list.html",
                           list=pagination.list, pagination=pagination)


@bp.get("/create", endpoint="create")
@has_permission(can_edit)
def show_add_currency_form() -> str:
    """Shows the form to add a currency.

    :return: The form to add a currency.
    """
    if "form" in session:
        form = CurrencyForm(ImmutableMultiDict(parse_qsl(session["form"])))
        del session["form"]
        form.validate()
    else:
        form = CurrencyForm()
    return render_template("accounting/currency/create.html",
                           form=form)


@bp.post("/store", endpoint="store")
@has_permission(can_edit)
def add_currency() -> redirect:
    """Adds a currency.

    :return: The redirection to the currency detail on success, or the currency
        creation form on error.
    """
    form = CurrencyForm(request.form)
    if not form.validate():
        flash_form_errors(form)
        session["form"] = urlencode(list(request.form.items()))
        return redirect(inherit_next(url_for("accounting.currency.create")))
    currency: Currency = Currency()
    form.populate_obj(currency)
    db.session.add(currency)
    db.session.commit()
    flash(s(lazy_gettext("The currency is added successfully.")), "success")
    return redirect(inherit_next(__get_detail_uri(currency)))


@bp.get("/<currency:currency>", endpoint="detail")
@has_permission(can_view)
def show_currency_detail(currency: Currency) -> str:
    """Shows the currency detail.

    :param currency: The currency.
    :return: The detail.
    """
    return render_template("accounting/currency/detail.html", obj=currency)


@bp.get("/<currency:currency>/edit", endpoint="edit")
@has_permission(can_edit)
def show_currency_edit_form(currency: Currency) -> str:
    """Shows the form to edit a currency.

    :param currency: The currency.
    :return: The form to edit the currency.
    """
    form: CurrencyForm
    if "form" in session:
        form = CurrencyForm(ImmutableMultiDict(parse_qsl(session["form"])))
        del session["form"]
        form.validate()
    else:
        form = CurrencyForm(obj=currency)
    return render_template("accounting/currency/edit.html",
                           currency=currency, form=form)


@bp.post("/<currency:currency>/update", endpoint="update")
@has_permission(can_edit)
def update_currency(currency: Currency) -> redirect:
    """Updates a currency.

    :param currency: The currency.
    :return: The redirection to the currency detail on success, or the currency
        edit form on error.
    """
    form = CurrencyForm(request.form)
    form.obj_code = currency.code
    if not form.validate():
        flash_form_errors(form)
        session["form"] = urlencode(list(request.form.items()))
        return redirect(inherit_next(url_for("accounting.currency.edit",
                                             currency=currency)))
    with db.session.no_autoflush:
        form.populate_obj(currency)
    if not currency.is_modified:
        flash(s(lazy_gettext("The currency was not modified.")), "success")
        return redirect(inherit_next(__get_detail_uri(currency)))
    currency.updated_by_id = get_current_user_pk()
    currency.updated_at = sa.func.now()
    db.session.commit()
    flash(s(lazy_gettext("The currency is updated successfully.")), "success")
    return redirect(inherit_next(__get_detail_uri(currency)))


@bp.post("/<currency:currency>/delete", endpoint="delete")
@has_permission(can_edit)
def delete_currency(currency: Currency) -> redirect:
    """Deletes a currency.

    :param currency: The currency.
    :return: The redirection to the currency list on success, or the currency
        detail on error.
    """
    if not currency.can_delete:
        flash(s(lazy_gettext("The currency cannot be deleted.")), "error")
        return redirect(inherit_next(__get_detail_uri(currency)))
    currency.delete()
    db.session.commit()
    flash(s(lazy_gettext("The currency is deleted successfully.")), "success")
    return redirect(or_next(url_for("accounting.currency.list")))


@api_bp.get("/exists-code", endpoint="exists")
@has_permission(can_edit)
def exists_code() -> dict[str, bool]:
    """Validates whether a currency code exists.

    :return: Whether the currency code exists.
    """
    return {"exists": db.session.get(Currency, request.args["q"]) is not None}


def __get_detail_uri(currency: Currency) -> str:
    """Returns the detail URI of a currency.

    :param currency: The currency.
    :return: The detail URI of the currency.
    """
    return url_for("accounting.currency.detail", currency=currency)
