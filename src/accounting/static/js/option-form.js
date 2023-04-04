/* The Mia! Accounting Project
 * account-form.js: The JavaScript for the account form
 */

/*  Copyright (c) 2023 imacat.
 *
 *  Licensed under the Apache License, Version 2.0 (the "License");
 *  you may not use this file except in compliance with the License.
 *  You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 */

/* Author: imacat@mail.imacat.idv.tw (imacat)
 * First written: 2023/3/22
 */
"use strict";

// Initializes the page JavaScript.
document.addEventListener("DOMContentLoaded", () => {
    OptionForm.initialize();
});

/**
 * Escapes the HTML special characters and returns.
 *
 * @param s {string} the original string
 * @returns {string} the string with HTML special character escaped
 * @private
 */
function escapeHtml(s) {
    return String(s)
         .replaceAll("&", "&amp;")
         .replaceAll("<", "&lt;")
         .replaceAll(">", "&gt;")
         .replaceAll("\"", "&quot;");
}

/**
 * The option form.
 *
 * @private
 */
class OptionForm {

    /**
     * The form element
     * @type {HTMLFormElement}
     */
    #element;

    /**
     * The default currency
     * @type {HTMLSelectElement}
     */
    #defaultCurrency;

    /**
     * The error message for the default currency
     * @type {HTMLDivElement}
     */
    #defaultCurrencyError;

    /**
     * The default account for the income and expenses log
     * @type {HTMLSelectElement}
     */
    #defaultIeAccount;

    /**
     * The error message for the default account for the income and expenses log
     * @type {HTMLDivElement}
     */
    #defaultIeAccountError;

    /**
     * The recurring item template
     * @type {string}
     */
    recurringItemTemplate;

    /**
     * The recurring expenses or incomes sub-form
     * @type {{expense: RecurringExpenseIncomeSubForm, income: RecurringExpenseIncomeSubForm}}
     */
    #expenseIncome;

    /**
     * Constructs the option form.
     *
     */
    constructor() {
        this.#element = document.getElementById("accounting-form");
        this.#defaultCurrency = document.getElementById("accounting-default-currency");
        this.#defaultCurrencyError = document.getElementById("accounting-default-currency-error");
        this.#defaultIeAccount = document.getElementById("accounting-default-ie-account");
        this.#defaultIeAccountError = document.getElementById("accounting-default-ie-account-error");
        this.recurringItemTemplate = this.#element.dataset.recurringItemTemplate;
        this.#expenseIncome = RecurringExpenseIncomeSubForm.getInstances(this);

        this.#defaultCurrency.onchange = () => this.#validateDefaultCurrency();
        this.#defaultIeAccount.onchange = () => this.#validateDefaultIeAccount();
        this.#element.onsubmit = () => {
            return this.#validate();
        };
    }

    /**
     * Validates the form.
     *
     * @returns {boolean} true if valid, or false otherwise
     */
    #validate() {
        let isValid = true;
        isValid = this.#validateDefaultCurrency() && isValid;
        isValid = this.#validateDefaultIeAccount() && isValid;
        isValid = this.#expenseIncome.expense.validate() && isValid;
        isValid = this.#expenseIncome.income.validate() && isValid;
        return isValid;
    }

    /**
     * Validates the default currency.
     *
     * @returns {boolean} true if valid, or false otherwise
     */
    #validateDefaultCurrency() {
        if (this.#defaultCurrency.value === "") {
            this.#defaultCurrency.classList.add("is-invalid");
            this.#defaultCurrencyError.innerText = A_("Please select the default currency.");
            return false;
        }
        this.#defaultCurrency.classList.remove("is-invalid");
        this.#defaultCurrencyError.innerText = "";
        return true;
    }

    /**
     * Validates the default account for the income and expenses log.
     *
     * @returns {boolean} true if valid, or false otherwise
     */
    #validateDefaultIeAccount() {
        if (this.#defaultIeAccount.value === "") {
            this.#defaultIeAccount.classList.add("is-invalid");
            this.#defaultIeAccountError.innerText = A_("Please select the default account for the income and expenses log.");
            return false;
        }
        this.#defaultIeAccount.classList.remove("is-invalid");
        this.#defaultIeAccountError.innerText = "";
        return true;
    }

    /**
     * The option form
     * @type {OptionForm}
     */
    static #form;

    /**
     * Initializes the option form.
     *
     */
    static initialize() {
        this.#form = new OptionForm();
    }
}

