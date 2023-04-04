/* The Mia! Accounting Project
 * journal-entry-line-item-editor.js: The JavaScript for the journal entry line item editor
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
 * The journal entry line item editor.
 *
 */
class JournalEntryLineItemEditor {

    /**
     * The journal entry form
     * @type {JournalEntryForm}
     */
    form;

    /**
     * The journal entry line item editor
     * @type {HTMLFormElement}
     */
    #element;

    /**
     * The bootstrap modal
     * @type {HTMLDivElement}
     */
    modal;

    /**
     * Either "debit" or "credit"
     * @type {string}
     */
    debitCredit;

    /**
     * The prefix of the HTML ID and class names
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
     * The control of the description
     * @type {HTMLDivElement}
     */
    #descriptionControl;

    /**
     * The description
     * @type {HTMLDivElement}
     */
    #descriptionText;

    /**
     * The error message of the description
     * @type {HTMLDivElement}
     */
    #descriptionError;

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
     * The journal entry line item to edit
     * @type {LineItemSubForm|null}
     */
    lineItem;

    /**
     * The debit or credit sub-form
     * @type {DebitCreditSubForm}
     */
    #debitCreditSubForm;

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
     * The account
     * @type {JournalEntryAccount|null}
     */
    account = null;

    /**
     * Whether the user has confirmed the account
     * @type {boolean}
     */
    isAccountConfirmed = false;

    /**
     * The description
     * @type {string|null}
     */
    description = null;

    /**
     * The description editors
     * @type {{debit: DescriptionEditor, credit: DescriptionEditor}}
     */
    #descriptionEditors;

    /**
     * The account selectors
     * @type {{debit: JournalEntryAccountSelector, credit: JournalEntryAccountSelector}}
     */
    #accountSelectors;

    /**
     * The original line item selector
     * @type {OriginalLineItemSelector}
     */
    originalLineItemSelector;

    /**
     * Constructs a new journal entry line item editor.
     *
     * @param form {JournalEntryForm} the journal entry form
     */
    constructor(form) {
        this.form = form;
        this.#element = document.getElementById(this.#prefix);
        this.modal = document.getElementById(`${this.#prefix}-modal`);
        this.#originalLineItemContainer = document.getElementById(`${this.#prefix}-original-line-item-container`);
        this.#originalLineItemControl = document.getElementById(`${this.#prefix}-original-line-item-control`);
        this.#originalLineItemText = document.getElementById(`${this.#prefix}-original-line-item`);
        this.#originalLineItemError = document.getElementById(`${this.#prefix}-original-line-item-error`);
        this.#originalLineItemDelete = document.getElementById(`${this.#prefix}-original-line-item-delete`);
        this.#descriptionControl = document.getElementById(`${this.#prefix}-description-control`);
        this.#descriptionText = document.getElementById(`${this.#prefix}-description`);
        this.#descriptionError = document.getElementById(`${this.#prefix}-description-error`);
        this.#accountControl = document.getElementById(`${this.#prefix}-account-control`);
        this.#accountText = document.getElementById(`${this.#prefix}-account`);
        this.#accountError = document.getElementById(`${this.#prefix}-account-error`)
        this.#amountInput = document.getElementById(`${this.#prefix}-amount`);
        this.#amountError = document.getElementById(`${this.#prefix}-amount-error`);
        this.#descriptionEditors = DescriptionEditor.getInstances(this);
        this.#accountSelectors = JournalEntryAccountSelector.getInstances(this);
        this.originalLineItemSelector = new OriginalLineItemSelector(this);

        this.#originalLineItemControl.onclick = () => this.originalLineItemSelector.onOpen()
        this.#originalLineItemDelete.onclick = () => this.clearOriginalLineItem();
        this.#descriptionControl.onclick = () => this.#descriptionEditors[this.debitCredit].onOpen();
        this.#accountControl.onclick = () => this.#accountSelectors[this.debitCredit].onOpen();
        this.#amountInput.onchange = () => this.#validateAmount();
        this.#element.onsubmit = () => {
            if (this.#validate()) {
                if (this.lineItem === null) {
                    this.lineItem = this.#debitCreditSubForm.addLineItem();
                }
                this.lineItem.save(this);
                bootstrap.Modal.getInstance(this.modal).hide();
            }
            return false;
        };
        this.modal.addEventListener("hidden.bs.modal", () => this.#debitCreditSubForm.onLineItemEditorClosed());
    }

