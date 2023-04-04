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
"""The getter and setter for the option management.

"""
import json

import sqlalchemy as sa

from accounting import db
from accounting.models import Option, Account, Currency
from accounting.utils.current_account import CurrentAccount
from accounting.utils.user import get_current_user_pk


class RecurringItem:
    """A recurring item."""

    def __init__(self, name: str, account_code: str,
                 description_template: str):
        """Constructs the recurring item.

        :param name: The name.
        :param account_code: The account code.
        :param description_template: The description template.
        """
        self.name: str = name
        self.account_code: str = account_code
        self.description_template: str = description_template

    @property
    def account_text(self) -> str:
        """Returns the account text.

        :return: The account text.
        """
        return str(Account.find_by_code(self.account_code))


class Recurring:
    """The recurring expenses or incomes."""

    def __init__(self, data: dict[str, list[tuple[str, str, str]]]):
        """Constructs the recurring item.

        :param data: The data.
        """
        self.expenses: list[RecurringItem] \
            = [RecurringItem(x[0], x[1], x[2]) for x in data["expense"]]
        self.incomes: list[RecurringItem] \
            = [RecurringItem(x[0], x[1], x[2]) for x in data["income"]]

    @property
    def codes(self) -> set[str]:
        """Returns all the account codes.

        :return: All the account codes.
        """
        return {x.account_code for x in self.expenses + self.incomes}


class Options:
    """The options."""

    def __init__(self):
        """Constructs the options."""
        self.is_modified: bool = False
        """Whether the options were modified."""

    @property
    def default_currency_code(self) -> str:
        """Returns the default currency code.

        :return: The default currency code.
        """
        return self.__get_option("default_currency_code", "USD")

    @default_currency_code.setter
    def default_currency_code(self, value: str) -> None:
        """Sets the default currency code.

        :param value: The default currency code.
        :return: None.
        """
        self.__set_option("default_currency_code", value)

    @property
    def default_currency_text(self) -> str:
        """Returns the text of the default currency code.

        :return: The text of the default currency code.
        """
        return str(db.session.get(Currency, self.default_currency_code))

    @property
    def default_ie_account_code(self) -> str:
        """Returns the default account code for the income and expenses log.

        :return: The default account code for the income and expenses log.
        """
        return self.__get_option("default_ie_account", Account.CASH_CODE)

    @default_ie_account_code.setter
    def default_ie_account_code(self, value: str) -> None:
        """Sets the default account code for the income and expenses log.

        :param value: The default account code for the income and expenses log.
        :return: None.
        """
        self.__set_option("default_ie_account", value)

    @property
    def default_ie_account_code_text(self) -> str:
        """Returns the text of the default currency code.

        :return: The text of the default currency code.
        """
        code: str = self.default_ie_account_code
        if code == CurrentAccount.CURRENT_AL_CODE:
            return str(CurrentAccount.current_assets_and_liabilities())
        return str(CurrentAccount(Account.find_by_code(code)))

    @property
    def default_ie_account(self) -> CurrentAccount:
        """Returns the default account code for the income and expenses log.

        :return: The default account code for the income and expenses log.
        """
        if self.default_ie_account_code \
                == CurrentAccount.CURRENT_AL_CODE:
            return CurrentAccount.current_assets_and_liabilities()
        return CurrentAccount(
            Account.find_by_code(self.default_ie_account_code))

    @property
    def recurring_data(self) -> dict[str, list[tuple[str, str, str]]]:
        """Returns the data of the recurring expenses and incomes.

        :return: The data of the recurring expenses and incomes.
        """
        json_data: str | None = self.__get_option("recurring")
        if json_data is None:
            return {"expense": [], "income": []}
        return json.loads(json_data)

    @recurring_data.setter
    def recurring_data(self,
                       value: dict[str, list[tuple[str, str, str]]]) -> None:
        """Sets the data of the recurring expenses and incomes.

        :param value: The data of the recurring expenses and incomes.
        :return: None.
        """
        self.__set_option("recurring", json.dumps(value, ensure_ascii=False,
                                                  separators=(",", ":")))

    @property
    def recurring(self) -> Recurring:
        """Returns the recurring expenses and incomes.

        :return: The recurring expenses and incomes.
        """
        return Recurring(self.recurring_data)

    @staticmethod
    def __get_option(name: str, default: str | None = None) -> str:
        """Returns the value of an option.

        :param name: The name.
        :param default: The default value when the value does not exist.
        :return: The value.
        """
        option: Option | None = db.session.get(Option, name)
        if option is None:
            return default
        return option.value

    def __set_option(self, name: str, value: str) -> None:
        """Sets the value of an option.

        :param name: The name.
        :param value: The value.
        :return: None.
        """
        option: Option | None = db.session.get(Option, name)
        if option is None:
            current_user_pk: int = get_current_user_pk()
            db.session.add(Option(name=name,
                                  value=value,
                                  created_by_id=current_user_pk,
                                  updated_by_id=current_user_pk))
            self.is_modified = True
            return
        if option.value == value:
            return
        option.value = value
        option.updated_by_id = get_current_user_pk()
        option.updated_at = sa.func.now()
        self.is_modified = True

    def commit(self) -> None:
        """Commits the options to the database.

        :return: None.
        """
        db.session.commit()
        self.is_modified = False


options: Options = Options()
"""The options."""
