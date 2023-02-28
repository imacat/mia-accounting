/* The Mia! Accounting Flask Project
 * transaction-transfer-form.js: The JavaScript for the transfer transaction form
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

// Initializes the page JavaScript.
document.addEventListener("DOMContentLoaded", function () {
    initializeCurrencyForms();
    initializeJournalEntries();
    initializeFormValidation();
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
 * Initializes the currency forms.
 *
 * @private
 */
function initializeCurrencyForms() {
    const form = document.getElementById("accounting-form");
    const btnNew = document.getElementById("accounting-btn-new-currency");
    const currencyList = document.getElementById("accounting-currency-list");
    const deleteButtons = Array.from(document.getElementsByClassName("accounting-btn-delete-currency"));
    const onReorder = function () {
        const currencies = Array.from(currencyList.children);
        for (let i = 0; i < currencies.length; i++) {
            const no = document.getElementById(currencies[i].dataset.prefix + "-no");
            no.value = String(i + 1);
        }
    };
    btnNew.onclick = function () {
        const currencies = Array.from(document.getElementsByClassName("accounting-currency"));
        let maxIndex = 0;
        for (const currency of currencies) {
            const index = parseInt(currency.dataset.index);
            if (maxIndex < index) {
                maxIndex = index;
            }
        }
        const newIndex = String(maxIndex + 1);
        const html = form.dataset.currencyTemplate
            .replaceAll("CURRENCY_INDEX", escapeHtml(newIndex));
        currencyList.insertAdjacentHTML("beforeend", html);
        const newEntryButtons = Array.from(document.getElementsByClassName("accounting-currency-" + newIndex + "-btn-new-entry"));
        const btnDelete = document.getElementById("accounting-btn-delete-currency-" + newIndex);
        newEntryButtons.forEach(initializeNewEntryButton);
        initializeBtnDeleteCurrency(btnDelete);
        resetDeleteCurrencyButtons();
        initializeDragAndDropReordering(currencyList, onReorder);
    };
    deleteButtons.forEach(initializeBtnDeleteCurrency);
    initializeDragAndDropReordering(currencyList, onReorder);
}

/**
 * Initializes the button to delete a currency.
 *
 * @param button {HTMLButtonElement} the button to delete a currency.
 * @private
 */
function initializeBtnDeleteCurrency(button) {
    const target = document.getElementById(button.dataset.target);
    button.onclick = function () {
        target.parentElement.removeChild(target);
        resetDeleteCurrencyButtons();
    };
}

/**
 * Resets the status of the delete currency buttons.
 *
 * @private
 */
function resetDeleteCurrencyButtons() {
    const buttons = Array.from(document.getElementsByClassName("accounting-btn-delete-currency"));
    if (buttons.length > 1) {
        for (const button of buttons) {
            button.classList.remove("d-none");
        }
    } else {
        buttons[0].classList.add("d-none");
    }
}

/**
 * Initializes the journal entry forms.
 *
 * @private
 */
function initializeJournalEntries() {
    const newButtons = Array.from(document.getElementsByClassName("accounting-btn-new-entry"));
    const entryLists = Array.from(document.getElementsByClassName("accounting-entry-list"));
    const entries = Array.from(document.getElementsByClassName("accounting-entry"))
    const deleteButtons = Array.from(document.getElementsByClassName("accounting-btn-delete-entry"));
    newButtons.forEach(initializeNewEntryButton);
    entryLists.forEach(initializeJournalEntryListReorder);
    entries.forEach(initializeJournalEntry);
    deleteButtons.forEach(initializeDeleteJournalEntryButton);
    initializeJournalEntryFormModal();
}

/**
 * Initializes the button to add a new journal entry.
 *
 * @param button {HTMLButtonElement} the button to add a new journal entry
 */
