# The Mia! Accounting Flask Project.
# Author: imacat@mail.imacat.idv.tw (imacat), 2023/2/19

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
"""The operators for different voucher types.

"""
import typing as t
from abc import ABC, abstractmethod

from flask import render_template, request, abort
from flask_wtf import FlaskForm

from accounting.models import Voucher
from accounting.template_globals import default_currency_code
from accounting.utils.voucher_types import VoucherType
from accounting.voucher.forms import VoucherForm, CashReceiptVoucherForm, \
    CashDisbursementVoucherForm, TransferVoucherForm


class VoucherOperator(ABC):
    """The base voucher operator."""
    CHECK_ORDER: int = -1
    """The order when checking the voucher operator."""

    @property
    @abstractmethod
    def form(self) -> t.Type[VoucherForm]:
        """Returns the form class.

        :return: The form class.
        """

    @abstractmethod
    def render_create_template(self, form: FlaskForm) -> str:
        """Renders the template for the form to create a voucher.

        :param form: The voucher form.
        :return: the form to create a voucher.
        """

    @abstractmethod
    def render_detail_template(self, voucher: Voucher) -> str:
        """Renders the template for the detail page.

        :param voucher: The voucher.
        :return: the detail page.
        """

    @abstractmethod
    def render_edit_template(self, voucher: Voucher, form: FlaskForm) -> str:
        """Renders the template for the form to edit a voucher.

        :param voucher: The voucher.
        :param form: The form.
        :return: the form to edit a voucher.
        """

    @abstractmethod
    def is_my_type(self, voucher: Voucher) -> bool:
        """Checks and returns whether the voucher belongs to the type.

        :param voucher: The voucher.
        :return: True if the voucher belongs to the type, or False
            otherwise.
        """

    @property
    def _line_item_template(self) -> str:
        """Renders and returns the template for the line item sub-form.

        :return: The template for the line item sub-form.
        """
        return render_template(
            "accounting/voucher/include/form-line-item.html",
            currency_index="CURRENCY_INDEX",
            side="SIDE",
            line_item_index="LINE_ITEM_INDEX")


class CashReceiptVoucher(VoucherOperator):
    """A cash receipt voucher."""
    CHECK_ORDER: int = 2
    """The order when checking the voucher operator."""

    @property
    def form(self) -> t.Type[VoucherForm]:
        """Returns the form class.

        :return: The form class.
        """
        return CashReceiptVoucherForm

    def render_create_template(self, form: CashReceiptVoucherForm) -> str:
        """Renders the template for the form to create a voucher.

        :param form: The voucher form.
        :return: the form to create a voucher.
        """
        return render_template("accounting/voucher/receipt/create.html",
                               form=form,
                               voucher_type=VoucherType.CASH_RECEIPT,
                               currency_template=self.__currency_template,
                               line_item_template=self._line_item_template)

    def render_detail_template(self, voucher: Voucher) -> str:
        """Renders the template for the detail page.

        :param voucher: The voucher.
        :return: the detail page.
        """
        return render_template("accounting/voucher/receipt/detail.html",
                               obj=voucher)

    def render_edit_template(self, voucher: Voucher,
                             form: CashReceiptVoucherForm) -> str:
        """Renders the template for the form to edit a voucher.

        :param voucher: The voucher.
        :param form: The form.
        :return: the form to edit a voucher.
        """
        return render_template("accounting/voucher/receipt/edit.html",
                               voucher=voucher, form=form,
                               currency_template=self.__currency_template,
                               line_item_template=self._line_item_template)

    def is_my_type(self, voucher: Voucher) -> bool:
        """Checks and returns whether the voucher belongs to the type.

        :param voucher: The voucher.
        :return: True if the voucher belongs to the type, or False
            otherwise.
        """
        return voucher.is_cash_receipt

    @property
    def __currency_template(self) -> str:
        """Renders and returns the template for the currency sub-form.

        :return: The template for the currency sub-form.
        """
        return render_template(
            "accounting/voucher/receipt/include/form-currency-item.html",
            currency_index="CURRENCY_INDEX",
            currency_code_data=default_currency_code(),
            credit_total="-")


