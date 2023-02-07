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

// Initializes the page JavaScript.
document.addEventListener("DOMContentLoaded", function () {
    initializeBaseAccountSelector();
    document.getElementById("accounting-base-code")
        .onchange = validateBase;
    document.getElementById("accounting-title")
        .onchange = validateTitle;
    document.getElementById("accounting-form")
        .onsubmit = validateForm;
});

/**
 * Initializes the base account selector.
 *
 * @private
 */
function initializeBaseAccountSelector() {
    const selector = document.getElementById("accounting-base-selector-model");
    const base = document.getElementById("accounting-base");
    const baseCode = document.getElementById("accounting-base-code");
    const baseContent = document.getElementById("accounting-base-content");
    const options = Array.from(document.getElementsByClassName("accounting-base-option"));
    const btnClear = document.getElementById("accounting-btn-clear-base");
    selector.addEventListener("show.bs.modal", function () {
        base.classList.add("accounting-not-empty");
        options.forEach(function (item) {
            item.classList.remove("active");
        });
        const selected = document.getElementById("accounting-base-option-" + baseCode.value);
        if (selected !== null) {
            selected.classList.add("active");
        }
    });
    selector.addEventListener("hidden.bs.modal", function () {
        if (baseCode.value === "") {
            base.classList.remove("accounting-not-empty");
        }
    });
    options.forEach(function (option) {
        option.onclick = function () {
            baseCode.value = option.dataset.code;
            baseContent.innerText = option.dataset.content;
            btnClear.classList.add("btn-danger");
            btnClear.classList.remove("btn-secondary")
            btnClear.disabled = false;
            validateBase();
            bootstrap.Modal.getInstance(selector).hide();
        };
    });
    btnClear.onclick = function () {
        baseCode.value = "";
        baseContent.innerText = "";
        btnClear.classList.add("btn-secondary")
        btnClear.classList.remove("btn-danger");
        btnClear.disabled = true;
        validateBase();
        bootstrap.Modal.getInstance(selector).hide();
    }
    initializeBaseAccountQuery();
}

/**
 * Initializes the query on the base account options.
 *
 * @private
 */
function initializeBaseAccountQuery() {
    const query = document.getElementById("accounting-base-selector-query");
    const optionList = document.getElementById("accounting-base-option-list");
    const options = Array.from(document.getElementsByClassName("accounting-base-option"));
    const queryNoResult = document.getElementById("accounting-base-option-no-result");
    query.addEventListener("input", function () {
        console.log(query.value);
        if (query.value === "") {
            options.forEach(function (option) {
                option.classList.remove("d-none");
            });
            optionList.classList.remove("d-none");
            queryNoResult.classList.add("d-none");
            return
        }
        let hasAnyMatched = false;
        options.forEach(function (option) {
            const queryValues = JSON.parse(option.dataset.queryValues);
            let isMatched = false;
            for (let i = 0; i < queryValues.length; i++) {
                if (queryValues[i].includes(query.value)) {
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
        });
        if (!hasAnyMatched) {
            optionList.classList.add("d-none");
            queryNoResult.classList.remove("d-none");
        } else {
            optionList.classList.remove("d-none");
            queryNoResult.classList.add("d-none");
        }
    });
}

/**
 * Validates the form.
 *
 * @returns {boolean} true if valid, or false otherwise
 * @private
 */
function validateForm() {
    let isValid = true;
    isValid = validateBase() && isValid;
    isValid = validateTitle() && isValid;
    return isValid;
}

/**
 * Validates the base account.
 *
 * @returns {boolean} true if valid, or false otherwise
 * @private
 */
function validateBase() {
    const field = document.getElementById("accounting-base-code");
    const error = document.getElementById("accounting-base-code-error");
    const displayField = document.getElementById("accounting-base");
    field.value = field.value.trim();
    if (field.value === "") {
        displayField.classList.add("is-invalid");
        error.innerText = A_("Please select the base account.");
        return false;
    }
    displayField.classList.remove("is-invalid");
    error.innerText = "";
    return true;
}

/**
 * Validates the title.
 *
 * @returns {boolean} true if valid, or false otherwise
 * @private
 */
function validateTitle() {
    const field = document.getElementById("accounting-title");
    const error = document.getElementById("accounting-title-error");
    field.value = field.value.trim();
    if (field.value === "") {
        field.classList.add("is-invalid");
        error.innerText = A_("Please fill in the title.");
        return false;
    }
    field.classList.remove("is-invalid");
    error.innerText = "";
    return true;
}