function initializeNewEntryButton(button) {
    const entryForm = document.getElementById("accounting-entry-form");
    const formAccountControl = document.getElementById("accounting-entry-form-account-control");
    const formAccount = document.getElementById("accounting-entry-form-account");
    const formAccountError = document.getElementById("accounting-entry-form-account-error")
    const formSummaryControl = document.getElementById("accounting-entry-form-summary-control");
    const formSummary = document.getElementById("accounting-entry-form-summary");
    const formSummaryError = document.getElementById("accounting-entry-form-summary-error");
    const formAmount = document.getElementById("accounting-entry-form-amount");
    const formAmountError = document.getElementById("accounting-entry-form-amount-error");
    button.onclick = function () {
        entryForm.dataset.currencyIndex = button.dataset.currencyIndex;
        entryForm.dataset.entryType = button.dataset.entryType;
        entryForm.dataset.entryIndex = button.dataset.entryIndex;
        formAccountControl.classList.remove("accounting-not-empty");
        formAccountControl.classList.remove("is-invalid");
        formAccountControl.dataset.bsTarget = button.dataset.accountModal;
        formAccount.innerText = "";
        formAccount.dataset.code = "";
        formAccount.dataset.text = "";
        formAccountError.innerText = "";
        formSummaryControl.dataset.bsTarget = "#accounting-summary-helper-" + button.dataset.entryType + "-modal";
        formSummaryControl.classList.remove("accounting-not-empty");
        formSummaryControl.classList.remove("is-invalid");
        formSummary.dataset.value = "";
        formSummary.innerText = ""
        formSummaryError.innerText = ""
        formAmount.value = "";
        formAmount.classList.remove("is-invalid");
        formAmountError.innerText = "";
        SummaryHelper.initializeNewJournalEntry(button.dataset.entryType);
    };
}

/**
 * Initializes the reordering of a journal entry list.
 *
 * @param entryList {HTMLUListElement} the journal entry list.
 */
function initializeJournalEntryListReorder(entryList) {
    initializeDragAndDropReordering(entryList, function () {
        const entries = Array.from(entryList.children);
        for (let i = 0; i < entries.length; i++) {
            const no = document.getElementById(entries[i].dataset.prefix + "-no");
            no.value = String(i + 1);
        }
    });
}

/**
 * Initializes the journal entry.
 *
 * @param entry {HTMLLIElement} the journal entry.
 */
function initializeJournalEntry(entry) {
    const entryForm = document.getElementById("accounting-entry-form");
    const accountCode = document.getElementById(entry.dataset.prefix + "-account-code");
    const summary = document.getElementById(entry.dataset.prefix + "-summary");
    const amount = document.getElementById(entry.dataset.prefix + "-amount");
    const control = document.getElementById(entry.dataset.prefix + "-control");
    const formAccountControl = document.getElementById("accounting-entry-form-account-control");
    const formAccount = document.getElementById("accounting-entry-form-account");
    const formSummaryControl = document.getElementById("accounting-entry-form-summary-control");
    const formSummary = document.getElementById("accounting-entry-form-summary");
    const formAmount = document.getElementById("accounting-entry-form-amount");
    control.onclick = function () {
        entryForm.dataset.currencyIndex = entry.dataset.currencyIndex;
        entryForm.dataset.entryType = entry.dataset.entryType;
        entryForm.dataset.entryIndex = entry.dataset.entryIndex;
        if (accountCode.value === "") {
            formAccountControl.classList.remove("accounting-not-empty");
        } else {
            formAccountControl.classList.add("accounting-not-empty");
        }
        formAccountControl.dataset.bsTarget = entry.dataset.accountModal;
        formAccount.innerText = accountCode.dataset.text;
        formAccount.dataset.code = accountCode.value;
        formAccount.dataset.text = accountCode.dataset.text;
        formSummaryControl.dataset.bsTarget = "#accounting-summary-helper-" + entry.dataset.entryType + "-modal";
        if (summary.value === "") {
            formSummaryControl.classList.remove("accounting-not-empty");
        } else {
            formSummaryControl.classList.add("accounting-not-empty");
        }
        formSummary.dataset.value = summary.value;
        formSummary.innerText = summary.value;
        formAmount.value = amount.value;
        validateJournalEntryForm();
    };
}

/**
 * Initializes the journal entry form modal.
 *
 * @private
 */
function initializeJournalEntryFormModal() {
    const entryForm = document.getElementById("accounting-entry-form");
    const formAmount = document.getElementById("accounting-entry-form-amount");
    const modal = document.getElementById("accounting-entry-form-modal");
    formAmount.onchange = validateJournalEntryAmount;
    entryForm.onsubmit = function () {
        if (validateJournalEntryForm()) {
            saveJournalEntryForm();
            bootstrap.Modal.getInstance(modal).hide();
        }
        return false;
    }
}

/**
 * Validates the journal entry form modal.
 *
 * @return {boolean} true if the form is valid, or false otherwise.
 * @private
 */
function validateJournalEntryForm() {
    let isValid = true;
    isValid = validateJournalEntryAccount() && isValid;
    isValid = validateJournalEntrySummary() && isValid;
    isValid = validateJournalEntryAmount() && isValid
    return isValid;
}

