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
     * The entry type
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
        const tabs = Array.from(document.getElementsByClassName(this.#prefix + "-tab"));
        tabs.forEach(function (tab) {
            tab.onclick = function () {
                helper.#switchToTab(tab.dataset.tabId);
            }
        });
        this.#initializeGeneralTagHelper();
        this.#initializeGeneralTripHelper();
        this.#initializeBusTripHelper();
        this.#initializeNumberHelper();
        this.#initializeSubmission();
    }

    /**
     * Switches to a tab.
     *
     * @param tabId {string} the tab ID.
     */
    #switchToTab(tabId) {
        const tabs = Array.from(document.getElementsByClassName(this.#prefix + "-tab"));
        const pages = Array.from(document.getElementsByClassName(this.#prefix + "-page"));
        tabs.forEach(function (tab) {
            if (tab.dataset.tabId === tabId) {
                tab.classList.add("active");
                tab.ariaCurrent = "page";
            } else {
                tab.classList.remove("active");
                tab.ariaCurrent = "false";
            }
        });
        pages.forEach(function (page) {
            if (page.dataset.tabId === tabId) {
                page.classList.remove("d-none");
                page.ariaCurrent = "page";
            } else {
                page.classList.add("d-none");
                page.ariaCurrent = "false";
            }
        });
    }

    /**
     * Initializes the general tag helper.
     *
     */
    #initializeGeneralTagHelper() {
        const buttons = Array.from(document.getElementsByClassName(this.#prefix + "-general-btn-tag"));
        const summary = document.getElementById(this.#prefix + "-summary");
        const tag = document.getElementById(this.#prefix + "-general-tag");
        const updateSummary = function () {
            const pos = summary.value.indexOf("—");
            const prefix = tag.value === ""? "": tag.value + "—";
            if (pos === -1) {
                summary.value = prefix + summary.value;
            } else {
                summary.value = prefix + summary.value.substring(pos + 1);
            }
        }
        buttons.forEach(function (button) {
            button.onclick = function () {
                buttons.forEach(function (otherButton) {
                    otherButton.classList.remove("btn-primary");
                    otherButton.classList.add("btn-outline-primary");
                });
                button.classList.remove("btn-outline-primary");
                button.classList.add("btn-primary");
                tag.value = button.dataset.value;
                updateSummary();
            };
        });
        tag.onchange = function () {
            buttons.forEach(function (button) {
                if (button.dataset.value === tag.value) {
                    button.classList.remove("btn-outline-primary");
                    button.classList.add("btn-primary");
                } else {
                    button.classList.remove("btn-primary");
                    button.classList.add("btn-outline-primary");
                }
            });
            updateSummary();
        };
    }

    /**
     * Initializes the general trip helper.
     *
     */
    #initializeGeneralTripHelper() {
        const buttons = Array.from(document.getElementsByClassName(this.#prefix + "-travel-btn-tag"));
        const summary = document.getElementById(this.#prefix + "-summary");
        const tag = document.getElementById(this.#prefix + "-travel-tag");
        const from = document.getElementById(this.#prefix + "-travel-from");
        const directionButtons = Array.from(document.getElementsByClassName(this.#prefix + "-travel-direction"))
        const to = document.getElementById(this.#prefix + "-travel-to");
        const helper = this;
        const updateSummary = function () {
            let direction;
            for (const button of directionButtons) {
                if (button.classList.contains("btn-primary")) {
                    direction = button.dataset.arrow;
                    break;
                }
            }
            summary.value = tag.value + "—" + from.value + direction + to.value;
        };
        buttons.forEach(function (button) {
            button.onclick = function () {
                buttons.forEach(function (otherButton) {
                    otherButton.classList.remove("btn-primary");
                    otherButton.classList.add("btn-outline-primary");
                });
                button.classList.remove("btn-outline-primary");
                button.classList.add("btn-primary");
                tag.value = button.dataset.value;
                updateSummary();
            };
        });
        tag.onchange = function () {
            buttons.forEach(function (button) {
                if (button.dataset.value === tag.value) {
                    button.classList.remove("btn-outline-primary");
                    button.classList.add("btn-primary");
                } else {
                    button.classList.remove("btn-primary");
                    button.classList.add("btn-outline-primary");
                }
            });
            updateSummary();
            helper.#validateGeneralTripTag();
        };
        from.onchange = function () {
            updateSummary();
            helper.#validateGeneralTripFrom();
        };
        directionButtons.forEach(function (button) {
            button.onclick = function () {
                directionButtons.forEach(function (otherButton) {
                    otherButton.classList.remove("btn-primary");
                    otherButton.classList.add("btn-outline-primary");
                });
                button.classList.remove("btn-outline-primary");
                button.classList.add("btn-primary");
                updateSummary();
            };
        });
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
        const buttons = Array.from(document.getElementsByClassName(this.#prefix + "-bus-btn-tag"));
        const summary = document.getElementById(this.#prefix + "-summary");
        const tag = document.getElementById(this.#prefix + "-bus-tag");
        const route = document.getElementById(this.#prefix + "-bus-route");
        const from = document.getElementById(this.#prefix + "-bus-from");
        const to = document.getElementById(this.#prefix + "-bus-to");
        const helper = this;
        const updateSummary = function () {
            summary.value = tag.value + "—" + route.value + "—" + from.value + "→" + to.value;
        };
        buttons.forEach(function (button) {
            button.onclick = function () {
                buttons.forEach(function (otherButton) {
                    otherButton.classList.remove("btn-primary");
                    otherButton.classList.add("btn-outline-primary");
                });
                button.classList.remove("btn-outline-primary");
                button.classList.add("btn-primary");
                tag.value = button.dataset.value;
                updateSummary();
            };
        });
        tag.onchange = function () {
            buttons.forEach(function (button) {
                if (button.dataset.value === tag.value) {
                    button.classList.remove("btn-outline-primary");
                    button.classList.add("btn-primary");
                } else {
                    button.classList.remove("btn-primary");
                    button.classList.add("btn-outline-primary");
                }
            });
            updateSummary();
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
        const summary = document.getElementById(this.#prefix + "-summary");
        const formSummaryControl = document.getElementById("accounting-entry-form-summary-control");
        const formSummary = document.getElementById("accounting-entry-form-summary");
        const helperModal = document.getElementById(this.#prefix + "-modal");
        const entryModal = document.getElementById("accounting-entry-form-modal");
        if (summary.value === "") {
            formSummaryControl.classList.remove("accounting-not-empty");
        } else {
            formSummaryControl.classList.add("accounting-not-empty");
        }
        formSummary.dataset.value = summary.value;
        formSummary.innerText = summary.value;
        bootstrap.Modal.getInstance(helperModal).hide();
        bootstrap.Modal.getOrCreateInstance(entryModal).show();
    }

    /**
     * Initializes the summary help when it is shown.
     *
     * @param isNew {boolean} true for adding a new journal entry, or false otherwise
     */
    initShow(isNew) {
        const closeButtons = Array.from(document.getElementsByClassName(this.#prefix + "-close"));
        closeButtons.forEach(function (button) {
            if (isNew) {
                button.dataset.bsTarget = "";
            } else {
                button.dataset.bsTarget = "#accounting-entry-form-modal";
            }
        });
        this.#reset();
        if (!isNew) {
            this.#populate();
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
        inputs.forEach(function (input) {
            input.value = "";
            input.classList.remove("is-invalid");
        });
        tagButtons.forEach(function (button) {
            button.classList.remove("btn-primary");
            button.classList.add("btn-outline-primary");
        });
        directionButtons.forEach(function (button) {
            if (button.classList.contains("accounting-default")) {
                button.classList.remove("btn-outline-primary");
                button.classList.add("btn-primary");
            } else {
                button.classList.add("btn-outline-primary");
                button.classList.remove("btn-primary");
            }
        });
        this.#switchToTab(this.#defaultTabId);
    }

    /**
     * Populates the summary helper from the journal entry form.
     *
     */
    #populate() {
        const formSummary = document.getElementById("accounting-entry-form-summary");
        const summary = document.getElementById(this.#prefix + "-summary");
        summary.value = formSummary.dataset.value;
        const pos = summary.value.indexOf("—");
        if (pos === -1) {
            return;
        }
        let found;
        found = summary.value.match(/^(.+?)—(.+?)—(.+?)→(.+?)(?:×(\d+)?)?$/);
        if (found !== null) {
            return this.#populateBusTrip(found[1], found[2], found[3], found[4], found[5]);
        }
        found = summary.value.match(/^(.+?)—(.+?)([→↔])(.+?)(?:×(\d+)?)?$/);
        if (found !== null) {
            return this.#populateGeneralTrip(found[1], found[2], found[3], found[4], found[5]);
        }
        found = summary.value.match(/^(.+?)—.+?(?:×(\d+)?)?$/);
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
        const buttons = Array.from(document.getElementsByClassName(this.#prefix + "-bus-btn-tag"));
        tag.value = tagName;
        route.value = routeName;
        from.value = fromName;
        to.value = toName;
        if (numberStr !== undefined) {
            number.value = parseInt(numberStr);
        }
        buttons.forEach(function (button) {
            if (button.dataset.value === tagName) {
                button.classList.remove("btn-outline-primary");
                button.classList.add("btn-primary");
            }
        });
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
        const buttons = Array.from(document.getElementsByClassName(this.#prefix + "-travel-btn-tag"));
        const directionButtons = Array.from(document.getElementsByClassName(this.#prefix + "-travel-direction"));
        tag.value = tagName;
        from.value = fromName;
        directionButtons.forEach(function (btnDirection) {
            if (btnDirection.dataset.arrow === direction) {
                btnDirection.classList.remove("btn-outline-primary");
                btnDirection.classList.add("btn-primary");
            } else {
                btnDirection.classList.add("btn-outline-primary");
                btnDirection.classList.remove("btn-primary");
            }
        });
        to.value = toName;
        if (numberStr !== undefined) {
            number.value = parseInt(numberStr);
        }
        buttons.forEach(function (button) {
            if (button.dataset.value === tagName) {
                button.classList.remove("btn-outline-primary");
                button.classList.add("btn-primary");
            }
        });
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
        const buttons = Array.from(document.getElementsByClassName(this.#prefix + "-general-btn-tag"));
        tag.value = tagName;
        if (numberStr !== undefined) {
            number.value = parseInt(numberStr);
        }
        buttons.forEach(function (button) {
            if (button.dataset.value === tagName) {
                button.classList.remove("btn-outline-primary");
                button.classList.add("btn-primary");
            }
        });
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
