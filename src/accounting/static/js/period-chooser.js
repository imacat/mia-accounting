/* The Mia! Accounting Project
 * period-chooser.js: The JavaScript for the period chooser
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
 * First written: 2023/3/4
 */
"use strict";

// Initializes the page JavaScript.
document.addEventListener("DOMContentLoaded", () => {
    PeriodChooser.initialize();
});

/**
 * The period chooser.
 *
 */
class PeriodChooser {

    /**
     * The modal of the period chooser
     * @type {HTMLDivElement}
     */
    modal;

    /**
     * The tab planes
     * @type {{month: MonthTab, year: YearTab, day: DayTab, custom: CustomTab}}
     */
    tabPlanes = {};

    /**
     * Constructs the period chooser.
     *
     */
    constructor() {
        const prefix = "accounting-period-chooser";
        this.modal = document.getElementById(`${prefix}-modal`);
        for (const cls of [MonthTab, YearTab, DayTab, CustomTab]) {
            const tab = new cls(this);
            this.tabPlanes[tab.tabId()] = tab;
        }
    }

    /**
     * The period chooser.
     * @type {PeriodChooser}
     */
    static #chooser;

    /**
     * Initializes the period chooser.
     *
     */
    static initialize() {
        this.#chooser = new PeriodChooser();
    }
}

/**
 * A tab plane.
 *
 * @abstract
 * @private
 */
class TabPlane {

    /**
     * The period chooser
     * @type {PeriodChooser}
     */
    chooser;

    /**
     * The prefix of the HTML ID and class names
     * @type {string}
     */
    prefix;

    /**
     * The tab
     * @type {HTMLSpanElement}
     */
    #tab;

    /**
     * The page
     * @type {HTMLDivElement}
     */
    #page;

    /**
     * Constructs a tab plane.
     *
     * @param chooser {PeriodChooser} the period chooser
     */
    constructor(chooser) {
        this.chooser = chooser;
        this.prefix = `accounting-period-chooser-${this.tabId()}`;
        this.#tab = document.getElementById(`${this.prefix}-tab`);
        this.#page = document.getElementById(`${this.prefix}-page`);
        this.#tab.onclick = () => this.#switchToMe();
    }

    /**
     * The tab ID
     *
     * @return {string}
     * @abstract
     */
    tabId() { throw new Error("Method not implemented.") };

    /**
     * Switches to the tab plane.
     *
     */
    #switchToMe() {
        for (const tabPlane of Object.values(this.chooser.tabPlanes)) {
            tabPlane.#tab.classList.remove("active")
            tabPlane.#tab.ariaCurrent = "false";
            tabPlane.#page.classList.add("d-none");
            tabPlane.#page.ariaCurrent = "false";
        }
        this.#tab.classList.add("active");
        this.#tab.ariaCurrent = "page";
        this.#page.classList.remove("d-none");
        this.#page.ariaCurrent = "page";
    }
}

/**
 * The month tab plane.
 *
 * @private
 */
class MonthTab extends TabPlane {

    /**
     * The month chooser.
     * @type {tempusDominus.TempusDominus}
     */
    #monthChooser

    /**
     * Constructs a tab plane.
     *
     * @param chooser {PeriodChooser} the period chooser
     */
    constructor(chooser) {
        super(chooser);
        const monthChooser = document.getElementById(`${this.prefix}-chooser`);
        if (monthChooser !== null) {
            this.#monthChooser = new tempusDominus.TempusDominus(monthChooser, {
                restrictions: {
                    minDate: new Date(monthChooser.dataset.start),
                },
                display: {
                    inline: true,
                    components: {
                        date: false,
                        clock: false,
                    },
                },
                defaultDate: new Date(monthChooser.dataset.default),
            });
            monthChooser.addEventListener(tempusDominus.Namespace.events.change, (e) => {
                const date = e.detail.date;
                const zeroPaddedMonth = `0${date.month + 1}`.slice(-2)
                const period = `${date.year}-${zeroPaddedMonth}`;
                window.location = chooser.modal.dataset.urlTemplate
                    .replaceAll("PERIOD", period);
            });
        }
    }

    /**
     * The tab ID
     *
     * @return {string}
     */
    tabId() {
        return "month";
    }
}

/**
 * The year tab plane.
 *
 * @private
 */
class YearTab extends TabPlane {

    /**
     * The tab ID
     *
     * @return {string}
     */
    tabId() {
        return "year";
    }
}

/**
 * The day tab plane.
 *
 * @private
 */
class DayTab extends TabPlane {

    /**
     * The day input
     * @type {HTMLInputElement}
     */
    #date;