/**
 * Validates the account in the journal entry form modal.
 *
 * @return {boolean} true if valid, or false otherwise
 */
function validateJournalEntryAccount() {
    const field = document.getElementById("accounting-entry-form-account");
    const error = document.getElementById("accounting-entry-form-account-error");
    const control = document.getElementById("accounting-entry-form-account-control");
    if (field.dataset.code === "") {
        control.classList.add("is-invalid");
        error.innerText = A_("Please select the account.");
        return false;
    }
    control.classList.remove("is-invalid");
    error.innerText = "";
    return true;
}

/**
 * Validates the summary in the journal entry form modal.
 *
 * @return {boolean} true if valid, or false otherwise
 * @private
 */
function validateJournalEntrySummary() {
    const control = document.getElementById("accounting-entry-form-summary-control");
    const error = document.getElementById("accounting-entry-form-summary-error");
    control.classList.remove("is-invalid");
    error.innerText = "";
    return true;
}

/**
 * Validates the amount in the journal entry form modal.
 *
 * @return {boolean} true if valid, or false otherwise
 * @private
 */
function validateJournalEntryAmount() {
    const field = document.getElementById("accounting-entry-form-amount");
    const error = document.getElementById("accounting-entry-form-amount-error");
    field.value = field.value.trim();
    field.classList.remove("is-invalid");
    if (field.value === "") {
        field.classList.add("is-invalid");
        error.innerText = A_("Please fill in the amount.");
        return false;
    }
    error.innerText = "";
    return true;
}

/**
 * Saves the journal entry form modal to the form.
 *
 * @private
 */
function saveJournalEntryForm() {
    const form = document.getElementById("accounting-form");
    const entryForm = document.getElementById("accounting-entry-form");
    const formAccount = document.getElementById("accounting-entry-form-account");
    const formSummary = document.getElementById("accounting-entry-form-summary");
    const formAmount = document.getElementById("accounting-entry-form-amount");
    const currencyIndex = entryForm.dataset.currencyIndex;
    const entryType = entryForm.dataset.entryType;
    let entryIndex;
    if (entryForm.dataset.entryIndex === "new") {
        const entries = Array.from(document.getElementsByClassName("accounting-currency-" + currencyIndex + "-" + entryType));
        const entryList = document.getElementById("accounting-currency-" + currencyIndex + "-" + entryType + "-list")
        let maxIndex = 0;
        for (const entry of entries) {
            const index = parseInt(entry.dataset.entryIndex);
            if (maxIndex < index) {
                maxIndex = index;
            }
        }
        entryIndex = String(maxIndex + 1);
        const html = form.dataset.entryTemplate
            .replaceAll("CURRENCY_INDEX", escapeHtml(currencyIndex))
            .replaceAll("ENTRY_TYPE", escapeHtml(entryType))
            .replaceAll("ENTRY_INDEX", escapeHtml(entryIndex));
        entryList.insertAdjacentHTML("beforeend", html);
        initializeJournalEntryListReorder(entryList);
    } else {
        entryIndex = entryForm.dataset.entryIndex;
    }
    const currency = document.getElementById("accounting-currency-" + currencyIndex);
    const entry = document.getElementById("accounting-currency-" + currencyIndex + "-" + entryType + "-" + entryIndex);
    const accountCode = document.getElementById(entry.dataset.prefix + "-account-code");
    const accountText = document.getElementById(entry.dataset.prefix + "-account-text");
    const summary = document.getElementById(entry.dataset.prefix + "-summary");
    const summaryText = document.getElementById(entry.dataset.prefix + "-summary-text");
    const amount = document.getElementById(entry.dataset.prefix + "-amount");
    const amountText = document.getElementById(entry.dataset.prefix + "-amount-text");
    accountCode.value = formAccount.dataset.code;
    accountCode.dataset.text = formAccount.dataset.text;
    accountText.innerText = formAccount.dataset.text;
    summary.value = formSummary.dataset.value;
    summaryText.innerText = formSummary.dataset.value;
    amount.value = formAmount.value;
    amountText.innerText = formatDecimal(new Decimal(formAmount.value));
    if (entryForm.dataset.entryIndex === "new") {
        const btnDelete = document.getElementById(entry.dataset.prefix + "-btn-delete");
        initializeJournalEntry(entry);
        initializeDeleteJournalEntryButton(btnDelete);
        resetDeleteJournalEntryButtons(btnDelete.dataset.sameClass);
    }
    updateBalance(currencyIndex, entryType);
    validateJournalEntriesReal(currencyIndex, entryType);
    validateBalance(currency);
}

