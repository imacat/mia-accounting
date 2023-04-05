# The Mia! Accounting Project.
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
"""The views for the journal entry management.

"""
from datetime import date
from urllib.parse import parse_qsl, urlencode

import sqlalchemy as sa
from flask import Blueprint, render_template, session, redirect, request, \
    flash, url_for
from werkzeug.datastructures import ImmutableMultiDict

from accounting import db
from accounting.locale import lazy_gettext
from accounting.models import JournalEntry
from accounting.utils.cast import s
from accounting.utils.flash_errors import flash_form_errors
from accounting.utils.next_uri import inherit_next, or_next
from accounting.utils.permission import has_permission, can_view, can_edit
from accounting.utils.journal_entry_types import JournalEntryType
from accounting.utils.user import get_current_user_pk
from .forms import sort_journal_entries_in, JournalEntryReorderForm
from .template_filters import with_type, to_transfer, format_amount_input, \
    text2html
from .utils.operators import JournalEntryOperator, JOURNAL_ENTRY_TYPE_TO_OP, \
    get_journal_entry_op

bp: Blueprint = Blueprint("journal-entry", __name__)
"""The view blueprint for the journal entry management."""
bp.add_app_template_filter(with_type, "accounting_journal_entry_with_type")
bp.add_app_template_filter(to_transfer, "accounting_journal_entry_to_transfer")
bp.add_app_template_filter(format_amount_input,
                           "accounting_journal_entry_format_amount_input")
bp.add_app_template_filter(text2html, "accounting_journal_entry_text2html")


@bp.get("/create/<journalEntryType:journal_entry_type>", endpoint="create")
@has_permission(can_edit)
def show_add_journal_entry_form(journal_entry_type: JournalEntryType) -> str:
    """Shows the form to add a journal entry.

    :param journal_entry_type: The journal entry type.
    :return: The form to add a journal entry.
    """
    journal_entry_op: JournalEntryOperator \
        = JOURNAL_ENTRY_TYPE_TO_OP[journal_entry_type]
    form: journal_entry_op.form
    if "form" in session:
        form = journal_entry_op.form(
            ImmutableMultiDict(parse_qsl(session["form"])))
        del session["form"]
        form.validate()
    else:
        form = journal_entry_op.form()
        form.date.data = date.today()
    return journal_entry_op.render_create_template(form)


@bp.post("/store/<journalEntryType:journal_entry_type>", endpoint="store")
@has_permission(can_edit)
def add_journal_entry(journal_entry_type: JournalEntryType) -> redirect:
    """Adds a journal entry.

    :param journal_entry_type: The journal entry type.
    :return: The redirection to the journal entry detail on success, or the
        journal entry creation form on error.
    """
    journal_entry_op: JournalEntryOperator \
        = JOURNAL_ENTRY_TYPE_TO_OP[journal_entry_type]
    form: journal_entry_op.form = journal_entry_op.form(request.form)
    if not form.validate():
        flash_form_errors(form)
        session["form"] = urlencode(list(request.form.items()))
        return redirect(inherit_next(with_type(
            url_for("accounting.journal-entry.create",
                    journal_entry_type=journal_entry_type))))
    journal_entry: JournalEntry = JournalEntry()
    form.populate_obj(journal_entry)
    db.session.add(journal_entry)
    db.session.commit()
    flash(s(lazy_gettext("The journal entry is added successfully.")),
          "success")
    return redirect(inherit_next(__get_detail_uri(journal_entry)))


@bp.get("/<journalEntry:journal_entry>", endpoint="detail")
@has_permission(can_view)
def show_journal_entry_detail(journal_entry: JournalEntry) -> str:
    """Shows the journal entry detail.

    :param journal_entry: The journal entry.
    :return: The detail.
    """
    journal_entry_op: JournalEntryOperator \
        = get_journal_entry_op(journal_entry)
    return journal_entry_op.render_detail_template(journal_entry)


@bp.get("/<journalEntry:journal_entry>/edit", endpoint="edit")
@has_permission(can_edit)
def show_journal_entry_edit_form(journal_entry: JournalEntry) -> str:
    """Shows the form to edit a journal entry.

    :param journal_entry: The journal entry.
    :return: The form to edit the journal entry.
    """
    journal_entry_op: JournalEntryOperator \
        = get_journal_entry_op(journal_entry, is_check_as=True)
    form: journal_entry_op.form
    if "form" in session:
        form = journal_entry_op.form(
            ImmutableMultiDict(parse_qsl(session["form"])))
        del session["form"]
        form.obj = journal_entry
        form.validate()
    else:
        form = journal_entry_op.form(obj=journal_entry)
    return journal_entry_op.render_edit_template(journal_entry, form)


