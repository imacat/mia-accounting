/* The Mia! Accounting Flask Project
 * original-entry-selector.js: The JavaScript for the original entry selector
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
 * First written: 2023/3/10
 */
"use strict";

/**
 * The original entry selector.
 *
 */
class OriginalEntrySelector {

    /**
     * The journal entry editor
     * @type {JournalEntryEditor}
     */
    entryEditor;

    /**
     * The prefix of the HTML ID and class
     * @type {string}
     */
    #prefix = "accounting-original-entry-selector";

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
     * @type {OriginalEntry[]}
     */
    #options;

    /**
     * The options by their ID
     * @type {Object.<string, OriginalEntry>}
     */
    #optionById;

    /**
     * The currency code
     * @type {string}
     */
    #currencyCode;

    /**
     * The entry
     */
    #entryType;

    /**
     * Constructs an original entry selector.
     *
     * @param entryEditor {JournalEntryEditor} the journal entry editor
     */
    constructor(entryEditor) {
        this.entryEditor = entryEditor;
        this.#query = document.getElementById(this.#prefix + "-query");
        this.#queryNoResult = document.getElementById(this.#prefix + "-option-no-result");
        this.#optionList = document.getElementById(this.#prefix + "-option-list");
        this.#options = Array.from(document.getElementsByClassName(this.#prefix + "-option")).map((element) => new OriginalEntry(this, element));
        this.#optionById = {};
        for (const option of this.#options) {
            this.#optionById[option.id] = option;
        }
        this.#query.addEventListener("input", () => {
            this.#filterOptions();
        });
    }

    /**
     * Returns the net balance for an original entry.
     *
     * @param currentEntry {JournalEntrySubForm} the journal entry sub-form that is currently editing
     * @param form {VoucherForm} the voucher form
     * @param originalEntryId {string} the ID of the original entry
     * @return {Decimal} the net balance of the original entry
     */
    getNetBalance(currentEntry, form, originalEntryId) {
        const otherEntries = form.getEntries().filter((entry) => entry !== currentEntry);
        let otherOffset = new Decimal(0);
        for (const otherEntry of otherEntries) {
            if (otherEntry.getOriginalEntryId() === originalEntryId) {
                const amount = otherEntry.getAmount();
                if (amount !== null) {
                    otherOffset = otherOffset.plus(amount);
                }
            }
        }
        return this.#optionById[originalEntryId].bareNetBalance.minus(otherOffset);
    }

    /**
     * Updates the net balances, subtracting the offset amounts on the form but the currently editing journal entry
     *
     */
    #updateNetBalances() {
        const otherEntries = this.entryEditor.form.getEntries().filter((entry) => entry !== this.entryEditor.entry);
        const otherOffsets = {}
        for (const otherEntry of otherEntries) {
            const otherOriginalEntryId = otherEntry.getOriginalEntryId();
            const amount = otherEntry.getAmount();
            if (otherOriginalEntryId === null || amount === null) {
                continue;
            }
            if (!(otherOriginalEntryId in otherOffsets)) {
                otherOffsets[otherOriginalEntryId] = new Decimal("0");
            }
            otherOffsets[otherOriginalEntryId] = otherOffsets[otherOriginalEntryId].plus(amount);
        }
        for (const option of this.#options) {
            if (option.id in otherOffsets) {
                option.updateNetBalance(otherOffsets[option.id]);
            } else {
                option.resetNetBalance();
            }
        }
    }

    /**
     * Filters the options.
     *
     */
    #filterOptions() {
        let hasAnyMatched = false;
        for (const option of this.#options) {
            if (option.isMatched(this.#entryType, this.#currencyCode, this.#query.value)) {
                option.setShown(true);
                hasAnyMatched = true;
            } else {
                option.setShown(false);
            }
        }
        if (!hasAnyMatched) {
            this.#optionList.classList.add("d-none");
            this.#queryNoResult.classList.remove("d-none");
        } else {
            this.#optionList.classList.remove("d-none");
            this.#queryNoResult.classList.add("d-none");
        }
    }

    /**
     * The callback when the original entry selector is shown.
     *
     */
    onOpen() {
        this.#currencyCode = this.entryEditor.getCurrencyCode();
        this.#entryType = this.entryEditor.entryType;
        for (const option of this.#options) {
            option.setActive(option.id === this.entryEditor.originalEntryId);
        }
        this.#query.value = "";
        this.#updateNetBalances();
        this.#filterOptions();
    }
}