/**
 * Initializes the button to delete a journal entry.
 *
 * @param button {HTMLButtonElement} the button to delete a journal entry
 */
function initializeDeleteJournalEntryButton(button) {
    const target = document.getElementById(button.dataset.target);
    const currencyIndex = target.dataset.currencyIndex;
    const entryType = target.dataset.entryType;
    const currency = document.getElementById("accounting-currency-" + currencyIndex);
    button.onclick = function () {
        target.parentElement.removeChild(target);
        resetDeleteJournalEntryButtons(button.dataset.sameClass);
        updateBalance(currencyIndex, entryType);
        validateJournalEntriesReal(currencyIndex, entryType);
        validateBalance(currency);
    };
}

/**
 * Resets the status of the delete journal entry buttons.
 *
 * @param sameClass {string} the class of the buttons
 * @private
 */
function resetDeleteJournalEntryButtons(sameClass) {
    const buttons = Array.from(document.getElementsByClassName(sameClass));
    if (buttons.length > 1) {
        for (const button of buttons) {
            button.classList.remove("d-none");
        }
    } else {
        buttons[0].classList.add("d-none");
    }
}

/**
 * Updates the balance.
 *
 * @param currencyIndex {string} the currency index.
 * @param entryType {string} the journal entry type, either "debit" or "credit"
 * @private
 */
function updateBalance(currencyIndex, entryType) {
    const prefix = "accounting-currency-" + currencyIndex + "-" + entryType;
    const amounts = Array.from(document.getElementsByClassName(prefix + "-amount"));
    const totalText = document.getElementById(prefix + "-total");
    let total = new Decimal("0");
    for (const amount of amounts) {
        if (amount.value !== "") {
            total = total.plus(new Decimal(amount.value));
        }
    }
    totalText.innerText = formatDecimal(total);
}

/**
 * Initializes the form validation.
 *
 * @private
 */
function initializeFormValidation() {
    const date = document.getElementById("accounting-date");
    const note = document.getElementById("accounting-note");
    const form = document.getElementById("accounting-form");
    date.onchange = validateDate;
    note.onchange = validateNote;
    form.onsubmit = validateForm;
}

/**
 * Validates the form.
 *
 * @return {boolean} true if valid, or false otherwise
 * @private
 */
function validateForm() {
    let isValid = true;
    isValid = validateDate() && isValid;
    isValid = validateCurrencies() && isValid;
    isValid = validateNote() && isValid;
    return isValid;
}

/**
 * Validates the date.
 *
 * @return {boolean} true if valid, or false otherwise
 * @private
 */
function validateDate() {
    const field = document.getElementById("accounting-date");
    const error = document.getElementById("accounting-date-error");
    field.value = field.value.trim();
    field.classList.remove("is-invalid");
    if (field.value === "") {
        field.classList.add("is-invalid");
        error.innerText = A_("Please fill in the date.");
        return false;
    }
    error.innerText = "";
    return true;
}

/**
 * Validates the currency sub-forms.
 *
 * @return {boolean} true if valid, or false otherwise
 * @private
 */
function validateCurrencies() {
    const currencies = Array.from(document.getElementsByClassName("accounting-currency"));
    let isValid = true;
    isValid = validateCurrenciesReal() && isValid;
    for (const currency of currencies) {
        isValid = validateCurrency(currency) && isValid;
    }
    return isValid;
}

/**
 * Validates the currency sub-forms, the validator itself.
 *
 * @return {boolean} true if valid, or false otherwise
 * @private
 */
function validateCurrenciesReal() {
    const field = document.getElementById("accounting-currencies");
    const error = document.getElementById("accounting-currencies-error");
    const currencies = Array.from(document.getElementsByClassName("accounting-currency"));
    if (currencies.length === 0) {
        field.classList.add("is-invalid");
        error.innerText = A_("Please add some currencies.");
        return false;
    }
    field.classList.remove("is-invalid");
    error.innerText = "";
    return true;
}

/**
 * Validates a currency sub-form.
 *
 * @param currency {HTMLDivElement} the currency sub-form
 * @return {boolean} true if valid, or false otherwise
 * @private
 */
