/* The Mia! Accounting Project
 * journal-entry-form.js: The JavaScript for the journal entry form
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
 * First written: 2023/2/25
 */
"use strict";

document.addEventListener("DOMContentLoaded", () => {
    JournalEntryForm.initialize();
});

/**
 * The journal entry form
 *
 */
class JournalEntryForm {

    /**
     * The form element
     * @type {HTMLFormElement}
     */
    #element;

    /**
     * The template to add a new line item
     * @type {string}
     */
    lineItemTemplate;

    /**
     * The date
     * @type {HTMLInputElement}
     */
    #date;

    /**
     * The error message of the date
     * @type {HTMLDivElement}
     */
    #dateError;

    /**
     * The control of the currencies
     * @type {HTMLDivElement}
     */
    #currencyControl;

    /**
     * The error message of the currencies
     * @type {HTMLDivElement}
     */
    #currencyError;

    /**
     * The currency list
     * @type {HTMLDivElement}
     */
    #currencyList;

    /**
     * The currency sub-forms
     * @type {CurrencySubForm[]}
     */
    #currencies;

    /**
     * The button to add a new currency
     * @type {HTMLButtonElement}
     */
    #addCurrencyButton;

    /**
     * The note
     * @type {HTMLTextAreaElement}
     */
    #note;

    /**
     * The error message of the note
     * @type {HTMLDivElement}
     */
    #noteError;

    /**
     * The line item editor
     * @type {JournalEntryLineItemEditor}
     */
    lineItemEditor;