@bp.post("/<journalEntry:journal_entry>/update", endpoint="update")
@has_permission(can_edit)
def update_journal_entry(journal_entry: JournalEntry) -> redirect:
    """Updates a journal entry.

    :param journal_entry: The journal entry.
    :return: The redirection to the journal entry detail on success, or the
        journal entry edit form on error.
    """
    journal_entry_op: JournalEntryOperator \
        = get_journal_entry_op(journal_entry, is_check_as=True)
    form: journal_entry_op.form = journal_entry_op.form(request.form)
    form.obj = journal_entry
    if not form.validate():
        flash_form_errors(form)
        session["form"] = urlencode(list(request.form.items()))
        return redirect(inherit_next(with_type(
            url_for("accounting.journal-entry.edit",
                    journal_entry=journal_entry))))
    with db.session.no_autoflush:
        form.populate_obj(journal_entry)
    if not form.is_modified:
        flash(s(lazy_gettext("The journal entry was not modified.")),
              "success")
        return redirect(inherit_next(__get_detail_uri(journal_entry)))
    journal_entry.updated_by_id = get_current_user_pk()
    journal_entry.updated_at = sa.func.now()
    db.session.commit()
    flash(s(lazy_gettext("The journal entry is updated successfully.")),
          "success")
    return redirect(inherit_next(__get_detail_uri(journal_entry)))


@bp.post("/<journalEntry:journal_entry>/delete", endpoint="delete")
@has_permission(can_edit)
def delete_journal_entry(journal_entry: JournalEntry) -> redirect:
    """Deletes a journal entry.

    :param journal_entry: The journal entry.
    :return: The redirection to the journal entry list on success, or the
        journal entry detail on error.
    """
    if not journal_entry.can_delete:
        flash(s(lazy_gettext("The journal entry cannot be deleted.")), "error")
        return redirect(inherit_next(__get_detail_uri(journal_entry)))
    journal_entry.delete()
    sort_journal_entries_in(journal_entry.date, journal_entry.id)
    db.session.commit()
    flash(s(lazy_gettext("The journal entry is deleted successfully.")),
          "success")
    return redirect(or_next(__get_default_page_uri()))


@bp.get("/dates/<date:journal_entry_date>", endpoint="order")
@has_permission(can_view)
def show_journal_entry_order(journal_entry_date: date) -> str:
    """Shows the order of the journal entries in a same date.

    :param journal_entry_date: The date.
    :return: The order of the journal entries in the date.
    """
    journal_entries: list[JournalEntry] = JournalEntry.query \
        .filter(JournalEntry.date == journal_entry_date) \
        .order_by(JournalEntry.no).all()
    return render_template("accounting/journal-entry/order.html",
                           date=journal_entry_date, list=journal_entries)


@bp.post("/dates/<date:journal_entry_date>", endpoint="sort")
@has_permission(can_edit)
def sort_journal_entries(journal_entry_date: date) -> redirect:
    """Reorders the journal entries in a date.

    :param journal_entry_date: The date.
    :return: The redirection to the incoming account or the account list.  The
        reordering operation does not fail.
    """
    form: JournalEntryReorderForm = JournalEntryReorderForm(journal_entry_date)
    form.save_order()
    if not form.is_modified:
        flash(s(lazy_gettext("The order was not modified.")), "success")
        return redirect(or_next(__get_default_page_uri()))
    db.session.commit()
    flash(s(lazy_gettext("The order is updated successfully.")), "success")
    return redirect(or_next(__get_default_page_uri()))


def __get_detail_uri(journal_entry: JournalEntry) -> str:
    """Returns the detail URI of a journal entry.

    :param journal_entry: The journal entry.
    :return: The detail URI of the journal entry.
    """
    return url_for("accounting.journal-entry.detail",
                   journal_entry=journal_entry)


def __get_default_page_uri() -> str:
    """Returns the URI for the default page.

    :return: The URI for the default page.
    """
    return url_for("accounting-report.default")
