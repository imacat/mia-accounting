/* The Mia! Accounting Flask Project
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

// Initializes the page JavaScript.
document.addEventListener("DOMContentLoaded", function () {
    document.getElementById("accounting-code")
        .onchange = validateCode;
    document.getElementById("accounting-name")
        .onchange = validateName;
    document.getElementById("accounting-form")
        .onsubmit = validateForm;
});

/**
 * The asynchronous validation result
 * @type {object}
 * @private
 */
let isAsyncValid = {};

/**
 * Validates the form.
 *
 * @returns {boolean} true if valid, or false otherwise
 * @private
 */
function validateForm() {
    isAsyncValid = {
        "code": false,
        "_sync": false,
    };
    let isValid = true;
    isValid = validateCode() && isValid;
    isValid = validateName() && isValid;
    isAsyncValid["_sync"] = isValid;
    submitFormIfAllAsyncValid();
    return false;
}

/**
 * Submits the form if the whole form passed the asynchronous
 * validations.
 *
 * @private
 */
function submitFormIfAllAsyncValid() {
    let isValid = true;
    for (const key of Object.keys(isAsyncValid)) {
        isValid = isAsyncValid[key] && isValid;
    }
    if (isValid) {
        document.getElementById("accounting-form").submit()
    }
}

/**
 * Validates the code.
 *
 * @param changeEvent {Event} the change event, if invoked from onchange
 * @returns {boolean} true if valid, or false otherwise
 * @private
 */
function validateCode(changeEvent = null) {
    const key = "code";
    const isSubmission = changeEvent === null;
    let hasAsyncValidation = false;
    const field = document.getElementById("accounting-code");
    const error = document.getElementById("accounting-code-error");
    field.value = field.value.trim();
    if (field.value === "") {
        field.classList.add("is-invalid");
        error.innerText = A_("Please fill in the code.");
        return false;
    }
    const blocklist = JSON.parse(field.dataset.blocklist);
    if (blocklist.includes(field.value)) {
        field.classList.add("is-invalid");
        error.innerText = A_("This code is not available.");
        return false;
    }
    if (!field.value.match(/^[A-Z]{3}$/)) {
        field.classList.add("is-invalid");
        error.innerText = A_("Code can only be composed of 3 upper-cased letters.");
        return false;
    }
    const original = field.dataset.original;
    if (original === "" || field.value !== original) {
        hasAsyncValidation = true;
        validateAsyncCodeIsDuplicated(isSubmission, key);
    }
    if (!hasAsyncValidation) {
        isAsyncValid[key] = true;
        field.classList.remove("is-invalid");
        error.innerText = "";
    }
    return true;
}

/**
 * Validates asynchronously whether the code is duplicated.
 * The boolean validation result is stored in isAsyncValid[key].
 *
 * @param isSubmission {boolean} whether this is invoked from a form submission
 * @param key {string} the key to store the result in isAsyncValid
 * @private
 */
function validateAsyncCodeIsDuplicated(isSubmission, key) {
    const field = document.getElementById("accounting-code");
    const error = document.getElementById("accounting-code-error");
    const url = field.dataset.existsUrl;
    const onLoad = function () {
        if (this.status === 200) {
            const result = JSON.parse(this.responseText);
            if (result["exists"]) {
                field.classList.add("is-invalid");
                error.innerText = A_("Code conflicts with another currency.");
                if (isSubmission) {
                    isAsyncValid[key] = false;
                }
                return;
            }
            field.classList.remove("is-invalid");
            error.innerText = "";
            if (isSubmission) {
                isAsyncValid[key] = true;
                submitFormIfAllAsyncValid();
            }
        }
    };
    const request = new XMLHttpRequest();
    request.onload = onLoad;
    request.open("GET", url + "?q=" + encodeURIComponent(field.value));
    request.send();
}

/**
 * Validates the name.
 *
 * @returns {boolean} true if valid, or false otherwise
 * @private
 */
function validateName() {
    const field = document.getElementById("accounting-name");
    const error = document.getElementById("accounting-name-error");
    field.value = field.value.trim();
    if (field.value === "") {
        field.classList.add("is-invalid");
        error.innerText = A_("Please fill in the name.");
        return false;
    }
    field.classList.remove("is-invalid");
    error.innerText = "";
    return true;
}
