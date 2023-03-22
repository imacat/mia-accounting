/* The Mia! Accounting Flask Project
 * account-form.js: The JavaScript for the account form
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
 * First written: 2023/2/1
 */
"use strict";

// Initializes the page JavaScript.
document.addEventListener("DOMContentLoaded", () => {
    AccountForm.initialize();
});

/**
 * The account form.
 *
 * @private
 */
class AccountForm {

    /**
     * The base account selector
     * @type {BaseAccountSelector}
     */
    #baseAccountSelector;

    /**
     * The form element
     * @type {HTMLFormElement}
     */
    #formElement;

    /**
     * The control of the base account
     * @type {HTMLDivElement}
     */
    #baseControl;

    /**
     * The input of the base account
     * @type {HTMLInputElement}
     */
    #baseCode;

    /**
     * The base account
     * @type {HTMLDivElement}
     */
    #base;

    /**
     * The error message for the base account
     * @type {HTMLDivElement}
     */
    #baseError;

    /**
     * The title
     * @type {HTMLInputElement}
     */
    #title;

    /**
     * The error message of the title
     * @type {HTMLDivElement}
     */
    #titleError;

    /**
     * The control of the is-need-offset option
     * @type {HTMLDivElement}
     */
    #isNeedOffsetControl;

    /**
     * The is-need-offset option
     * @type {HTMLInputElement}
     */
    #isNeedOffset;

    /**
     * Constructs the account form.
     *
     */
    constructor() {
        this.#baseAccountSelector = new BaseAccountSelector(this);
        this.#formElement = document.getElementById("accounting-form");
        this.#baseControl = document.getElementById("accounting-base-control");
        this.#baseCode = document.getElementById("accounting-base-code");
        this.#base = document.getElementById("accounting-base");
        this.#baseError = document.getElementById("accounting-base-error");
        this.#title = document.getElementById("accounting-title");
        this.#titleError = document.getElementById("accounting-title-error");
        this.#isNeedOffsetControl = document.getElementById("accounting-is-need-offset-control");
        this.#isNeedOffset = document.getElementById("accounting-is-need-offset");
        this.#formElement.onsubmit = () => {
            return this.#validate();
        };
        this.#baseControl.onclick = () => {
            this.#baseControl.classList.add("accounting-not-empty");
            this.#baseAccountSelector.onOpen(this.#baseCode.value);
        };
    }

    /**
     * The callback when the base account selector is closed.
     *
     */
    onBaseAccountSelectorClosed() {
        if (this.#baseCode.value === "") {
            this.#baseControl.classList.remove("accounting-not-empty");
        }
    }

    /**
     * Sets the base account.
     *
     * @param code {string} the base account code
     * @param text {string} the text for the base account
     */
    setBaseAccount(code, text) {
        this.#baseCode.value = code;
        this.#base.innerText = text;
        if (["1", "2", "3"].includes(code.substring(0, 1))) {
            this.#isNeedOffsetControl.classList.remove("d-none");
            this.#isNeedOffset.disabled = false;
        } else {
            this.#isNeedOffsetControl.classList.add("d-none");
            this.#isNeedOffset.disabled = true;
            this.#isNeedOffset.checked = false;
        }
        this.#validateBase();
    }

    /**
     * Clears the base account.
     *
     */
    clearBaseAccount() {
        this.#baseCode.value = "";
        this.#base.innerText = "";
        this.#validateBase();
    }

    /**
     * Validates the form.
     *
     * @returns {boolean} true if valid, or false otherwise
     */
    #validate() {
        let isValid = true;
        isValid = this.#validateBase() && isValid;
        isValid = this.#validateTitle() && isValid;
        return isValid;
    }

    /**
     * Validates the base account.
     *
     * @returns {boolean} true if valid, or false otherwise
     */
    #validateBase() {
        if (this.#baseCode.value === "") {
            this.#baseControl.classList.add("is-invalid");
            this.#baseError.innerText = A_("Please select the base account.");
            return false;
        }
        this.#baseControl.classList.remove("is-invalid");
        this.#baseError.innerText = "";
        return true;
    }

    /**
     * Validates the title.
     *
     * @returns {boolean} true if valid, or false otherwise
     */
    #validateTitle() {
        this.#title.value = this.#title.value.trim();
        if (this.#title.value === "") {
            this.#title.classList.add("is-invalid");
            this.#titleError.innerText = A_("Please fill in the title.");
            return false;
        }
        this.#title.classList.remove("is-invalid");
        this.#titleError.innerText = "";
        return true;
    }

    /**
     * The account form
     * @type {AccountForm} the form
     */
    static #form;

    static initialize() {
        this.#form = new AccountForm();
    }
}

