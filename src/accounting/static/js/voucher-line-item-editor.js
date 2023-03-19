/* The Mia! Accounting Flask Project
 * voucher-line-item-editor.js: The JavaScript for the voucher line item editor
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
 * The voucher line item editor.
 *
 */
class VoucherLineItemEditor {

    /**
     * The voucher form
     * @type {VoucherForm}
     */
    form;

    /**
     * The voucher line item editor
     * @type {HTMLFormElement}
     */
    #element;

    /**
     * The bootstrap modal
     * @type {HTMLDivElement}
     */
    #modal;

    /**
     * The side, either "debit" or "credit"
     * @type {string}
     */
    side;

    /**
     * The prefix of the HTML ID and class
     * @type {string}
     */
    #prefix = "accounting-line-item-editor"

    /**
     * The container of the original line item
     * @type {HTMLDivElement}
     */
    #originalLineItemContainer;

    /**
     * The control of the original line item
     * @type {HTMLDivElement}
     */
    #originalLineItemControl;

    /**
     * The original line item
     * @type {HTMLDivElement}
     */
    #originalLineItemText;

    /**
     * The error message of the original line item
     * @type {HTMLDivElement}
     */
    #originalLineItemError;

    /**
     * The delete button of the original line item
     * @type {HTMLButtonElement}
     */
    #originalLineItemDelete;

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
     * The voucher line item to edit
     * @type {LineItemSubForm|null}
     */
    lineItem;

    /**
     * The debit or credit side sub-form
     * @type {SideSubForm}
     */
    #sideSubForm;

    /**
     * Whether the voucher line item needs offset
     * @type {boolean}
     */
    isNeedOffset = false;

    /**
     * The ID of the original line item
     * @type {string|null}
     */
    originalLineItemId = null;

    /**
     * The date of the original line item
     * @type {string|null}
     */
    originalLineItemDate = null;

    /**
     * The text of the original line item
     * @type {string|null}
     */
    originalLineItemText = null;

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
     * The original line item selector
     * @type {OriginalLineItemSelector}
     */
    originalLineItemSelector;

    /**
     * Constructs a new voucher line item editor.
     *
     * @param form {VoucherForm} the voucher form
     */
    constructor(form) {
        this.form = form;
        this.#element = document.getElementById(this.#prefix);
        this.#modal = document.getElementById(this.#prefix + "-modal");
        this.#originalLineItemContainer = document.getElementById(this.#prefix + "-original-line-item-container");
        this.#originalLineItemControl = document.getElementById(this.#prefix + "-original-line-item-control");
        this.#originalLineItemText = document.getElementById(this.#prefix + "-original-line-item");
        this.#originalLineItemError = document.getElementById(this.#prefix + "-original-line-item-error");
        this.#originalLineItemDelete = document.getElementById(this.#prefix + "-original-line-item-delete");
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
        this.originalLineItemSelector = new OriginalLineItemSelector(this);
        this.#originalLineItemControl.onclick = () => this.originalLineItemSelector.onOpen()
        this.#originalLineItemDelete.onclick = () => this.clearOriginalLineItem();
        this.#summaryControl.onclick = () => this.#summaryEditors[this.side].onOpen();
        this.#accountControl.onclick = () => this.#accountSelectors[this.side].onOpen();
        this.#amountInput.onchange = () => this.#validateAmount();
        this.#element.onsubmit = () => {
            if (this.#validate()) {
                if (this.lineItem === null) {
                    this.lineItem = this.#sideSubForm.addLineItem();
                }
                this.amount = this.#amountInput.value;
                this.lineItem.save(this);
                bootstrap.Modal.getInstance(this.#modal).hide();
            }
            return false;
        };
    }

    /**
     * Saves the original line item from the original line item selector.
     *
     * @param originalLineItem {OriginalLineItem} the original line item
     */
    saveOriginalLineItem(originalLineItem) {
        this.isNeedOffset = false;
        this.#originalLineItemContainer.classList.remove("d-none");
        this.#originalLineItemControl.classList.add("accounting-not-empty");
        this.originalLineItemId = originalLineItem.id;
        this.originalLineItemDate = originalLineItem.date;
        this.originalLineItemText = originalLineItem.text;
        this.#originalLineItemText.innerText = originalLineItem.text;
        this.#setEnableSummaryAccount(false);
        if (originalLineItem.summary === "") {
            this.#summaryControl.classList.remove("accounting-not-empty");
        } else {
            this.#summaryControl.classList.add("accounting-not-empty");
        }
        this.summary = originalLineItem.summary === ""? null: originalLineItem.summary;
        this.#summaryText.innerText = originalLineItem.summary;
        this.#accountControl.classList.add("accounting-not-empty");
        this.accountCode = originalLineItem.accountCode;
        this.accountText = originalLineItem.accountText;
        this.#accountText.innerText = originalLineItem.accountText;
        this.#amountInput.value = String(originalLineItem.netBalance);
        this.#amountInput.max = String(originalLineItem.netBalance);
        this.#amountInput.min = "0";
        this.#validate();
    }