/**
 * The recurring expenses or incomes sub-form.
 *
 */
class RecurringExpenseIncomeSubForm {

    /**
     * The option form
     * @type {OptionForm}
     */
    #form;

    /**
     * Either "expense" or "income"
     * @type {string}
     */
    expenseIncome;

    /**
     * The recurring item editor
     * @type {RecurringItemEditor}
     */
    editor;

    /**
     * The prefix of the HTML ID and class names
     * @type {string}
     */
    #prefix;

    /**
     * The element
     * @type {HTMLDivElement}
     */
    #element;

    /**
     * The content
     * @type {HTMLDivElement}
     */
    #content;

    /**
     * The recurring items list
     * @type {HTMLUListElement}
     */
    #itemList;

    /**
     * The recurring items
     * @type {RecurringItemSubForm[]}
     */
    #items;

    /**
     * The button to add a new recurring item
     * @type {HTMLButtonElement}
     */
    #addButton;

    /**
     * Constructs the recurring expenses or incomes.
     *
     * @param form {OptionForm} the option form
     * @param expenseIncome {string} either "expense" or "income"
     */
    constructor(form, expenseIncome) {
        this.#form = form;
        this.expenseIncome = expenseIncome;
        this.editor = new RecurringItemEditor(this);
        this.#prefix = `accounting-recurring-${expenseIncome}`;
        this.#element = document.getElementById(this.#prefix);
        this.#content = document.getElementById(`${this.#prefix}-content`);
        this.#itemList = document.getElementById(`${this.#prefix}-list`);
        this.#items = Array.from(document.getElementsByClassName(`${this.#prefix}-item`)).map((element) => new RecurringItemSubForm(this, element));
        this.#addButton = document.getElementById(`${this.#prefix}-add`);

        this.#resetContent();
        this.#addButton.onclick = () => this.editor.onAddNew();
        this.#initializeDragAndDropReordering();
    }

    /**
     * Adds a recurring item.
     *
     * @return {RecurringItemSubForm} the recurring item
     */
    addItem() {
        const newIndex = 1 + (this.#items.length === 0? 0: Math.max(...this.#items.map((item) => item.itemIndex)));
        const html = this.#form.recurringItemTemplate
            .replaceAll("EXPENSE_INCOME", escapeHtml(this.expenseIncome))
            .replaceAll("ITEM_INDEX", escapeHtml(String(newIndex)));
        this.#itemList.insertAdjacentHTML("beforeend", html);
        const element = document.getElementById(`${this.#prefix}-${String(newIndex)}`)
        const item = new RecurringItemSubForm(this, element);
        this.#items.push(item);
        this.#resetContent();
        this.#initializeDragAndDropReordering();
        this.validate();
        return item;
    }

    /**
     * Deletes a recurring item sub-form.
     *
     * @param item {RecurringItemSubForm} the recurring item sub-form to delete
     */
    deleteItem(item) {
        const index = this.#items.indexOf(item);
        this.#items.splice(index, 1);
        this.#resetContent();
    }

    /**
     * Resets the layout of the content.
     *
     */
    #resetContent() {
        if (this.#items.length === 0) {
            this.#element.classList.remove("accounting-not-empty");
            this.#element.classList.add("accounting-clickable");
            this.#element.dataset.bsToggle = "modal"
            this.#element.dataset.bsTarget = `#${this.editor.modal.id}`;
            this.#element.onclick = () => this.editor.onAddNew();
            this.#content.classList.add("d-none");
        } else {
            this.#element.classList.add("accounting-not-empty");
            this.#element.classList.remove("accounting-clickable");
            delete this.#element.dataset.bsToggle;
            delete this.#element.dataset.bsTarget;
            this.#element.onclick = null;
            this.#content.classList.remove("d-none");
        }
    }

    /**
     * Initializes the drag and drop reordering on the recurring item sub-forms.
     *
     */
    #initializeDragAndDropReordering() {
        initializeDragAndDropReordering(this.#itemList, () => {
            for (const item of this.#items) {
                item.resetNo();
            }
        });
    }

    /**
     * Validates the form.
     *
     * @returns {boolean} true if valid, or false otherwise
     */
    validate() {
        let isValid = true;
        for (const item of this.#items) {
            isValid = item.validate() && isValid;
        }
        return isValid;
    }

    /**
     * Returns the recurring expenses or incomes sub-form instances.
     *
     * @param form {OptionForm} the option form
     * @return {{expense: RecurringExpenseIncomeSubForm, income: RecurringExpenseIncomeSubForm}}
     */
    static getInstances(form) {
        const subForms = {};
        for (const expenseIncome of ["expense", "income"]) {
            subForms[expenseIncome] = new RecurringExpenseIncomeSubForm(form, expenseIncome);
        }
        return subForms;
    }
}

