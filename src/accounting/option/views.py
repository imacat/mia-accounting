# The Mia! Accounting Project.
# Author: imacat@mail.imacat.idv.tw (imacat), 2023/3/22

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
"""The views for the option management.

"""
from urllib.parse import parse_qsl, urlencode

from flask import Blueprint, render_template, redirect, session, request, \
    flash, url_for
from werkzeug.datastructures import ImmutableMultiDict

from accounting.locale import lazy_gettext
from accounting.utils.cast import s
from accounting.utils.flash_errors import flash_form_errors
from accounting.utils.next_uri import inherit_next
from accounting.utils.options import options
from accounting.utils.permission import has_permission, can_admin
from .forms import OptionForm

bp: Blueprint = Blueprint("option", __name__)
"""The view blueprint for the currency management."""


@bp.get("", endpoint="detail")
@has_permission(can_admin)
def show_options() -> str:
    """Shows the options.

    :return: The options.
    """
    return render_template("accounting/option/detail.html", obj=options)


@bp.get("edit", endpoint="edit")
@has_permission(can_admin)
def show_option_form() -> str:
    """Shows the option form.

    :return: The option form.
    """
    form: OptionForm
    if "form" in session:
        form = OptionForm(ImmutableMultiDict(parse_qsl(session["form"])))
        del session["form"]
        form.validate()
    else:
        form = OptionForm(obj=options)
    return render_template("accounting/option/form.html", form=form)


@bp.post("update", endpoint="update")
@has_permission(can_admin)
def update_options() -> redirect:
    """Updates the options.

    :return: The redirection to the option form.
    """
    form = OptionForm(request.form)
    if not form.validate():
        flash_form_errors(form)
        session["form"] = urlencode(list(request.form.items()))
        return redirect(inherit_next(url_for("accounting.option.edit")))
    form.populate_obj(options)
    if not options.is_modified:
        flash(s(lazy_gettext("The settings were not modified.")), "success")
        return redirect(inherit_next(url_for("accounting.option.detail")))
    options.commit()
    flash(s(lazy_gettext("The settings are saved successfully.")), "success")
    return redirect(inherit_next(url_for("accounting.option.detail")))
