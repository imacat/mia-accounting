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

/**
 * The journal entry editor.
 *
 */
class JournalEntryEditor {

    /**
     * The transaction form
     * @type {TransactionForm}
     */
    form;

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
    #originalEntryText;

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
    #summaryText;

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
    #accountText;

    /**
     * The error message of the account
     * @type {HTMLDivElement}
     */
    #accountError;

    /**
     * The amount
     * @type {HTMLInputElement}
     */
    #amountInput;

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
     * Whether the journal entry needs offset
     * @type {boolean}
     */
    isNeedOffset = false;

    /**
     * The ID of the original entry
     * @type {string|null}
     */
    originalEntryId = null;

    /**
     * The date of the original entry
     * @type {string|null}
     */
    originalEntryDate = null;

    /**
     * The text of the original entry
     * @type {string|null}
     */
    originalEntryText = null;

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
     * The summary
     * @type {string|null}
     */
    summary = null;

    /**
     * The amount
     * @type {string}
     */
    amount = "";

    /**
     * The summary editors
     * @type {{debit: SummaryEditor, credit: SummaryEditor}}
     */
    #summaryEditors;

    /**
     * The account selectors
     * @type {{debit: AccountSelector, credit: AccountSelector}}
     */
    #accountSelectors;

    /**
     * The original entry selector
     * @type {OriginalEntrySelector}
     */
    originalEntrySelector;