/**
 * A recurring item sub-form.
 *
 */
class RecurringItemSubForm {

    /**
     * The recurring expenses or incomes sub-form
     * @type {RecurringExpenseIncomeSubForm}
     */
    #expenseIncomeSubForm;

    /**
     * The element
     * @type {HTMLLIElement}
     */
    #element;

    /**
     * The item index
     * @type {number}
     */
    itemIndex;

    /**
     * The control
     * @type {HTMLDivElement}
     */
    #control;

    /**
     * The error message
     * @type {HTMLDivElement}
     */
    #error;

    /**
     * The order number
     * @type {HTMLInputElement}
     */
    #no;

    /**
     * The name input
     * @type {HTMLInputElement}
     */
    #name;

    /**
     * The text display of the name
     * @type {HTMLDivElement}
     */
    #nameText;

    /**
     * The account code input
     * @type {HTMLInputElement}
     */
    #accountCode;

    /**
     * The text display of the account
     * @type {HTMLDivElement}
     */
    #accountText;

    /**
     * The description template input
     * @type {HTMLInputElement}
     */
    #descriptionTemplate;

    /**
     * The text display of the description template
     * @type {HTMLDivElement}
     */
    #descriptionTemplateText;

    /**
     * The button to delete this recurring item
     * @type {HTMLButtonElement}
     */
    deleteButton;

    /**
     * Constructs a recurring item sub-form.
     *
     * @param expenseIncomeSubForm {RecurringExpenseIncomeSubForm} the recurring expenses or incomes sub-form
     * @param element {HTMLLIElement} the element
     */
    constructor(expenseIncomeSubForm, element) {
        this.#expenseIncomeSubForm = expenseIncomeSubForm
        this.#element = element;
        this.itemIndex = parseInt(element.dataset.itemIndex);
        const prefix = `accounting-recurring-${expenseIncomeSubForm.expenseIncome}-${element.dataset.itemIndex}`;
        this.#control = document.getElementById(`${prefix}-control`);
        this.#error = document.getElementById(`${prefix}-error`);
        this.#no = document.getElementById(`${prefix}-no`);
        this.#name = document.getElementById(`${prefix}-name`);
        this.#nameText = document.getElementById(`${prefix}-name-text`);
        this.#accountCode = document.getElementById(`${prefix}-account-code`);
        this.#accountText = document.getElementById(`${prefix}-account-text`);
        this.#descriptionTemplate = document.getElementById(`${prefix}-description-template`);
        this.#descriptionTemplateText = document.getElementById(`${prefix}-description-template-text`);
        this.deleteButton = document.getElementById(`${prefix}-delete`);

        this.#control.onclick = () => this.#expenseIncomeSubForm.editor.onEdit(this);
        this.deleteButton.onclick = () => {
            this.#element.parentElement.removeChild(this.#element);
            this.#expenseIncomeSubForm.deleteItem(this);
        };
    }

