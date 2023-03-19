# The Mia! Accounting Flask Project.
# Author: imacat@mail.imacat.idv.tw (imacat), 2023/2/18

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
"""The views for the voucher management.

"""
from datetime import date
from urllib.parse import parse_qsl, urlencode

import sqlalchemy as sa
from flask import Blueprint, render_template, session, redirect, request, \
    flash, url_for
from werkzeug.datastructures import ImmutableMultiDict

from accounting import db
from accounting.locale import lazy_gettext
from accounting.models import Voucher
from accounting.utils.cast import s
from accounting.utils.flash_errors import flash_form_errors
from accounting.utils.next_uri import inherit_next, or_next
from accounting.utils.permission import has_permission, can_view, can_edit
from accounting.utils.voucher_types import VoucherType
from accounting.utils.user import get_current_user_pk
from .forms import sort_vouchers_in, VoucherReorderForm
from .template_filters import with_type, to_transfer, format_amount_input, \
    text2html
from .utils.operators import VoucherOperator, VOUCHER_TYPE_TO_OP, \
    get_voucher_op

bp: Blueprint = Blueprint("voucher", __name__)
"""The view blueprint for the voucher management."""
bp.add_app_template_filter(with_type, "accounting_voucher_with_type")
bp.add_app_template_filter(to_transfer, "accounting_voucher_to_transfer")
bp.add_app_template_filter(format_amount_input,
                           "accounting_voucher_format_amount_input")
bp.add_app_template_filter(text2html, "accounting_voucher_text2html")


@bp.get("/create/<voucherType:voucher_type>", endpoint="create")
@has_permission(can_edit)
def show_add_voucher_form(voucher_type: VoucherType) -> str:
    """Shows the form to add a voucher.

    :param voucher_type: The voucher type.
    :return: The form to add a voucher.
    """
    voucher_op: VoucherOperator = VOUCHER_TYPE_TO_OP[voucher_type]
    form: voucher_op.form
    if "form" in session:
        form = voucher_op.form(ImmutableMultiDict(parse_qsl(session["form"])))
        del session["form"]
        form.validate()
    else:
        form = voucher_op.form()
        form.date.data = date.today()
    return voucher_op.render_create_template(form)


@bp.post("/store/<voucherType:voucher_type>", endpoint="store")
@has_permission(can_edit)
def add_voucher(voucher_type: VoucherType) -> redirect:
    """Adds a voucher.

    :param voucher_type: The voucher type.
    :return: The redirection to the voucher detail on success, or the
        voucher creation form on error.
    """
    voucher_op: VoucherOperator = VOUCHER_TYPE_TO_OP[voucher_type]
    form: voucher_op.form = voucher_op.form(request.form)
    if not form.validate():
        flash_form_errors(form)
        session["form"] = urlencode(list(request.form.items()))
        return redirect(inherit_next(with_type(
            url_for("accounting.voucher.create", voucher_type=voucher_type))))
    voucher: Voucher = Voucher()
    form.populate_obj(voucher)
    db.session.add(voucher)
    db.session.commit()
    flash(s(lazy_gettext("The voucher is added successfully")), "success")
    return redirect(inherit_next(__get_detail_uri(voucher)))


@bp.get("/<voucher:voucher>", endpoint="detail")
@has_permission(can_view)
def show_voucher_detail(voucher: Voucher) -> str:
    """Shows the voucher detail.

    :param voucher: The voucher.
    :return: The detail.
    """
    voucher_op: VoucherOperator = get_voucher_op(voucher)
    return voucher_op.render_detail_template(voucher)


@bp.get("/<voucher:voucher>/edit", endpoint="edit")
@has_permission(can_edit)
def show_voucher_edit_form(voucher: Voucher) -> str:
    """Shows the form to edit a voucher.

    :param voucher: The voucher.
    :return: The form to edit the voucher.
    """
    voucher_op: VoucherOperator = get_voucher_op(voucher, is_check_as=True)
    form: voucher_op.form
    if "form" in session:
        form = voucher_op.form(ImmutableMultiDict(parse_qsl(session["form"])))
        del session["form"]
        form.obj = voucher
        form.validate()
    else:
        form = voucher_op.form(obj=voucher)
    return voucher_op.render_edit_template(voucher, form)


@bp.post("/<voucher:voucher>/update", endpoint="update")
@has_permission(can_edit)
def update_voucher(voucher: Voucher) -> redirect:
    """Updates a voucher.

    :param voucher: The voucher.
    :return: The redirection to the voucher detail on success, or the voucher
        edit form on error.
    """
    voucher_op: VoucherOperator = get_voucher_op(voucher, is_check_as=True)
    form: voucher_op.form = voucher_op.form(request.form)
    form.obj = voucher
    if not form.validate():
        flash_form_errors(form)
        session["form"] = urlencode(list(request.form.items()))
        return redirect(inherit_next(with_type(
            url_for("accounting.voucher.edit", voucher=voucher))))
    with db.session.no_autoflush:
        form.populate_obj(voucher)
    if not form.is_modified:
        flash(s(lazy_gettext("The voucher was not modified.")), "success")
        return redirect(inherit_next(__get_detail_uri(voucher)))
    voucher.updated_by_id = get_current_user_pk()
    voucher.updated_at = sa.func.now()
    db.session.commit()
    flash(s(lazy_gettext("The voucher is updated successfully.")), "success")
    return redirect(inherit_next(__get_detail_uri(voucher)))


@bp.post("/<voucher:voucher>/delete", endpoint="delete")
@has_permission(can_edit)
def delete_voucher(voucher: Voucher) -> redirect:
    """Deletes a voucher.

    :param voucher: The voucher.
    :return: The redirection to the voucher list on success, or the voucher
        detail on error.
    """
    voucher.delete()
    sort_vouchers_in(voucher.date, voucher.id)
    db.session.commit()
    flash(s(lazy_gettext("The voucher is deleted successfully.")), "success")
    return redirect(or_next(__get_default_page_uri()))


@bp.get("/dates/<date:voucher_date>", endpoint="order")
@has_permission(can_view)
def show_voucher_order(voucher_date: date) -> str:
    """Shows the order of the vouchers in a same date.

    :param voucher_date: The date.
    :return: The order of the vouchers in the date.
    """
    vouchers: list[Voucher] = Voucher.query \
        .filter(Voucher.date == voucher_date) \
        .order_by(Voucher.no).all()
    return render_template("accounting/voucher/order.html",
                           date=voucher_date, list=vouchers)


@bp.post("/dates/<date:voucher_date>", endpoint="sort")
@has_permission(can_edit)
def sort_vouchers(voucher_date: date) -> redirect:
    """Reorders the vouchers in a date.

    :param voucher_date: The date.
    :return: The redirection to the incoming account or the account list.  The
        reordering operation does not fail.
    """
    form: VoucherReorderForm = VoucherReorderForm(voucher_date)
    form.save_order()
    if not form.is_modified:
        flash(s(lazy_gettext("The order was not modified.")), "success")
        return redirect(or_next(__get_default_page_uri()))
    db.session.commit()
    flash(s(lazy_gettext("The order is updated successfully.")), "success")
    return redirect(or_next(__get_default_page_uri()))


def __get_detail_uri(voucher: Voucher) -> str:
    """Returns the detail URI of a voucher.

    :param voucher: The voucher.
    :return: The detail URI of the voucher.
    """
    return url_for("accounting.voucher.detail", voucher=voucher)


def __get_default_page_uri() -> str:
    """Returns the URI for the default page.

    :return: The URI for the default page.
    """
    return url_for("accounting.report.default")
