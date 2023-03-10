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
 * First written: 2023/2/28
 */
"use strict";

// Initializes the page JavaScript.
document.addEventListener("DOMContentLoaded", () => {
    AccountSelector.initialize();
});

/**
 * The account selector.
 *
 */
class AccountSelector {

    /**
     * The entry type
     * @type {string}
     */
    #entryType;

    /**
     * The prefix of the HTML ID and class
     * @type {string}
     */
    #prefix;

    /**
     * The button to clear the account
     * @type {HTMLButtonElement}
     */
    #clearButton

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
     * The options
     * @type {HTMLLIElement[]}
     */
    #options;

    /**
     * The more item to show all accounts
     * @type {HTMLLIElement}
     */
    #more;

    /**
     * Constructs an account selector.
     *
     * @param modal {HTMLDivElement} the account selector modal
     */
    constructor(modal) {
        this.#entryType = modal.dataset.entryType;
        this.#prefix = "accounting-account-selector-" + modal.dataset.entryType;
        this.#query = document.getElementById(this.#prefix + "-query");
        this.#queryNoResult = document.getElementById(this.#prefix + "-option-no-result");
        this.#optionList = document.getElementById(this.#prefix + "-option-list");
        // noinspection JSValidateTypes
        this.#options = Array.from(document.getElementsByClassName(this.#prefix + "-option"));
        this.#more = document.getElementById(this.#prefix + "-more");
        this.#clearButton = document.getElementById(this.#prefix + "-btn-clear");
        this.#more.onclick = () => {
            this.#more.classList.add("d-none");
            this.#filterAccountOptions();
        };
        this.#clearButton.onclick = () => {
            AccountSelector.#formAccountControl.classList.remove("accounting-not-empty");
            AccountSelector.#formAccount.innerText = "";
            AccountSelector.#formAccount.dataset.code = "";
            AccountSelector.#formAccount.dataset.text = "";
            validateJournalEntryAccount();
        };
        for (const option of this.#options) {
            option.onclick = () => {
                AccountSelector.#formAccountControl.classList.add("accounting-not-empty");
                AccountSelector.#formAccount.innerText = option.dataset.content;
                AccountSelector.#formAccount.dataset.code = option.dataset.code;
                AccountSelector.#formAccount.dataset.text = option.dataset.content;
                validateJournalEntryAccount();
            };
        }
        this.#query.addEventListener("input", () => {
            this.#filterAccountOptions();
        });
    }

    /**
     * Filters the account options.
     *
     */
    #filterAccountOptions() {
        const codesInUse = this.#getAccountCodeUsedInForm();
        let shouldAnyShow = false;
        for (const option of this.#options) {
            const shouldShow = this.#shouldAccountOptionShow(option, this.#more, codesInUse, this.#query);
            if (shouldShow) {
                option.classList.remove("d-none");
                shouldAnyShow = true;
            } else {
                option.classList.add("d-none");
            }
        }
        if (!shouldAnyShow && this.#more.classList.contains("d-none")) {
            this.#optionList.classList.add("d-none");
            this.#queryNoResult.classList.remove("d-none");
        } else {
            this.#optionList.classList.remove("d-none");
            this.#queryNoResult.classList.add("d-none");
        }
    }

    /**
     * Returns the account codes that are used in the form.
     *
     * @return {string[]} the account codes that are used in the form
     */
    #getAccountCodeUsedInForm() {
        const accountCodes = Array.from(document.getElementsByClassName("accounting-" + this.#prefix + "-account-code"));
        const inUse = [AccountSelector.#formAccount.dataset.code];
        for (const accountCode of accountCodes) {
            inUse.push(accountCode.value);
        }
        return inUse
    }

    /**
     * Returns whether an account option should show.
     *
     * @param option {HTMLLIElement} the account option
     * @param more {HTMLLIElement} the more account element
     * @param inUse {string[]} the account codes that are used in the form
     * @param query {HTMLInputElement} the query element, if any
     * @return {boolean} true if the account option should show, or false otherwise
     */
    #shouldAccountOptionShow(option, more, inUse, query) {
        const isQueryMatched = () => {
            if (query.value === "") {
                return true;
            }
            const queryValues = JSON.parse(option.dataset.queryValues);
            for (const queryValue of queryValues) {
                if (queryValue.includes(query.value)) {
                    return true;
                }
            }
            return false;
        };
        const isMoreMatched = () => {
            if (more.classList.contains("d-none")) {
                return true;
            }
            return option.classList.contains("accounting-account-in-use") || inUse.includes(option.dataset.code);
        };
        return isMoreMatched() && isQueryMatched();
    }

    /**
     * The callback when the account selector is shown.
     *
     */
    #onOpen() {
        this.#query.value = "";
        this.#more.classList.remove("d-none");
        this.#filterAccountOptions();
        for (const option of this.#options) {
            if (option.dataset.code === AccountSelector.#formAccount.dataset.code) {
                option.classList.add("active");
            } else {
                option.classList.remove("active");
            }
        }
        if (AccountSelector.#formAccount.dataset.code === "") {
            this.#clearButton.classList.add("btn-secondary");
            this.#clearButton.classList.remove("btn-danger");
            this.#clearButton.disabled = true;
        } else {
            this.#clearButton.classList.add("btn-danger");
            this.#clearButton.classList.remove("btn-secondary");
            this.#clearButton.disabled = false;
        }
    }

    /**
     * The account selectors.
     * @type {{debit: AccountSelector, credit: AccountSelector}}
     */
    static #selectors = {}

    /**
     * The journal entry form.
     * @type {HTMLFormElement}
     */
    static #entryForm;

    /**
     * The control of the account on the journal entry form
     * @type {HTMLDivElement}
     */
    static #formAccountControl;

    /**
     * The account on the journal entry form
     * @type {HTMLDivElement}
     */
    static #formAccount;

    /**
     * Initializes the account selectors.
     *
     */
    static initialize() {
        this.#entryForm = document.getElementById("accounting-entry-form");
        this.#formAccountControl = document.getElementById("accounting-entry-form-account-control");
        this.#formAccount = document.getElementById("accounting-entry-form-account");
        const modals = Array.from(document.getElementsByClassName("accounting-account-selector-modal"));
        for (const modal of modals) {
            const selector = new AccountSelector(modal);
            this.#selectors[selector.#entryType] = selector;
        }
        this.#initializeTransactionForm();
    }

    /**
     * Initializes the transaction form.
     *
     */
    static #initializeTransactionForm() {
        this.#formAccountControl.onclick = () => this.#selectors[this.#entryForm.dataset.entryType].#onOpen();
    }

    /**
     * Initializes the account selector for the journal entry form.
     *x
     */
    static initializeJournalEntryForm() {
        this.#formAccountControl.dataset.bsTarget = "#accounting-account-selector-" + this.#entryForm.dataset.entryType + "-modal";
    }
}
