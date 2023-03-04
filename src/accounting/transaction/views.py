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
"""The views for the transaction management.

"""
from datetime import date
from urllib.parse import parse_qsl, urlencode

import sqlalchemy as sa
from flask import Blueprint, render_template, session, redirect, request, \
    flash, url_for
from werkzeug.datastructures import ImmutableMultiDict

from accounting import db
from accounting.locale import lazy_gettext
from accounting.models import Transaction
from accounting.utils.flash_errors import flash_form_errors
from accounting.utils.next_uri import inherit_next, or_next
from accounting.utils.pagination import Pagination
from accounting.utils.permission import has_permission, can_view, can_edit
from accounting.utils.txn_types import TransactionTypeEnum
from accounting.utils.user import get_current_user_pk
from .operators import TransactionOperator, TXN_ENUM_TO_OP, get_txn_op
from .forms import sort_transactions_in, TransactionReorderForm
from .queries import get_transaction_query
from .template_filters import with_type, to_transfer, format_amount_input, \
    text2html

bp: Blueprint = Blueprint("transaction", __name__)
"""The view blueprint for the transaction management."""
bp.add_app_template_filter(with_type, "accounting_txn_with_type")
bp.add_app_template_filter(to_transfer, "accounting_txn_to_transfer")
bp.add_app_template_filter(format_amount_input,
                           "accounting_txn_format_amount_input")
bp.add_app_template_filter(text2html, "accounting_txn_text2html")


@bp.get("", endpoint="list")
@has_permission(can_view)
def list_transactions() -> str:
    """Lists the transactions.

    :return: The transaction list.
    """
    transactions: list[Transaction] = get_transaction_query()
    pagination: Pagination = Pagination[Transaction](transactions)
    return render_template("accounting/transaction/list.html",
                           list=pagination.list, pagination=pagination,
                           txn_types=TransactionTypeEnum)


@bp.get("/create/<transactionType:txn_type>", endpoint="create")
@has_permission(can_edit)
def show_add_transaction_form(txn_type: TransactionTypeEnum) -> str:
    """Shows the form to add a transaction.

    :param txn_type: The transaction type.
    :return: The form to add a transaction.
    """
    txn_op: TransactionOperator = TXN_ENUM_TO_OP[txn_type]
    form: txn_op.form
    if "form" in session:
        form = txn_op.form(ImmutableMultiDict(parse_qsl(session["form"])))
        del session["form"]
        form.validate()
    else:
        form = txn_op.form()
    return txn_op.render_create_template(form)


@bp.post("/store/<transactionType:txn_type>", endpoint="store")
@has_permission(can_edit)
def add_transaction(txn_type: TransactionTypeEnum) -> redirect:
    """Adds a transaction.

    :param txn_type: The transaction type.
    :return: The redirection to the transaction detail on success, or the
        transaction creation form on error.
    """
    txn_op: TransactionOperator = TXN_ENUM_TO_OP[txn_type]
    form: txn_op.form = txn_op.form(request.form)
    if not form.validate():
        flash_form_errors(form)
        session["form"] = urlencode(list(request.form.items()))
        return redirect(inherit_next(with_type(
            url_for("accounting.transaction.create", txn_type=txn_type))))
    txn: Transaction = Transaction()
    form.populate_obj(txn)
    db.session.add(txn)
    db.session.commit()
    flash(lazy_gettext("The transaction is added successfully"), "success")
    return redirect(inherit_next(__get_detail_uri(txn)))


@bp.get("/<transaction:txn>", endpoint="detail")
@has_permission(can_view)
def show_transaction_detail(txn: Transaction) -> str:
    """Shows the transaction detail.

    :param txn: The transaction.
    :return: The detail.
    """
    txn_op: TransactionOperator = get_txn_op(txn)
    return txn_op.render_detail_template(txn)


@bp.get("/<transaction:txn>/edit", endpoint="edit")
@has_permission(can_edit)
def show_transaction_edit_form(txn: Transaction) -> str:
    """Shows the form to edit a transaction.

    :param txn: The transaction.
    :return: The form to edit the transaction.
    """
    txn_op: TransactionOperator = get_txn_op(txn)
    form: txn_op.form
    if "form" in session:
        form = txn_op.form(ImmutableMultiDict(parse_qsl(session["form"])))
        del session["form"]
        form.validate()
    else:
        form = txn_op.form(obj=txn)
    return txn_op.render_edit_template(txn, form)


@bp.post("/<transaction:txn>/update", endpoint="update")
@has_permission(can_edit)
def update_transaction(txn: Transaction) -> redirect:
    """Updates a transaction.

    :param txn: The transaction.
    :return: The redirection to the transaction detail on success, or the
        transaction edit form on error.
    """
    txn_op: TransactionOperator = get_txn_op(txn)
    form: txn_op.form = txn_op.form(request.form)
    if not form.validate():
        flash_form_errors(form)
        session["form"] = urlencode(list(request.form.items()))
        return redirect(inherit_next(with_type(
            url_for("accounting.transaction.edit", txn=txn))))
    with db.session.no_autoflush:
        form.populate_obj(txn)
    if not form.is_modified:
        flash(lazy_gettext("The transaction was not modified."), "success")
        return redirect(inherit_next(with_type(__get_detail_uri(txn))))
    txn.updated_by_id = get_current_user_pk()
    txn.updated_at = sa.func.now()
    db.session.commit()
    flash(lazy_gettext("The transaction is updated successfully."), "success")
    return redirect(inherit_next(with_type(__get_detail_uri(txn))))


@bp.post("/<transaction:txn>/delete", endpoint="delete")
@has_permission(can_edit)
def delete_transaction(txn: Transaction) -> redirect:
    """Deletes a transaction.

    :param txn: The transaction.
    :return: The redirection to the transaction list on success, or the
        transaction detail on error.
    """
    txn.delete()
    sort_transactions_in(txn.date, txn.id)
    db.session.commit()
    flash(lazy_gettext("The transaction is deleted successfully."), "success")
    return redirect(or_next(with_type(url_for("accounting.transaction.list"))))


@bp.get("/dates/<date:txn_date>", endpoint="order")
@has_permission(can_view)
def show_transaction_order(txn_date: date) -> str:
    """Shows the order of the transactions in a same date.

    :param txn_date: The date.
    :return: The order of the transactions in the date.
    """
    transactions: list[Transaction] = Transaction.query \
        .filter(Transaction.date == txn_date) \
        .order_by(Transaction.no).all()
    return render_template("accounting/transaction/order.html",
                           date=txn_date, list=transactions)


@bp.post("/dates/<date:txn_date>", endpoint="sort")
@has_permission(can_edit)
def sort_accounts(txn_date: date) -> redirect:
    """Reorders the transactions in a date.

    :param txn_date: The date.
    :return: The redirection to the incoming account or the account list.  The
        reordering operation does not fail.
    """
    form: TransactionReorderForm = TransactionReorderForm(txn_date)
    form.save_order()
    if not form.is_modified:
        flash(lazy_gettext("The order was not modified."), "success")
        return redirect(or_next(url_for("accounting.account.list")))
    db.session.commit()
    flash(lazy_gettext("The order is updated successfully."), "success")
    return redirect(or_next(url_for("accounting.account.list")))


def __get_detail_uri(txn: Transaction) -> str:
    """Returns the detail URI of a transaction.

    :param txn: The transaction.
    :return: The detail URI of the transaction.
    """
    return url_for("accounting.transaction.detail", txn=txn)