    /**
     * Returns the amount.
     *
     * @return {string} the amount
     */
    get amount() {
        return this.#amountInput.value;
    }

    /**
     * Returns the currency code.
     *
     * @return {string} the currency code
     */
    get currencyCode() {
        return this.#debitCreditSubForm.currency.currencyCode;
    }

    /**
     * Saves the original line item from the original line item selector.
     *
     * @param originalLineItem {OriginalLineItem} the original line item
     */
    saveOriginalLineItem(originalLineItem) {
        this.#originalLineItemContainer.classList.remove("d-none");
        this.#originalLineItemControl.classList.add("accounting-not-empty");
        this.originalLineItemId = originalLineItem.id;
        this.originalLineItemDate = originalLineItem.date;
        this.originalLineItemText = originalLineItem.text;
        this.#originalLineItemText.innerText = originalLineItem.text;
        this.#setEnableDescriptionAccount(false);
        if (originalLineItem.description === "") {
            this.#descriptionControl.classList.remove("accounting-not-empty");
        } else {
            this.#descriptionControl.classList.add("accounting-not-empty");
        }
        this.description = originalLineItem.description === ""? null: originalLineItem.description;
        this.#descriptionText.innerText = originalLineItem.description;
        this.#accountControl.classList.add("accounting-not-empty");
        this.account = originalLineItem.account.copy();
        this.isAccountConfirmed = false;
        this.#accountText.innerText = this.account.text;
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
        this.#originalLineItemContainer.classList.add("d-none");
        this.#originalLineItemControl.classList.remove("accounting-not-empty");
        this.originalLineItemId = null;
        this.originalLineItemDate = null;
        this.originalLineItemText = null;
        this.#originalLineItemText.innerText = "";
        this.#setEnableDescriptionAccount(true);
        this.#accountControl.classList.remove("accounting-not-empty");
        this.account = null;
        this.isAccountConfirmed = false;
        this.#accountText.innerText = "";
        this.#amountInput.max = "";
    }

    /**
     * Saves the description from the description editor.
     *
     * @param editor {DescriptionEditor} the description editor
     */
    saveDescription(editor) {
        if (editor.selectedAccount !== null) {
            this.#accountControl.classList.add("accounting-not-empty");
            this.account = editor.selectedAccount.copy();
            this.#accountText.innerText = editor.selectedAccount.text;
            this.isAccountConfirmed = editor.isAccountConfirmed;
            this.#validateAccount();
        }
        if (editor.description === "") {
            this.#descriptionControl.classList.remove("accounting-not-empty");
        } else {
            this.#descriptionControl.classList.add("accounting-not-empty");
        }
        this.description = editor.description === ""? null: editor.description;
        this.#descriptionText.innerText = editor.description;
        this.#validateDescription();
        bootstrap.Modal.getOrCreateInstance(this.modal).show();
    }

    /**
     * Clears the account.
     *
     */
    clearAccount() {
        this.#accountControl.classList.remove("accounting-not-empty");
        this.account = null;
        this.isAccountConfirmed = false;
        this.#accountText.innerText = "";
        this.#validateAccount();
    }

    /**
     * Saves the selected account.
     *
     * @param account {JournalEntryAccountOption} the selected account
     */
    saveAccount(account) {
        this.#accountControl.classList.add("accounting-not-empty");
        this.account = new JournalEntryAccount(account.code, account.text, account.isNeedOffset);
        this.isAccountConfirmed = true;
        this.#accountText.innerText = account.text;
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
        isValid = this.#validateDescription() && isValid;
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
     * Validates the description.
     *
     * @return {boolean} true if valid, or false otherwise
     * @private
     */
    #validateDescription() {
        this.#descriptionText.classList.remove("is-invalid");
        this.#descriptionError.innerText = "";
        return true;
    }