function validateCurrency(currency) {
    const prefix = "accounting-currency-" + currency.dataset.index;
    const debit = document.getElementById(prefix + "-debit");
    const credit = document.getElementById(prefix + "-credit");
    let isValid = true;
    if (debit !== null) {
        isValid = validateJournalEntries(currency, "debit") && isValid;
    }
    if (credit !== null) {
        isValid = validateJournalEntries(currency, "credit") && isValid;
    }
    if (debit !== null && credit !== null) {
        isValid = validateBalance(currency) && isValid;
    }
    return isValid;
}

/**
 * Validates the journal entries in a currency sub-form.
 *
 * @param currency {HTMLDivElement} the currency
 * @param entryType {string} the journal entry type, either "debit" or "credit"
 * @return {boolean} true if valid, or false otherwise
 * @private
 */
function validateJournalEntries(currency, entryType) {
    const currencyIndex = currency.dataset.index;
    const entries = Array.from(document.getElementsByClassName("accounting-currency-" + currencyIndex + "-" + entryType));
    let isValid = true;
    isValid = validateJournalEntriesReal(currencyIndex, entryType) && isValid;
    for (const entry of entries) {
        isValid = validateJournalEntry(entry) && isValid;
    }
    return isValid;
}

/**
 * Validates the journal entries, the validator itself.
 *
 * @param currencyIndex {string} the currency index
 * @param entryType {string} the journal entry type, either "debit" or "credit"
 * @return {boolean} true if valid, or false otherwise
 * @private
 */
function validateJournalEntriesReal(currencyIndex, entryType) {
    const prefix = "accounting-currency-" + currencyIndex + "-" + entryType;
    const field = document.getElementById(prefix);
    const error = document.getElementById(prefix + "-error");
    const entries = Array.from(document.getElementsByClassName(prefix));
    if (entries.length === 0) {
        field.classList.add("is-invalid");
        error.innerText = A_("Please add some journal entries.");
        return false;
    }
    field.classList.remove("is-invalid");
    error.innerText = "";
    return true;
}

/**
 * Validates a journal entry sub-form in a currency sub-form.
 *
 * @param entry {HTMLLIElement} the journal entry
 * @return {boolean} true if valid, or false otherwise
 * @private
 */
function validateJournalEntry(entry) {
    const control = document.getElementById(entry.dataset.prefix + "-control");
    const error = document.getElementById(entry.dataset.prefix + "-error");
    const accountCode = document.getElementById(entry.dataset.prefix + "-account-code");
    const amount = document.getElementById(entry.dataset.prefix + "-amount");
    if (accountCode.value === "") {
        control.classList.add("is-invalid");
        error.innerText = A_("Please select the account.");
        return false;
    }
    if (amount.value === "") {
        control.classList.add("is-invalid");
        error.innerText = A_("Please fill in the amount.");
        return false;
    }
    control.classList.remove("is-invalid");
    error.innerText = "";
    return true;
}

/**
 * Validates the balance of a currency sub-form.
 *
 * @param currency {HTMLDivElement} the currency sub-form
 * @return {boolean} true if valid, or false otherwise
 * @private
 */
function validateBalance(currency) {
    const prefix = "accounting-currency-" + currency.dataset.index;
    const control = document.getElementById(prefix + "-control");
    const error = document.getElementById(prefix + "-error");
    const debit = document.getElementById(prefix + "-debit");
    const debitAmounts = Array.from(document.getElementsByClassName(prefix + "-debit-amount"));
    const credit = document.getElementById(prefix + "-credit");
    const creditAmounts = Array.from(document.getElementsByClassName(prefix + "-credit-amount"));
    if (debit !== null && credit !== null) {
        let debitTotal = new Decimal("0");
        for (const amount of debitAmounts) {
            if (amount.value !== "") {
                debitTotal = debitTotal.plus(new Decimal(amount.value));
            }
        }
        let creditTotal = new Decimal("0");
        for (const amount of creditAmounts) {
            if (amount.value !== "") {
                creditTotal = creditTotal.plus(new Decimal(amount.value));
            }
        }
        if (!debitTotal.equals(creditTotal)) {
            control.classList.add("is-invalid");
            error.innerText = A_("The totals of the debit and credit amounts do not match.");
            return false;
        }
    }
    control.classList.remove("is-invalid");
    error.innerText = "";
    return true;
}


/**
 * Validates the note.
 *
 * @return {boolean} true if valid, or false otherwise
 * @private
 */
function validateNote() {
    const field = document.getElementById("accounting-note");
    const error = document.getElementById("accounting-note-error");
    field.value = field.value
         .replace(/^\s*\n/, "")
         .trimEnd();
    field.classList.remove("is-invalid");
    error.innerText = "";
    return true;
}
