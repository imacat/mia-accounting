/* The Mia! Accounting Flask Project
 * journal-entry-editor.js: The JavaScript for the journal entry editor
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

// Initializes the page JavaScript.
document.addEventListener("DOMContentLoaded", () => {
    JournalEntryEditor.initialize();
});

/**
 * The journal entry editor.
 *
 */
class JournalEntryEditor {

    /**
     * The journal entry editor
     * @type {HTMLFormElement}
     */
    #element;

    /**
     * The bootstrap modal
     * @type {HTMLDivElement}
     */
    #modal;

    /**
     * The entry type, either "debit" or "credit"
     * @type {string}
     */
    entryType;

    /**
     * The prefix of the HTML ID and class
     * @type {string}
     */
    #prefix = "accounting-entry-editor"

    /**
     * The container of the original entry
     * @type {HTMLDivElement}
     */
    #originalEntryContainer;

    /**
     * The control of the original entry
     * @type {HTMLDivElement}
     */
    #originalEntryControl;

    /**
     * The original entry
     * @type {HTMLDivElement}
     */
    #originalEntry;

    /**
     * The error message of the original entry
     * @type {HTMLDivElement}
     */
    #originalEntryError;

    /**
     * The delete button of the original entry
     * @type {HTMLButtonElement}
     */
    #originalEntryDelete;

    /**
     * The control of the summary
     * @type {HTMLDivElement}
     */
    #summaryControl;

    /**
     * The summary
     * @type {HTMLDivElement}
     */
    #summary;

    /**
     * The error message of the summary
     * @type {HTMLDivElement}
     */
    #summaryError;

    /**
     * The control of the account
     * @type {HTMLDivElement}
     */
    #accountControl;

    /**
     * The account
     * @type {HTMLDivElement}
     */
    #account;

    /**
     * The error message of the account
     * @type {HTMLDivElement}
     */
    #accountError;

    /**
     * The amount
     * @type {HTMLInputElement}
     */
    #amount;

    /**
     * The error message of the amount
     * @type {HTMLDivElement}
     */
    #amountError;

    /**
     * The journal entry to edit
     * @type {JournalEntrySubForm|null}
     */
    entry;

    /**
     * The debit or credit entry side sub-form
     * @type {DebitCreditSideSubForm}
     */
    #side;

