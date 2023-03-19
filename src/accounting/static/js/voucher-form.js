/* The Mia! Accounting Flask Project
 * voucher-form.js: The JavaScript for the voucher form
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
    VoucherForm.initialize();
});

/**
 * The voucher form
 *
 */
class VoucherForm {

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
     * @type {VoucherLineItemEditor}
     */
    lineItemEditor;

    /**
     * Constructs the voucher form.
     *
     */
    constructor() {
        this.#element = document.getElementById("accounting-form");
        this.lineItemTemplate = this.#element.dataset.lineItemTemplate;
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
        this.lineItemEditor = new VoucherLineItemEditor(this);

        this.#addCurrencyButton.onclick = () => {
            const newIndex = 1 + (this.#currencies.length === 0? 0: Math.max(...this.#currencies.map((currency) => currency.index)));
            const html = this.#element.dataset.currencyTemplate
                .replaceAll("CURRENCY_INDEX", escapeHtml(String(newIndex)));
            this.#currencyList.insertAdjacentHTML("beforeend", html);
            const element = document.getElementById("accounting-currency-" + String(newIndex));
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
            this.#currencies[0].deleteButton.classList.add("d-none");
        } else {
            for (const currency of this.#currencies) {
                let isAnyLineItemMatched = false;
                for (const lineItem of currency.getLineItems()) {
                    if (lineItem.isMatched) {
                        isAnyLineItemMatched = true;
                        break;
                    }
                }
                if (isAnyLineItemMatched) {
                    currency.deleteButton.classList.add("d-none");
                } else {
                    currency.deleteButton.classList.remove("d-none");
                }
            }
        }
    }