    /**
     * Constructs the journal entry form.
     *
     */
    constructor() {
        this.#element = document.getElementById("accounting-form");
        this.lineItemTemplate = this.#element.dataset.lineItemTemplate;
        this.lineItemEditor = new JournalEntryLineItemEditor(this);
        this.#date = document.getElementById("accounting-date");
        this.#dateError = document.getElementById("accounting-date-error");
        this.#currencyControl = document.getElementById("accounting-currencies");
        this.#currencyError = document.getElementById("accounting-currencies-error");
        this.#currencyList = document.getElementById("accounting-currency-list");
        this.#currencies = Array.from(document.getElementsByClassName("accounting-currency"))
            .map((element) => new CurrencySubForm(this, element));
        this.#addCurrencyButton = document.getElementById("accounting-add-currency");
        this.#note = document.getElementById("accounting-note");
        this.#noteError = document.getElementById("accounting-note-error");

        this.#addCurrencyButton.onclick = () => {
            const newIndex = 1 + (this.#currencies.length === 0? 0: Math.max(...this.#currencies.map((currency) => currency.index)));
            const html = this.#element.dataset.currencyTemplate
                .replaceAll("CURRENCY_INDEX", escapeHtml(String(newIndex)));
            this.#currencyList.insertAdjacentHTML("beforeend", html);
            const element = document.getElementById(`accounting-currency-${String(newIndex)}`);
            this.#currencies.push(new CurrencySubForm(this, element));
            this.#resetDeleteCurrencyButtons();
            this.#initializeDragAndDropReordering();
        };
        this.#resetDeleteCurrencyButtons();
        this.#initializeDragAndDropReordering();
        this.#date.onchange = () => this.#validateDate();
        this.#note.onchange = () => this.#validateNote();
        this.#element.onsubmit = () => {
            return this.#validate();
        };
    }

    /**
     * Deletes a currency sub-form.
     *
     * @param currency {CurrencySubForm} the currency sub-form to delete
     */
    deleteCurrency(currency) {
        const index = this.#currencies.indexOf(currency);
        this.#currencies.splice(index, 1);
        this.#resetDeleteCurrencyButtons();
    }

    /**
     * Resets the buttons to delete the currency sub-forms
     *
     */
    #resetDeleteCurrencyButtons() {
        if (this.#currencies.length === 1) {
            this.#currencies[0].setDeleteButtonShown(false);
        } else {
            for (const currency of this.#currencies) {
                let isAnyLineItemMatched = false;
                for (const lineItem of currency.getLineItems()) {
                    if (lineItem.isMatched) {
                        isAnyLineItemMatched = true;
                        break;
                    }
                }
                currency.setDeleteButtonShown(!isAnyLineItemMatched);
            }
        }
    }

    /**
     * Initializes the drag and drop reordering on the currency sub-forms.
     *
     */
    #initializeDragAndDropReordering() {
        initializeDragAndDropReordering(this.#currencyList, () => {
            for (const currency of this.#currencies) {
                currency.resetNo();
            }
        });
    }

    /**
     * Returns all the line items in the form.
     *
     * @param debitCredit {string|null} Either "debit" or "credit", or null for both
     * @return {LineItemSubForm[]} all the line item sub-forms
     */
    getLineItems(debitCredit = null) {
        const lineItems = [];
        for (const currency of this.#currencies) {
            lineItems.push(...currency.getLineItems(debitCredit));
        }
        return lineItems;
    }

    /**
     * Returns the account codes used in the form.
     *
     * @param debitCredit {string} either "debit" or "credit"
     * @return {string[]} the account codes used in the form
     */
    getAccountCodesUsed(debitCredit) {
        return this.getLineItems(debitCredit).filter((lineItem) => lineItem.account !== null)
            .map((lineItem) => lineItem.account.code);
    }

    /**
     * Returns the date.
     *
     * @return {string} the date
     */
    get date() {
        return this.#date.value;
    }

    /**
     * Updates the minimal date.
     *
     */
    updateMinDate() {
        let lastOriginalLineItemDate = null;
        for (const lineItem of this.getLineItems()) {
            const date = lineItem.originalLineItemDate;
            if (date !== null) {
                if (lastOriginalLineItemDate === null || lastOriginalLineItemDate < date) {
                    lastOriginalLineItemDate = date;
                }
            }
        }
        this.#date.min = lastOriginalLineItemDate === null? "": lastOriginalLineItemDate;
        this.#validateDate();
    }

    /**
     * Validates the form.
     *
     * @returns {boolean} true if valid, or false otherwise
     */
    #validate() {
        let isValid = true;
        isValid = this.#validateDate() && isValid;
        isValid = this.#validateCurrencies() && isValid;
        isValid = this.#validateNote() && isValid;
        return isValid;
    }

    /**
     * Validates the date.
     *
     * @returns {boolean} true if valid, or false otherwise
     */
    #validateDate() {
        this.#date.value = this.#date.value.trim();
        this.#date.classList.remove("is-invalid");
        if (this.#date.value === "") {
            this.#date.classList.add("is-invalid");
            this.#dateError.innerText = A_("Please fill in the date.");
            return false;
        }
        if (this.#date.value < this.#date.min) {
            this.#date.classList.add("is-invalid");
            this.#dateError.innerText = A_("The date cannot be earlier than the original line items.");
            return false;
        }
        this.#date.classList.remove("is-invalid");
        this.#dateError.innerText = "";
        return true;
    }

    /**
     * Validates the currencies.
     *
     * @returns {boolean} true if valid, or false otherwise
     */
    #validateCurrencies() {
        let isValid = true;
        isValid = this.#validateCurrenciesReal() && isValid;
        for (const currency of this.#currencies) {
            isValid = currency.validate() && isValid;
        }
        return isValid;
    }

    /**
     * Validates the currency sub-forms, the validator itself.
     *
     * @returns {boolean} true if valid, or false otherwise
     */
    #validateCurrenciesReal() {
        if (this.#currencies.length === 0) {
            this.#currencyControl.classList.add("is-invalid");
            this.#currencyError.innerText = A_("Please add some currencies.");
            return false;
        }
        this.#currencyControl.classList.remove("is-invalid");
        this.#currencyError.innerText = "";
        return true;
    }

    /**
     * Validates the note.
     *
     * @returns {boolean} true if valid, or false otherwise
     */
    #validateNote() {
        this.#note.value = this.#note.value
             .replace(/^\s*\n/, "")
             .trimEnd();
        this.#note.classList.remove("is-invalid");
        this.#noteError.innerText = "";
        return true;
    }

    /**
     * The journal entry form
     * @type {JournalEntryForm}
     */
    static #form;

    /**
     * Initializes the journal entry form.
     *
     */
    static initialize() {
        this.#form = new JournalEntryForm()
    }
}

