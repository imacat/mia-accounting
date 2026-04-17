/* The Mia! Accounting Project
 * base-tablist.js: The JavaScript for base abstract tablist
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
 * The base abstract tablist.
 *
 * @abstract
 * @template {BaseTab} T
 */
class BaseTablist {

    /**
     * The tabs.
     * @type {T[]}
     */
    tabs;

    /**
     * The current tab.
     * @type {T}
     */
    currentTab;

    /**
     * Constructs a new base abstract tablist.
     *
     * @param tablist {HTMLUListElement} the tab list
     */
    constructor(tablist) {
        tablist.onkeydown = this.onTabKeyDown.bind(this);
    }

    /**
     * Actions when keys are pressed on the tabs.
     *
     * @param event {KeyboardEvent} the key event
     */
    onTabKeyDown(event) {
        const currentIndex = this.tabs.indexOf(this.currentTab);
        if (currentIndex === -1) {
            return;
        }

        let newIndex = currentIndex;
        switch (event.key) {
            case "ArrowRight":
                newIndex = (newIndex + 1) % this.tabs.length;
                break;
            case "ArrowLeft":
                newIndex = (newIndex - 1 + this.tabs.length) % this.tabs.length;
                break;
            case "Home":
                newIndex = 0;
                break;
            case "End":
                newIndex = this.tabs.length - 1;
                break;
            default:
                return;
        }
        event.preventDefault();
        this.tabs[newIndex].focus();
        this.onTabFocus(this.tabs[newIndex]);
    }

    /**
     * Actions when a tab is focused.
     *
     * @param tab {T} the tab
     */
    onTabFocus(tab) { /* Do nothing */ }

    /**
     * Switches to a tab.
     *
     * @param tab {T} the tab
     */
    switchTo(tab) {
        this.tabs.forEach(t => t.setActive(t === tab));
        this.currentTab = tab;
        this.currentTab.onActivated();
    }
}

/**
 * The base abstract tab.
 *
 * @abstract
 */
class BaseTab {

    /**
     * The tab element.
     * @type {HTMLButtonElement}
     */
    #tab;

    /**
     * The panel element.
     * @type {HTMLDivElement}
     */
    #panel;

    /**
     * Constructs a new base abstract tab.
     *
     * @param tab {HTMLButtonElement} The tab element.
     * @param panel {HTMLDivElement} The panel element.
     * @param switchTo {function(BaseTab): void} The function to switch to the tab.
     */
    constructor(tab, panel, switchTo) {
        this.#tab = tab;
        this.#panel = panel;
        this.#tab.onclick = () => switchTo(this);
    }

    /**
     * Sets the active state of the tab.
     *
     * @param isActive {boolean} true if the tab is active, false otherwise
     */
    setActive(isActive) {
        if (isActive) {
            this.#tab.classList.add("active");
            this.#tab.tabIndex = 0;
            this.#tab.ariaSelected = "true";
            this.#panel.classList.remove("d-none");
        } else {
            this.#tab.classList.remove("active");
            this.#tab.tabIndex = -1;
            this.#tab.ariaSelected = "false";
            this.#panel.classList.add("d-none");
        }
    }

    /**
     * Returns whether the tab is active.
     *
     * @returns {boolean} true if the tab is active, false otherwise
     */
    isActive() {
        return this.#tab.classList.contains("active");
    }

    /**
     * Actions when the tab is activated.
     */
    onActivated() { /* Do nothing */ }

    /**
     * Focuses the tab.
     */
    focus() {
        this.#tab.focus();
    }
}
