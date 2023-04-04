/* The Mia! Accounting Project
 * journal-entry-account-selector.js: The JavaScript for the account selector of the journal entry form
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
class JournalEntryAccountSelector {

    /**
     * The line item editor
     * @type {JournalEntryLineItemEditor}
     */
    lineItemEditor;

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
     * @type {JournalEntryAccountOption[]}
     */
    #options;

    /**
     * The more item to show all accounts
     * @type {HTMLLIElement}
     */
    #more;

    /**
     * Whether to show all accounts
     * @type {boolean}
     */
    #isShowMore = false;

    /**
     * Constructs an account selector.
     *
     * @param lineItemEditor {JournalEntryLineItemEditor} the line item editor
     * @param debitCredit {string} either "debit" or "credit"
     */
    constructor(lineItemEditor, debitCredit) {
        this.lineItemEditor = lineItemEditor
        this.#debitCredit = debitCredit;
        const prefix = `accounting-account-selector-${debitCredit}`;
        this.#query = document.getElementById(`${prefix}-query`);
        this.#queryNoResult = document.getElementById(`${prefix}-option-no-result`);
        this.#optionList = document.getElementById(`${prefix}-option-list`);
        this.#options = Array.from(document.getElementsByClassName(`${prefix}-option`)).map((element) => new JournalEntryAccountOption(this, element));
        this.#more = document.getElementById(`${prefix}-more`);
        this.#clearButton = document.getElementById(`${prefix}-btn-clear`);

        this.#more.onclick = () => {
            this.#isShowMore = true;
            this.#more.classList.add("d-none");
            this.#filterOptions();
        };
        this.#query.oninput = () => this.#filterOptions();
        this.#clearButton.onclick = () => this.lineItemEditor.clearAccount();
    }

    /**
     * Filters the options.
     *
     */
    #filterOptions() {
        const codesInUse = this.#getCodesUsedInForm();
        let isAnyMatched = false;
        for (const option of this.#options) {
            if (option.isMatched(this.#isShowMore, codesInUse, this.#query.value)) {
                option.setShown(true);
                isAnyMatched = true;
            } else {
                option.setShown(false);
            }
        }
        if (!isAnyMatched) {
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
        const inUse = this.lineItemEditor.form.getAccountCodesUsed(this.#debitCredit);
        if (this.lineItemEditor.account !== null) {
            inUse.push(this.lineItemEditor.account.code);
        }
        return inUse
    }

    /**
     * The callback when the account selector is shown.
     *
     */
    onOpen() {
        this.#query.value = "";
        this.#isShowMore = false;
        this.#more.classList.remove("d-none");
        this.#filterOptions();
        for (const option of this.#options) {
            option.setActive(this.lineItemEditor.account !== null && option.code === this.lineItemEditor.account.code);
        }
        if (this.lineItemEditor.account === null) {
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
     * @return {{debit: JournalEntryAccountSelector, credit: JournalEntryAccountSelector}}
     */
    static getInstances(lineItemEditor) {
        const selectors = {}
        const modals = Array.from(document.getElementsByClassName("accounting-account-selector"));
        for (const modal of modals) {
            selectors[modal.dataset.debitCredit] = new JournalEntryAccountSelector(lineItemEditor, modal.dataset.debitCredit);
        }
        return selectors;
    }
}

/**
 * An account option
 *
 */
class JournalEntryAccountOption {

    /**
     * The element
     * @type {HTMLLIElement}
     */
    #element;

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
     * Whether the account is in use
     * @type {boolean}
     */
    #isInUse;

    /**
     * Whether line items in the account need offset
     * @type {boolean}
     */
    isNeedOffset;

    /**
     * The values to query against
     * @type {string[]}
     */
    #queryValues;

    /**
     * Constructs the account in the account selector.
     *
     * @param selector {JournalEntryAccountSelector} the account selector
     * @param element {HTMLLIElement} the element
     */
    constructor(selector, element) {
        this.#element = element;
        this.code = element.dataset.code;
        this.text = element.dataset.text;
        this.#isInUse = element.classList.contains("accounting-account-is-in-use");
        this.isNeedOffset = element.classList.contains("accounting-account-is-need-offset");
        this.#queryValues = JSON.parse(element.dataset.queryValues);

        this.#element.onclick = () => selector.lineItemEditor.saveAccount(this);
    }

    /**
     * Returns whether the account matches the query.
     *
     * @param isShowMore {boolean} true to show all accounts, or false to show only those in use
     * @param codesInUse {string[]} the account codes that are used in the form
     * @param query {string} the query term
     * @return {boolean} true if the option matches, or false otherwise
     */
    isMatched(isShowMore, codesInUse, query) {
        return this.#isInUseMatched(isShowMore, codesInUse) && this.#isQueryMatched(query);
    }

    /**
     * Returns whether the account matches the "in-use" condition.
     *
     * @param isShowMore {boolean} true to show all accounts, or false to show only those in use
     * @param codesInUse {string[]} the account codes that are used in the form
     * @return {boolean} true if the option matches, or false otherwise
     */
    #isInUseMatched(isShowMore, codesInUse) {
        return isShowMore || this.#isInUse || codesInUse.includes(this.code);
    }

    /**
     * Returns whether the account matches the query term.
     *
     * @param query {string} the query term
     * @return {boolean} true if the option matches, or false otherwise
     */
    #isQueryMatched(query) {
        if (query === "") {
            return true;
        }
        for (const queryValue of this.#queryValues) {
            if (queryValue.toLowerCase().includes(query.toLowerCase())) {
                return true;
            }
        }
        return false;
    }

    /**
     * Sets whether the option is shown.
     *
     * @param isShown {boolean} true to show, or false otherwise
     */
    setShown(isShown) {
        if (isShown) {
            this.#element.classList.remove("d-none");
        } else {
            this.#element.classList.add("d-none");
        }
    }

    /**
     * Sets whether the option is active.
     *
     * @param isActive {boolean} true if active, or false otherwise
     */
    setActive(isActive) {
        if (isActive) {
            this.#element.classList.add("active");
        } else {
            this.#element.classList.remove("active");
        }
    }
}