    /**
     * Initializes the drag and drop reordering on the currency sub-forms.
     *
     */
    #initializeDragAndDropReordering() {
        initializeDragAndDropReordering(this.#currencyList, () => {
            const currencyId = Array.from(this.#currencyList.children).map((currency) => currency.id);
            this.#currencies.sort((a, b) => currencyId.indexOf(a.element.id) - currencyId.indexOf(b.element.id));
            for (let i = 0; i < this.#currencies.length; i++) {
                this.#currencies[i].no.value = String(i + 1);
            }
        });
    }

    /**
     * Returns all the line items in the form.
     *
     * @param side {string|null} the side, either "debit" or "credit", or null for both
     * @return {LineItemSubForm[]} all the line item sub-forms
     */
    getLineItems(side = null) {
        const lineItems = [];
        for (const currency of this.#currencies) {
            lineItems.push(...currency.getLineItems(side));
        }
        return lineItems;
    }

    /**
     * Returns the account codes used in the form.
     *
     * @param side {string} the side, either "debit" or "credit"
     * @return {string[]} the account codes used in the form
     */
    getAccountCodesUsed(side) {
        return this.getLineItems(side).map((lineItem) => lineItem.getAccountCode())
            .filter((code) => code !== null);
    }

    /**
     * Returns the date.
     *
     * @return {string} the date
     */
    getDate() {
        return this.#date.value;
    }

    /**
     * Updates the minimal date.
     *
     */
    updateMinDate() {
        let lastOriginalLineItemDate = null;
        for (const lineItem of this.getLineItems()) {
            const date = lineItem.getOriginalLineItemDate();
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
     * The voucher form
     * @type {VoucherForm}
     */
    static #form;

    /**
     * Initializes the voucher form.
     *
     */
    static initialize() {
        this.#form = new VoucherForm()
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
    element;

    /**
     * The voucher form
     * @type {VoucherForm}
     */
    form;

    /**
     * The currency index
     * @type {number}
     */
    index;

    /**
     * The prefix of the HTML ID and class
     * @type {string}
     */
    #prefix;

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
    no;

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
    deleteButton;

    /**
     * The debit side
     * @type {SideSubForm|null}
     */
    #debit;

    /**
     * The credit side
     * @type {SideSubForm|null}
     */
    #credit;

    /**
     * Constructs a currency sub-form
     *
     * @param form {VoucherForm} the voucher form
     * @param element {HTMLDivElement} the currency sub-form element
     */
    constructor(form, element) {
        this.element = element;
        this.form = form;
        this.index = parseInt(this.element.dataset.index);
        this.#prefix = "accounting-currency-" + String(this.index);
        this.#control = document.getElementById(this.#prefix + "-control");
        this.#error = document.getElementById(this.#prefix + "-error");
        this.no = document.getElementById(this.#prefix + "-no");
        this.#code = document.getElementById(this.#prefix + "-code");
        this.#codeSelect = document.getElementById(this.#prefix + "-code-select");
        this.deleteButton = document.getElementById(this.#prefix + "-delete");
        const debitElement = document.getElementById(this.#prefix + "-debit");
        this.#debit = debitElement === null? null: new SideSubForm(this, debitElement, "debit");
        const creditElement = document.getElementById(this.#prefix + "-credit");
        this.#credit = creditElement == null? null: new SideSubForm(this, creditElement, "credit");
        this.#codeSelect.onchange = () => this.#code.value = this.#codeSelect.value;
        this.deleteButton.onclick = () => {
            this.element.parentElement.removeChild(this.element);
            this.form.deleteCurrency(this);
        };
    }

    /**
     * Returns the currency code.
     *
     * @return {string} the currency code
     */
    getCurrencyCode() {
        return this.#code.value;
    }

    /**
     * Returns all the line items in the form.
     *
     * @param side {string|null} the side, either "debit" or "credit", or null for both
     * @return {LineItemSubForm[]} all the line item sub-forms
     */
    getLineItems(side = null) {
        const lineItems = []
        for (const sideSubForm of [this.#debit, this.#credit]) {
            if (sideSubForm !== null ) {
                if (side === null || sideSubForm.side === side) {
                    lineItems.push(...sideSubForm.lineItems);
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
            if (lineItem.getOriginalLineItemId() !== null) {
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
            if (!this.#debit.getTotal().equals(this.#credit.getTotal())) {
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
 * The debit or credit side sub-form
 *
 */
class SideSubForm {

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
     * The currencyIndex
     * @type {number}
     */
    #currencyIndex;

    /**
     * The side, either "debit" or "credit"
     * @type {string}
     */
    side;

    /**
     * The prefix of the HTML ID and class
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
     * Constructs a debit or credit side sub-form
     *
     * @param currency {CurrencySubForm} the currency sub-form
     * @param element {HTMLDivElement} the element
     * @param side {string} the side, either "debit" or "credit"
     */
    constructor(currency, element, side) {
        this.currency = currency;
        this.#element = element;
        this.#currencyIndex = currency.index;
        this.side = side;
        this.#prefix = "accounting-currency-" + String(this.#currencyIndex) + "-" + side;
        this.#error = document.getElementById(this.#prefix + "-error");
        this.#lineItemList = document.getElementById(this.#prefix + "-list");
        // noinspection JSValidateTypes
        this.lineItems = Array.from(document.getElementsByClassName(this.#prefix)).map((element) => new LineItemSubForm(this, element));
        this.#total = document.getElementById(this.#prefix + "-total");
        this.#addLineItemButton = document.getElementById(this.#prefix + "-add-line-item");
        this.#addLineItemButton.onclick = () => this.currency.form.lineItemEditor.onAddNew(this);
        this.#resetDeleteLineItemButtons();
        this.#initializeDragAndDropReordering();
    }

    /**
     * Adds a new line item sub-form
     *
     * @returns {LineItemSubForm} the newly-added line item sub-form
     */
    addLineItem() {
        const newIndex = 1 + (this.lineItems.length === 0? 0: Math.max(...this.lineItems.map((lineItem) => lineItem.lineItemIndex)));
        const html = this.currency.form.lineItemTemplate
            .replaceAll("CURRENCY_INDEX", escapeHtml(String(this.#currencyIndex)))
            .replaceAll("SIDE", escapeHtml(this.side))
            .replaceAll("LINE_ITEM_INDEX", escapeHtml(String(newIndex)));
        this.#lineItemList.insertAdjacentHTML("beforeend", html);
        const lineItem = new LineItemSubForm(this, document.getElementById(this.#prefix + "-" + String(newIndex)));
        this.lineItems.push(lineItem);
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
        this.#resetDeleteLineItemButtons();
    }

    /**
     * Resets the buttons to delete the line item sub-forms
     *
     */
    #resetDeleteLineItemButtons() {
        if (this.lineItems.length === 1) {
            this.lineItems[0].deleteButton.classList.add("d-none");
        } else {
            for (const lineItem of this.lineItems) {
                if (lineItem.isMatched) {
                    lineItem.deleteButton.classList.add("d-none");
                } else {
                    lineItem.deleteButton.classList.remove("d-none");
                }
            }
        }
    }

    /**
     * Returns the total amount.
     *
     * @return {Decimal} the total amount
     */
    getTotal() {
        let total = new Decimal("0");
        for (const lineItem of this.lineItems) {
            const amount = lineItem.getAmount();
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
        this.#total.innerText = formatDecimal(this.getTotal());
        this.currency.validateBalance();
    }

    /**
     * Initializes the drag and drop reordering on the currency sub-forms.
     *
     */
    #initializeDragAndDropReordering() {
        initializeDragAndDropReordering(this.#lineItemList, () => {
            const lineItemId = Array.from(this.#lineItemList.children).map((lineItem) => lineItem.id);
            this.lineItems.sort((a, b) => lineItemId.indexOf(a.element.id) - lineItemId.indexOf(b.element.id));
            for (let i = 0; i < this.lineItems.length; i++) {
                this.lineItems[i].no.value = String(i + 1);
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
 * The line item sub-form.
 *
 */
class LineItemSubForm {

    /**
     * The debit or credit side sub-form
     * @type {SideSubForm}
     */
    sideSubForm;

    /**
     * The element
     * @type {HTMLLIElement}
     */
    element;

    /**
     * The side, either "debit" or "credit"
     * @type {string}
     */
    side;

    /**
     * The line item index
     * @type {number}
     */
    lineItemIndex;

    /**
     * Whether this is an original line item with offsets
     * @type {boolean}
     */
    isMatched;

    /**
     * The prefix of the HTML ID and class
     * @type {string}
     */
    #prefix;

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
    no;

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
     * The summary
     * @type {HTMLInputElement}
     */
    #summary;

    /**
     * The text display of the summary
     * @type {HTMLDivElement}
     */
    #summaryText;

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
    deleteButton;

    /**
     * Constructs the line item sub-form.
     *
     * @param side {SideSubForm} the debit or credit side sub-form
     * @param element {HTMLLIElement} the element
     */
    constructor(side, element) {
        this.sideSubForm = side;
        this.element = element;
        this.side = element.dataset.side;
        this.lineItemIndex = parseInt(element.dataset.lineItemIndex);
        this.isMatched = element.classList.contains("accounting-matched-line-item");
        this.#prefix = "accounting-currency-" + element.dataset.currencyIndex + "-" + this.side + "-" + this.lineItemIndex;
        this.#control = document.getElementById(this.#prefix + "-control");
        this.#error = document.getElementById(this.#prefix + "-error");
        this.no = document.getElementById(this.#prefix + "-no");
        this.#accountCode = document.getElementById(this.#prefix + "-account-code");
        this.#accountText = document.getElementById(this.#prefix + "-account-text");
        this.#summary = document.getElementById(this.#prefix + "-summary");
        this.#summaryText = document.getElementById(this.#prefix + "-summary-text");
        this.#originalLineItemId = document.getElementById(this.#prefix + "-original-line-item-id");
        this.#originalLineItemText = document.getElementById(this.#prefix + "-original-line-item-text");
        this.#offsets = document.getElementById(this.#prefix + "-offsets");
        this.#amount = document.getElementById(this.#prefix + "-amount");
        this.#amountText = document.getElementById(this.#prefix + "-amount-text");
        this.deleteButton = document.getElementById(this.#prefix + "-delete");
        this.#control.onclick = () => this.sideSubForm.currency.form.lineItemEditor.onEdit(this);
        this.deleteButton.onclick = () => {
            this.element.parentElement.removeChild(this.element);
            this.sideSubForm.deleteLineItem(this);
        };
    }

    /**
     * Returns whether the line item needs offset.
     *
     * @return {boolean} true if the line item needs offset, or false otherwise
     */
    isNeedOffset() {
        return "isNeedOffset" in this.element.dataset;
    }

    /**
     * Returns the ID of the original line item.
     *
     * @return {string|null} the ID of the original line item
     */
    getOriginalLineItemId() {
        return this.#originalLineItemId.value === ""? null: this.#originalLineItemId.value;
    }

    /**
     * Returns the date of the original line item.
     *
     * @return {string|null} the date of the original line item
     */
    getOriginalLineItemDate() {
        return this.#originalLineItemId.dataset.date === ""? null: this.#originalLineItemId.dataset.date;
    }

    /**
     * Returns the text of the original line item.
     *
     * @return {string|null} the text of the original line item
     */
    getOriginalLineItemText() {
        return this.#originalLineItemId.dataset.text === ""? null: this.#originalLineItemId.dataset.text;
    }

    /**
     * Returns the summary.
     *
     * @return {string|null} the summary
     */
    getSummary() {
        return this.#summary.value === ""? null: this.#summary.value;
    }

    /**
     * Returns the account code.
     *
     * @return {string|null} the account code
     */
    getAccountCode() {
        return this.#accountCode.value === ""? null: this.#accountCode.value;
    }

    /**
     * Returns the account text.
     *
     * @return {string|null} the account text
     */
    getAccountText() {
        return this.#accountCode.dataset.text === ""? null: this.#accountCode.dataset.text;
    }

    /**
     * Returns the amount.
     *
     * @return {Decimal|null} the amount
     */
    getAmount() {
        return this.#amount.value === ""? null: new Decimal(this.#amount.value);
    }

    /**
     * Returns the minimal amount.
     *
     * @return {Decimal|null} the minimal amount
     */
    getAmountMin() {
        return this.#amount.dataset.min === ""? null: new Decimal(this.#amount.dataset.min);
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
     * @param editor {VoucherLineItemEditor} the line item editor
     */
    save(editor) {
        if (editor.isNeedOffset) {
            this.#offsets.classList.remove("d-none");
        } else {
            this.#offsets.classList.add("d-none");
        }
        this.#originalLineItemId.value = editor.originalLineItemId === null? "": editor.originalLineItemId;
        this.#originalLineItemId.dataset.date = editor.originalLineItemDate === null? "": editor.originalLineItemDate;
        this.#originalLineItemId.dataset.text = editor.originalLineItemText === null? "": editor.originalLineItemText;
        if (editor.originalLineItemText === null) {
            this.#originalLineItemText.classList.add("d-none");
            this.#originalLineItemText.innerText = "";
        } else {
            this.#originalLineItemText.classList.remove("d-none");
            this.#originalLineItemText.innerText = A_("Offset %(item)s", {item: editor.originalLineItemText});
        }
        this.#accountCode.value = editor.accountCode === null? "": editor.accountCode;
        this.#accountCode.dataset.text = editor.accountText === null? "": editor.accountText;
        this.#accountText.innerText = editor.accountText === null? "": editor.accountText;
        this.#summary.value = editor.summary === null? "": editor.summary;
        this.#summaryText.innerText = editor.summary === null? "": editor.summary;
        this.#amount.value = editor.amount;
        this.#amountText.innerText = formatDecimal(new Decimal(editor.amount));
        this.validate();
        this.sideSubForm.updateTotal();
        this.sideSubForm.currency.updateCodeSelectorStatus();
        this.sideSubForm.currency.form.updateMinDate();
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
