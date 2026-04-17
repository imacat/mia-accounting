/* The Mia! Accounting Project
 * base-combobox.js: The JavaScript for the base abstract combobox
 */

/*  Copyright (c) 2026 imacat.
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
 * First written: 2026/4/16
 */
"use strict";

/**
 * The base abstract combobox.
 *
 * @abstract
 * @template {BaseOption} T
 */
class BaseCombobox {

    /**
     * The query input
     * @type {HTMLInputElement}
     */
    query;

    /**
     * The options
     * @type {T[]}
     */
    options;

    /**
     * The options that are shown
     * @type {T[]}
     */
    shownOptions;

    /**
     * Constructs a base abstract combobox.
     *
     * @param query {HTMLInputElement} the query input
     * @param options {T[]} the options
     */
    constructor(query, options) {
        this.query = query;
        this.query.oninput = () => this.filterOptions();
        this.query.onkeydown = this.onQueryKeyDown.bind(this);
        this.options = options;
        this.shownOptions = [];
    }

    /**
     * Actions when keys are pressed on the query input.
     *
     * @param event {KeyboardEvent} the key event
     */
    onQueryKeyDown(event) {
        if (this.shownOptions.length === 0) {
            return;
        }
        const currentID = this.query.getAttribute("aria-activedescendant");
        const currentIndex = this.shownOptions.findIndex((option) => option.elementID === currentID);

        let newIndex;
        switch (event.key) {
            case "ArrowUp":
                if (currentIndex === -1) {
                    newIndex = this.shownOptions.length - 1;
                } else {
                    newIndex = (currentIndex - 1 + this.shownOptions.length) % this.shownOptions.length;
                }
                break;
            case "ArrowDown":
                if (currentIndex === -1) {
                    newIndex = 0;
                } else {
                    newIndex = (currentIndex + 1) % this.shownOptions.length;
                }
                break;
            case "Home":
                if (this.query.value !== "") {
                    return;
                }
                newIndex = 0;
                break;
            case "End":
                if (this.query.value !== "") {
                    return;
                }
                newIndex = this.shownOptions.length - 1;
                break;
            case "PageUp":
                if (currentIndex === -1) {
                    newIndex = this.shownOptions.length - 1;
                } else {
                    newIndex = Math.max(currentIndex - 10, 0);
                }
                break;
            case "PageDown":
                if (currentIndex === -1) {
                    newIndex = 0;
                } else {
                    newIndex = Math.min(currentIndex + 10, this.shownOptions.length - 1);
                }
                break;
            case "Enter":
                event.preventDefault();
                if (currentIndex !== -1) {
                    this.shownOptions[currentIndex].click();
                }
                return;
            case "Escape":
                if (this.query.value !== "") {
                    event.preventDefault();
                    event.stopPropagation();
                    this.query.value = "";
                    this.filterOptions();
                }
                return;
            default:
                return;
        }
        event.preventDefault();
        this.selectOption(this.shownOptions[newIndex]);
    }

    /**
     * Filters the options.
     *
     * @abstract
     */
    filterOptions() {
        throw new Error("Method not implemented");
    }

    /**
     * Selects an option.
     *
     * @param option {T|undefined} the option.
     */
    selectOption(option) {
        this.options.forEach((opt) => opt.setActive(false));
        if (option === undefined) {
            return;
        }
        option.setActive(true);
        this.query.setAttribute("aria-activedescendant", option.elementID);
        option.scrollIntoView();
    }
}

/**
 * The base abstract option
 *
 * @abstract
 */
class BaseOption {

    /**
     * The element
     * @type {HTMLLIElement}
     */
    #element;

    /**
     * The element ID
     * @type {string}
     */
    elementID;

    /**
     * Constructs the base abstract option.
     *
     * @param element {HTMLLIElement} the element
     */
    constructor(element) {
        this.#element = element;
        this.elementID = element.id;
    }

    /**
     * Sets whether the option is shown.
     *
     * @param isShown {boolean} true to show, or false otherwise
     */
    setShown(isShown) {
        if (isShown) {
            this.#element.classList.remove("d-none");
        } else {
            this.#element.classList.add("d-none");
        }
    }

    /**
     * Sets whether the option is active.
     *
     * @param isActive {boolean} true if active, or false otherwise
     */
    setActive(isActive) {
        if (isActive) {
            this.#element.classList.add("active");
            this.#element.ariaSelected = "true";
        } else {
            this.#element.classList.remove("active");
            this.#element.ariaSelected = "false";
        }
    }

    /**
     * Clicks the option.
     *
     */
    click() {
        this.#element.click();
    }

    /**
     * Scrolls the option into view.
     *
     */
    scrollIntoView() {
        this.#element.scrollIntoView({block: "nearest"});
    }
}