    /**
     * Constructs a new journal entry editor.
     *
     * @param form {TransactionForm} the transaction form
     */
    constructor(form) {
        this.form = form;
        this.#element = document.getElementById(this.#prefix);
        this.#modal = document.getElementById(this.#prefix + "-modal");
        this.#originalEntryContainer = document.getElementById(this.#prefix + "-original-entry-container");
        this.#originalEntryControl = document.getElementById(this.#prefix + "-original-entry-control");
        this.#originalEntryText = document.getElementById(this.#prefix + "-original-entry");
        this.#originalEntryError = document.getElementById(this.#prefix + "-original-entry-error");
        this.#originalEntryDelete = document.getElementById(this.#prefix + "-original-entry-delete");
        this.#summaryControl = document.getElementById(this.#prefix + "-summary-control");
        this.#summaryText = document.getElementById(this.#prefix + "-summary");
        this.#summaryError = document.getElementById(this.#prefix + "-summary-error");
        this.#accountControl = document.getElementById(this.#prefix + "-account-control");
        this.#accountText = document.getElementById(this.#prefix + "-account");
        this.#accountError = document.getElementById(this.#prefix + "-account-error")
        this.#amountInput = document.getElementById(this.#prefix + "-amount");
        this.#amountError = document.getElementById(this.#prefix + "-amount-error");
        this.#summaryEditors = SummaryEditor.getInstances(this);
        this.#accountSelectors = AccountSelector.getInstances(this);
        this.originalEntrySelector = new OriginalEntrySelector(this);
        this.#originalEntryControl.onclick = () => this.originalEntrySelector.onOpen()
        this.#originalEntryDelete.onclick = () => this.clearOriginalEntry();
        this.#summaryControl.onclick = () => this.#summaryEditors[this.entryType].onOpen();
        this.#accountControl.onclick = () => this.#accountSelectors[this.entryType].onOpen();
        this.#amountInput.onchange = () => this.#validateAmount();
        this.#element.onsubmit = () => {
            if (this.#validate()) {
                if (this.entry === null) {
                    this.entry = this.#side.addJournalEntry();
                }
                this.amount = this.#amountInput.value;
                this.entry.save(this);
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
        this.isNeedOffset = false;
        this.#originalEntryContainer.classList.remove("d-none");
        this.#originalEntryControl.classList.add("accounting-not-empty");
        this.originalEntryId = originalEntry.id;
        this.originalEntryDate = originalEntry.date;
        this.originalEntryText = originalEntry.text;
        this.#originalEntryText.innerText = originalEntry.text;
        this.#setEnableSummaryAccount(false);
        if (originalEntry.summary === "") {
            this.#summaryControl.classList.remove("accounting-not-empty");
        } else {
            this.#summaryControl.classList.add("accounting-not-empty");
        }
        this.summary = originalEntry.summary === ""? null: originalEntry.summary;
        this.#summaryText.innerText = originalEntry.summary;
        this.#accountControl.classList.add("accounting-not-empty");
        this.accountCode = originalEntry.accountCode;
        this.accountText = originalEntry.accountText;
        this.#accountText.innerText = originalEntry.accountText;
        this.#amountInput.value = String(originalEntry.netBalance);
        this.#amountInput.max = String(originalEntry.netBalance);
        this.#amountInput.min = "0";
        this.#validate();
    }

    /**
     * Clears the original entry.
     *
     */
    clearOriginalEntry() {
        this.isNeedOffset = false;
        this.#originalEntryContainer.classList.add("d-none");
        this.#originalEntryControl.classList.remove("accounting-not-empty");
        this.originalEntryId = null;
        this.originalEntryDate = null;
        this.originalEntryText = null;
        this.#originalEntryText.innerText = "";
        this.#setEnableSummaryAccount(true);
        this.#accountControl.classList.remove("accounting-not-empty");
        this.accountCode = null;
        this.accountText = null;
        this.#accountText.innerText = "";
        this.#amountInput.max = "";
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
        this.summary = summary === ""? null: summary;
        this.#summaryText.innerText = summary;
        this.#validateSummary();
        bootstrap.Modal.getOrCreateInstance(this.#modal).show();
    }

    /**
     * Saves the summary with the suggested account from the summary editor.
     *
     * @param summary {string} the summary
     * @param accountCode {string} the account code
     * @param accountText {string} the account text
     * @param isAccountNeedOffset {boolean} true if the journal entries in the account need offset, or false otherwise
     */
    saveSummaryWithAccount(summary, accountCode, accountText, isAccountNeedOffset) {
        this.isNeedOffset = isAccountNeedOffset;
        this.#accountControl.classList.add("accounting-not-empty");
        this.accountCode = accountCode;
        this.accountText = accountText;
        this.#accountText.innerText = accountText;
        this.#validateAccount();
        this.saveSummary(summary)
    }

    /**
     * Clears the account.
     *
     */
    clearAccount() {
        this.isNeedOffset = false;
        this.#accountControl.classList.remove("accounting-not-empty");
        this.accountCode = null;
        this.accountText = null;
        this.#accountText.innerText = "";
        this.#validateAccount();
    }

    /**
     * Sets the account.
     *
     * @param code {string} the account code
     * @param text {string} the account text
     * @param isNeedOffset {boolean} true if the journal entries in the account need offset or false otherwise
     */
    saveAccount(code, text, isNeedOffset) {
        this.isNeedOffset = isNeedOffset;
        this.#accountControl.classList.add("accounting-not-empty");
        this.accountCode = code;
        this.accountText = text;
        this.#accountText.innerText = text;
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
        this.#summaryText.classList.remove("is-invalid");
        this.#summaryError.innerText = "";
        return true;
    }

    /**
     * Validates the account.
     *
     * @return {boolean} true if valid, or false otherwise
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
     * Validates the amount.
     *
     * @return {boolean} true if valid, or false otherwise
     * @private
     */
    #validateAmount() {
        this.#amountInput.value = this.#amountInput.value.trim();
        this.#amountInput.classList.remove("is-invalid");
        if (this.#amountInput.value === "") {
            this.#amountInput.classList.add("is-invalid");
            this.#amountError.innerText = A_("Please fill in the amount.");
            return false;
        }
        const amount =new Decimal(this.#amountInput.value);
        if (amount.lessThanOrEqualTo(0)) {
            this.#amountInput.classList.add("is-invalid");
            this.#amountError.innerText = A_("Please fill in a positive amount.");
            return false;
        }
        if (this.#amountInput.max !== "") {
            if (amount.greaterThan(new Decimal(this.#amountInput.max))) {
                this.#amountInput.classList.add("is-invalid");
                this.#amountError.innerText = A_("The amount must not exceed the net balance %(balance)s of the original entry.", {balance: new Decimal(this.#amountInput.max)});
                return false;
            }
        }
        if (this.#amountInput.min !== "") {
            const min = new Decimal(this.#amountInput.min);
            if (amount.lessThan(min)) {
                this.#amountInput.classList.add("is-invalid");
                this.#amountError.innerText = A_("The amount must not be less than the offset total %(total)s.", {total: formatDecimal(min)});
                return false;
            }
        }
        this.#amountInput.classList.remove("is-invalid");
        this.#amountError.innerText = "";
        return true;
    }

    /**
     * The callback when adding a new journal entry.
     *
     * @param side {DebitCreditSideSubForm} the debit or credit side sub-form
     */
    onAddNew(side) {
        this.entry = null;
        this.#side = side;
        this.entryType = this.#side.entryType;
        this.isNeedOffset = false;
        this.#originalEntryContainer.classList.add("d-none");
        this.#originalEntryControl.classList.remove("accounting-not-empty");
        this.#originalEntryControl.classList.remove("is-invalid");
        this.originalEntryId = null;
        this.originalEntryDate = null;
        this.originalEntryText = null;
        this.#originalEntryText.innerText = "";
        this.#setEnableSummaryAccount(true);
        this.#summaryControl.classList.remove("accounting-not-empty");
        this.#summaryControl.classList.remove("is-invalid");
        this.summary = null;
        this.#summaryText.innerText = ""
        this.#summaryError.innerText = ""
        this.#accountControl.classList.remove("accounting-not-empty");
        this.#accountControl.classList.remove("is-invalid");
        this.accountCode = null;
        this.accountText = null;
        this.#accountText.innerText = "";
        this.#accountError.innerText = "";
        this.#amountInput.value = "";
        this.#amountInput.max = "";
        this.#amountInput.min = "0";
        this.#amountInput.classList.remove("is-invalid");
        this.#amountError.innerText = "";
    }

    /**
     * The callback when editing a journal entry.
     *
     * @param entry {JournalEntrySubForm} the journal entry sub-form
     */
    onEdit(entry) {
        this.entry = entry;
        this.#side = entry.side;
        this.entryType = this.#side.entryType;
        this.isNeedOffset = entry.isNeedOffset();
        this.originalEntryId = entry.getOriginalEntryId();
        this.originalEntryDate = entry.getOriginalEntryDate();
        this.originalEntryText = entry.getOriginalEntryText();
        this.#originalEntryText.innerText = this.originalEntryText;
        if (this.originalEntryId === null) {
            this.#originalEntryContainer.classList.add("d-none");
            this.#originalEntryControl.classList.remove("accounting-not-empty");
        } else {
            this.#originalEntryContainer.classList.remove("d-none");
            this.#originalEntryControl.classList.add("accounting-not-empty");
        }
        this.#setEnableSummaryAccount(!entry.isMatched && this.originalEntryId === null);
        this.summary = entry.getSummary();
        if (this.summary === null) {
            this.#summaryControl.classList.remove("accounting-not-empty");
        } else {
            this.#summaryControl.classList.add("accounting-not-empty");
        }
        this.#summaryText.innerText = this.summary === null? "": this.summary;
        if (entry.getAccountCode() === null) {
            this.#accountControl.classList.remove("accounting-not-empty");
        } else {
            this.#accountControl.classList.add("accounting-not-empty");
        }
        this.accountCode = entry.getAccountCode();
        this.accountText = entry.getAccountText();
        this.#accountText.innerText = this.accountText;
        this.#amountInput.value = entry.getAmount() === null? "": String(entry.getAmount());
        const maxAmount = this.#getMaxAmount();
        this.#amountInput.max = maxAmount === null? "": maxAmount;
        this.#amountInput.min = entry.getAmountMin() === null? "": String(entry.getAmountMin());
        this.#validate();
    }

    /**
     * Finds out the max amount.
     *
     * @return {Decimal|null} the max amount
     */
    #getMaxAmount() {
        if (this.originalEntryId === null) {
            return null;
        }
        return this.originalEntrySelector.getNetBalance(this.entry, this.form, this.originalEntryId);
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
}
