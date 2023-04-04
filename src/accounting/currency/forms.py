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
"""The forms for the currency management.

"""
from flask_wtf import FlaskForm
from wtforms import StringField, ValidationError
from wtforms.validators import DataRequired, Regexp, NoneOf

from accounting import db
from accounting.locale import lazy_gettext
from accounting.models import Currency
from accounting.utils.strip_text import strip_text
from accounting.utils.user import get_current_user_pk


class CodeUnique:
    """The validator to check if the code is unique."""

    def __call__(self, form: FlaskForm, field: StringField) -> None:
        assert isinstance(form, CurrencyForm)
        if field.data == "":
            return
        if form.obj_code is not None and form.obj_code == field.data:
            return
        if db.session.get(Currency, field.data) is not None:
            raise ValidationError(lazy_gettext(
                "Code conflicts with another currency."))


class CurrencyForm(FlaskForm):
    """The form to create or edit a currency."""
    CODE_BLOCKLIST: list[str] = ["create", "store", "exists-code"]
    """The reserved codes that are not available."""
    code = StringField(
        filters=[strip_text],
        validators=[DataRequired(lazy_gettext("Please fill in the code.")),
                    Regexp(r"^[A-Z]{3}$",
                           message=lazy_gettext(
                               "Code can only be composed of 3 upper-cased"
                               " letters.")),
                    NoneOf(CODE_BLOCKLIST, message=lazy_gettext(
                        "This code is not available.")),
                    CodeUnique()])
    """The code.  It may not conflict with another currency."""
    name = StringField(
        filters=[strip_text],
        validators=[DataRequired(lazy_gettext("Please fill in the name."))])
    """The name."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.obj_code: str | None = None
        """The current code of the currency, or None when adding a new
        currency."""

    def populate_obj(self, obj: Currency) -> None:
        """Populates the form data into a currency object.

        :param obj: The currency object.
        :return: None.
        """
        is_new: bool = obj.code is None
        obj.code = self.code.data
        obj.name = self.name.data
        if is_new:
            current_user_pk: int = get_current_user_pk()
            obj.created_by_id = current_user_pk
            obj.updated_by_id = current_user_pk
