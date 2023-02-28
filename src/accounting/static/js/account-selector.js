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

// Initializes the page JavaScript.
document.addEventListener("DOMContentLoaded", function () {
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
     * Constructs an account selector.
     *
     * @param modal {HTMLFormElement} the account selector modal
     */
    constructor(modal) {
        this.#entryType = modal.dataset.entryType;
        this.#prefix = "accounting-account-selector-" + modal.dataset.entryType;
        this.#init();
    }

    /**
     * Initializes the account selector.
     *
     */
    #init() {
        const formAccountControl = document.getElementById("accounting-entry-form-account-control");
        const formAccount = document.getElementById("accounting-entry-form-account");
        const more = document.getElementById(this.#prefix + "-more");
        const btnClear = document.getElementById(this.#prefix + "-btn-clear");
        const options = Array.from(document.getElementsByClassName(this.#prefix + "-option"));
        const selector1 = this
        more.onclick = function () {
            more.classList.add("d-none");
            selector1.#filterAccountOptions();
        };
        this.#initializeAccountQuery();
        btnClear.onclick = function () {
            formAccountControl.classList.remove("accounting-not-empty");
            formAccount.innerText = "";
            formAccount.dataset.code = "";
            formAccount.dataset.text = "";
            validateJournalEntryAccount();
        };
        for (const option of options) {
            option.onclick = function () {
                formAccountControl.classList.add("accounting-not-empty");
                formAccount.innerText = option.dataset.content;
                formAccount.dataset.code = option.dataset.code;
                formAccount.dataset.text = option.dataset.content;
                validateJournalEntryAccount();
            };
        }
    }

    /**
     * Initializes the query on the account options.
     *
     */
    #initializeAccountQuery() {
        const query = document.getElementById(this.#prefix + "-query");
        const helper = this;
        query.addEventListener("input", function () {
            helper.#filterAccountOptions();
        });
    }

    /**
     * Filters the account options.
     *
     */
    #filterAccountOptions() {
        const query = document.getElementById(this.#prefix + "-query");
        const optionList = document.getElementById(this.#prefix + "-option-list");
        if (optionList === null) {
            console.log(this.#prefix + "-option-list");
        }
        const options = Array.from(document.getElementsByClassName(this.#prefix + "-option"));
        const more = document.getElementById(this.#prefix + "-more");
        const queryNoResult = document.getElementById(this.#prefix + "-option-no-result");
        const codesInUse = this.#getAccountCodeUsedInForm();
        let shouldAnyShow = false;
        for (const option of options) {
            const shouldShow = this.#shouldAccountOptionShow(option, more, codesInUse, query);
            if (shouldShow) {
                option.classList.remove("d-none");
                shouldAnyShow = true;
            } else {
                option.classList.add("d-none");
            }
        }
        if (!shouldAnyShow && more.classList.contains("d-none")) {
            optionList.classList.add("d-none");
            queryNoResult.classList.remove("d-none");
        } else {
            optionList.classList.remove("d-none");
            queryNoResult.classList.add("d-none");
        }
    }

    /**
     * Returns the account codes that are used in the form.
     *
     * @return {string[]} the account codes that are used in the form
     */
    #getAccountCodeUsedInForm() {
        const accountCodes = Array.from(document.getElementsByClassName("accounting-" + this.#prefix + "-account-code"));
        const formAccount = document.getElementById("accounting-entry-form-account");
        const inUse = [formAccount.dataset.code];
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
        const isQueryMatched = function () {
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
        const isMoreMatched = function () {
            if (more.classList.contains("d-none")) {
                return true;
            }
            return option.classList.contains("accounting-account-in-use") || inUse.includes(option.dataset.code);
        };
        return isMoreMatched() && isQueryMatched();
    }

    /**
     * Initializes the account selector when it is shown.
     *
     */
    initShow() {
        const formAccount = document.getElementById("accounting-entry-form-account");
        const query = document.getElementById(this.#prefix + "-query")
        const more = document.getElementById(this.#prefix + "-more");
        const options = Array.from(document.getElementsByClassName(this.#prefix + "-option"));
        const btnClear = document.getElementById(this.#prefix + "-btn-clear");
        query.value = "";
        more.classList.remove("d-none");
        this.#filterAccountOptions();
        for (const option of options) {
            if (option.dataset.code === formAccount.dataset.code) {
                option.classList.add("active");
            } else {
                option.classList.remove("active");
            }
        }
        if (formAccount.dataset.code === "") {
            btnClear.classList.add("btn-secondary");
            btnClear.classList.remove("btn-danger");
            btnClear.disabled = true;
        } else {
            btnClear.classList.add("btn-danger");
            btnClear.classList.remove("btn-secondary");
            btnClear.disabled = false;
        }
    }

    /**
     * The account selectors.
     * @type {{debit: AccountSelector, credit: AccountSelector}}
     */
    static #selectors = {}

    /**
     * Initializes the account selectors.
     *
     */
    static initialize() {
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
        const entryForm = document.getElementById("accounting-entry-form");
        const formAccountControl = document.getElementById("accounting-entry-form-account-control");
        const selectors = this.#selectors;
        formAccountControl.onclick = function () {
            selectors[entryForm.dataset.entryType].initShow();
        };
    }
    /**
     * Initializes the account selector for the journal entry form.
     *x
     */
    static initializeJournalEntryForm() {
        const entryForm = document.getElementById("accounting-entry-form");
        const formAccountControl = document.getElementById("accounting-entry-form-account-control");
        formAccountControl.dataset.bsTarget = "#accounting-account-selector-" + entryForm.dataset.entryType + "-modal";
    }
}