/**
 * The base account selector.
 *
 * @private
 */
class BaseAccountSelector {

    /**
     * The account form
     * @type {AccountForm}
     */
    #form;

    /**
     * The selector modal
     * @type {HTMLDivElement}
     */
    #modal;

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
     * The button to clear the base account value
     * @type {HTMLButtonElement}
     */
    #clearButton;

    /**
     * Constructs the base account selector.
     *
     * @param form {AccountForm} the form
     */
    constructor(form) {
        this.#form = form;
        this.#modal = document.getElementById("accounting-base-selector-modal");
        this.#query = document.getElementById("accounting-base-selector-query");
        this.#optionList = document.getElementById("accounting-base-selector-option-list");
        // noinspection JSValidateTypes
        this.#options = Array.from(document.getElementsByClassName("accounting-base-selector-option"));
        this.#clearButton = document.getElementById("accounting-base-selector-clear");
        this.#queryNoResult = document.getElementById("accounting-base-selector-option-no-result");
        this.#modal.addEventListener("hidden.bs.modal", () => {
            this.#form.onBaseAccountSelectorClosed();
        });
        for (const option of this.#options) {
            option.onclick = () => {
                this.#form.setBaseAccount(option.dataset.code, option.dataset.text);
            };
        }
        this.#clearButton.onclick = () => {
            this.#form.clearBaseAccount();
        };
        this.#initializeBaseAccountQuery();
    }

    /**
     * Initializes the query.
     *
     */
    #initializeBaseAccountQuery() {
        this.#query.addEventListener("input", () => {
            if (this.#query.value === "") {
                for (const option of this.#options) {
                    option.classList.remove("d-none");
                }
                this.#optionList.classList.remove("d-none");
                this.#queryNoResult.classList.add("d-none");
                return
            }
            let hasAnyMatched = false;
            for (const option of this.#options) {
                const queryValues = JSON.parse(option.dataset.queryValues);
                let isMatched = false;
                for (const queryValue of queryValues) {
                    if (queryValue.toLowerCase().includes(this.#query.value.toLowerCase())) {
                        isMatched = true;
                        break;
                    }
                }
                if (isMatched) {
                    option.classList.remove("d-none");
                    hasAnyMatched = true;
                } else {
                    option.classList.add("d-none");
                }
            }
            if (!hasAnyMatched) {
                this.#optionList.classList.add("d-none");
                this.#queryNoResult.classList.remove("d-none");
            } else {
                this.#optionList.classList.remove("d-none");
                this.#queryNoResult.classList.add("d-none");
            }
        });
    }

    /**
     * The callback when the base account selector is shown.
     *
     * @param baseCode {string} the active base code
     */
    onOpen(baseCode) {
        for (const option of this.#options) {
            if (option.dataset.code === baseCode) {
                option.classList.add("active");
            } else {
                option.classList.remove("active");
            }
        }
        if (baseCode === "") {
            this.#clearButton.classList.add("btn-secondary")
            this.#clearButton.classList.remove("btn-danger");
            this.#clearButton.disabled = true;
        } else {
            this.#clearButton.classList.add("btn-danger");
            this.#clearButton.classList.remove("btn-secondary")
            this.#clearButton.disabled = false;
        }
    }
}