    /**
     * Reset the order number.
     *
     */
    resetNo() {
        const siblings = Array.from(this.#element.parentElement.children);
        this.#no.value = String(siblings.indexOf(this.#element) + 1);
    }

    /**
     * Returns the name.
     *
     * @return {string|null} the name
     */
    get name() {
        return this.#name.value === ""? null: this.#name.value;
    }

    /**
     * Returns the account code.
     *
     * @return {string|null} the account code
     */
    get accountCode() {
        return this.#accountCode.value === ""? null: this.#accountCode.value;
    }

    /**
     * Returns the account text.
     *
     * @return {string|null} the account text
     */
    get accountText() {
        return this.#accountCode.dataset.text === ""? null: this.#accountCode.dataset.text;
    }

    /**
     * Returns the description template.
     *
     * @return {string|null} the description template
     */
    get descriptionTemplate() {
        return this.#descriptionTemplate.value === ""? null: this.#descriptionTemplate.value;
    }

    /**
     * Saves the recurring item from the recurring item editor.
     *
     * @param editor {RecurringItemEditor} the recurring item editor
     */
    save(editor) {
        this.#name.value = editor.name === null? "": editor.name;
        this.#nameText.innerText = this.#name.value;
        this.#accountCode.value = editor.accountCode;
        this.#accountCode.dataset.text = editor.accountText;
        this.#accountText.innerText = editor.accountText;
        this.#descriptionTemplate.value = editor.descriptionTemplate === null? "": editor.descriptionTemplate;
        this.#descriptionTemplateText.innerText = this.#descriptionTemplate.value;
        this.validate();
    }

    /**
     * Validates the form.
     *
     * @returns {boolean} true if valid, or false otherwise
     */
    validate() {
        if (this.#name.value === "") {
            this.#control.classList.add("is-invalid");
            this.#error.innerText = A_("Please fill in the name.");
            return false;
        }
        if (this.#accountCode.value === "") {
            this.#control.classList.add("is-invalid");
            this.#error.innerText = A_("Please select the account.");
            return false;
        }
        if (this.#descriptionTemplate.value === "") {
            this.#control.classList.add("is-invalid");
            this.#error.innerText = A_("Please fill in the description template.");
            return false;
        }
        this.#control.classList.remove("is-invalid");
        this.#error.innerText = "";
        return true;
    }
}

/**
 * The recurring item editor.
 *
 */
class RecurringItemEditor {

    /**
     * The recurring expense or income sub-form
     * @type {RecurringExpenseIncomeSubForm}
     */
    #subForm;

    /**
     * Either "expense" or "income"
     * @type {string}
     */
    expenseIncome;

    /**
     * The form
     * @type {HTMLFormElement}
     */
    #form;

    /**
     * The modal
     * @type {HTMLDivElement}
     */
    modal;

    /**
     * The name
     * @type {HTMLInputElement}
     */
    #name;

    /**
     * The error message of the name
     * @type {HTMLDivElement}
     */
    #nameError;

    /**
     * The control of the account
     * @type {HTMLDivElement}
     */
    #accountControl;

    /**
     * The text display of the account
     * @type {HTMLDivElement}
     */
    #accountContainer;

    /**
     * The error message of the account
     * @type {HTMLDivElement}
     */
    #accountError;

    /**
     * The description template
     * @type {HTMLInputElement}
     */
    #descriptionTemplate;

    /**
     * The error message of the description template
     * @type {HTMLDivElement}
     */
    #descriptionTemplateError;

    /**
     * The account selector
     * @type {RecurringAccountSelector}
     */
    #accountSelector;

    /**
     * The account code
     * @type {string|null}
     */
    accountCode = null;

    /**
     * The account text
     * @type {string|null}
     */
    accountText = null;

    /**
     * The recurring item sub-form
     * @type {RecurringItemSubForm|null}
     */
    #item = null;

    /**
     * Constructs the recurring item editor.
     *
     * @param subForm {RecurringExpenseIncomeSubForm} the recurring expense or income sub-form
     */
    constructor(subForm) {
        this.#subForm = subForm;
        this.expenseIncome = subForm.expenseIncome;
        const prefix = `accounting-recurring-item-editor-${subForm.expenseIncome}`;
        this.#form = document.getElementById(prefix);
        this.modal = document.getElementById(`${prefix}-modal`);
        this.#name = document.getElementById(`${prefix}-name`);
        this.#nameError = document.getElementById(`${prefix}-name-error`);
        this.#accountControl = document.getElementById(`${prefix}-account-control`);
        this.#accountContainer = document.getElementById(`${prefix}-account`);
        this.#accountError = document.getElementById(`${prefix}-account-error`);
        this.#descriptionTemplate = document.getElementById(`${prefix}-description-template`);
        this.#descriptionTemplateError = document.getElementById(`${prefix}-description-template-error`);
        this.#accountSelector = new RecurringAccountSelector(this);

        this.#name.onchange = () => this.#validateName();
        this.#accountControl.onclick = () => this.#accountSelector.onOpen();
        this.#descriptionTemplate.onchange = () => this.#validateDescriptionTemplate();
        this.#form.onsubmit = () => {
            if (this.#validate()) {
                if (this.#item === null) {
                    this.#item = this.#subForm.addItem();
                }
                this.#item.save(this);
                bootstrap.Modal.getInstance(this.modal).hide();
            }
            return false;
        };
    }

