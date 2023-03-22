/* The Mia! Accounting Flask Project
 * account-selector.js: The JavaScript for the account selector
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

/**
 * The account selector.
 *
 */
class AccountSelector {

    /**
     * The line item editor
     * @type {JournalEntryLineItemEditor}
     */
    #lineItemEditor;

    /**
     * Either "debit" or "credit"
     * @type {string}
     */
    #debitCredit;

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
     * @param lineItemEditor {JournalEntryLineItemEditor} the line item editor
     * @param debitCredit {string} either "debit" or "credit"
     */
    constructor(lineItemEditor, debitCredit) {
        this.#lineItemEditor = lineItemEditor
        this.#debitCredit = debitCredit;
        const prefix = "accounting-account-selector-" + debitCredit;
        this.#query = document.getElementById(prefix + "-query");
        this.#queryNoResult = document.getElementById(prefix + "-option-no-result");
        this.#optionList = document.getElementById(prefix + "-option-list");
        // noinspection JSValidateTypes
        this.#options = Array.from(document.getElementsByClassName(prefix + "-option"));
        this.#more = document.getElementById(prefix + "-more");
        this.#clearButton = document.getElementById(prefix + "-btn-clear");
        this.#more.onclick = () => {
            this.#more.classList.add("d-none");
            this.#filterOptions();
        };
        this.#clearButton.onclick = () => this.#lineItemEditor.clearAccount();
        for (const option of this.#options) {
            option.onclick = () => this.#lineItemEditor.saveAccount(option.dataset.code, option.dataset.text, option.classList.contains("accounting-account-is-need-offset"));
        }
        this.#query.addEventListener("input", () => {
            this.#filterOptions();
        });
    }

    /**
     * Filters the options.
     *
     */
    #filterOptions() {
        const codesInUse = this.#getCodesUsedInForm();
        let shouldAnyShow = false;
        for (const option of this.#options) {
            const shouldShow = this.#shouldOptionShow(option, this.#more, codesInUse, this.#query);
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
    #getCodesUsedInForm() {
        const inUse = this.#lineItemEditor.form.getAccountCodesUsed(this.#debitCredit);
        if (this.#lineItemEditor.accountCode !== null) {
            inUse.push(this.#lineItemEditor.accountCode);
        }
        return inUse
    }

    /**
     * Returns whether an option should show.
     *
     * @param option {HTMLLIElement} the option
     * @param more {HTMLLIElement} the more element
     * @param inUse {string[]} the account codes that are used in the form
     * @param query {HTMLInputElement} the query element, if any
     * @return {boolean} true if the option should show, or false otherwise
     */
    #shouldOptionShow(option, more, inUse, query) {
        const isQueryMatched = () => {
            if (query.value === "") {
                return true;
            }
            const queryValues = JSON.parse(option.dataset.queryValues);
            for (const queryValue of queryValues) {
                if (queryValue.toLowerCase().includes(query.value.toLowerCase())) {
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
    onOpen() {
        this.#query.value = "";
        this.#more.classList.remove("d-none");
        this.#filterOptions();
        for (const option of this.#options) {
            if (option.dataset.code === this.#lineItemEditor.accountCode) {
                option.classList.add("active");
            } else {
                option.classList.remove("active");
            }
        }
        if (this.#lineItemEditor.accountCode === null) {
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
     * Returns the account selector instances.
     *
     * @param lineItemEditor {JournalEntryLineItemEditor} the line item editor
     * @return {{debit: AccountSelector, credit: AccountSelector}}
     */
    static getInstances(lineItemEditor) {
        const selectors = {}
        const modals = Array.from(document.getElementsByClassName("accounting-account-selector"));
        for (const modal of modals) {
            selectors[modal.dataset.debitCredit] = new AccountSelector(lineItemEditor, modal.dataset.debitCredit);
        }
        return selectors;
    }
}
