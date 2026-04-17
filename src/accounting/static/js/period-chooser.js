/* The Mia! Accounting Project
 * period-chooser.js: The JavaScript for the period chooser
 */

/*  Copyright (c) 2023-2026 imacat.
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
 * @extends {BaseTablist<BasePeriodTab>}
 * @private
 */
class PeriodChooser extends BaseTablist {

    /**
     * The URL template for different periods.
     * @type {string}
     */
    urlTemplate;

    /**
     * Constructs the period chooser.
     *
     */
    constructor() {
        const prefix = "accounting-period-chooser";
        super(document.getElementById(`${prefix}-tab-list`));
        this.tabs = [new MonthTab(this), new YearTab(this), new DayTab(this), new CustomTab(this)];
        const modal = document.getElementById(`${prefix}-modal`);
        this.urlTemplate = modal.dataset.urlTemplate;
        for (const tab of this.tabs) {
            if (tab.isActive()) {
                this.currentTab = tab;
                break;
            }
        }
    }

    /**
     * @inheritDoc
     * @override
     */
    onTabFocus(tab) { this.switchTo(tab); }

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
 * A base abstract period tab.
 *
 * @abstract
 * @private
 */
class BasePeriodTab extends BaseTab {

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
     * Constructs a base abstract period tab.
     *
     * @param tabID {string} the tab ID
     * @param chooser {PeriodChooser} the period chooser
     */
    constructor(tabID, chooser) {
        const prefix = `accounting-period-chooser-${tabID}`;
        const tab = document.getElementById(`${prefix}-tab`);
        const panel = document.getElementById(`${prefix}-panel`);
        super(tab, panel, chooser.switchTo.bind(chooser));
        this.chooser = chooser;
        this.prefix = prefix;
    }
}

/**
 * The month tab.
 *
 * @private
 */
class MonthTab extends BasePeriodTab {

    /**
     * The month chooser.
     * @type {tempusDominus.TempusDominus}
     */
    #monthChooser

    /**
     * Constructs a month tab.
     *
     * @param chooser {PeriodChooser} the period chooser
     */
    constructor(chooser) {
        super("month", chooser);
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
                window.location = chooser.urlTemplate
                    .replaceAll("PERIOD", period);
            });
        }
    }
}

/**
 * The year tab.
 *
 * @private
 */
class YearTab extends BasePeriodTab {

    /**
     * Constructs a year tab.
     *
     * @param chooser {PeriodChooser} the period chooser
     */
    constructor(chooser) {
        super("year", chooser);
    }
}

/**
 * The day tab.
 *
 * @private
 */
class DayTab extends BasePeriodTab {

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
     * Constructs a day tab.
     *
     * @param chooser {PeriodChooser} the period chooser
     */
    constructor(chooser) {
        super("day", chooser);
        this.#date = document.getElementById(`${this.prefix}-date`);
        this.#dateError = document.getElementById(`${this.prefix}-date-error`);
        if (this.#date !== null) {
            this.#date.onchange = () => {
                if (this.#validateDate()) {
                    window.location = chooser.urlTemplate
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
}

/**
 * The custom tab.
 *
 * @private
 */
class CustomTab extends BasePeriodTab {

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
    #confirm;

    /**
     * Constructs a custom tab.
     *
     * @param chooser {PeriodChooser} the period chooser
     */
    constructor(chooser) {
        super("custom", chooser);
        this.#start = document.getElementById(`${this.prefix}-start`);
        this.#startError = document.getElementById(`${this.prefix}-start-error`);
        this.#end = document.getElementById(`${this.prefix}-end`);
        this.#endError = document.getElementById(`${this.prefix}-end-error`);
        this.#confirm = document.getElementById(`${this.prefix}-confirm`);
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
            this.#confirm.onclick = () => {
                let isValid = true;
                isValid = this.#validateStart() && isValid;
                isValid = this.#validateEnd() && isValid;
                if (isValid) {
                    window.location = chooser.urlTemplate
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
}
