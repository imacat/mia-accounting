/* The Mia! Accounting Project
 * original-line-item-selector.js: The JavaScript for the original line item selector
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
 * The original line item selector.
 *
 */
class OriginalLineItemSelector {

    /**
     * The line item editor
     * @type {JournalEntryLineItemEditor}
     */
    lineItemEditor;

    /**
     * The prefix of the HTML ID and class names
     * @type {string}
     */
    #prefix = "accounting-original-line-item-selector";

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
     * @type {OriginalLineItem[]}
     */
    #options;

    /**
     * The options by their ID
     * @type {Object.<string, OriginalLineItem>}
     */
    #optionById;

    /**
     * The currency code
     * @type {string}
     */
    #currencyCode;

    /**
     * Either "credit" or "debit"
     */
    #debitCredit;

    /**
     * Constructs an original line item selector.
     *
     * @param lineItemEditor {JournalEntryLineItemEditor} the line item editor
     */
    constructor(lineItemEditor) {
        this.lineItemEditor = lineItemEditor;
        this.#query = document.getElementById(`${this.#prefix}-query`);
        this.#queryNoResult = document.getElementById(`${this.#prefix}-option-no-result`);
        this.#optionList = document.getElementById(`${this.#prefix}-option-list`);
        this.#options = Array.from(document.getElementsByClassName(`${this.#prefix}-option`)).map((element) => new OriginalLineItem(this, element));
        this.#optionById = {};
        for (const option of this.#options) {
            this.#optionById[option.id] = option;
        }
        this.#query.oninput = () => this.#filterOptions();
    }

    /**
     * Returns the net balance for an original line item.
     *
     * @param currentLineItem {LineItemSubForm} the line item sub-form that is currently editing
     * @param form {JournalEntryForm} the journal entry form
     * @param originalLineItemId {string} the ID of the original line item
     * @return {Decimal} the net balance of the original line item
     */
    getNetBalance(currentLineItem, form, originalLineItemId) {
        const otherLineItems = form.getLineItems().filter((lineItem) => lineItem !== currentLineItem);
        let otherOffset = new Decimal(0);
        for (const otherLineItem of otherLineItems) {
            if (otherLineItem.originalLineItemId === originalLineItemId) {
                const amount = otherLineItem.amount;
                if (amount !== null) {
                    otherOffset = otherOffset.plus(amount);
                }
            }
        }
        return this.#optionById[originalLineItemId].bareNetBalance.minus(otherOffset);
    }

    /**
     * Updates the net balances, subtracting the offset amounts on the form but the currently editing line item
     *
     */
    #updateNetBalances() {
        const otherLineItems = this.lineItemEditor.form.getLineItems().filter((lineItem) => lineItem !== this.lineItemEditor.lineItem);
        const otherOffsets = {}
        for (const otherLineItem of otherLineItems) {
            const otherOriginalLineItemId = otherLineItem.originalLineItemId;
            const amount = otherLineItem.amount;
            if (otherOriginalLineItemId === null || amount === null) {
                continue;
            }
            if (!(otherOriginalLineItemId in otherOffsets)) {
                otherOffsets[otherOriginalLineItemId] = new Decimal("0");
            }
            otherOffsets[otherOriginalLineItemId] = otherOffsets[otherOriginalLineItemId].plus(amount);
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
        let isAnyMatched = false;
        for (const option of this.#options) {
            if (option.isMatched(this.#debitCredit, this.#currencyCode, this.#query.value)) {
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
     * The callback when the original line item selector is shown.
     *
     */
    onOpen() {
        this.#currencyCode = this.lineItemEditor.currencyCode;
        this.#debitCredit = this.lineItemEditor.debitCredit;
        for (const option of this.#options) {
            option.setActive(option.id === this.lineItemEditor.originalLineItemId);
        }
        this.#query.value = "";
        this.#updateNetBalances();
        this.#filterOptions();
    }
}

/**
 * An original line item.
 *
 */
class OriginalLineItem {

    /**
     * The journal entry form
     * @type {JournalEntryForm}
     */
    #form;

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
     * Either "debit" or "credit"
     * @type {string}
     */
    #debitCredit;

    /**
     * The currency code
     * @type {string}
     */
    #currencyCode;

    /**
     * The account
     * @type {JournalEntryAccount}
     */
    account;

    /**
     * The description
     * @type {string}
     */
    description;

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
     * The text representation of the original line item
     * @type {string}
     */
    text;

    /**
     * The values to query against
     * @type {string[]}
     */
    #queryValues;

    /**
     * Constructs an original line item.
     *
     * @param selector {OriginalLineItemSelector} the original line item selector
     * @param element {HTMLLIElement} the element
     */
    constructor(selector, element) {
        this.#form = selector.lineItemEditor.form;
        this.#element = element;
        this.id = element.dataset.id;
        this.date = element.dataset.date;
        this.#debitCredit = element.dataset.debitCredit;
        this.#currencyCode = element.dataset.currencyCode;
        this.account = new JournalEntryAccount(element.dataset.accountCode, element.dataset.accountText, false);
        this.description = element.dataset.description;
        this.bareNetBalance = new Decimal(element.dataset.netBalance);
        this.netBalance = this.bareNetBalance;
        this.netBalanceText = document.getElementById(`accounting-original-line-item-selector-option-${this.id}-net-balance`);
        this.text = element.dataset.text;
        this.#queryValues = JSON.parse(element.dataset.queryValues);
        this.#element.onclick = () => selector.lineItemEditor.saveOriginalLineItem(this);
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
     * @param debitCredit {string} either "debit" or "credit"
     * @param currencyCode {string} the currency code
     * @param query {string|null} the query term
     */
    isMatched(debitCredit, currencyCode, query = null) {
        return this.netBalance.greaterThan(0)
            && this.date <= this.#form.date
            && this.#isDebitCreditMatched(debitCredit)
            && this.#currencyCode === currencyCode
            && this.#isQueryMatched(query);
    }

    /**
     * Returns whether the original line item matches the debit or credit.
     *
     * @param debitCredit {string} either "debit" or credit
     * @return {boolean} true if the option matches, or false otherwise
     */
    #isDebitCreditMatched(debitCredit) {
        return (debitCredit === "debit" && this.#debitCredit === "credit")
            || (debitCredit === "credit" && this.#debitCredit === "debit");
    }

    /**
     * Returns whether the original line item matches the query term.
     *
     * @param query {string|null} the query term
     * @return {boolean} true if the option matches, or false otherwise
     */
    #isQueryMatched(query) {
        if (query === "") {
            return true;
        }
        if (this.#getNetBalanceForQuery().includes(query.toLowerCase())) {
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
     * Returns the net balance in the format for query match.
     *
     * @return {string} the net balance in the format for query match
     */
    #getNetBalanceForQuery() {
        const frac = this.netBalance.modulo(1);
        const whole = Number(this.netBalance.minus(frac));
        return String(whole) + String(frac).substring(1);
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