    /**
     * Clears the original line item.
     *
     */
    clearOriginalLineItem() {
        this.isNeedOffset = false;
        this.#originalLineItemContainer.classList.add("d-none");
        this.#originalLineItemControl.classList.remove("accounting-not-empty");
        this.originalLineItemId = null;
        this.originalLineItemDate = null;
        this.originalLineItemText = null;
        this.#originalLineItemText.innerText = "";
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
        return this.#sideSubForm.currency.getCurrencyCode();
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
     * @param isAccountNeedOffset {boolean} true if the line items in the account need offset, or false otherwise
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
     * @param isNeedOffset {boolean} true if the line items in the account need offset or false otherwise
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
        isValid = this.#validateOriginalLineItem() && isValid;
        isValid = this.#validateSummary() && isValid;
        isValid = this.#validateAccount() && isValid;
        isValid = this.#validateAmount() && isValid
        return isValid;
    }

    /**
     * Validates the original line item.
     *
     * @return {boolean} true if valid, or false otherwise
     * @private
     */
    #validateOriginalLineItem() {
        this.#originalLineItemControl.classList.remove("is-invalid");
        this.#originalLineItemError.innerText = "";
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
                this.#amountError.innerText = A_("The amount must not exceed the net balance %(balance)s of the original line item.", {balance: new Decimal(this.#amountInput.max)});
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
     * The callback when adding a new voucher line item.
     *
     * @param side {SideSubForm} the debit or credit side sub-form
     */
    onAddNew(side) {
        this.lineItem = null;
        this.#sideSubForm = side;
        this.side = this.#sideSubForm.side;
        this.isNeedOffset = false;
        this.#originalLineItemContainer.classList.add("d-none");
        this.#originalLineItemControl.classList.remove("accounting-not-empty");
        this.#originalLineItemControl.classList.remove("is-invalid");
        this.originalLineItemId = null;
        this.originalLineItemDate = null;
        this.originalLineItemText = null;
        this.#originalLineItemText.innerText = "";
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
     * The callback when editing a voucher line item.
     *
     * @param lineItem {LineItemSubForm} the voucher line item sub-form
     */
    onEdit(lineItem) {
        this.lineItem = lineItem;
        this.#sideSubForm = lineItem.sideSubForm;
        this.side = this.#sideSubForm.side;
        this.isNeedOffset = lineItem.isNeedOffset();
        this.originalLineItemId = lineItem.getOriginalLineItemId();
        this.originalLineItemDate = lineItem.getOriginalLineItemDate();
        this.originalLineItemText = lineItem.getOriginalLineItemText();
        this.#originalLineItemText.innerText = this.originalLineItemText;
        if (this.originalLineItemId === null) {
            this.#originalLineItemContainer.classList.add("d-none");
            this.#originalLineItemControl.classList.remove("accounting-not-empty");
        } else {
            this.#originalLineItemContainer.classList.remove("d-none");
            this.#originalLineItemControl.classList.add("accounting-not-empty");
        }
        this.#setEnableSummaryAccount(!lineItem.isMatched && this.originalLineItemId === null);
        this.summary = lineItem.getSummary();
        if (this.summary === null) {
            this.#summaryControl.classList.remove("accounting-not-empty");
        } else {
            this.#summaryControl.classList.add("accounting-not-empty");
        }
        this.#summaryText.innerText = this.summary === null? "": this.summary;
        if (lineItem.getAccountCode() === null) {
            this.#accountControl.classList.remove("accounting-not-empty");
        } else {
            this.#accountControl.classList.add("accounting-not-empty");
        }
        this.accountCode = lineItem.getAccountCode();
        this.accountText = lineItem.getAccountText();
        this.#accountText.innerText = this.accountText;
        this.#amountInput.value = lineItem.getAmount() === null? "": String(lineItem.getAmount());
        const maxAmount = this.#getMaxAmount();
        this.#amountInput.max = maxAmount === null? "": maxAmount;
        this.#amountInput.min = lineItem.getAmountMin() === null? "": String(lineItem.getAmountMin());
        this.#validate();
    }

    /**
     * Finds out the max amount.
     *
     * @return {Decimal|null} the max amount
     */
    #getMaxAmount() {
        if (this.originalLineItemId === null) {
            return null;
        }
        return this.originalLineItemSelector.getNetBalance(this.lineItem, this.form, this.originalLineItemId);
    }

    /**
     * Sets the enable status of the summary and account.
     *
     * @param isEnabled {boolean} true to enable, or false otherwise
     */
    #setEnableSummaryAccount(isEnabled) {
        if (isEnabled) {
            this.#summaryControl.dataset.bsToggle = "modal";
            this.#summaryControl.dataset.bsTarget = "#accounting-summary-editor-" + this.#sideSubForm.side + "-modal";
            this.#summaryControl.classList.remove("accounting-disabled");
            this.#summaryControl.classList.add("accounting-clickable");
            this.#accountControl.dataset.bsToggle = "modal";
            this.#accountControl.dataset.bsTarget = "#accounting-account-selector-" + this.#sideSubForm.side + "-modal";
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
