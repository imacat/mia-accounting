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
"""The voucher management.

"""
from flask import Flask, Blueprint


def init_app(app: Flask, bp: Blueprint) -> None:
    """Initialize the application.

    :param app: The Flask application.
    :param bp: The blueprint of the accounting application.
    :return: None.
    """
    from .converters import VoucherConverter, VoucherTypeConverter, \
        DateConverter
    app.url_map.converters["voucher"] = VoucherConverter
    app.url_map.converters["voucherType"] = VoucherTypeConverter
    app.url_map.converters["date"] = DateConverter

    from .views import bp as voucher_bp
    bp.register_blueprint(voucher_bp, url_prefix="/vouchers")
