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
 * @extends {BaseCombobox<BaseJournalEntryAccountOption>}
 * @private
 */
class JournalEntryAccountSelector extends BaseCombobox {

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
     * The more item to show all accounts
     * @type {MoreItems}
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
        const prefix = `accounting-account-selector-${debitCredit}`;
        const query = document.getElementById(`${prefix}-query`);
        const options = Array.from(document.getElementsByClassName(`${prefix}-option`)).map((element) => new JournalEntryAccountOption(element, lineItemEditor.saveAccount.bind(lineItemEditor)));
        super(query, options);
        this.#lineItemEditor = lineItemEditor;
        this.#debitCredit = debitCredit;
        this.#queryNoResult = document.getElementById(`${prefix}-option-no-result`);
        this.#optionList = document.getElementById(`${prefix}-option-list`);
        const moreElement = document.getElementById(`${prefix}-more`);
        this.#more = new MoreItems(moreElement);
        moreElement.onclick = () => {
            this.#isShowMore = true;
            this.#more.setShown(false);
            this.filterOptions();
        };

        this.#clearButton = document.getElementById(`${prefix}-btn-clear`);
        this.#clearButton.onclick = () => this.#lineItemEditor.clearAccount();
    }

    /**
     * Filters the options.
     *
     * @override
     */
    filterOptions() {
        this.shownOptions = [];
        const codesInUse = this.#getCodesUsedInForm();
        let isAnyMatched = false;
        for (const option of this.options) {
            if (option.isMatched(this.#isShowMore, codesInUse, this.query.value)) {
                option.setShown(true);
                this.shownOptions.push(option);
                isAnyMatched = true;
            } else {
                option.setShown(false);
            }
        }
        if (!this.#isShowMore) {
            this.shownOptions.push(this.#more);
        }
        if (!isAnyMatched && this.#isShowMore) {
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
        if (this.#lineItemEditor.account !== null) {
            inUse.push(this.#lineItemEditor.account.code);
        }
        return inUse
    }

    /**
     * The callback when the account selector is shown.
     *
     */
    onOpen() {
        this.query.value = "";
        this.#isShowMore = false;
        this.#more.setShown(true);
        this.filterOptions();
        this.query.removeAttribute("aria-activedescendant");
        this.selectOption(this.shownOptions.find((option) => this.#lineItemEditor.account !== null && option.code === this.#lineItemEditor.account.code));
        if (this.#lineItemEditor.account === null) {
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
     * Selects an option.
     *
     * @param option {BaseJournalEntryAccountOption|undefined} the option.
     * @override
     */
    selectOption(option) {
        this.#more.setActive(false);
        super.selectOption(option);
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
 * The base abstract account option
 *
 * @private
 */
class BaseJournalEntryAccountOption extends BaseOption {

    /**
     * The account code
     * @type {string}
     */
    code = "";

    /**
     * Returns whether the account matches the query.
     *
     * @param isShowMore {boolean} true to show all accounts, or false to show only those in use
     * @param codesInUse {string[]} the account codes that are used in the form
     * @param query {string} the query term
     * @return {boolean} true if the option matches, or false otherwise
     */
    isMatched(isShowMore, codesInUse, query) {
        return false;
    }
}

/**
 * An account option
 *
 * @private
 */
class JournalEntryAccountOption extends BaseJournalEntryAccountOption {

    /**
     * The account title
     * @type {string}
     */
    title;

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
     * @param element {HTMLLIElement} the element
     * @param save {function(JournalEntryAccountOption): void} the callback to save the option
     */
    constructor(element, save) {
        super(element);
        this.code = element.dataset.code;
        this.title = element.dataset.title;
        this.text = element.dataset.text;
        this.#isInUse = element.classList.contains("accounting-account-is-in-use");
        this.isNeedOffset = element.classList.contains("accounting-account-is-need-offset");
        this.#queryValues = JSON.parse(element.dataset.queryValues);

        element.onclick = () => save(this);
    }

    /**
     * Returns whether the account matches the query.
     *
     * @param isShowMore {boolean} true to show all accounts, or false to show only those in use
     * @param codesInUse {string[]} the account codes that are used in the form
     * @param query {string} the query term
     * @return {boolean} true if the option matches, or false otherwise
     * @override
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
}

/**
 * The more item to show all accounts.
 *
 * @private
 */
class MoreItems extends BaseJournalEntryAccountOption {
}
