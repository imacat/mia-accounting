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
    #entry;

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
        this.#summaryControl = document.getElementById(this.#prefix + "-summary-control");
        this.#summary = document.getElementById(this.#prefix + "-summary");
        this.#summaryError = document.getElementById(this.#prefix + "-summary-error");
        this.#accountControl = document.getElementById(this.#prefix + "-account-control");
        this.#account = document.getElementById(this.#prefix + "-account");
        this.#accountError = document.getElementById(this.#prefix + "-account-error")
        this.#amount = document.getElementById(this.#prefix + "-amount");
        this.#amountError = document.getElementById(this.#prefix + "-amount-error")
        this.#summaryControl.onclick = () => {
            SummaryEditor.start(this, this.#summary.dataset.value);
        };
        this.#accountControl.onclick = () => {
            AccountSelector.start(this, this.entryType);
        }
        this.#element.onsubmit = () => {
            if (this.#validate()) {
                if (this.#entry === null) {
                    this.#entry = this.#side.addJournalEntry();
                }
                this.#entry.save(this.#account.dataset.code, this.#account.dataset.text, this.#summary.dataset.value, this.#amount.value);
                bootstrap.Modal.getInstance(this.#modal).hide();
            }
            return false;
        };
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
        bootstrap.Modal.getOrCreateInstance(this.#modal).show();
    }

    /**
     * Saves the summary with the suggested account from the summary editor.
     *
     * @param summary {string} the summary
     * @param accountCode {string} the account code
     * @param accountText {string} the account text
     */
    saveSummaryWithAccount(summary, accountCode, accountText) {
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
     */
    saveAccount(code, text) {
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
        isValid = this.#validateSummary() && isValid;
        isValid = this.#validateAccount() && isValid;
        isValid = this.#validateAmount() && isValid
        return isValid;
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
        this.#amount.classList.remove("is-invalid");
        this.#amount.innerText = "";
        return true;
    }

    /**
     * Adds a new journal entry.
     *
     * @param side {DebitCreditSideSubForm} the debit or credit side sub-form
     */
    #onAddNew(side) {
        this.#entry = null;
        this.#side = side;
        this.entryType = this.#side.entryType;
        this.#element.dataset.entryType = side.entryType;
        this.#summaryControl.dataset.bsTarget = "#accounting-summary-editor-" + side.entryType + "-modal";
        this.#summaryControl.classList.remove("accounting-not-empty");
        this.#summaryControl.classList.remove("is-invalid");
        this.#summary.dataset.value = "";
        this.#summary.innerText = ""
        this.#summaryError.innerText = ""
        this.#accountControl.dataset.bsTarget = "#accounting-account-selector-" + side.entryType + "-modal";
        this.#accountControl.classList.remove("accounting-not-empty");
        this.#accountControl.classList.remove("is-invalid");
        this.#account.innerText = "";
        this.#account.dataset.code = "";
        this.#account.dataset.text = "";
        this.#accountError.innerText = "";
        this.#amount.value = "";
        this.#amount.classList.remove("is-invalid");
        this.#amountError.innerText = "";
    }

    /**
     * Edits a journal entry.
     *
     * @param entry {JournalEntrySubForm} the journal entry sub-form
     * @param summary {string} the summary
     * @param accountCode {string} the account code
     * @param accountText {string} the account text
     * @param amount {string} the amount
     */
    #onEdit(entry, summary, accountCode, accountText, amount) {
        this.#entry = entry;
        this.#side = entry.side;
        this.entryType = this.#side.entryType;
        this.#element.dataset.entryType = entry.entryType;
        this.#summaryControl.dataset.bsTarget = "#accounting-summary-editor-" + entry.entryType + "-modal";
        if (summary === "") {
            this.#summaryControl.classList.remove("accounting-not-empty");
        } else {
            this.#summaryControl.classList.add("accounting-not-empty");
        }
        this.#summary.dataset.value = summary;
        this.#summary.innerText = summary;
        this.#accountControl.dataset.bsTarget = "#accounting-account-selector-" + entry.entryType + "-modal";
        if (accountCode === "") {
            this.#accountControl.classList.remove("accounting-not-empty");
        } else {
            this.#accountControl.classList.add("accounting-not-empty");
        }
        this.#account.innerText = accountText;
        this.#account.dataset.code = accountCode;
        this.#account.dataset.text = accountText;
        this.#amount.value = amount;
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
     * @param summary {string} the summary
     * @param accountCode {string} the account code
     * @param accountText {string} the account text
     * @param amount {string} the amount
     */
    static edit(entry, summary, accountCode, accountText, amount) {
        this.#editor.#onEdit(entry, summary, accountCode, accountText, amount);
    }
}