    /**
     * Constructs a new journal entry editor.
     *
     */
    constructor() {
        this.#element = document.getElementById(this.#prefix);
        this.#modal = document.getElementById(this.#prefix + "-modal");
        this.#originalEntryContainer = document.getElementById(this.#prefix + "-original-entry-container");
        this.#originalEntryControl = document.getElementById(this.#prefix + "-original-entry-control");
        this.#originalEntry = document.getElementById(this.#prefix + "-original-entry");
        this.#originalEntryError = document.getElementById(this.#prefix + "-original-entry-error");
        this.#originalEntryDelete = document.getElementById(this.#prefix + "-original-entry-delete");
        this.#summaryControl = document.getElementById(this.#prefix + "-summary-control");
        this.#summary = document.getElementById(this.#prefix + "-summary");
        this.#summaryError = document.getElementById(this.#prefix + "-summary-error");
        this.#accountControl = document.getElementById(this.#prefix + "-account-control");
        this.#account = document.getElementById(this.#prefix + "-account");
        this.#accountError = document.getElementById(this.#prefix + "-account-error")
        this.#amount = document.getElementById(this.#prefix + "-amount");
        this.#amountError = document.getElementById(this.#prefix + "-amount-error");
        this.#originalEntryControl.onclick = () => OriginalEntrySelector.start(this, this.#originalEntry.dataset.id);
        this.#originalEntryDelete.onclick = () => this.clearOriginalEntry();
        this.#summaryControl.onclick = () => {
            SummaryEditor.start(this, this.#summary.dataset.value);
        };
        this.#accountControl.onclick = () => {
            AccountSelector.start(this, this.entryType);
        }
        this.#amount.onchange = () => {
            this.#validateAmount();
        }
        this.#element.onsubmit = () => {
            if (this.#validate()) {
                if (this.entry === null) {
                    this.entry = this.#side.addJournalEntry();
                }
                this.entry.save("isOriginalEntry" in this.#element.dataset, this.#originalEntry.dataset.id, this.#originalEntry.dataset.date, this.#originalEntry.dataset.text, this.#account.dataset.code, this.#account.dataset.text, this.#summary.dataset.value, this.#amount.value);
                bootstrap.Modal.getInstance(this.#modal).hide();
            }
            return false;
        };
    }

    /**
     * Saves the original entry from the original entry selector.
     *
     * @param originalEntry {OriginalEntry} the original entry
     */
    saveOriginalEntry(originalEntry) {
        delete this.#element.dataset.isOriginalEntry;
        this.#originalEntryContainer.classList.remove("d-none");
        this.#originalEntryControl.classList.add("accounting-not-empty");
        this.#originalEntry.dataset.id = originalEntry.id;
        this.#originalEntry.dataset.date = originalEntry.date;
        this.#originalEntry.dataset.text = originalEntry.text;
        this.#originalEntry.innerText = originalEntry.text;
        this.#setEnableSummaryAccount(false);
        if (originalEntry.summary === "") {
            this.#summaryControl.classList.remove("accounting-not-empty");
        } else {
            this.#summaryControl.classList.add("accounting-not-empty");
        }
        this.#summary.dataset.value = originalEntry.summary;
        this.#summary.innerText = originalEntry.summary;
        this.#accountControl.classList.add("accounting-not-empty");
        this.#account.dataset.code = originalEntry.accountCode;
        this.#account.dataset.text = originalEntry.accountText;
        this.#account.innerText = originalEntry.accountText;
        this.#amount.value = String(originalEntry.netBalance);
        this.#amount.max = String(originalEntry.netBalance);
        this.#amount.min = "0";
        this.#validate();
    }

    /**
     * Clears the original entry.
     *
     */
    clearOriginalEntry() {
        delete this.#element.dataset.isOriginalEntry;
        this.#originalEntryContainer.classList.add("d-none");
        this.#originalEntryControl.classList.remove("accounting-not-empty");
        this.#originalEntry.dataset.id = "";
        this.#originalEntry.dataset.date = "";
        this.#originalEntry.dataset.text = "";
        this.#originalEntry.innerText = "";
        this.#setEnableSummaryAccount(true);
        this.#accountControl.classList.remove("accounting-not-empty");
        this.#account.dataset.code = "";
        this.#account.dataset.text = "";
        this.#account.innerText = "";
        this.#amount.max = "";
    }

    /**
     * Returns the currency code.
     *
     * @return {string} the currency code
     */
    getCurrencyCode() {
        return this.#side.currency.getCurrencyCode();
    }

    /**
     * Returns the transaction form.
     *
     * @return {TransactionForm} the transaction form
     */
    getTransactionForm() {
        return this.#side.currency.form;
    }

    /**
     * Saves the summary from the summary editor.
     *
     * @param summary {string} the summary
     */
    saveSummary(summary) {
        if (summary === "") {
            this.#summaryControl.classList.remove("accounting-not-empty");
        } else {
            this.#summaryControl.classList.add("accounting-not-empty");
        }
        this.#summary.dataset.value = summary;
        this.#summary.innerText = summary;
        this.#validateSummary();
        bootstrap.Modal.getOrCreateInstance(this.#modal).show();
    }

    /**
     * Saves the summary with the suggested account from the summary editor.
     *
     * @param summary {string} the summary
     * @param accountCode {string} the account code
     * @param accountText {string} the account text
     * @param isAccountOffsetNeeded {boolean} true if the journal entries in the account need offset, or false otherwise
     */
    saveSummaryWithAccount(summary, accountCode, accountText, isAccountOffsetNeeded) {
        if (isAccountOffsetNeeded) {
            this.#element.dataset.isOriginalEntry = "true";
        } else {
            delete this.#element.dataset.isOriginalEntry;
        }
        this.#accountControl.classList.add("accounting-not-empty");
        this.#account.dataset.code = accountCode;
        this.#account.dataset.text = accountText;
        this.#account.innerText = accountText;
        this.#validateAccount();
        this.saveSummary(summary)
    }

    /**
     * Returns the account code.
     *
     * @return {string|null} the account code
     */
    getAccountCode() {
        return this.#account.dataset.code === "" ? null : this.#account.dataset.code;
    }

    /**
     * Clears the account.
     *
     */
    clearAccount() {
        delete this.#element.dataset.isOriginalEntry;
        this.#accountControl.classList.remove("accounting-not-empty");
        this.#account.dataset.code = "";
        this.#account.dataset.text = "";
        this.#account.innerText = "";
        this.#validateAccount();
    }

    /**
     * Sets the account.
     *
     * @param code {string} the account code
     * @param text {string} the account text
     * @param isOffsetNeeded {boolean} true if the journal entries in the account need offset or false otherwise
     */
    saveAccount(code, text, isOffsetNeeded) {
        if (isOffsetNeeded) {
            this.#element.dataset.isOriginalEntry = "true";
        } else {
            delete this.#element.dataset.isOriginalEntry;
        }
        this.#accountControl.classList.add("accounting-not-empty");
        this.#account.dataset.code = code;
        this.#account.dataset.text = text;
        this.#account.innerText = text;
        this.#validateAccount();
    }

    /**
     * Validates the form.
     *
     * @returns {boolean} true if valid, or false otherwise
     */
    #validate() {
        let isValid = true;
        isValid = this.#validateOriginalEntry() && isValid;
        isValid = this.#validateSummary() && isValid;
        isValid = this.#validateAccount() && isValid;
        isValid = this.#validateAmount() && isValid
        return isValid;
    }

    /**
     * Validates the original entry.
     *
     * @return {boolean} true if valid, or false otherwise
     * @private
     */
    #validateOriginalEntry() {
        this.#originalEntryControl.classList.remove("is-invalid");
        this.#originalEntryError.innerText = "";
        return true;
    }

    /**
     * Validates the summary.
     *
     * @return {boolean} true if valid, or false otherwise
     * @private
     */
    #validateSummary() {
        this.#summary.classList.remove("is-invalid");
        this.#summaryError.innerText = "";
        return true;
    }

    /**
     * Validates the account.
     *
     * @return {boolean} true if valid, or false otherwise
     */
    #validateAccount() {
        if (this.#account.dataset.code === "") {
            this.#accountControl.classList.add("is-invalid");
            this.#accountError.innerText = A_("Please select the account.");
            return false;
        }
        this.#accountControl.classList.remove("is-invalid");
        this.#accountError.innerText = "";
        return true;
    }

    /**
     * Validates the amount.
     *
     * @return {boolean} true if valid, or false otherwise
     * @private
     */
    #validateAmount() {
        this.#amount.value = this.#amount.value.trim();
        this.#amount.classList.remove("is-invalid");
        if (this.#amount.value === "") {
            this.#amount.classList.add("is-invalid");
            this.#amountError.innerText = A_("Please fill in the amount.");
            return false;
        }
        const amount =new Decimal(this.#amount.value);
        if (amount.lessThanOrEqualTo(0)) {
            this.#amount.classList.add("is-invalid");
            this.#amountError.innerText = A_("Please fill in a positive amount.");
            return false;
        }
        if (this.#amount.max !== "") {
            if (amount.greaterThan(new Decimal(this.#amount.max))) {
                this.#amount.classList.add("is-invalid");
                this.#amountError.innerText = A_("The amount must not exceed the net balance %(balance)s of the original entry.", {balance: new Decimal(this.#amount.max)});
                return false;
            }
        }
        if (this.#amount.min !== "") {
            const min = new Decimal(this.#amount.min);
            if (amount.lessThan(min)) {
                this.#amount.classList.add("is-invalid");
                this.#amountError.innerText = A_("The amount must not be less than the offset total %(total)s.", {total: formatDecimal(min)});
                return false;
            }
        }
        this.#amount.classList.remove("is-invalid");
        this.#amountError.innerText = "";
        return true;
    }

    /**
     * Adds a new journal entry.
     *
     * @param side {DebitCreditSideSubForm} the debit or credit side sub-form
     */
    #onAddNew(side) {
        this.entry = null;
        this.#side = side;
        this.entryType = this.#side.entryType;
        this.#element.dataset.entryType = side.entryType;
        delete this.#element.dataset.isOriginalEntry;
        this.#originalEntryContainer.classList.add("d-none");
        this.#originalEntryControl.classList.remove("accounting-not-empty");
        this.#originalEntryControl.classList.remove("is-invalid");
        this.#originalEntry.dataset.id = "";
        this.#originalEntry.dataset.date = "";
        this.#originalEntry.dataset.text = "";
        this.#originalEntry.innerText = "";
        this.#setEnableSummaryAccount(true);
        this.#summaryControl.classList.remove("accounting-not-empty");
        this.#summaryControl.classList.remove("is-invalid");
        this.#summary.dataset.value = "";
        this.#summary.innerText = ""
        this.#summaryError.innerText = ""
        this.#accountControl.classList.remove("accounting-not-empty");
        this.#accountControl.classList.remove("is-invalid");
        this.#account.dataset.code = "";
        this.#account.dataset.text = "";
        this.#account.innerText = "";
        this.#accountError.innerText = "";
        this.#amount.value = "";
        this.#amount.max = "";
        this.#amount.min = "0";
        this.#amount.classList.remove("is-invalid");
        this.#amountError.innerText = "";
    }

    /**
     * Edits a journal entry.
     *
     * @param entry {JournalEntrySubForm} the journal entry sub-form
     * @param originalEntryId {string} the ID of the original entry
     * @param originalEntryDate {string} the date of the original entry
     * @param originalEntryText {string} the text of the original entry
     * @param summary {string} the summary
     * @param accountCode {string} the account code
     * @param accountText {string} the account text
     * @param amount {string} the amount
     * @param amountMin {string} the minimal amount
     */
    #onEdit(entry, originalEntryId, originalEntryDate, originalEntryText, summary, accountCode, accountText, amount, amountMin) {
        this.entry = entry;
        this.#side = entry.side;
        this.entryType = this.#side.entryType;
        this.#element.dataset.entryType = entry.entryType;
        if (entry.isOriginalEntry()) {
            this.#element.dataset.isOriginalEntry = "true";
        } else {
            delete this.#element.dataset.isOriginalEntry;
        }
        if (originalEntryId === "") {
            this.#originalEntryContainer.classList.add("d-none");
            this.#originalEntryControl.classList.remove("accounting-not-empty");
        } else {
            this.#originalEntryContainer.classList.remove("d-none");
            this.#originalEntryControl.classList.add("accounting-not-empty");
        }
        this.#originalEntry.dataset.id = originalEntryId;
        this.#originalEntry.dataset.date = originalEntryDate;
        this.#originalEntry.dataset.text = originalEntryText;
        this.#originalEntry.innerText = originalEntryText;
        this.#setEnableSummaryAccount(!entry.isMatched && originalEntryId === "");
        if (summary === "") {
            this.#summaryControl.classList.remove("accounting-not-empty");
        } else {
            this.#summaryControl.classList.add("accounting-not-empty");
        }
        this.#summary.dataset.value = summary;
        this.#summary.innerText = summary;
        if (accountCode === "") {
            this.#accountControl.classList.remove("accounting-not-empty");
        } else {
            this.#accountControl.classList.add("accounting-not-empty");
        }
        this.#account.dataset.code = accountCode;
        this.#account.dataset.text = accountText;
        this.#account.innerText = accountText;
        this.#amount.value = amount;
        const maxAmount = this.#getMaxAmount();
        this.#amount.max = maxAmount === null? "": maxAmount;
        this.#amount.min = amountMin;
        this.#validate();
    }

    /**
     * Finds out the max amount.
     *
     * @return {Decimal|null} the max amount
     */
    #getMaxAmount() {
        if (this.#originalEntry.dataset.id === "") {
            return null;
        }
        return OriginalEntrySelector.getNetBalance(this.entry, this.getTransactionForm(), this.#originalEntry.dataset.id);
    }

    /**
     * Sets the enable status of the summary and account.
     *
     * @param isEnabled {boolean} true to enable, or false otherwise
     */
    #setEnableSummaryAccount(isEnabled) {
        if (isEnabled) {
            this.#summaryControl.dataset.bsToggle = "modal";
            this.#summaryControl.dataset.bsTarget = "#accounting-summary-editor-" + this.#side.entryType + "-modal";
            this.#summaryControl.classList.remove("accounting-disabled");
            this.#summaryControl.classList.add("accounting-clickable");
            this.#accountControl.dataset.bsToggle = "modal";
            this.#accountControl.dataset.bsTarget = "#accounting-account-selector-" + this.#side.entryType + "-modal";
            this.#accountControl.classList.remove("accounting-disabled");
            this.#accountControl.classList.add("accounting-clickable");
        } else {
            this.#summaryControl.dataset.bsToggle = "";
            this.#summaryControl.dataset.bsTarget = "";
            this.#summaryControl.classList.add("accounting-disabled");
            this.#summaryControl.classList.remove("accounting-clickable");
            this.#accountControl.dataset.bsToggle = "";
            this.#accountControl.dataset.bsTarget = "";
            this.#accountControl.classList.add("accounting-disabled");
            this.#accountControl.classList.remove("accounting-clickable");
        }
    }

    /**
     * The journal entry editor
     * @type {JournalEntryEditor}
     */
    static #editor;

    /**
     * Initializes the journal entry editor.
     *
     */
    static initialize() {
        this.#editor = new JournalEntryEditor();
    }

    /**
     * Adds a new journal entry.
     *
     * @param side {DebitCreditSideSubForm} the debit or credit side sub-form
     */
    static addNew(side) {
        this.#editor.#onAddNew(side);
    }

    /**
     * Edits a journal entry.
     *
     * @param entry {JournalEntrySubForm} the journal entry sub-form
     * @param originalEntryId {string} the ID of the original entry
     * @param originalEntryDate {string} the date of the original entry
     * @param originalEntryText {string} the text of the original entry
     * @param summary {string} the summary
     * @param accountCode {string} the account code
     * @param accountText {string} the account text
     * @param amount {string} the amount
     * @param amountMin {string} the minimal amount
     */
    static edit(entry, originalEntryId, originalEntryDate, originalEntryText, summary, accountCode, accountText, amount, amountMin) {
        this.#editor.#onEdit(entry, originalEntryId, originalEntryDate, originalEntryText, summary, accountCode, accountText, amount, amountMin);
    }
}