    /**
     * The error of the date input
     * @type {HTMLDivElement}
     */
    #dateError;

    /**
     * Constructs a tab plane.
     *
     * @param chooser {PeriodChooser} the period chooser
     */
    constructor(chooser) {
        super(chooser);
        this.#date = document.getElementById(`${this.prefix}-date`);
        this.#dateError = document.getElementById(`${this.prefix}-date-error`);
        if (this.#date !== null) {
            this.#date.onchange = () => {
                if (this.#validateDate()) {
                    window.location = chooser.modal.dataset.urlTemplate
                        .replaceAll("PERIOD", this.#date.value);
                }
            };
        }
    }

    /**
     * Validates the date.
     *
     * @return {boolean} true if valid, or false otherwise
     */
    #validateDate() {
        if (this.#date.value === "") {
            this.#date.classList.add("is-invalid");
            this.#dateError.innerText = A_("Please fill in the date.");
            return false;
        }
        if (this.#date.value < this.#date.min) {
            this.#date.classList.add("is-invalid");
            this.#dateError.innerText = A_("The date is too early.");
            return false;
        }
        this.#date.classList.remove("is-invalid");
        this.#dateError.innerText = "";
        return true;
    }

    /**
     * The tab ID
     *
     * @return {string}
     */
    tabId() {
        return "day";
    }
}

/**
 * The custom tab plane.
 *
 * @private
 */
class CustomTab extends TabPlane {

    /**
     * The start of the period
     * @type {HTMLInputElement}
     */
    #start;

    /**
     * The error of the start
     * @type {HTMLDivElement}
     */
    #startError;

    /**
     * The end of the period
     * @type {HTMLInputElement}
     */
    #end;

    /**
     * The error of the end
     * @type {HTMLDivElement}
     */
    #endError;

    /**
     * The confirm button
     * @type {HTMLButtonElement}
     */
    #conform;

    /**
     * Constructs a tab plane.
     *
     * @param chooser {PeriodChooser} the period chooser
     */
    constructor(chooser) {
        super(chooser);
        this.#start = document.getElementById(`${this.prefix}-start`);
        this.#startError = document.getElementById(`${this.prefix}-start-error`);
        this.#end = document.getElementById(`${this.prefix}-end`);
        this.#endError = document.getElementById(`${this.prefix}-end-error`);
        this.#conform = document.getElementById(`${this.prefix}-confirm`);
        if (this.#start !== null) {
            this.#start.onchange = () => {
                if (this.#validateStart()) {
                    this.#end.min = this.#start.value;
                }
            };
            this.#end.onchange = () => {
                if (this.#validateEnd()) {
                    this.#start.max = this.#end.value;
                }
            };
            this.#conform.onclick = () => {
                let isValid = true;
                isValid = this.#validateStart() && isValid;
                isValid = this.#validateEnd() && isValid;
                if (isValid) {
                    window.location = chooser.modal.dataset.urlTemplate
                        .replaceAll("PERIOD", `${this.#start.value}-${this.#end.value}`);
                }
            };
        }
    }

    /**
     * Validates the start of the period.
     *
     * @returns {boolean} true if valid, or false otherwise
     * @private
     */
    #validateStart() {
        if (this.#start.value === "") {
            this.#start.classList.add("is-invalid");
            this.#startError.innerText = A_("Please fill in the start date.");
            return false;
        }
        if (this.#start.value < this.#start.min) {
            this.#start.classList.add("is-invalid");
            this.#startError.innerText = A_("The start date is too early.");
            return false;
        }
        if (this.#start.value > this.#start.max) {
            this.#start.classList.add("is-invalid");
            this.#startError.innerText = A_("The start date cannot be beyond the end date.");
            return false;
        }
        this.#start.classList.remove("is-invalid");
        this.#startError.innerText = "";
        return true;
    }

    /**
     * Validates the end of the period.
     *
     * @returns {boolean} true if valid, or false otherwise
     * @private
     */
    #validateEnd() {
        this.#end.value = this.#end.value.trim();
        if (this.#end.value === "") {
            this.#end.classList.add("is-invalid");
            this.#endError.innerText = A_("Please fill in the end date.");
            return false;
        }
        if (this.#end.value < this.#end.min) {
            this.#end.classList.add("is-invalid");
            this.#endError.innerText = A_("The end date cannot be beyond the start date.");
            return false;
        }
        this.#end.classList.remove("is-invalid");
        this.#endError.innerText = "";
        return true;
    }

    /**
     * The tab ID
     *
     * @return {string}
     */
    tabId() {
        return "custom";
    }
}
