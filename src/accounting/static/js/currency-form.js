/* The Mia! Accounting Project
 * currency-form.js: The JavaScript for the currency form
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
 * First written: 2023/2/6
 */
"use strict";

// Initializes the page JavaScript.
document.addEventListener("DOMContentLoaded", () => {
    CurrencyForm.initialize();
});

/**
 * The currency form.
 *
 * @private
 */
class CurrencyForm {

    /**
     * The form.
     * @type {HTMLFormElement}
     */
    #formElement;

    /**
     * The code
     * @type {HTMLInputElement}
     */
    #code;

    /**
     * The error message of the code
     * @type {HTMLDivElement}
     */
    #codeError;

    /**
     * The name
     * @type {HTMLInputElement}
     */
    #name;

    /**
     * The error message of the name
     * @type {HTMLDivElement}
     */
    #nameError;

    /**
     * Constructs the currency form.
     *
     */
    constructor() {
        this.#formElement = document.getElementById("accounting-form");
        this.#code = document.getElementById("accounting-code");
        this.#codeError = document.getElementById("accounting-code-error");
        this.#name = document.getElementById("accounting-name");
        this.#nameError = document.getElementById("accounting-name-error");
        this.#code.onchange = () => {
            this.#validateCode().then();
        };
        this.#name.onchange = () => {
            this.#validateName();
        };
        this.#formElement.onsubmit = () => {
            this.#validate().then((isValid) => {
                if (isValid) {
                    this.#formElement.submit();
                }
            });
            return false;
        };
    }

    /**
     * Validates the form.
     *
     * @returns {Promise<boolean>} true if valid, or false otherwise
     */
    async #validate() {
        let isValid = true;
        isValid = await this.#validateCode() && isValid;
        isValid = this.#validateName() && isValid;
        return isValid;
    }

    /**
     * Validates the code.
     *
     * @param changeEvent {Event} the change event, if invoked from onchange
     * @returns {Promise<boolean>} true if valid, or false otherwise
     */
    async #validateCode(changeEvent = null) {
        this.#code.value = this.#code.value.trim();
        if (this.#code.value === "") {
            this.#code.classList.add("is-invalid");
            this.#codeError.innerText = A_("Please fill in the code.");
            return false;
        }
        const blocklist = JSON.parse(this.#code.dataset.blocklist);
        if (blocklist.includes(this.#code.value)) {
            this.#code.classList.add("is-invalid");
            this.#codeError.innerText = A_("This code is not available.");
            return false;
        }
        if (!this.#code.value.match(/^[A-Z]{3}$/)) {
            this.#code.classList.add("is-invalid");
            this.#codeError.innerText = A_("Code can only be composed of 3 upper-cased letters.");
            return false;
        }
        const original = this.#code.dataset.original;
        if (original === "" || this.#code.value !== original) {
            const response = await fetch(`${this.#code.dataset.existsUrl}?q=${encodeURIComponent(this.#code.value)}`);
            const data = await response.json();
            if (data["exists"]) {
                this.#code.classList.add("is-invalid");
                this.#codeError.innerText = A_("Code conflicts with another currency.");
                return false;
            }
        }
        this.#code.classList.remove("is-invalid");
        this.#codeError.innerText = "";
        return true;
    }

    /**
     * Validates the name.
     *
     * @returns {boolean} true if valid, or false otherwise
     */
    #validateName() {
        this.#name.value = this.#name.value.trim();
        if (this.#name.value === "") {
            this.#name.classList.add("is-invalid");
            this.#nameError.innerText = A_("Please fill in the name.");
            return false;
        }
        this.#name.classList.remove("is-invalid");
        this.#nameError.innerText = "";
        return true;
    }

    /**
     * The form
     * @type {CurrencyForm}
     */
    static #form;

    /**
     * Initializes the currency form.
     *
     */
    static initialize() {
        this.#form = new CurrencyForm();
    }
}