/**
 * The currency sub-form.
 *
 */
class CurrencySubForm {

    /**
     * The element
     * @type {HTMLDivElement}
     */
    #element;

    /**
     * The journal entry form
     * @type {JournalEntryForm}
     */
    form;

    /**
     * The currency index
     * @type {number}
     */
    index;

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
     * The number
     * @type {HTMLInputElement}
     */
    #no;

    /**
     * The currency code
     * @type {HTMLInputElement}
     */
    #code;

    /**
     * The currency code selector
     * @type {HTMLSelectElement}
     */
    #codeSelect;

    /**
     * The button to delete the currency
     * @type {HTMLButtonElement}
     */
    #deleteButton;

    /**
     * The debit sub-form
     * @type {DebitCreditSubForm|null}
     */
    #debit;

    /**
     * The credit sub-form
     * @type {DebitCreditSubForm|null}
     */
    #credit;

    /**
     * Constructs a currency sub-form
     *
     * @param form {JournalEntryForm} the journal entry form
     * @param element {HTMLDivElement} the currency sub-form element
     */
    constructor(form, element) {
        this.#element = element;
        this.form = form;
        this.index = parseInt(this.#element.dataset.index);
        const prefix = `accounting-currency-${String(this.index)}`;
        this.#control = document.getElementById(`${prefix}-control`);
        this.#error = document.getElementById(`${prefix}-error`);
        this.#no = document.getElementById(`${prefix}-no`);
        this.#code = document.getElementById(`${prefix}-code`);
        this.#codeSelect = document.getElementById(`${prefix}-code-select`);
        this.#deleteButton = document.getElementById(`${prefix}-delete`);
        const debitElement = document.getElementById(`${prefix}-debit`);
        this.#debit = debitElement === null? null: new DebitCreditSubForm(this, debitElement, "debit");
        const creditElement = document.getElementById(`${prefix}-credit`);
        this.#credit = creditElement == null? null: new DebitCreditSubForm(this, creditElement, "credit");
        this.#codeSelect.onchange = () => this.#code.value = this.#codeSelect.value;
        this.#deleteButton.onclick = () => {
            this.#element.parentElement.removeChild(this.#element);
            this.form.deleteCurrency(this);
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
     * Returns the currency code.
     *
     * @return {string} the currency code
     */
    get currencyCode() {
        return this.#code.value;
    }

    /**
     * Sets whether the delete button is shown.
     *
     * @param isShown {boolean} true to show, or false otherwise
     */
    setDeleteButtonShown(isShown) {
        setElementShown(this.#deleteButton, isShown);
    }

    /**
     * Returns all the line items in the form.
     *
     * @param debitCredit {string|null} either "debit" or "credit", or null for both
     * @return {LineItemSubForm[]} all the line item sub-forms
     */
    getLineItems(debitCredit = null) {
        const lineItems = []
        for (const debitCreditSubForm of [this.#debit, this.#credit]) {
            if (debitCreditSubForm !== null ) {
                if (debitCredit === null || debitCreditSubForm.debitCredit === debitCredit) {
                    lineItems.push(...debitCreditSubForm.lineItems);
                }
            }
        }
        return lineItems;
    }

    /**
     * Updates whether to enable the currency code selector
     *
     */
    updateCodeSelectorStatus() {
        let isEnabled = true;
        for (const lineItem of this.getLineItems()) {
            if (lineItem.originalLineItemId !== null) {
                isEnabled = false;
                break;
            }
        }
        this.#codeSelect.disabled = !isEnabled;
    }

    /**
     * Validates the form.
     *
     * @returns {boolean} true if valid, or false otherwise
     */
    validate() {
        let isValid = true;
        if (this.#debit !== null) {
            isValid = this.#debit.validate() && isValid;
        }
        if (this.#credit !== null) {
            isValid = this.#credit.validate() && isValid;
        }
        isValid = this.validateBalance() && isValid;
        return isValid;
    }

    /**
     * Validates the valance.
     *
     * @returns {boolean} true if valid, or false otherwise
     */
    validateBalance() {
        if (this.#debit !== null && this.#credit !== null) {
            if (!this.#debit.total.equals(this.#credit.total)) {
                this.#control.classList.add("is-invalid");
                this.#error.innerText = A_("The totals of the debit and credit amounts do not match.");
                return false;
            }
        }
        this.#control.classList.remove("is-invalid");
        this.#error.innerText = "";
        return true;
    }
}

/**
 * The debit or credit sub-form
 *
 */
class DebitCreditSubForm {

    /**
     * The currency sub-form
     * @type {CurrencySubForm}
     */
    currency;

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
     * The currencyIndex
     * @type {number}
     */
    #currencyIndex;

    /**
     * Either "debit" or "credit"
     * @type {string}
     */
    debitCredit;

    /**
     * The prefix of the HTML ID and class names
     * @type {string}
     */
    #prefix;

    /**
     * The error message
     * @type {HTMLDivElement}
     */
    #error;

    /**
     * The line item list
     * @type {HTMLUListElement}
     */
    #lineItemList;

    /**
     * The line item sub-forms
     * @type {LineItemSubForm[]}
     */
    lineItems;

    /**
     * The total
     * @type {HTMLSpanElement}
     */
    #total;

    /**
     * The button to add a new line item
     * @type {HTMLButtonElement}
     */
    #addLineItemButton;

    /**
     * Constructs a debit or credit sub-form
     *
     * @param currency {CurrencySubForm} the currency sub-form
     * @param element {HTMLDivElement} the element
     * @param debitCredit {string} either "debit" or "credit"
     */
    constructor(currency, element, debitCredit) {
        this.currency = currency;
        this.#element = element;
        this.#currencyIndex = currency.index;
        this.debitCredit = debitCredit;
        this.#prefix = `accounting-currency-${String(this.#currencyIndex)}-${debitCredit}`;
        this.#content = document.getElementById(`${this.#prefix}-content`);
        this.#error = document.getElementById(`${this.#prefix}-error`);
        this.#lineItemList = document.getElementById(`${this.#prefix}-list`);
        this.lineItems = Array.from(document.getElementsByClassName(this.#prefix)).map((element) => new LineItemSubForm(this, element));
        this.#total = document.getElementById(`${this.#prefix}-total`);
        this.#addLineItemButton = document.getElementById(`${this.#prefix}-add-line-item`);

        this.#resetContent();
        this.#addLineItemButton.onclick = () => this.currency.form.lineItemEditor.onAddNew(this);
        this.#resetDeleteLineItemButtons();
        this.#initializeDragAndDropReordering();
    }

    /**
     * The callback when the line item editor is closed.
     *
     */
    onLineItemEditorClosed() {
        if (this.lineItems.length === 0) {
            this.#element.classList.remove("accounting-not-empty");
        }
    }

    /**
     * Adds a new line item sub-form
     *
     * @returns {LineItemSubForm} the newly-added line item sub-form
     */
    addLineItem() {
        const newIndex = 1 + (this.lineItems.length === 0? 0: Math.max(...this.lineItems.map((lineItem) => lineItem.index)));
        const html = this.currency.form.lineItemTemplate
            .replaceAll("CURRENCY_INDEX", escapeHtml(String(this.#currencyIndex)))
            .replaceAll("DEBIT_CREDIT", escapeHtml(this.debitCredit))
            .replaceAll("LINE_ITEM_INDEX", escapeHtml(String(newIndex)));
        this.#lineItemList.insertAdjacentHTML("beforeend", html);
        const lineItem = new LineItemSubForm(this, document.getElementById(`${this.#prefix}-${String(newIndex)}`));
        this.lineItems.push(lineItem);
        this.#resetContent();
        this.#resetDeleteLineItemButtons();
        this.#initializeDragAndDropReordering();
        this.validate();
        return lineItem;
    }

    /**
     * Deletes a line item sub-form
     *
     * @param lineItem {LineItemSubForm}
     */
    deleteLineItem(lineItem) {
        const index = this.lineItems.indexOf(lineItem);
        this.lineItems.splice(index, 1);
        this.updateTotal();
        this.currency.updateCodeSelectorStatus();
        this.currency.form.updateMinDate();
        this.#resetContent();
        this.#resetDeleteLineItemButtons();
    }

    /**
     * Resets the buttons to delete the line item sub-forms
     *
     */
    #resetDeleteLineItemButtons() {
        if (this.lineItems.length === 1) {
            this.lineItems[0].setDeleteButtonShown(false);
        } else {
            for (const lineItem of this.lineItems) {
                lineItem.setDeleteButtonShown(!lineItem.isMatched);
            }
        }
    }

    /**
     * Resets the layout of the content.
     *
     */
    #resetContent() {
        if (this.lineItems.length === 0) {
            this.#element.classList.remove("accounting-not-empty");
            this.#element.classList.add("accounting-clickable");
            this.#element.dataset.bsToggle = "modal"
            this.#element.dataset.bsTarget = `#${this.currency.form.lineItemEditor.modal.id}`;
            this.#element.onclick = () => {
                this.#element.classList.add("accounting-not-empty");
                this.currency.form.lineItemEditor.onAddNew(this);
            };
        } else {
            this.#element.classList.add("accounting-not-empty");
            this.#element.classList.remove("accounting-clickable");
            delete this.#element.dataset.bsToggle;
            delete this.#element.dataset.bsTarget;
            this.#element.onclick = null;
        }
        setElementShown(this.#content, this.lineItems.length !== 0);
    }

    /**
     * Returns the total amount.
     *
     * @return {Decimal} the total amount
     */
    get total() {
        let total = new Decimal("0");
        for (const lineItem of this.lineItems) {
            const amount = lineItem.amount;
            if (amount !== null) {
                total = total.plus(amount);
            }
        }
        return total;
    }

    /**
     * Updates the total
     *
     */
    updateTotal() {
        this.#total.innerText = formatDecimal(this.total);
        this.currency.validateBalance();
    }

    /**
     * Initializes the drag and drop reordering on the currency sub-forms.
     *
     */
    #initializeDragAndDropReordering() {
        initializeDragAndDropReordering(this.#lineItemList, () => {
            for (const lineItem of this.lineItems) {
                lineItem.resetNo();
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
        isValid = this.#validateReal() && isValid;
        for (const lineItem of this.lineItems) {
            isValid = lineItem.validate() && isValid;
        }
        return isValid;
    }

    /**
     * Validates the form, the validator itself.
     *
     * @returns {boolean} true if valid, or false otherwise
     */
    #validateReal() {
        if (this.lineItems.length === 0) {
            this.#element.classList.add("is-invalid");
            this.#error.innerText = A_("Please add some line items.");
            return false;
        }
        this.#element.classList.remove("is-invalid");
        this.#error.innerText = "";
        return true;
    }
}

/**
 * A journal entry account.
 *
 */
class JournalEntryAccount {

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
     * Whether the line items in the account needs offset
     * @type {boolean}
     */
    isNeedOffset;

    /**
     * Constructs a journal entry account.
     *
     * @param code {string} the account code
     * @param text {string} the account text
     * @param isNeedOffset {boolean} true if the line items in the account needs offset, or false otherwise
     */
    constructor(code, text, isNeedOffset) {
        this.code = code;
        this.text = text;
        this.isNeedOffset = isNeedOffset;
    }

    /**
     * Returns a copy of the account.
     *
     * @return {JournalEntryAccount} the copy of the account
     */
    copy() {
        return new JournalEntryAccount(this.code, this.text, this.isNeedOffset);
    }
}

/**
 * The line item sub-form.
 *
 */
class LineItemSubForm {

    /**
     * The debit or credit sub-form
     * @type {DebitCreditSubForm}
     */
    debitCreditSubForm;

    /**
     * The element
     * @type {HTMLLIElement}
     */
    #element;

    /**
     * Either "debit" or "credit"
     * @type {string}
     */
    debitCredit;

    /**
     * The line item index
     * @type {number}
     */
    index;

    /**
     * Whether this is an original line item with offsets
     * @type {boolean}
     */
    isMatched;

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
     * The number
     * @type {HTMLInputElement}
     */
    #no;

    /**
     * The account code
     * @type {HTMLInputElement}
     */
    #accountCode;

    /**
     * The text display of the account
     * @type {HTMLDivElement}
     */
    #accountText;

    /**
     * The description
     * @type {HTMLInputElement}
     */
    #description;

    /**
     * The text display of the description
     * @type {HTMLDivElement}
     */
    #descriptionText;

    /**
     * The ID of the original line item
     * @type {HTMLInputElement}
     */
    #originalLineItemId;

    /**
     * The text of the original line item
     * @type {HTMLDivElement}
     */
    #originalLineItemText;

    /**
     * The offset items
     * @type {HTMLInputElement}
     */
    #offsets;

    /**
     * The amount
     * @type {HTMLInputElement}
     */
    #amount;

    /**
     * The text display of the amount
     * @type {HTMLSpanElement}
     */
    #amountText;

    /**
     * The button to delete line item
     * @type {HTMLButtonElement}
     */
    #deleteButton;

    /**
     * Constructs the line item sub-form.
     *
     * @param debitCredit {DebitCreditSubForm} the debit or credit sub-form
     * @param element {HTMLLIElement} the element
     */
    constructor(debitCredit, element) {
        this.debitCreditSubForm = debitCredit;
        this.#element = element;
        this.debitCredit = element.dataset.debitCredit;
        this.index = parseInt(element.dataset.lineItemIndex);
        this.isMatched = element.classList.contains("accounting-matched-line-item");
        const prefix = `accounting-currency-${element.dataset.currencyIndex}-${this.debitCredit}-${String(this.index)}`;
        this.#control = document.getElementById(`${prefix}-control`);
        this.#error = document.getElementById(`${prefix}-error`);
        this.#no = document.getElementById(`${prefix}-no`);
        this.#accountCode = document.getElementById(`${prefix}-account-code`);
        this.#accountText = document.getElementById(`${prefix}-account-text`);
        this.#description = document.getElementById(`${prefix}-description`);
        this.#descriptionText = document.getElementById(`${prefix}-description-text`);
        this.#originalLineItemId = document.getElementById(`${prefix}-original-line-item-id`);
        this.#originalLineItemText = document.getElementById(`${prefix}-original-line-item-text`);
        this.#offsets = document.getElementById(`${prefix}-offsets`);
        this.#amount = document.getElementById(`${prefix}-amount`);
        this.#amountText = document.getElementById(`${prefix}-amount-text`);
        this.#deleteButton = document.getElementById(`${prefix}-delete`);
        this.#control.onclick = () => this.debitCreditSubForm.currency.form.lineItemEditor.onEdit(this);
        this.#deleteButton.onclick = () => {
            this.#element.parentElement.removeChild(this.#element);
            this.debitCreditSubForm.deleteLineItem(this);
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
     * Returns the ID of the original line item.
     *
     * @return {string|null} the ID of the original line item
     */
    get originalLineItemId() {
        return this.#originalLineItemId.value === ""? null: this.#originalLineItemId.value;
    }

    /**
     * Returns the date of the original line item.
     *
     * @return {string|null} the date of the original line item
     */
    get originalLineItemDate() {
        return this.#originalLineItemId.dataset.date === ""? null: this.#originalLineItemId.dataset.date;
    }

    /**
     * Returns the text of the original line item.
     *
     * @return {string|null} the text of the original line item
     */
    get originalLineItemText() {
        return this.#originalLineItemId.dataset.text === ""? null: this.#originalLineItemId.dataset.text;
    }

    /**
     * Returns the description.
     *
     * @return {string|null} the description
     */
    get description() {
        return this.#description.value === ""? null: this.#description.value;
    }

    /**
     * Returns the account.
     *
     * @return {JournalEntryAccount|null} the account
     */
    get account() {
        return this.#accountCode.value === null? null: new JournalEntryAccount(this.#accountCode.value, this.#accountCode.dataset.text, this.#accountCode.classList.contains("accounting-account-is-need-offset"));
    }

    /**
     * Returns the amount.
     *
     * @return {Decimal|null} the amount
     */
    get amount() {
        return this.#amount.value === ""? null: new Decimal(this.#amount.value);
    }

    /**
     * Returns the minimal amount.
     *
     * @return {Decimal|null} the minimal amount
     */
    get amountMin() {
        return this.#amount.dataset.min === ""? null: new Decimal(this.#amount.dataset.min);
    }

    /**
     * Sets whether the delete button is shown.
     *
     * @param isShown {boolean} true to show, or false otherwise
     */
    setDeleteButtonShown(isShown) {
        setElementShown(this.#deleteButton, isShown);
    }

    /**
     * Validates the form.
     *
     * @returns {boolean} true if valid, or false otherwise
     */
    validate() {
        if (this.#accountCode.value === "") {
            this.#control.classList.add("is-invalid");
            this.#error.innerText = A_("Please select the account.");
            return false;
        }
        if (this.#amount.value === "") {
            this.#control.classList.add("is-invalid");
            this.#error.innerText = A_("Please fill in the amount.");
            return false;
        }
        this.#control.classList.remove("is-invalid");
        this.#error.innerText = "";
        return true;
    }

    /**
     * Stores the data into the line item sub-form.
     *
     * @param editor {JournalEntryLineItemEditor} the line item editor
     */
    save(editor) {
        setElementShown(this.#offsets, editor.account.isNeedOffset);
        this.#originalLineItemId.value = editor.originalLineItemId === null? "": editor.originalLineItemId;
        this.#originalLineItemId.dataset.date = editor.originalLineItemDate === null? "": editor.originalLineItemDate;
        this.#originalLineItemId.dataset.text = editor.originalLineItemText === null? "": editor.originalLineItemText;
        setElementShown(this.#originalLineItemText, editor.originalLineItemText !== null);
        if (editor.originalLineItemText === null) {
            this.#originalLineItemText.innerText = "";
        } else {
            this.#originalLineItemText.innerText = A_("Offset %(item)s", {item: editor.originalLineItemText});
        }
        this.#accountCode.value = editor.account.code;
        this.#accountCode.dataset.text = editor.account.text;
        if (editor.account.isNeedOffset) {
            this.#accountCode.classList.add("accounting-account-is-need-offset");
        } else {
            this.#accountCode.classList.remove("accounting-account-is-need-offset");
        }
        this.#accountText.innerText = editor.account.text;
        this.#description.value = editor.description === null? "": editor.description;
        this.#descriptionText.innerText = editor.description === null? "": editor.description;
        this.#amount.value = editor.amount;
        this.#amountText.innerText = formatDecimal(new Decimal(editor.amount));
        this.validate();
        this.debitCreditSubForm.updateTotal();
        this.debitCreditSubForm.currency.updateCodeSelectorStatus();
        this.debitCreditSubForm.currency.form.updateMinDate();
    }
}

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
 * Formats a Decimal number.
 *
 * @param number {Decimal} the Decimal number
 * @returns {string} the formatted Decimal number
 */
function formatDecimal(number) {
    if (number.equals(new Decimal("0"))) {
        return "-";
    }
    const frac = number.modulo(1);
    const whole = Number(number.minus(frac)).toLocaleString();
    return whole + String(frac).substring(1);
}

/**
 * Sets whether an element is shown.
 *
 * @param element {HTMLElement} the element
 * @param isShown {boolean} true to show, or false otherwise
 * @private
 */
function setElementShown(element, isShown) {
    if (isShown) {
        element.classList.remove("d-none");
    } else {
        element.classList.add("d-none");
    }
}