/**
 * An original entry.
 *
 */
class OriginalEntry {

    /**
     * The original entry selector
     * @type {OriginalEntrySelector}
     */
    #selector;

    /**
     * The element
     * @type {HTMLLIElement}
     */
    #element;

    /**
     * The ID
     * @type {string}
     */
    id;

    /**
     * The date
     * @type {string}
     */
    date;

    /**
     * The entry type, either "debit" or "credit"
     * @type {string}
     */
    #entryType;

    /**
     * The currency code
     * @type {string}
     */
    #currencyCode;

    /**
     * The account code
     * @type {string}
     */
    accountCode;

    /**
     * The account text
     * @type {string}
     */
    accountText;

    /**
     * The summary
     * @type {string}
     */
    summary;

    /**
     * The net balance, without the offset amounts on the form
     * @type {Decimal}
     */
    bareNetBalance;

    /**
     * The net balance
     * @type {Decimal}
     */
    netBalance;

    /**
     * The text of the net balance
     * @type {HTMLSpanElement}
     */
    netBalanceText;

    /**
     * The text representation of the original entry
     * @type {string}
     */
    text;

    /**
     * The values to query against
     * @type {string[][]}
     */
    #queryValues;

    /**
     * Constructs an original entry.
     *
     * @param selector {OriginalEntrySelector} the original entry selector
     * @param element {HTMLLIElement} the element
     */
    constructor(selector, element) {
        this.#selector = selector;
        this.#element = element;
        this.id = element.dataset.id;
        this.date = element.dataset.date;
        this.#entryType = element.dataset.entryType;
        this.#currencyCode = element.dataset.currencyCode;
        this.accountCode = element.dataset.accountCode;
        this.accountText = element.dataset.accountText;
        this.summary = element.dataset.summary;
        this.bareNetBalance = new Decimal(element.dataset.netBalance);
        this.netBalance = this.bareNetBalance;
        this.netBalanceText = document.getElementById("accounting-original-entry-selector-option-" + this.id + "-net-balance");
        this.text = element.dataset.text;
        this.#queryValues = JSON.parse(element.dataset.queryValues);
        this.#element.onclick = () => this.#selector.entryEditor.saveOriginalEntry(this);
    }

    /**
     * Resets the net balance to its initial value, without the offset amounts on the form.
     *
     */
    resetNetBalance() {
        if (this.netBalance !== this.bareNetBalance) {
            this.netBalance = this.bareNetBalance;
            this.#updateNetBalanceText();
        }
    }

    /**
     * Updates the net balance with an offset.
     *
     * @param offset {Decimal} the offset to be added to the net balance
     */
    updateNetBalance(offset) {
        this.netBalance = this.bareNetBalance.minus(offset);
        this.#updateNetBalanceText();
    }

    /**
     * Updates the text display of the net balance.
     *
     */
    #updateNetBalanceText() {
        this.netBalanceText.innerText = formatDecimal(this.netBalance);
    }

    /**
     * Returns whether the original matches.
     *
     * @param entryType {string} the entry type, either "debit" or "credit"
     * @param currencyCode {string} the currency code
     * @param query {string|null} the query term
     */
    isMatched(entryType, currencyCode, query = null) {
        return this.netBalance.greaterThan(0)
            && this.date <= this.#selector.entryEditor.form.getDate()
            && this.#isEntryTypeMatches(entryType)
            && this.#currencyCode === currencyCode
            && this.#isQueryMatches(query);
    }

    /**
     * Returns whether the original entry matches the entry type.
     *
     * @param entryType {string} the entry type, either "debit" or credit
     * @return {boolean} true if the option matches, or false otherwise
     */
    #isEntryTypeMatches(entryType) {
        return (entryType === "debit" && this.#entryType === "credit")
            || (entryType === "credit" && this.#entryType === "debit");
    }

    /**
     * Returns whether the original entry matches the query.
     *
     * @param query {string|null} the query term
     * @return {boolean} true if the option matches, or false otherwise
     */
    #isQueryMatches(query) {
        if (query === "") {
            return true;
        }
        for (const queryValue of this.#queryValues[0]) {
            if (queryValue.toLowerCase().includes(query.toLowerCase())) {
                return true;
            }
        }
        for (const queryValue of this.#queryValues[1]) {
            if (queryValue === query) {
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
