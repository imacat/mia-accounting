/* The Mia! Accounting Flask Project
 * transaction-form.js: The JavaScript for the transaction form
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
    TransactionForm.initialize();
});

/**
 * The transaction form
 *
 */
class TransactionForm {

    /**
     * The form element
     * @type {HTMLFormElement}
     */
    #element;

    /**
     * The template to add a new journal entry
     * @type {string}
     */
    entryTemplate;

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
     * Constructs the transaction form.
     *
     */
    constructor() {
        this.#element = document.getElementById("accounting-form");
        this.entryTemplate = this.#element.dataset.entryTemplate;
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
            const element = document.getElementById("accounting-currency-" + String(newIndex));
            this.#currencies.push(new CurrencySubForm(this, element));
            this.#resetDeleteCurrencyButtons();
            this.#initializeDragAndDropReordering();
        };
        this.#resetDeleteCurrencyButtons();
        this.#initializeDragAndDropReordering();
        this.#date.onchange = () => {
            this.#validateDate();
        };
        this.#note.onchange = () => {
            this.#validateNote();
        }
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
                const isAnyEntryMatched = () => {
                    for (const entry of currency.getEntries()) {
                        if (entry.isMatched) {
                            return true;
                        }
                    }
                    return false;
                };
                if (isAnyEntryMatched()) {
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
     * Returns all the journal entries in the form.
     *
     * @param entryType {string|null} the entry type, either "debit" or "credit", or null for both
     * @return {JournalEntrySubForm[]} all the journal entry sub-forms
     */
    getEntries(entryType = null) {
        const entries = [];
        for (const currency of this.#currencies) {
            entries.push(...currency.getEntries(entryType));
        }
        return entries;
    }

    /**
     * Returns the account codes used in the form.
     *
     * @param entryType {string} the entry type, either "debit" or "credit"
     * @return {string[]} the account codes used in the form
     */
    getAccountCodesUsed(entryType) {
        return this.getEntries(entryType).map((entry) => entry.getAccountCode())
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
        let lastOriginalEntryDate = null;
        for (const entry of this.getEntries()) {
            const date = entry.getOriginalEntryDate();
            if (date !== null) {
                if (lastOriginalEntryDate === null || lastOriginalEntryDate < date) {
                    lastOriginalEntryDate = date;
                }
            }
        }
        this.#date.min = lastOriginalEntryDate === null? "": lastOriginalEntryDate;
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
            this.#dateError.innerText = A_("The date cannot be earlier than the original entries.");
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
     * The transaction form
     * @type {TransactionForm}
     */
    static #form;

    /**
     * Initializes the transaction form.
     *
     */
    static initialize() {
        this.#form = new TransactionForm()
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
     * The transaction form
     * @type {TransactionForm}
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
     * @type {DebitCreditSideSubForm|null}
     */
    #debit;

    /**
     * The credit side
     * @type {DebitCreditSideSubForm|null}
     */
    #credit;

    /**
     * Constructs a currency sub-form
     *
     * @param form {TransactionForm} the transaction form
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
        this.#debit = debitElement === null? null: new DebitCreditSideSubForm(this, debitElement, "debit");
        const creditElement = document.getElementById(this.#prefix + "-credit");
        this.#credit = creditElement == null? null: new DebitCreditSideSubForm(this, creditElement, "credit");
        this.#codeSelect.onchange = () => {
            this.#code.value = this.#codeSelect.value;
        };
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
     * Returns all the journal entries in the form.
     *
     * @param entryType {string|null} the entry type, either "debit" or "credit", or null for both
     * @return {JournalEntrySubForm[]} all the journal entry sub-forms
     */
    getEntries(entryType = null) {
        const entries = []
        for (const side of [this.#debit, this.#credit]) {
            if (side !== null ) {
                if (entryType === null || side.entryType === entryType) {
                    entries.push(...side.entries);
                }
            }
        }
        return entries;
    }

    /**
     * Updates whether to enable the currency code selector
     *
     */
    updateCodeSelectorStatus() {
        let isEnabled = true;
        for (const entry of this.getEntries()) {
            if (entry.getOriginalEntryId() !== null) {
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
class DebitCreditSideSubForm {

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
     * The entry type, either "debit" or "credit"
     * @type {string}
     */
    entryType;

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
     * The journal entry list
     * @type {HTMLUListElement}
     */
    #entryList;

    /**
     * The journal entry sub-forms
     * @type {JournalEntrySubForm[]}
     */
    entries;

    /**
     * The total
     * @type {HTMLSpanElement}
     */
    #total;

    /**
     * The button to add a new entry
     * @type {HTMLButtonElement}
     */
    #addEntryButton;

    /**
     * Constructs a debit or credit side sub-form
     *
     * @param currency {CurrencySubForm} the currency sub-form
     * @param element {HTMLDivElement} the element
     * @param entryType {string} the entry type, either "debit" or "credit"
     */
    constructor(currency, element, entryType) {
        this.currency = currency;
        this.#element = element;
        this.#currencyIndex = currency.index;
        this.entryType = entryType;
        this.#prefix = "accounting-currency-" + String(this.#currencyIndex) + "-" + entryType;
        this.#error = document.getElementById(this.#prefix + "-error");
        this.#entryList = document.getElementById(this.#prefix + "-list");
        // noinspection JSValidateTypes
        this.entries = Array.from(document.getElementsByClassName(this.#prefix)).map((element) => new JournalEntrySubForm(this, element));
        this.#total = document.getElementById(this.#prefix + "-total");
        this.#addEntryButton = document.getElementById(this.#prefix + "-add-entry");
        this.#addEntryButton.onclick = () => {
            JournalEntryEditor.addNew(this);
        };
        this.#resetDeleteJournalEntryButtons();
        this.#initializeDragAndDropReordering();
    }

    /**
     * Adds a new journal entry sub-form
     *
     * @returns {JournalEntrySubForm} the newly-added journal entry sub-form
     */
    addJournalEntry() {
        const newIndex = 1 + (this.entries.length === 0? 0: Math.max(...this.entries.map((entry) => entry.entryIndex)));
        const html = this.currency.form.entryTemplate
            .replaceAll("CURRENCY_INDEX", escapeHtml(String(this.#currencyIndex)))
            .replaceAll("ENTRY_TYPE", escapeHtml(this.entryType))
            .replaceAll("ENTRY_INDEX", escapeHtml(String(newIndex)));
        this.#entryList.insertAdjacentHTML("beforeend", html);
        const entry = new JournalEntrySubForm(this, document.getElementById(this.#prefix + "-" + String(newIndex)));
        this.entries.push(entry);
        this.#resetDeleteJournalEntryButtons();
        this.#initializeDragAndDropReordering();
        this.validate();
        return entry;
    }

    /**
     * Deletes a journal entry sub-form
     *
     * @param entry {JournalEntrySubForm}
     */
    deleteJournalEntry(entry) {
        const index = this.entries.indexOf(entry);
        this.entries.splice(index, 1);
        this.updateTotal();
        this.currency.updateCodeSelectorStatus();
        this.currency.form.updateMinDate();
        this.#resetDeleteJournalEntryButtons();
    }

    /**
     * Resets the buttons to delete the journal entry sub-forms
     *
     */
    #resetDeleteJournalEntryButtons() {
        if (this.entries.length === 1) {
            this.entries[0].deleteButton.classList.add("d-none");
        } else {
            for (const entry of this.entries) {
                if (entry.isMatched) {
                    entry.deleteButton.classList.add("d-none");
                } else {
                    entry.deleteButton.classList.remove("d-none");
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
        for (const entry of this.entries) {
            const amount = entry.getAmount();
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
        initializeDragAndDropReordering(this.#entryList, () => {
            const entryId = Array.from(this.#entryList.children).map((entry) => entry.id);
            this.entries.sort((a, b) => entryId.indexOf(a.element.id) - entryId.indexOf(b.element.id));
            for (let i = 0; i < this.entries.length; i++) {
                this.entries[i].no.value = String(i + 1);
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
        for (const entry of this.entries) {
            isValid = entry.validate() && isValid;
        }
        return isValid;
    }

    /**
     * Validates the form, the validator itself.
     *
     * @returns {boolean} true if valid, or false otherwise
     */
    #validateReal() {
        if (this.entries.length === 0) {
            this.#element.classList.add("is-invalid");
            this.#error.innerText = A_("Please add some journal entries.");
            return false;
        }
        this.#element.classList.remove("is-invalid");
        this.#error.innerText = "";
        return true;
    }
}

/**
 * The journal entry sub-form.
 *
 */
class JournalEntrySubForm {

    /**
     * The debit or credit entry side sub-form
     * @type {DebitCreditSideSubForm}
     */
    side;

    /**
     * The element
     * @type {HTMLLIElement}
     */
    element;

    /**
     * The entry type, either "debit" or "credit"
     * @type {string}
     */
    entryType;

    /**
     * The entry index
     * @type {number}
     */
    entryIndex;

    /**
     * Whether this is an original entry with offsets
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
     * The ID of the original entry
     * @type {HTMLInputElement}
     */
    #originalEntryId;

    /**
     * The text of the original entry
     * @type {HTMLDivElement}
     */
    #originalEntryText;

    /**
     * The offset entries
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
     * The button to delete journal entry
     * @type {HTMLButtonElement}
     */
    deleteButton;

    /**
     * Constructs the journal entry sub-form.
     *
     * @param side {DebitCreditSideSubForm} the debit or credit entry side sub-form
     * @param element {HTMLLIElement} the element
     */
    constructor(side, element) {
        this.side = side;
        this.element = element;
        this.entryType = element.dataset.entryType;
        this.entryIndex = parseInt(element.dataset.entryIndex);
        this.isMatched = element.classList.contains("accounting-matched-entry");
        this.#prefix = "accounting-currency-" + element.dataset.currencyIndex + "-" + this.entryType + "-" + this.entryIndex;
        this.#control = document.getElementById(this.#prefix + "-control");
        this.#error = document.getElementById(this.#prefix + "-error");
        this.no = document.getElementById(this.#prefix + "-no");
        this.#accountCode = document.getElementById(this.#prefix + "-account-code");
        this.#accountText = document.getElementById(this.#prefix + "-account-text");
        this.#summary = document.getElementById(this.#prefix + "-summary");
        this.#summaryText = document.getElementById(this.#prefix + "-summary-text");
        this.#originalEntryId = document.getElementById(this.#prefix + "-original-entry-id");
        this.#originalEntryText = document.getElementById(this.#prefix + "-original-entry-text");
        this.#offsets = document.getElementById(this.#prefix + "-offsets");
        this.#amount = document.getElementById(this.#prefix + "-amount");
        this.#amountText = document.getElementById(this.#prefix + "-amount-text");
        this.deleteButton = document.getElementById(this.#prefix + "-delete");
        this.#control.onclick = () => {
            JournalEntryEditor.edit(this, this.#originalEntryId.value, this.#originalEntryId.dataset.date, this.#originalEntryId.dataset.text, this.#summary.value, this.#accountCode.value, this.#accountCode.dataset.text, this.#amount.value, this.#amount.dataset.min);
        };
        this.deleteButton.onclick = () => {
            this.element.parentElement.removeChild(this.element);
            this.side.deleteJournalEntry(this);
        };
    }

    /**
     * Returns whether the entry is an original entry.
     *
     * @return {boolean} true if the entry is an original entry, or false otherwise
     */
    isOriginalEntry() {
        return "isOriginalEntry" in this.element.dataset;
    }

    /**
     * Returns the ID of the original entry.
     *
     * @return {string|null} the ID of the original entry
     */
    getOriginalEntryId() {
        return this.#originalEntryId.value === ""? null: this.#originalEntryId.value;
    }

    /**
     * Returns the date of the original entry.
     *
     * @return {string|null} the date of the original entry
     */
    getOriginalEntryDate() {
        return this.#originalEntryId.dataset.date === ""? null: this.#originalEntryId.dataset.date;
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
     * Returns the amount.
     *
     * @return {Decimal|null} the amount
     */
    getAmount() {
        return this.#amount.value === ""? null: new Decimal(this.#amount.value);
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
     * Stores the data into the journal entry sub-form.
     *
     * @param isOriginalEntry {boolean} true if this is an original entry, or false otherwise
     * @param originalEntryId {string} the ID of the original entry
     * @param originalEntryDate {string} the date of the original entry
     * @param originalEntryText {string} the text of the original entry
     * @param accountCode {string} the account code
     * @param accountText {string} the account text
     * @param summary {string} the summary
     * @param amount {string} the amount
     */
    save(isOriginalEntry, originalEntryId, originalEntryDate, originalEntryText, accountCode, accountText, summary, amount) {
        if (isOriginalEntry) {
            this.#offsets.classList.remove("d-none");
        } else {
            this.#offsets.classList.add("d-none");
        }
        this.#originalEntryId.value = originalEntryId;
        this.#originalEntryId.dataset.date = originalEntryDate;
        this.#originalEntryId.dataset.text = originalEntryText;
        if (originalEntryText === "") {
            this.#originalEntryText.classList.add("d-none");
            this.#originalEntryText.innerText = "";
        } else {
            this.#originalEntryText.classList.remove("d-none");
            this.#originalEntryText.innerText = A_("Offset %(entry)s", {entry: originalEntryText});
        }
        this.#accountCode.value = accountCode;
        this.#accountCode.dataset.text = accountText;
        this.#accountText.innerText = accountText;
        this.#summary.value = summary;
        this.#summaryText.innerText = summary;
        this.#amount.value = amount;
        this.#amountText.innerText = formatDecimal(new Decimal(amount));
        this.validate();
        this.side.updateTotal();
        this.side.currency.updateCodeSelectorStatus();
        this.side.currency.form.updateMinDate();
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
