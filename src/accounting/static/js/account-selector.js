/* The Mia! Accounting Flask Project
 * transaction-transfer-form.js: The JavaScript for the transfer transaction form
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

// Initializes the page JavaScript.
document.addEventListener("DOMContentLoaded", function () {
    initializeAccountSelectors();
});

/**
 * Initializes the account selectors.
 *
 * @private
 */
function initializeAccountSelectors() {
    const selectors = Array.from(document.getElementsByClassName("accounting-account-selector-modal"));
    const formAccountControl = document.getElementById("accounting-entry-form-account-control");
    const formAccount = document.getElementById("accounting-entry-form-account");
    formAccountControl.onclick = function () {
        const entryForm = document.getElementById("accounting-entry-form");
        const prefix = "accounting-account-selector-" + entryForm.dataset.entryType;
        const query = document.getElementById(prefix + "-query")
        const more = document.getElementById(prefix + "-more");
        const options = Array.from(document.getElementsByClassName(prefix + "-option"));
        const btnClear = document.getElementById(prefix + "-btn-clear");
        query.value = "";
        more.classList.remove("d-none");
        filterAccountOptions(prefix);
        for (const option of options) {
            if (option.dataset.code === formAccount.dataset.code) {
                option.classList.add("active");
            } else {
                option.classList.remove("active");
            }
        }
        if (formAccount.dataset.code === "") {
            btnClear.classList.add("btn-secondary");
            btnClear.classList.remove("btn-danger");
            btnClear.disabled = true;
        } else {
            btnClear.classList.add("btn-danger");
            btnClear.classList.remove("btn-secondary");
            btnClear.disabled = false;
        }
    };
    for (const selector of selectors) {
        const more = document.getElementById(selector.dataset.prefix + "-more");
        const btnClear = document.getElementById(selector.dataset.prefix + "-btn-clear");
        const options = Array.from(document.getElementsByClassName(selector.dataset.prefix + "-option"));
        more.onclick = function () {
            more.classList.add("d-none");
            filterAccountOptions(selector.dataset.prefix);
        };
        initializeAccountQuery(selector);
        btnClear.onclick = function () {
            formAccountControl.classList.remove("accounting-not-empty");
            formAccount.innerText = "";
            formAccount.dataset.code = "";
            formAccount.dataset.text = "";
            validateJournalEntryAccount();
        };
        for (const option of options) {
            option.onclick = function () {
                formAccountControl.classList.add("accounting-not-empty");
                formAccount.innerText = option.dataset.content;
                formAccount.dataset.code = option.dataset.code;
                formAccount.dataset.text = option.dataset.content;
                validateJournalEntryAccount();
            };
        }
    }
}

/**
 * Initializes the query on the account options.
 *
 * @param selector {HTMLDivElement} the selector modal
 * @private
 */
function initializeAccountQuery(selector) {
    const query = document.getElementById(selector.dataset.prefix + "-query");
    query.addEventListener("input", function () {
        filterAccountOptions(selector.dataset.prefix);
    });
}

/**
 * Filters the account options.
 *
 * @param prefix {string} the HTML ID and class prefix
 * @private
 */
function filterAccountOptions(prefix) {
    const query = document.getElementById(prefix + "-query");
    const optionList = document.getElementById(prefix + "-option-list");
    if (optionList === null) {
        console.log(prefix + "-option-list");
    }
    const options = Array.from(document.getElementsByClassName(prefix + "-option"));
    const more = document.getElementById(prefix + "-more");
    const queryNoResult = document.getElementById(prefix + "-option-no-result");
    const codesInUse = getAccountCodeUsedInForm();
    let shouldAnyShow = false;
    for (const option of options) {
        const shouldShow = shouldAccountOptionShow(option, more, codesInUse, query);
        if (shouldShow) {
            option.classList.remove("d-none");
            shouldAnyShow = true;
        } else {
            option.classList.add("d-none");
        }
    }
    if (!shouldAnyShow && more.classList.contains("d-none")) {
        optionList.classList.add("d-none");
        queryNoResult.classList.remove("d-none");
    } else {
        optionList.classList.remove("d-none");
        queryNoResult.classList.add("d-none");
    }
}

/**
 * Returns whether an account option should show.
 *
 * @param option {HTMLLIElement} the account option
 * @param more {HTMLLIElement} the more account element
 * @param inUse {string[]} the account codes that are used in the form
 * @param query {HTMLInputElement} the query element, if any
 * @return {boolean} true if the account option should show, or false otherwise
 * @private
 */
function shouldAccountOptionShow(option, more, inUse, query) {
    const isQueryMatched = function () {
        if (query.value === "") {
            return true;
        }
        const queryValues = JSON.parse(option.dataset.queryValues);
        for (const queryValue of queryValues) {
            if (queryValue.includes(query.value)) {
                return true;
            }
        }
        return false;
    };
    const isMoreMatched = function () {
        if (more.classList.contains("d-none")) {
            return true;
        }
        return option.classList.contains("accounting-account-in-use") || inUse.includes(option.dataset.code);
    };
    return isMoreMatched() && isQueryMatched();
}

/**
 * Returns the account codes that are used in the form.
 *
 * @return {string[]} the account codes that are used in the form
 * @private
 */
function getAccountCodeUsedInForm() {
    const accountCodes = Array.from(document.getElementsByClassName("accounting-account-code"));
    const formAccount = document.getElementById("accounting-entry-form-account");
    const inUse = [formAccount.dataset.code];
    for (const accountCode of accountCodes) {
        inUse.push(accountCode.value);
    }
    return inUse
}