class CashDisbursementVoucher(VoucherOperator):
    """A cash disbursement voucher."""
    CHECK_ORDER: int = 1
    """The order when checking the voucher operator."""

    @property
    def form(self) -> t.Type[VoucherForm]:
        """Returns the form class.

        :return: The form class.
        """
        return CashDisbursementVoucherForm

    def render_create_template(self, form: CashDisbursementVoucherForm) -> str:
        """Renders the template for the form to create a voucher.

        :param form: The voucher form.
        :return: the form to create a voucher.
        """
        return render_template("accounting/voucher/disbursement/create.html",
                               form=form,
                               voucher_type=VoucherType.CASH_DISBURSEMENT,
                               currency_template=self.__currency_template,
                               line_item_template=self._line_item_template)

    def render_detail_template(self, voucher: Voucher) -> str:
        """Renders the template for the detail page.

        :param voucher: The voucher.
        :return: the detail page.
        """
        return render_template("accounting/voucher/disbursement/detail.html",
                               obj=voucher)

    def render_edit_template(self, voucher: Voucher,
                             form: CashDisbursementVoucherForm) -> str:
        """Renders the template for the form to edit a voucher.

        :param voucher: The voucher.
        :param form: The form.
        :return: the form to edit a voucher.
        """
        return render_template("accounting/voucher/disbursement/edit.html",
                               voucher=voucher, form=form,
                               currency_template=self.__currency_template,
                               line_item_template=self._line_item_template)

    def is_my_type(self, voucher: Voucher) -> bool:
        """Checks and returns whether the voucher belongs to the type.

        :param voucher: The voucher.
        :return: True if the voucher belongs to the type, or False
            otherwise.
        """
        return voucher.is_cash_disbursement

    @property
    def __currency_template(self) -> str:
        """Renders and returns the template for the currency sub-form.

        :return: The template for the currency sub-form.
        """
        return render_template(
            "accounting/voucher/disbursement/include/form-currency-item.html",
            currency_index="CURRENCY_INDEX",
            currency_code_data=default_currency_code(),
            debit_total="-")


class TransferVoucher(VoucherOperator):
    """A transfer voucher."""
    CHECK_ORDER: int = 3
    """The order when checking the voucher operator."""

    @property
    def form(self) -> t.Type[VoucherForm]:
        """Returns the form class.

        :return: The form class.
        """
        return TransferVoucherForm

    def render_create_template(self, form: TransferVoucherForm) -> str:
        """Renders the template for the form to create a voucher.

        :param form: The voucher form.
        :return: the form to create a voucher.
        """
        return render_template("accounting/voucher/transfer/create.html",
                               form=form,
                               voucher_type=VoucherType.TRANSFER,
                               currency_template=self.__currency_template,
                               line_item_template=self._line_item_template)

    def render_detail_template(self, voucher: Voucher) -> str:
        """Renders the template for the detail page.

        :param voucher: The voucher.
        :return: the detail page.
        """
        return render_template("accounting/voucher/transfer/detail.html",
                               obj=voucher)

    def render_edit_template(self, voucher: Voucher,
                             form: TransferVoucherForm) -> str:
        """Renders the template for the form to edit a voucher.

        :param voucher: The voucher.
        :param form: The form.
        :return: the form to edit a voucher.
        """
        return render_template("accounting/voucher/transfer/edit.html",
                               voucher=voucher, form=form,
                               currency_template=self.__currency_template,
                               line_item_template=self._line_item_template)

    def is_my_type(self, voucher: Voucher) -> bool:
        """Checks and returns whether the voucher belongs to the type.

        :param voucher: The voucher.
        :return: True if the voucher belongs to the type, or False
            otherwise.
        """
        return True

    @property
    def __currency_template(self) -> str:
        """Renders and returns the template for the currency sub-form.

        :return: The template for the currency sub-form.
        """
        return render_template(
            "accounting/voucher/transfer/include/form-currency-item.html",
            currency_index="CURRENCY_INDEX",
            currency_code_data=default_currency_code(),
            debit_total="-", credit_total="-")


VOUCHER_TYPE_TO_OP: dict[VoucherType, VoucherOperator] \
    = {VoucherType.CASH_RECEIPT: CashReceiptVoucher(),
       VoucherType.CASH_DISBURSEMENT: CashDisbursementVoucher(),
       VoucherType.TRANSFER: TransferVoucher()}
"""The map from the voucher types to their operators."""


def get_voucher_op(voucher: Voucher, is_check_as: bool = False) \
        -> VoucherOperator:
    """Returns the voucher operator that may be specified in the "as" query
    parameter.  If it is not specified, check the voucher type from the
    voucher.

    :param voucher: The voucher.
    :param is_check_as: True to check the "as" parameter, or False otherwise.
    :return: None.
    """
    if is_check_as and "as" in request.args:
        type_dict: dict[str, VoucherType] \
            = {x.value: x for x in VoucherType}
        if request.args["as"] not in type_dict:
            abort(404)
        return VOUCHER_TYPE_TO_OP[type_dict[request.args["as"]]]
    for voucher_type in sorted(VOUCHER_TYPE_TO_OP.values(),
                               key=lambda x: x.CHECK_ORDER):
        if voucher_type.is_my_type(voucher):
            return voucher_type
