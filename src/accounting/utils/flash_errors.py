# The Mia! Accounting Project.
# Author: imacat@mail.imacat.idv.tw (imacat), 2023/2/1

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
"""The utility to flash all errors from the forms.

This module should not import any other module from the application.

"""
import typing as t

from flask import flash
from flask_wtf import FlaskForm


def flash_form_errors(form: FlaskForm) -> None:
    """Flash all errors from a form recursively.

    :param form: The form.
    :return: None.
    """
    __flash_errors(form.errors)


def __flash_errors(error: t.Any) -> None:
    """Flash all errors recursively.

    :param error: The errors.
    :return: None.
    """
    if isinstance(error, dict):
        for key in error:
            __flash_errors(error[key])
    elif isinstance(error, list):
        for e in error:
            __flash_errors(e)
    else:
        flash(error, "error")
