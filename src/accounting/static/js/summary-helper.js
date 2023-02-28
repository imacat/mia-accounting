/* The Mia! Accounting Flask Project
 * summary-helper.js: The JavaScript for the summary helper
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
    SummaryHelper.initialize();
});

/**
 * A summary helper.
 *
 */
class SummaryHelper {

    /**
     * The entry type, either "debit" or "credit"
     * @type {string}
     */
    #entryType;

    /**
     * The prefix of the HTML ID and class
     * @type {string}
     */
    #prefix;

    /**
     * The default tab ID
     * @type {string}
     */
    #defaultTabId;

    /**
     * Constructs a summary helper.
     *
     * @param form {HTMLFormElement} the summary helper form
     */
    constructor(form) {
        this.#entryType = form.dataset.entryType;
        this.#prefix = "accounting-summary-helper-" + form.dataset.entryType;
        this.#defaultTabId = form.dataset.defaultTabId;
        this.#init();
    }

    /**
     * Initializes the summary helper.
     *
     */
    #init() {
        const helper = this;
        const summary = document.getElementById(this.#prefix + "-summary");
        const tabs = Array.from(document.getElementsByClassName(this.#prefix + "-tab"));
        for (const tab of tabs) {
            tab.onclick = function () {
                helper.#switchToTab(tab.dataset.tabId);
            }
        }
        this.#initializeGeneralTagHelper();
        this.#initializeGeneralTripHelper();
        this.#initializeBusTripHelper();
        this.#initializeNumberHelper();
        this.#initializeSuggestedAccounts();
        this.#initializeSubmission();
        summary.onchange = function () {
            summary.value = summary.value.trim();
            helper.#parseAndPopulate();
        };
    }

    /**
     * Switches to a tab.
     *
     * @param tabId {string} the tab ID.
     */
    #switchToTab(tabId) {
        const tabs = Array.from(document.getElementsByClassName(this.#prefix + "-tab"));
        const pages = Array.from(document.getElementsByClassName(this.#prefix + "-page"));
        const tagButtons = Array.from(document.getElementsByClassName(this.#prefix + "-" + tabId + "-btn-tag"));
        for (const tab of tabs) {
            if (tab.dataset.tabId === tabId) {
                tab.classList.add("active");
                tab.ariaCurrent = "page";
            } else {
                tab.classList.remove("active");
                tab.ariaCurrent = "false";
            }
        }
        for (const page of pages) {
            if (page.dataset.tabId === tabId) {
                page.classList.remove("d-none");
                page.ariaCurrent = "page";
            } else {
                page.classList.add("d-none");
                page.ariaCurrent = "false";
            }
        }
        let selectedBtnTag = null;
        for (const tagButton of tagButtons) {
            if (tagButton.classList.contains("btn-primary")) {
                selectedBtnTag = tagButton;
                break;
            }
        }
        this.#filterSuggestedAccounts(selectedBtnTag);
    }

    /**
     * Initializes the general tag helper.
     *
     */
    #initializeGeneralTagHelper() {
        const summary = document.getElementById(this.#prefix + "-summary");
        const tag = document.getElementById(this.#prefix + "-general-tag");
        const helper = this;
        const updateSummary = function () {
            const pos = summary.value.indexOf("—");
            const prefix = tag.value === ""? "": tag.value + "—";
            if (pos === -1) {
                summary.value = prefix + summary.value;
            } else {
                summary.value = prefix + summary.value.substring(pos + 1);
            }
        }
        this.#initializeTagButtons("general", tag, updateSummary);
        tag.onchange = function () {
            helper.#onTagInputChange("general", tag, updateSummary);
        };
    }

    /**
     * Initializes the general trip helper.
     *
     */
    #initializeGeneralTripHelper() {
        const summary = document.getElementById(this.#prefix + "-summary");
        const tag = document.getElementById(this.#prefix + "-travel-tag");
        const from = document.getElementById(this.#prefix + "-travel-from");
        const directionButtons = Array.from(document.getElementsByClassName(this.#prefix + "-travel-direction"))
        const to = document.getElementById(this.#prefix + "-travel-to");
        const helper = this;
        const updateSummary = function () {
            let direction;
            for (const directionButton of directionButtons) {
                if (directionButton.classList.contains("btn-primary")) {
                    direction = directionButton.dataset.arrow;
                    break;
                }
            }
            summary.value = tag.value + "—" + from.value + direction + to.value;
        };
        this.#initializeTagButtons("travel", tag, updateSummary);
        tag.onchange = function () {
            helper.#onTagInputChange("travel", tag, updateSummary);
            helper.#validateGeneralTripTag();
        };
        from.onchange = function () {
            updateSummary();
            helper.#validateGeneralTripFrom();
        };
        for (const directionButton of directionButtons) {
            directionButton.onclick = function () {
                for (const otherButton of directionButtons) {
                    otherButton.classList.remove("btn-primary");
                    otherButton.classList.add("btn-outline-primary");
                }
                directionButton.classList.remove("btn-outline-primary");
                directionButton.classList.add("btn-primary");
                updateSummary();
            };
        }
        to.onchange = function () {
            updateSummary();
            helper.#validateGeneralTripTo();
        };
    }

    /**
     * Initializes the bus trip helper.
     *
     */
    #initializeBusTripHelper() {
        const summary = document.getElementById(this.#prefix + "-summary");
        const tag = document.getElementById(this.#prefix + "-bus-tag");
        const route = document.getElementById(this.#prefix + "-bus-route");
        const from = document.getElementById(this.#prefix + "-bus-from");
        const to = document.getElementById(this.#prefix + "-bus-to");
        const helper = this;
        const updateSummary = function () {
            summary.value = tag.value + "—" + route.value + "—" + from.value + "→" + to.value;
        };
        this.#initializeTagButtons("bus", tag, updateSummary);
        tag.onchange = function () {
            helper.#onTagInputChange("bus", tag, updateSummary);
            helper.#validateBusTripTag();
        };
        route.onchange = function () {
            updateSummary();
            helper.#validateBusTripRoute();
        };
        from.onchange = function () {
            updateSummary();
            helper.#validateBusTripFrom();
        };
        to.onchange = function () {
            updateSummary();
            helper.#validateBusTripTo();
        };
    }

    /**
     * Initializes the tag buttons.
     *
     * @param tabId {string} the tab ID
     * @param tag {HTMLInputElement} the tag input
     * @param updateSummary {function(): void} the callback to update the summary
     */
    #initializeTagButtons(tabId, tag, updateSummary) {
        const tagButtons = Array.from(document.getElementsByClassName(this.#prefix + "-" + tabId + "-btn-tag"));
        const helper = this;
        for (const tagButton of tagButtons) {
            tagButton.onclick = function () {
                for (const otherButton of tagButtons) {
                    otherButton.classList.remove("btn-primary");
                    otherButton.classList.add("btn-outline-primary");
                }
                tagButton.classList.remove("btn-outline-primary");
                tagButton.classList.add("btn-primary");
                tag.value = tagButton.dataset.value;
                helper.#filterSuggestedAccounts(tagButton);
                updateSummary();
            };
        }
    }

    /**
     * The callback when the tag input is changed.
     *
     * @param tabId {string} the tab ID
     * @param tag {HTMLInputElement} the tag input
     * @param updateSummary {function(): void} the callback to update the summary
     */
    #onTagInputChange(tabId, tag, updateSummary) {
        const tagButtons = Array.from(document.getElementsByClassName(this.#prefix + "-" + tabId + "-btn-tag"));
        let isMatched = false;
        for (const tagButton of tagButtons) {
            if (tagButton.dataset.value === tag.value) {
                tagButton.classList.remove("btn-outline-primary");
                tagButton.classList.add("btn-primary");
                this.#filterSuggestedAccounts(tagButton);
                isMatched = true;
            } else {
                tagButton.classList.remove("btn-primary");
                tagButton.classList.add("btn-outline-primary");
            }
        }
        if (!isMatched) {
            this.#filterSuggestedAccounts(null);
        }
        updateSummary();
    }

    /**
     * Filters the suggested accounts.
     *
     * @param tagButton {HTMLButtonElement|null} the tag button
     */
    #filterSuggestedAccounts(tagButton) {
        const accountButtons = Array.from(document.getElementsByClassName(this.#prefix + "-account"));
        if (tagButton === null) {
            for (const accountButton of accountButtons) {
                accountButton.classList.add("d-none");
                accountButton.classList.remove("btn-primary");
                accountButton.classList.add("btn-outline-primary");
                this.#selectAccount(null);
            }
            return;
        }
        const suggested = JSON.parse(tagButton.dataset.accounts);
        for (const accountButton of accountButtons) {
            if (suggested.includes(accountButton.dataset.code)) {
                accountButton.classList.remove("d-none");
            } else {
                accountButton.classList.add("d-none");
            }
            this.#selectAccount(suggested[0]);
        }
    }

    /**
     * Initializes the number helper.
     *
     */
    #initializeNumberHelper() {
        const summary = document.getElementById(this.#prefix + "-summary");
        const number = document.getElementById(this.#prefix + "-number");
        number.onchange = function () {
            const found = summary.value.match(/^(.+)×(\d+)$/);
            if (found !== null) {
                summary.value = found[1];
            }
            if (number.value > 1) {
                summary.value = summary.value + "×" + String(number.value);
            }
        };
    }

    /**
     * Initializes the suggested accounts.
     *
     */
    #initializeSuggestedAccounts() {
        const accountButtons = Array.from(document.getElementsByClassName(this.#prefix + "-account"));
        const helper = this;
        for (const accountButton of accountButtons) {
            accountButton.onclick = function () {
                helper.#selectAccount(accountButton.dataset.code);
            };
        }
    }

    /**
     * Select a suggested account.
     *
     * @param selectedCode {string|null} the account code, or null to deselect the account
     */
    #selectAccount(selectedCode) {
        const form = document.getElementById(this.#prefix);
        if (selectedCode === null) {
            form.dataset.selectedAccountCode = "";
            form.dataset.selectedAccountText = "";
            return;
        }
        const accountButtons = Array.from(document.getElementsByClassName(this.#prefix + "-account"));
        for (const accountButton of accountButtons) {
            if (accountButton.dataset.code === selectedCode) {
                accountButton.classList.remove("btn-outline-primary");
                accountButton.classList.add("btn-primary");
                form.dataset.selectedAccountCode = accountButton.dataset.code;
                form.dataset.selectedAccountText = accountButton.dataset.text;
            } else {
                accountButton.classList.remove("btn-primary");
                accountButton.classList.add("btn-outline-primary");
            }
        }
    }

    /**
     * Initializes the summary submission
     *
     */
    #initializeSubmission() {
        const form = document.getElementById(this.#prefix);
        const helper = this;
        form.onsubmit = function () {
            if (helper.#validate()) {
                helper.#submit();
            }
            return false;
        };
    }

    /**
     * Validates the form.
     *
     * @return {boolean} true if valid, or false otherwise
     */
    #validate() {
        const tabs = Array.from(document.getElementsByClassName(this.#prefix + "-tab"));
        let isValid = true;
        for (const tab of tabs) {
            if (tab.classList.contains("active")) {
                switch (tab.dataset.tabId) {
                    case "general":
                        isValid = this.#validateGeneralTag() && isValid;
                        break;
                    case "travel":
                        isValid = this.#validateGeneralTrip() && isValid;
                        break;
                    case "bus":
                        isValid = this.#validateBusTrip() && isValid;
                        break;
                }
            }
        }
        return isValid;
    }

    /**
     * Validates a general tag.
     *
     * @return {boolean} true if valid, or false otherwise
     */
    #validateGeneralTag() {
        const field = document.getElementById(this.#prefix + "-general-tag");
        const error = document.getElementById(this.#prefix + "-general-tag-error");
        field.value = field.value.trim();
        field.classList.remove("is-invalid");
        error.innerText = "";
        return true;
    }

    /**
     * Validates a general trip.
     *
     * @return {boolean} true if valid, or false otherwise
     */
    #validateGeneralTrip() {
        let isValid = true;
        isValid = this.#validateGeneralTripTag() && isValid;
        isValid = this.#validateGeneralTripFrom() && isValid;
        isValid = this.#validateGeneralTripTo() && isValid;
        return isValid;
    }

    /**
     * Validates the tag of a general trip.
     *
     * @return {boolean} true if valid, or false otherwise
     */
    #validateGeneralTripTag() {
        const field = document.getElementById(this.#prefix + "-travel-tag");
        const error = document.getElementById(this.#prefix + "-travel-tag-error");
        field.value = field.value.trim();
        if (field.value === "") {
            field.classList.add("is-invalid");
            error.innerText = A_("Please fill in the tag.");
            return false;
        }
        field.classList.remove("is-invalid");
        error.innerText = "";
        return true;
    }

    /**
     * Validates the origin of a general trip.
     *
     * @return {boolean} true if valid, or false otherwise
     */
    #validateGeneralTripFrom() {
        const field = document.getElementById(this.#prefix + "-travel-from");
        const error = document.getElementById(this.#prefix + "-travel-from-error");
        field.value = field.value.trim();
        if (field.value === "") {
            field.classList.add("is-invalid");
            error.innerText = A_("Please fill in the origin.");
            return false;
        }
        field.classList.remove("is-invalid");
        error.innerText = "";
        return true;
    }

    /**
     * Validates the destination of a general trip.
     *
     * @return {boolean} true if valid, or false otherwise
     */
    #validateGeneralTripTo() {
        const field = document.getElementById(this.#prefix + "-travel-to");
        const error = document.getElementById(this.#prefix + "-travel-to-error");
        field.value = field.value.trim();
        if (field.value === "") {
            field.classList.add("is-invalid");
            error.innerText = A_("Please fill in the destination.");
            return false;
        }
        field.classList.remove("is-invalid");
        error.innerText = "";
        return true;
    }

    /**
     * Validates a bus trip.
     *
     * @return {boolean} true if valid, or false otherwise
     */
    #validateBusTrip() {
        let isValid = true;
        isValid = this.#validateBusTripTag() && isValid;
        isValid = this.#validateBusTripRoute() && isValid;
        isValid = this.#validateBusTripFrom() && isValid;
        isValid = this.#validateBusTripTo() && isValid;
        return isValid;
    }

    /**
     * Validates the tag of a bus trip.
     *
     * @return {boolean} true if valid, or false otherwise
     */
    #validateBusTripTag() {
        const field = document.getElementById(this.#prefix + "-bus-tag");
        const error = document.getElementById(this.#prefix + "-bus-tag-error");
        field.value = field.value.trim();
        if (field.value === "") {
            field.classList.add("is-invalid");
            error.innerText = A_("Please fill in the tag.");
            return false;
        }
        field.classList.remove("is-invalid");
        error.innerText = "";
        return true;
    }

    /**
     * Validates the route of a bus trip.
     *
     * @return {boolean} true if valid, or false otherwise
     */
    #validateBusTripRoute() {
        const field = document.getElementById(this.#prefix + "-bus-route");
        const error = document.getElementById(this.#prefix + "-bus-route-error");
        field.value = field.value.trim();
        if (field.value === "") {
            field.classList.add("is-invalid");
            error.innerText = A_("Please fill in the route.");
            return false;
        }
        field.classList.remove("is-invalid");
        error.innerText = "";
        return true;
    }

    /**
     * Validates the origin of a bus trip.
     *
     * @return {boolean} true if valid, or false otherwise
     */
    #validateBusTripFrom() {
        const field = document.getElementById(this.#prefix + "-bus-from");
        const error = document.getElementById(this.#prefix + "-bus-from-error");
        field.value = field.value.trim();
        if (field.value === "") {
            field.classList.add("is-invalid");
            error.innerText = A_("Please fill in the origin.");
            return false;
        }
        field.classList.remove("is-invalid");
        error.innerText = "";
        return true;
    }

    /**
     * Validates the destination of a bus trip.
     *
     * @return {boolean} true if valid, or false otherwise
     */
    #validateBusTripTo() {
        const field = document.getElementById(this.#prefix + "-bus-to");
        const error = document.getElementById(this.#prefix + "-bus-to-error");
        field.value = field.value.trim();
        if (field.value === "") {
            field.classList.add("is-invalid");
            error.innerText = A_("Please fill in the destination.");
            return false;
        }
        field.classList.remove("is-invalid");
        error.innerText = "";
        return true;
    }

    /**
     * Submits the summary.
     *
     */
    #submit() {
        const form = document.getElementById(this.#prefix);
        const summary = document.getElementById(this.#prefix + "-summary");
        const formSummaryControl = document.getElementById("accounting-entry-form-summary-control");
        const formSummary = document.getElementById("accounting-entry-form-summary");
        const formAccountControl = document.getElementById("accounting-entry-form-account-control");
        const formAccount = document.getElementById("accounting-entry-form-account");
        const helperModal = document.getElementById(this.#prefix + "-modal");
        const entryModal = document.getElementById("accounting-entry-form-modal");
        if (summary.value === "") {
            formSummaryControl.classList.remove("accounting-not-empty");
        } else {
            formSummaryControl.classList.add("accounting-not-empty");
        }
        if (form.dataset.selectedAccountCode !== "") {
            formAccountControl.classList.add("accounting-not-empty");
            formAccount.dataset.code = form.dataset.selectedAccountCode;
            formAccount.dataset.text = form.dataset.selectedAccountText;
            formAccount.innerText = form.dataset.selectedAccountText;
        }
        formSummary.dataset.value = summary.value;
        formSummary.innerText = summary.value;
        bootstrap.Modal.getInstance(helperModal).hide();
        bootstrap.Modal.getOrCreateInstance(entryModal).show();
    }

    /**
     * Initializes the summary helper when it is shown.
     *
     * @param isNew {boolean} true for adding a new journal entry, or false otherwise
     */
    initShow(isNew) {
        const formSummary = document.getElementById("accounting-entry-form-summary");
        const summary = document.getElementById(this.#prefix + "-summary");
        const closeButtons = Array.from(document.getElementsByClassName(this.#prefix + "-close"));
        for (const closeButton of closeButtons) {
            if (isNew) {
                closeButton.dataset.bsTarget = "#" + this.#prefix + "-modal";
            } else {
                closeButton.dataset.bsTarget = "#accounting-entry-form-modal";
            }
        }
        this.#reset();
        if (!isNew) {
            summary.value = formSummary.dataset.value;
            this.#parseAndPopulate();
        }
    }

    /**
     * Resets the summary helper.
     *
     */
    #reset() {
        const inputs = Array.from(document.getElementsByClassName(this.#prefix + "-input"));
        const tagButtons = Array.from(document.getElementsByClassName(this.#prefix + "-btn-tag"));
        const directionButtons = Array.from(document.getElementsByClassName(this.#prefix + "-travel-direction"));
        for (const input of inputs) {
            input.value = "";
            input.classList.remove("is-invalid");
        }
        for (const tagButton of tagButtons) {
            tagButton.classList.remove("btn-primary");
            tagButton.classList.add("btn-outline-primary");
        }
        for (const directionButton of directionButtons) {
            if (directionButton.classList.contains("accounting-default")) {
                directionButton.classList.remove("btn-outline-primary");
                directionButton.classList.add("btn-primary");
            } else {
                directionButton.classList.add("btn-outline-primary");
                directionButton.classList.remove("btn-primary");
            }
        }
        this.#filterSuggestedAccounts(null);
        this.#switchToTab(this.#defaultTabId);
    }

    /**
     * Parses the summary input and populates the summary helper.
     *
     */
    #parseAndPopulate() {
        const summary = document.getElementById(this.#prefix + "-summary");
        const pos = summary.value.indexOf("—");
        if (pos === -1) {
            return;
        }
        let found;
        found = summary.value.match(/^([^—]+)—([^—]+)—([^—→]+)→(.+?)(?:×(\d+))?$/);
        if (found !== null) {
            return this.#populateBusTrip(found[1], found[2], found[3], found[4], found[5]);
        }
        found = summary.value.match(/^([^—]+)—([^—→↔]+)([→↔])(.+?)(?:×(\d+))?$/);
        if (found !== null) {
            return this.#populateGeneralTrip(found[1], found[2], found[3], found[4], found[5]);
        }
        found = summary.value.match(/^([^—]+)—.+?(?:×(\d+)?)?$/);
        if (found !== null) {
            return this.#populateGeneralTag(found[1], found[2]);
        }
    }

    /**
     * Populates a bus trip.
     *
     * @param tagName {string} the tag name
     * @param routeName {string} the route name or route number
     * @param fromName {string} the name of the origin
     * @param toName {string} the name of the destination
     * @param numberStr {string|undefined} the number of items, if any
     */
    #populateBusTrip(tagName, routeName, fromName, toName, numberStr) {
        const tag = document.getElementById(this.#prefix + "-bus-tag");
        const route = document.getElementById(this.#prefix + "-bus-route");
        const from = document.getElementById(this.#prefix + "-bus-from");
        const to = document.getElementById(this.#prefix + "-bus-to");
        const number = document.getElementById(this.#prefix + "-number");
        const tagButtons = Array.from(document.getElementsByClassName(this.#prefix + "-bus-btn-tag"));
        tag.value = tagName;
        route.value = routeName;
        from.value = fromName;
        to.value = toName;
        if (numberStr !== undefined) {
            number.value = parseInt(numberStr);
        }
        for (const tagButton of tagButtons) {
            if (tagButton.dataset.value === tagName) {
                tagButton.classList.remove("btn-outline-primary");
                tagButton.classList.add("btn-primary");
                this.#filterSuggestedAccounts(tagButton);
            }
        }
        this.#switchToTab("bus");
    }

    /**
     * Populates a general trip.
     *
     * @param tagName {string} the tag name
     * @param fromName {string} the name of the origin
     * @param direction {string} the direction arrow, either "→" or "↔"
     * @param toName {string} the name of the destination
     * @param numberStr {string|undefined} the number of items, if any
     */
    #populateGeneralTrip(tagName, fromName, direction, toName, numberStr) {
        const tag = document.getElementById(this.#prefix + "-travel-tag");
        const from = document.getElementById(this.#prefix + "-travel-from");
        const to = document.getElementById(this.#prefix + "-travel-to");
        const number = document.getElementById(this.#prefix + "-number");
        const tagButtons = Array.from(document.getElementsByClassName(this.#prefix + "-travel-btn-tag"));
        const directionButtons = Array.from(document.getElementsByClassName(this.#prefix + "-travel-direction"));
        tag.value = tagName;
        from.value = fromName;
        for (const directionButton of directionButtons) {
            if (directionButton.dataset.arrow === direction) {
                directionButton.classList.remove("btn-outline-primary");
                directionButton.classList.add("btn-primary");
            } else {
                directionButton.classList.add("btn-outline-primary");
                directionButton.classList.remove("btn-primary");
            }
        }
        to.value = toName;
        if (numberStr !== undefined) {
            number.value = parseInt(numberStr);
        }
        for (const tagButton of tagButtons) {
            if (tagButton.dataset.value === tagName) {
                tagButton.classList.remove("btn-outline-primary");
                tagButton.classList.add("btn-primary");
                this.#filterSuggestedAccounts(tagButton);
            }
        }
        this.#switchToTab("travel");
    }

    /**
     * Populates a general tag.
     *
     * @param tagName {string} the tag name
     * @param numberStr {string|undefined} the number of items, if any
     */
    #populateGeneralTag(tagName, numberStr) {
        const tag = document.getElementById(this.#prefix + "-general-tag");
        const number = document.getElementById(this.#prefix + "-number");
        const tagButtons = Array.from(document.getElementsByClassName(this.#prefix + "-general-btn-tag"));
        tag.value = tagName;
        if (numberStr !== undefined) {
            number.value = parseInt(numberStr);
        }
        for (const tagButton of tagButtons) {
            if (tagButton.dataset.value === tagName) {
                tagButton.classList.remove("btn-outline-primary");
                tagButton.classList.add("btn-primary");
                this.#filterSuggestedAccounts(tagButton);
            }
        }
        this.#switchToTab("general");
    }

    /**
     * The summary helpers.
     * @type {{debit: SummaryHelper, credit: SummaryHelper}}
     */
    static #helpers = {}

    /**
     * Initializes the summary helpers.
     *
     */
    static initialize() {
        const forms = Array.from(document.getElementsByClassName("accounting-summary-helper"));
        for (const form of forms) {
            const helper = new SummaryHelper(form);
            this.#helpers[helper.#entryType] = helper;
        }
        this.#initializeTransactionForm();
    }

    /**
     * Initializes the transaction form.
     *
     */
    static #initializeTransactionForm() {
        const entryForm = document.getElementById("accounting-entry-form");
        const formSummaryControl = document.getElementById("accounting-entry-form-summary-control");
        const helpers = this.#helpers;
        formSummaryControl.onclick = function () {
            helpers[entryForm.dataset.entryType].initShow(false);
        };
    }

    /**
     * Initializes the summary helper for a new journal entry.
     *
     * @param entryType {string} the entry type, either "debit" or "credit"
     */
    static initializeNewJournalEntry(entryType) {
        this.#helpers[entryType].initShow(true);
    }
}
