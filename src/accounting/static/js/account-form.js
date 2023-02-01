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
    initializeBaseAccountSelector()
    document.getElementById("account-base-code")
        .onchange = validateBase;
    document.getElementById("account-title")
        .onchange = validateTitle;
    document.getElementById("account-form")
        .onsubmit = validateForm;
});

/**
 * Initializes the base account selector.
 *
 * @private
 */
function initializeBaseAccountSelector() {
    const selector = document.getElementById("select-base-modal");
    const base = document.getElementById("account-base");
    const baseCode = document.getElementById("account-base-code");
    const baseContent = document.getElementById("account-base-content");
    const options = Array.from(document.getElementsByClassName("list-group-item-base"));
    const btnClear = document.getElementById("btn-clear-base");
    selector.addEventListener("show.bs.modal", function () {
        base.classList.add("not-empty");
        options.forEach(function (item) {
            item.classList.remove("active");
        });
        const selected = document.getElementById("list-group-item-base-" + baseCode.value);
        if (selected !== null) {
            selected.classList.add("active");
        }
    });
    selector.addEventListener("hidden.bs.modal", function () {
        if (baseCode.value === "") {
            base.classList.remove("not-empty");
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
    const field = document.getElementById("account-base-code");
    const error = document.getElementById("account-base-code-error");
    const displayField = document.getElementById("account-base");
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
    const field = document.getElementById("account-title");
    const error = document.getElementById("account-title-error");
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