    /**
     * Returns the name.
     *
     * @return {string|null} the name
     */
    get name() {
        return this.#name.value === ""? null: this.#name.value;
    }

    /**
     * Returns the description template.
     *
     * @return {string|null} the description template
     */
    get descriptionTemplate() {
        return this.#descriptionTemplate.value === ""? null: this.#descriptionTemplate.value;
    }

    /**
     * Saves the selected account.
     *
     * @param account {RecurringAccount} the selected account
     */
    saveAccount(account) {
        this.accountCode = account.code;
        this.accountText = account.text;
        this.#accountControl.classList.add("accounting-not-empty");
        this.#accountContainer.innerText = account.text;
        this.#validateAccount();
    }

    /**
     * Clears account.
     *
     */
    clearAccount() {
        this.accountCode = null;
        this.accountText = null;
        this.#accountControl.classList.remove("accounting-not-empty");
        this.#accountContainer.innerText = "";
        this.#validateAccount()
    }

    /**
     * The callback when adding a new recurring item.
     *
     */
    onAddNew() {
        this.#item = null;
        this.#name.value = "";
        this.#name.classList.remove("is-invalid");
        this.#nameError.innerText = "";
        this.accountCode = null;
        this.accountText = null;
        this.#accountControl.classList.remove("accounting-not-empty");
        this.#accountControl.classList.remove("is-invalid");
        this.#accountContainer.innerText = "";
        this.#accountError.innerText = "";
        this.#descriptionTemplate.value = "";
        this.#descriptionTemplate.classList.remove("is-invalid");
        this.#descriptionTemplateError.innerText = "";
    }

    /**
     * The callback when editing a recurring item.
     *
     * @param item {RecurringItemSubForm} the recurring item to edit
     */
    onEdit(item) {
        this.#item = item;
        this.#name.value = item.name === null? "": item.name;
        this.accountCode = item.accountCode;
        this.accountText = item.accountText;
        if (this.accountText === null) {
            this.#accountControl.classList.remove("accounting-not-empty");
        } else {
            this.#accountControl.classList.add("accounting-not-empty");
        }
        this.#accountContainer.innerText = this.accountText === null? "": this.accountText;
        this.#descriptionTemplate.value = item.descriptionTemplate === null? "": item.descriptionTemplate;
        this.#validate();
    }

    /**
     * Validates the form.
     *
     * @returns {boolean} true if valid, or false otherwise
     */
    #validate() {
        let isValid = true;
        isValid = this.#validateName() && isValid;
        isValid = this.#validateAccount() && isValid;
        isValid = this.#validateDescriptionTemplate() && isValid;
        return isValid;
    }

    /**
     * Validates the name.
     *
     * @returns {boolean} true if valid, or false otherwise
     */
    #validateName() {
        this.#name.value = this.#name.value.trim();
        if (this.#name.value === "") {
            this.#name.classList.add("is-invalid");
            this.#nameError.innerText = A_("Please fill in the name.");
            return false;
        }
        this.#name.classList.remove("is-invalid");
        this.#nameError.innerText = "";
        return true;
    }

    /**
     * Validates the account.
     *
     * @returns {boolean} true if valid, or false otherwise
     */
    #validateAccount() {
        if (this.accountCode === null) {
            this.#accountControl.classList.add("is-invalid");
            this.#accountError.innerText = A_("Please select the account.");
            return false;
        }
        this.#accountControl.classList.remove("is-invalid");
        this.#accountError.innerText = "";
        return true;
    }

    /**
     * Validates the description template.
     *
     * @returns {boolean} true if valid, or false otherwise
     */
    #validateDescriptionTemplate() {
        this.#descriptionTemplate.value = this.#descriptionTemplate.value.trim();
        if (this.#descriptionTemplate.value === "") {
            this.#descriptionTemplate.classList.add("is-invalid");
            this.#descriptionTemplateError.innerText = A_("Please fill in the description template.");
            return false;
        }
        this.#descriptionTemplate.classList.remove("is-invalid");
        this.#descriptionTemplateError.innerText = "";
        return true;
    }
}

/**
 * The account selector for the recurring item editor.
 *
 */
class RecurringAccountSelector {

    /**
     * The recurring item editor
     * @type {RecurringItemEditor}
     */
    editor;