    /**
     * Validates the account.
     *
     * @return {boolean} true if valid, or false otherwise
     */
    #validateAccount() {
        if (this.account === null) {
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
     * The callback when adding a new journal entry line item.
     *
     * @param debitCredit {DebitCreditSubForm} the debit or credit sub-form
     */
    onAddNew(debitCredit) {
        this.lineItem = null;
        this.#debitCreditSubForm = debitCredit;
        this.debitCredit = this.#debitCreditSubForm.debitCredit;
        this.#originalLineItemContainer.classList.add("d-none");
        this.#originalLineItemControl.classList.remove("accounting-not-empty");
        this.#originalLineItemControl.classList.remove("is-invalid");
        this.originalLineItemId = null;
        this.originalLineItemDate = null;
        this.originalLineItemText = null;
        this.#originalLineItemText.innerText = "";
        this.#setEnableDescriptionAccount(true);
        this.#descriptionControl.classList.remove("accounting-not-empty");
        this.#descriptionControl.classList.remove("is-invalid");
        this.description = null;
        this.#descriptionText.innerText = ""
        this.#descriptionError.innerText = ""
        this.#accountControl.classList.remove("accounting-not-empty");
        this.#accountControl.classList.remove("is-invalid");
        this.account = null;
        this.isAccountConfirmed = false;
        this.#accountText.innerText = "";
        this.#accountError.innerText = "";
        this.#amountInput.value = "";
        this.#amountInput.max = "";
        this.#amountInput.min = "0";
        this.#amountInput.classList.remove("is-invalid");
        this.#amountError.innerText = "";
    }

    /**
     * The callback when editing a journal entry line item.
     *
     * @param lineItem {LineItemSubForm} the journal entry line item sub-form
     */
    onEdit(lineItem) {
        this.lineItem = lineItem;
        this.#debitCreditSubForm = lineItem.debitCreditSubForm;
        this.debitCredit = this.#debitCreditSubForm.debitCredit;
        this.originalLineItemId = lineItem.originalLineItemId;
        this.originalLineItemDate = lineItem.originalLineItemDate;
        this.originalLineItemText = lineItem.originalLineItemText;
        this.#originalLineItemText.innerText = this.originalLineItemText;
        if (this.originalLineItemId === null) {
            this.#originalLineItemContainer.classList.add("d-none");
            this.#originalLineItemControl.classList.remove("accounting-not-empty");
        } else {
            this.#originalLineItemContainer.classList.remove("d-none");
            this.#originalLineItemControl.classList.add("accounting-not-empty");
        }
        this.#setEnableDescriptionAccount(!lineItem.isMatched && this.originalLineItemId === null);
        this.description = lineItem.description;
        if (this.description === null) {
            this.#descriptionControl.classList.remove("accounting-not-empty");
        } else {
            this.#descriptionControl.classList.add("accounting-not-empty");
        }
        this.#descriptionText.innerText = this.description === null? "": this.description;
        this.account = lineItem.account;
        this.isAccountConfirmed = true;
        if (this.account === null) {
            this.#accountControl.classList.remove("accounting-not-empty");
        } else {
            this.#accountControl.classList.add("accounting-not-empty");
        }
        this.#accountText.innerText = this.account.text;
        this.#amountInput.value = lineItem.amount === null? "": String(lineItem.amount);
        const maxAmount = this.#getMaxAmount();
        this.#amountInput.max = maxAmount === null? "": maxAmount;
        this.#amountInput.min = lineItem.amountMin === null? "": String(lineItem.amountMin);
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
     * Sets the enable status of the description and account.
     *
     * @param isEnabled {boolean} true to enable, or false otherwise
     */
    #setEnableDescriptionAccount(isEnabled) {
        if (isEnabled) {
            this.#descriptionControl.dataset.bsToggle = "modal";
            this.#descriptionControl.dataset.bsTarget = `#accounting-description-editor-${this.#debitCreditSubForm.debitCredit}-modal`;
            this.#descriptionControl.classList.remove("accounting-disabled");
            this.#descriptionControl.classList.add("accounting-clickable");
            this.#accountControl.dataset.bsToggle = "modal";
            this.#accountControl.dataset.bsTarget = `#accounting-account-selector-${this.#debitCreditSubForm.debitCredit}-modal`;
            this.#accountControl.classList.remove("accounting-disabled");
            this.#accountControl.classList.add("accounting-clickable");
        } else {
            this.#descriptionControl.dataset.bsToggle = "";
            this.#descriptionControl.dataset.bsTarget = "";
            this.#descriptionControl.classList.add("accounting-disabled");
            this.#descriptionControl.classList.remove("accounting-clickable");
            this.#accountControl.dataset.bsToggle = "";
            this.#accountControl.dataset.bsTarget = "";
            this.#accountControl.classList.add("accounting-disabled");
            this.#accountControl.classList.remove("accounting-clickable");
        }
    }
}