    /**
     * Either "expense" or "income"
     * @type {string}
     */
    #expenseIncome;

    /**
     * The query input
     * @type {HTMLInputElement}
     */
    #query;

    /**
     * The error message when the query has no result
     * @type {HTMLParagraphElement}
     */
    #queryNoResult;

    /**
     * The option list
     * @type {HTMLUListElement}
     */
    #optionList;

    /**
     * The account options
     * @type {RecurringAccount[]}
     */
    #options;

    /**
     * The button to clear the account
     * @type {HTMLButtonElement}
     */
    #clearButton;

    /**
     * Constructs the account selector for the recurring item editor.
     *
     * @param editor {RecurringItemEditor} the recurring item editor
     */
    constructor(editor) {
        this.editor = editor;
        this.#expenseIncome = editor.expenseIncome;
        const prefix = `accounting-recurring-accounting-selector-${editor.expenseIncome}`;
        this.#query = document.getElementById(`${prefix}-query`);
        this.#queryNoResult = document.getElementById(`${prefix}-option-no-result`);
        this.#optionList = document.getElementById(`${prefix}-option-list`);
        this.#options = Array.from(document.getElementsByClassName(`${prefix}-option`)).map((element) => new RecurringAccount(this, element));
        this.#clearButton = document.getElementById(`${prefix}-clear`);

        this.#query.oninput = () => this.#filterOptions();
        this.#clearButton.onclick = () => this.editor.clearAccount();
    }

    /**
     * Filters the options.
     *
     */
    #filterOptions() {
        let isAnyMatched = false;
        for (const option of this.#options) {
            if (option.isMatched(this.#query.value)) {
                option.setShown(true);
                isAnyMatched = true;
            } else {
                option.setShown(false);
            }
        }
        if (!isAnyMatched) {
            this.#optionList.classList.add("d-none");
            this.#queryNoResult.classList.remove("d-none");
        } else {
            this.#optionList.classList.remove("d-none");
            this.#queryNoResult.classList.add("d-none");
        }
    }

    /**
     * The callback when the account selector is shown.
     *
     */
    onOpen() {
        this.#query.value = "";
        this.#filterOptions();
        for (const option of this.#options) {
            option.setActive(option.code === this.editor.accountCode);
        }
        if (this.editor.accountCode === null) {
            this.#clearButton.classList.add("btn-secondary");
            this.#clearButton.classList.remove("btn-danger");
            this.#clearButton.disabled = true;
        } else {
            this.#clearButton.classList.add("btn-danger");
            this.#clearButton.classList.remove("btn-secondary");
            this.#clearButton.disabled = false;
        }
    }
}

/**
 * An account in the account selector for the recurring item editor.
 *
 */
class RecurringAccount {

    /**
     * The element
     * @type {HTMLLIElement}
     */
    #element;

    /**
     * The account code
     * @type {string}
     */
    code;

    /**
     * The account text
     * @type {string}
     */
    text;

    /**
     * The values to query against
     * @type {string[]}
     */
    #queryValues;

    /**
     * Constructs the account in the account selector for the recurring item editor.
     *
     * @param selector {RecurringAccountSelector} the account selector
     * @param element {HTMLLIElement} the element
     */
    constructor(selector, element) {
        this.#element = element;
        this.code = element.dataset.code;
        this.text = element.dataset.text;
        this.#queryValues = JSON.parse(element.dataset.queryValues);

        this.#element.onclick = () => selector.editor.saveAccount(this);
    }

    /**
     * Returns whether the account matches the query.
     *
     * @param query {string} the query term
     * @return {boolean} true if the option matches, or false otherwise
     */
    isMatched(query) {
        if (query === "") {
            return true;
        }
        for (const queryValue of this.#queryValues) {
            if (queryValue.toLowerCase().includes(query.toLowerCase())) {
                return true;
            }
        }
        return false;
    }

    /**
     * Sets whether the option is shown.
     *
     * @param isShown {boolean} true to show, or false otherwise
     */
    setShown(isShown) {
        if (isShown) {
            this.#element.classList.remove("d-none");
        } else {
            this.#element.classList.add("d-none");
        }
    }

    /**
     * Sets whether the option is active.
     *
     * @param isActive {boolean} true if active, or false otherwise
     */
    setActive(isActive) {
        if (isActive) {
            this.#element.classList.add("active");
        } else {
            this.#element.classList.remove("active");
        }
    }
}
