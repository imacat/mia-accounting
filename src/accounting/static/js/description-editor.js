/* The Mia! Accounting Project
 * description-editor.js: The JavaScript for the description editor
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
"use strict";

/**
 * A description editor.
 *
 * @extends {BaseTablist<BaseDescriptionEditorTab>}
 */
class DescriptionEditor extends BaseTablist {

    /**
     * The line item editor
     * @type {JournalEntryLineItemEditor}
     */
    lineItemEditor;

    /**
     * The description editor form
     * @type {HTMLFormElement}
     */
    #form;

    /**
     * The prefix of the HTML ID and class names
     * @type {string}
     */
    prefix;

    /**
     * The modal of the description editor
     * @type {HTMLDivElement}
     */
    #modal;

    /**
     * Either "debit" or "credit"
     * @type {string}
     */
    debitCredit;

    /**
     * The description input
     * @type {HTMLInputElement}
     */
    #descriptionInput;

    /**
     * The button to the original line item selector
     * @type {HTMLButtonElement}
     */
    #offsetButton;

    /**
     * The number input
     * @type {HTMLInputElement}
     */
    number;

    /**
     * The note
     * @type {HTMLInputElement}
     */
    note;

    /**
     * The placeholder of the confirmed account
     * @type {DescriptionEditorConfirmedAccount}
     */
    #confirmedAccountPlaceholder;

    /**
     * All the suggested accounts
     * @type {DescriptionEditorSuggestedAccount[]}
     */
    #allSuggestedAccounts;

    /**
     * The current suggested accounts
     * @type {DescriptionEditorSuggestedAccount[]}
     */
    #currentSuggestedAccounts;

    /**
     * The account that the user specified or confirmed
     * @type {DescriptionEditorConfirmedAccount|null}
     */
    #confirmedAccount = null;

    /**
     * Whether the user has confirmed the account
     * @type {boolean}
     */
    isAccountConfirmed = false;

    /**
     * The selected account.
     * @type {DescriptionEditorAccount|null}
     */
    selectedAccount = null;

    /**
     * The tabs by their ID.
     * @type {DescriptionEditorTabFactory}
     */
    #tabsByID;

    /**
     * Constructs a description editor.
     *
     * @param lineItemEditor {JournalEntryLineItemEditor} the line item editor
     * @param debitCredit {string} either "debit" or "credit"
     */
    constructor(lineItemEditor, debitCredit) {
        const prefix = `accounting-description-editor-${debitCredit}`;
        super(document.getElementById(`${prefix}-tab-list`));
        this.prefix = prefix;
        this.lineItemEditor = lineItemEditor;
        this.debitCredit = debitCredit;
        this.#form = document.getElementById(prefix);
        this.#modal = document.getElementById(`${prefix}-modal`);
        this.#descriptionInput = document.getElementById(`${prefix}-description`);
        this.#offsetButton = document.getElementById(`${prefix}-offset`);
        this.number = document.getElementById(`${prefix}-annotation-number`);
        this.note = document.getElementById(`${prefix}-annotation-note`);
        this.#confirmedAccountPlaceholder = new DescriptionEditorConfirmedAccount(this, document.getElementById(`${prefix}-account-confirmed`));
        this.#allSuggestedAccounts = Array.from(document.getElementsByClassName(`${prefix}-account`)).map((button) => new DescriptionEditorSuggestedAccount(this, button));

        this.#tabsByID = new DescriptionEditorTabFactory(this);
        this.tabs = [this.#tabsByID.general, this.#tabsByID.travel, this.#tabsByID.bus, this.#tabsByID.recurring, this.#tabsByID.annotation];
        this.currentTab = this.tabs[0];
        this.#descriptionInput.onchange = () => this.#onDescriptionChange();
        this.#offsetButton.onclick = () => this.lineItemEditor.originalLineItemSelector.onOpen(this.#modal.id);
        this.#form.onsubmit = () => {
            if (this.currentTab.validate()) {
                this.#submit();
            }
            return false;
        };

        const closeButton = document.getElementById(`${prefix}-close`);
        this.#modal.onkeydown = (event) => {
            if (event.key === "Escape") {
                closeButton.click();
            }
        };
    }

    /**
     * Returns the description.
     *
     * @return {string} the description
     */
    get description() {
        return this.#descriptionInput.value;
    }

    /**
     * Sets the description.
     *
     * @param description {string} the description
     */
    set description(description) {
        this.#descriptionInput.value = description;
    }

    /**
     * Returns the current account options.
     *
     * @return {DescriptionEditorAccount[]} the current account options.
     */
    get #currentAccountOptions() {
        if (this.#confirmedAccount === null) {
            return this.#currentSuggestedAccounts;
        }
        return [this.#confirmedAccount].concat(this.#currentSuggestedAccounts);
    }

    /**
     * The callback when the description input is changed.
     *
     */
    #onDescriptionChange() {
        this.#resetTabs();
        this.selectedAccount = null;
        this.description = this.description.trim();
        for (const tab of [this.#tabsByID.recurring, this.#tabsByID.bus, this.#tabsByID.travel, this.#tabsByID.general]) {
            if (tab.populate()) {
                break;
            }
        }
        this.#tabsByID.annotation.populate();
    }

    /**
     * Resets the tabs.
     *
     */
    #resetTabs() {
        for (const tab of this.tabs) {
            tab.reset();
        }
        this.switchTo(this.tabs[0]);
    }

    /**
     * Updates the current suggested accounts.
     *
     * @param tagButton {HTMLButtonElement} the tag button
     */
    updateCurrentSuggestedAccounts(tagButton) {
        this.clearSuggestedAccounts();
        const suggestedAccountCodes = JSON.parse(tagButton.dataset.accounts);
        this.#currentSuggestedAccounts = this.#allSuggestedAccounts.filter((account) => {
            if (this.#confirmedAccount !== null && account.code === this.#confirmedAccount.code) {
                return false;
            }
            return suggestedAccountCodes.includes(account.code);
        });
        for (const account of this.#currentSuggestedAccounts) {
            account.setShown(true);
        }
        this.#selectSuggestedAccount(suggestedAccountCodes[0]);
    }

    /**
     * Selects the suggested account.
     *
     * @param code {string} the code of the most-frequent suggested account
     */
    #selectSuggestedAccount(code) {
        if (this.isAccountConfirmed) {
            return;
        }
        for (const account of this.#currentAccountOptions) {
            if (account.code === code) {
                this.selectAccount(account);
                return;
            }
        }
    }

    /**
     * Clears the suggested accounts.
     *
     */
    clearSuggestedAccounts() {
        for (const account of this.#allSuggestedAccounts) {
            account.setShown(false);
            account.setActive(false);
        }
        this.#currentSuggestedAccounts = [];
    }

    /**
     * Select an account.
     *
     * @param selectedAccount {DescriptionEditorAccount|null} the account, or null to deselect the account
     */
    selectAccount(selectedAccount) {
        for (const account of this.#currentAccountOptions) {
            account.setActive(false);
        }
        if (selectedAccount !== null) {
            selectedAccount.setActive(true);
        }
        this.selectedAccount = selectedAccount;
        if (this.selectedAccount !== null) {
            this.isAccountConfirmed &&= this.selectedAccount.isConfirmedAccount;
        }
    }

    /**
     * Submits the description.
     *
     */
    #submit() {
        bootstrap.Modal.getOrCreateInstance(this.#modal).hide();
        this.lineItemEditor.saveDescription(this);
    }

    /**
     * The callback when the description editor is shown.
     *
     */
    onOpen() {
        this.description = this.lineItemEditor.description === null? "": this.lineItemEditor.description;
        this.#setConfirmedAccount();
        this.#onDescriptionChange();
        if (this.isAccountConfirmed) {
            this.selectAccount(this.#confirmedAccount);
        }
    }

    /**
     * Sets the confirmed account.
     *
     */
    #setConfirmedAccount() {
        this.isAccountConfirmed = this.lineItemEditor.isAccountConfirmed;
        this.#confirmedAccountPlaceholder.setShown(this.isAccountConfirmed);
        if (this.isAccountConfirmed) {
            this.#confirmedAccountPlaceholder.initializeFrom(this.lineItemEditor.account);
            this.#confirmedAccount = this.#confirmedAccountPlaceholder;
        } else {
            this.#confirmedAccount = null;
        }
    }

    /**
     * Returns the description editor instances.
     *
     * @param lineItemEditor {JournalEntryLineItemEditor} the line item editor
     * @return {{debit: DescriptionEditor, credit: DescriptionEditor}}
     */
    static getInstances(lineItemEditor) {
        const editors = {}
        const forms = Array.from(document.getElementsByClassName("accounting-description-editor"));
        for (const form of forms) {
            editors[form.dataset.debitCredit] = new DescriptionEditor(lineItemEditor, form.dataset.debitCredit);
        }
        return editors;
    }
}

/**
 * An account option in the description editor.
 *
 * @private
 */
class DescriptionEditorAccount extends JournalEntryAccount {

    /**
     * The account button
     * @type {HTMLButtonElement}
     */
    #element;

    /**
     * Whether this is the account specified or confirmed by the user
     * @type {boolean}
     */
    isConfirmedAccount = false;

    /**
     * Constructs an account option in the description editor.
     *
     * @param editor {DescriptionEditor} the description editor
     * @param code {string} the account code
     * @param title {string} the account title
     * @param text {string} the account text
     * @param isNeedOffset {boolean} true if the line items in the account needs offset, or false otherwise
     * @param button {HTMLButtonElement} the account button
     */
    constructor(editor, code, title, text, isNeedOffset, button) {
        super(code, title, text, isNeedOffset);
        this.#element = button;
        this.#element.onclick = () => editor.selectAccount(this);
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
            this.#element.classList.add("btn-primary");
            this.#element.classList.remove("btn-outline-primary");
        } else {
            this.#element.classList.remove("btn-primary");
            this.#element.classList.add("btn-outline-primary");
        }
    }

    /**
     * Sets the content of the account button.
     *
     */
    resetContent() {
        this.#element.innerText = this.text;
    }
}

/**
 * A suggested account.
 *
 * @private
 */
class DescriptionEditorSuggestedAccount extends DescriptionEditorAccount {

    /**
     * Constructs a suggested account.
     *
     * @param editor {DescriptionEditor} the description editor
     * @param button {HTMLButtonElement} the account button
     */
    constructor(editor, button) {
        super(editor, button.dataset.code, button.dataset.title, button.dataset.text, button.classList.contains("accounting-account-is-need-offset"), button);
    }
}

/**
 * The account option that is specified or confirmed by the user.
 *
 * @private
 */
class DescriptionEditorConfirmedAccount extends DescriptionEditorAccount {

    /**
     * Constructs the account option that is specified or confirmed by the user.
     *
     * @param editor {DescriptionEditor} the description editor
     * @param button {HTMLButtonElement} the account button
     */
    constructor(editor, button) {
        super(editor, "", "", "", false, button);
        this.isConfirmedAccount = true;
    }

    /**
     * Initializes the confirmed account from the line item editor.
     *
     * @param account {JournalEntryAccount} the confirmed account from the line item editor
     */
    initializeFrom(account) {
        this.code = account.code;
        this.text = account.text;
        this.isNeedOffset = account.isNeedOffset;
        this.resetContent();
    }
}

/**
 * The tab factory.
 *
 * @private
 */
class DescriptionEditorTabFactory {

    /**
     * The general tag tab
     * @type {GeneralTagTab}
     */
    general;

    /**
     * The general trip tab
     * @type {GeneralTripTab}
     */
    travel;

    /**
     * The bus trip tab
     * @type {BusTripTab}
     */
    bus;

    /**
     * The recurring transactions tab
     * @type {RecurringTab}
     */
    recurring;

    /**
     * The annotation tab
     * @type {AnnotationTab}
     */
    annotation;

    /**
     * Constructs the tab factory
     *
     * @param editor {DescriptionEditor} the parent description editor
     */
    constructor(editor) {
        this.general = new GeneralTagTab(editor);
        this.travel = new GeneralTripTab(editor);
        this.bus = new BusTripTab(editor);
        this.recurring = new RecurringTab(editor);
        this.annotation = new AnnotationTab(editor);
    }
}

/**
 * The base abstract tab in the description editor.
 *
 * @abstract
 * @private
 */
class BaseDescriptionEditorTab extends BaseTab {

    /**
     * The parent description editor
     * @type {DescriptionEditor}
     */
    editor;

    /**
     * The prefix of the HTML ID and class names
     * @type {string}
     */
    prefix;

    /**
     * Constructs a base abstract tab in the description editor.
     *
     * @param tabID {string} the tab ID
     * @param editor {DescriptionEditor} the parent description editor
     */
    constructor(tabID, editor) {
        const prefix = `${editor.prefix}-${tabID}`;
        const tab = document.getElementById(`${prefix}-tab`);
        const panel = document.getElementById(`${prefix}-panel`);
        super(tab, panel, editor.switchTo.bind(editor));
        this.editor = editor;
        this.prefix = prefix;
    }

    /**
     * Resets the tab panel input.
     *
     * @abstract
     */
    reset() { throw new Error("Method not implemented."); }

    /**
     * Populates the tab panel with the description input.
     *
     * @return {boolean} true if the description input matches this tab, or false otherwise
     * @abstract
     */
    populate() { throw new Error("Method not implemented."); }

    /**
     * Validates the input in the tab panel.
     *
     * @return {boolean} true if valid, or false otherwise
     * @abstract
     */
    validate() { throw new Error("Method not implemented."); }
}

/**
 * The base abstract tab with selectable tags.
 *
 * @abstract
 * @private
 */
class BaseTagTab extends BaseDescriptionEditorTab {

    /**
     * The tag input
     * @type {HTMLInputElement}
     */
    tag;

    /**
     * The error message for the tag input
     * @type {HTMLDivElement}
     */
    tagError;

    /**
     * The tag buttons
     * @type {HTMLButtonElement[]}
     */
    #tagButtons;

    /**
     * Constructs a base abstract tab with selectable tags.
     *
     * @param tabID {string} the tab ID
     * @param editor {DescriptionEditor} the parent description editor
     * @override
     */
    constructor(tabID, editor) {
        super(tabID, editor);
        this.tag = document.getElementById(`${this.prefix}-tag`);
        this.tagError = document.getElementById(`${this.prefix}-tag-error`);
        // noinspection JSValidateTypes
        this.#tagButtons = Array.from(document.getElementsByClassName(`${this.prefix}-btn-tag`));
        this.initializeTagButtons();
        this.tag.onchange = () => {
            this.onTagChange();
            this.updateDescription();
        };
    }

    /**
     * The callback when the tag input is changed
     *
     */
    onTagChange() {
        this.tag.value = this.tag.value.trim();
        let isMatched = false;
        for (const tagButton of this.#tagButtons) {
            if (tagButton.dataset.value === this.tag.value) {
                tagButton.classList.remove("btn-outline-primary");
                tagButton.classList.add("btn-primary");
                this.editor.updateCurrentSuggestedAccounts(tagButton);
                isMatched = true;
            } else {
                tagButton.classList.remove("btn-primary");
                tagButton.classList.add("btn-outline-primary");
            }
        }
        if (!isMatched) {
            this.editor.clearSuggestedAccounts();
        }
        this.validateTag();
    }

    /**
     * Updates the description according to the input in the tab panel.
     *
     * @abstract
     */
    updateDescription() { throw new Error("Method not implemented."); }

    /**
     * @inheritDoc
     * @override
     */
    onActivated() {
        for (const tagButton of this.#tagButtons) {
            if (tagButton.classList.contains("btn-primary")) {
                this.editor.updateCurrentSuggestedAccounts(tagButton);
                return;
            }
        }
        this.editor.clearSuggestedAccounts();
    }

    /**
     * Initializes the tag buttons.
     *
     */
    initializeTagButtons() {
        for (const tagButton of this.#tagButtons) {
            tagButton.onclick = () => {
                for (const otherButton of this.#tagButtons) {
                    otherButton.classList.remove("btn-primary");
                    otherButton.classList.add("btn-outline-primary");
                }
                tagButton.classList.remove("btn-outline-primary");
                tagButton.classList.add("btn-primary");
                this.tag.value = tagButton.dataset.value;
                this.editor.updateCurrentSuggestedAccounts(tagButton);
                this.updateDescription();
            };
        }
    }

    /**
     * Validates the tag input.
     *
     * @return {boolean} true if valid, or false otherwise
     */
    validateTag() {
        this.tag.value = this.tag.value.trim();
        this.tag.classList.remove("is-invalid");
        this.tagError.innerText = "";
        return true;
    }

    /**
     * Validates a required field.
     *
     * @param field {HTMLInputElement} the input field
     * @param errorContainer {HTMLDivElement} the error message container
     * @param errorMessage {string} the error message
     * @return {boolean} true if valid, or false otherwise
     */
    validateRequiredField(field, errorContainer, errorMessage) {
        field.value = field.value.trim();
        if (field.value === "") {
            field.classList.add("is-invalid");
            errorContainer.innerText = errorMessage;
            return false;
        }
        field.classList.remove("is-invalid");
        errorContainer.innerText = "";
        return true;
    }

    /**
     * Resets the tab panel input.
     *
     * @override
     */
    reset() {
        this.tag.value = "";
        this.tag.classList.remove("is-invalid");
        this.tagError.innerText = "";
        for (const tagButton of this.#tagButtons) {
            tagButton.classList.remove("btn-primary");
            tagButton.classList.add("btn-outline-primary");
        }
    }
}

/**
 * The general tag tab.
 *
 * @private
 */
class GeneralTagTab extends BaseTagTab {

    /**
     * Constructs a general tag tab.
     *
     * @param editor {DescriptionEditor} the parent description editor
     * @override
     */
    constructor(editor) {
        super("general", editor);
    }

    /**
     * Updates the description according to the input in the tab panel.
     *
     * @override
     */
    updateDescription() {
        const pos = this.editor.description.indexOf("—");
        const prefix = this.tag.value === ""? "": `${this.tag.value}—`;
        if (pos === -1) {
            this.editor.description = `${prefix}${this.editor.description}`;
        } else {
            this.editor.description = `${prefix}${this.editor.description.substring(pos + 1)}`;
        }
    }

    /**
     * Populates the tab panel with the description input.
     *
     * @return {boolean} true if the description input matches this tab, or false otherwise
     * @override
     */
    populate() {
        const found = this.editor.description.match(/^([^—]+)—/);
        if (found === null) {
            return false;
        }
        if (this.tag.value !== found[1]) {
            this.tag.value = found[1];
            this.onTagChange();
        }
        this.editor.switchTo(this);
        return true;
    }

    /**
     * Validates the input in the tab panel.
     *
     * @return {boolean} true if valid, or false otherwise
     */
    validate() {
        return this.validateTag();
    }
}

/**
 * The general trip tab.
 *
 * @private
 */
class GeneralTripTab extends BaseTagTab {

    /**
     * The origin
     * @type {HTMLInputElement}
     */
    #from;

    /**
     * The error of the origin
     * @type {HTMLDivElement}
     */
    #fromError;

    /**
     * The destination
     * @type {HTMLInputElement}
     */
    #to;

    /**
     * The error of the destination
     * @type {HTMLDivElement}
     */
    #toError;

    /**
     * The direction buttons
     * @type {HTMLButtonElement[]}
     */
    #directionButtons;

    /**
     * Constructs a general trip tab.
     *
     * @param editor {DescriptionEditor} the parent description editor
     * @override
     */
    constructor(editor) {
        super("travel", editor);
        this.#from = document.getElementById(`${this.prefix}-from`);
        this.#fromError = document.getElementById(`${this.prefix}-from-error`);
        this.#to = document.getElementById(`${this.prefix}-to`);
        this.#toError = document.getElementById(`${this.prefix}-to-error`)
        // noinspection JSValidateTypes
        this.#directionButtons = Array.from(document.getElementsByClassName(`${this.prefix}-direction`));
        this.#from.onchange = () => {
            this.#from.value = this.#from.value.trim();
            this.updateDescription();
            this.validateFrom();
        };
        for (const directionButton of this.#directionButtons) {
            directionButton.onclick = () => {
                for (const otherButton of this.#directionButtons) {
                    otherButton.classList.remove("btn-primary");
                    otherButton.classList.add("btn-outline-primary");
                }
                directionButton.classList.remove("btn-outline-primary");
                directionButton.classList.add("btn-primary");
                this.updateDescription();
            };
        }
        this.#to.onchange = () => {
            this.#to.value = this.#to.value.trim();
            this.updateDescription();
            this.validateTo();
        };
    }

    /**
     * Updates the description according to the input in the tab panel.
     *
     * @override
     */
    updateDescription() {
        let direction;
        for (const directionButton of this.#directionButtons) {
            if (directionButton.classList.contains("btn-primary")) {
                direction = directionButton.dataset.arrow;
                break;
            }
        }
        this.editor.description = `${this.tag.value}—${this.#from.value}${direction}${this.#to.value}`;
    }

    /**
     * Resets the tab panel input.
     *
     * @override
     */
    reset() {
        super.reset();
        this.#from.value = "";
        this.#from.classList.remove("is-invalid");
        this.#fromError.innerText = "";
        for (const directionButton of this.#directionButtons) {
            if (directionButton.classList.contains("accounting-default")) {
                directionButton.classList.remove("btn-outline-primary");
                directionButton.classList.add("btn-primary");
            } else {
                directionButton.classList.add("btn-outline-primary");
                directionButton.classList.remove("btn-primary");
            }
        }
        this.#to.value = "";
        this.#to.classList.remove("is-invalid");
        this.#toError.innerText = "";
    }

    /**
     * Populates the tab panel with the description input.
     *
     * @return {boolean} true if the description input matches this tab, or false otherwise
     * @override
     */
    populate() {
        const found = this.editor.description.match(/^([^—]+)—([^—→↔]+)([→↔])(.+?)(?:[*×]\d+)?(?:\([^()]+\))?$/);
        if (found === null) {
            return false;
        }
        if (this.tag.value !== found[1]) {
            this.tag.value = found[1];
            this.onTagChange();
        }
        this.#from.value = found[2];
        for (const directionButton of this.#directionButtons) {
            if (directionButton.dataset.arrow === found[3]) {
                directionButton.classList.remove("btn-outline-primary");
                directionButton.classList.add("btn-primary");
            } else {
                directionButton.classList.add("btn-outline-primary");
                directionButton.classList.remove("btn-primary");
            }
        }
        this.#to.value = found[4];
        this.editor.switchTo(this);
        return true;
    }

    /**
     * Validates the input in the tab panel.
     *
     * @return {boolean} true if valid, or false otherwise
     * @override
     */
    validate() {
        let isValid = true;
        isValid = this.validateTag() && isValid;
        isValid = this.validateFrom() && isValid;
        isValid = this.validateTo() && isValid;
        return isValid;
    }

    /**
     * Validates the tag input.
     *
     * @return {boolean} true if valid, or false otherwise
     * @override
     */
    validateTag() {
        return this.validateRequiredField(this.tag, this.tagError, A_("Please fill in the tag."));
    }

    /**
     * Validates the origin.
     *
     * @return {boolean} true if valid, or false otherwise
     * @override
     */
    validateFrom() {
        return this.validateRequiredField(this.#from, this.#fromError, A_("Please fill in the origin."));
    }

    /**
     * Validates the destination.
     *
     * @return {boolean} true if valid, or false otherwise
     * @override
     */
    validateTo() {
        return this.validateRequiredField(this.#to, this.#toError, A_("Please fill in the destination."));
    }
}

/**
 * The bus trip tab.
 *
 * @private
 */
class BusTripTab extends BaseTagTab {

    /**
     * The route
     * @type {HTMLInputElement}
     */
    #route;

    /**
     * The error of the route
     * @type {HTMLDivElement}
     */
    #routeError;

    /**
     * The origin
     * @type {HTMLInputElement}
     */
    #from;

    /**
     * The error of the origin
     * @type {HTMLDivElement}
     */
    #fromError;

    /**
     * The destination
     * @type {HTMLInputElement}
     */
    #to;

    /**
     * The error of the destination
     * @type {HTMLDivElement}
     */
    #toError;

    /**
     * Constructs a bus trip tab.
     *
     * @param editor {DescriptionEditor} the parent description editor
     * @override
     */
    constructor(editor) {
        super("bus", editor);
        this.#route = document.getElementById(`${this.prefix}-route`);
        this.#routeError = document.getElementById(`${this.prefix}-route-error`);
        this.#from = document.getElementById(`${this.prefix}-from`);
        this.#fromError = document.getElementById(`${this.prefix}-from-error`);
        this.#to = document.getElementById(`${this.prefix}-to`);
        this.#toError = document.getElementById(`${this.prefix}-to-error`)
        this.#route.onchange = () => {
            this.#route.value = this.#route.value.trim();
            this.updateDescription();
            this.validateRoute();
        };
        this.#from.onchange = () => {
            this.#from.value = this.#from.value.trim();
            this.updateDescription();
            this.validateFrom();
        };
        this.#to.onchange = () => {
            this.#to.value = this.#to.value.trim();
            this.updateDescription();
            this.validateTo();
        };
    }

    /**
     * Updates the description according to the input in the tab panel.
     *
     * @override
     */
    updateDescription() {
        this.editor.description = `${this.tag.value}—${this.#route.value}—${this.#from.value}→${this.#to.value}`;
    }

    /**
     * Resets the tab panel input.
     *
     * @override
     */
    reset() {
        super.reset();
        this.#route.value = "";
        this.#route.classList.remove("is-invalid");
        this.#routeError.innerText = "";
        this.#from.value = "";
        this.#from.classList.remove("is-invalid");
        this.#fromError.innerText = "";
        this.#to.value = "";
        this.#to.classList.remove("is-invalid");
        this.#toError.innerText = "";
    }

    /**
     * Populates the tab panel with the description input.
     *
     * @return {boolean} true if the description input matches this tab, or false otherwise
     * @override
     */
    populate() {
        const found = this.editor.description.match(/^([^—]+)—([^—]+)—([^—→]+)→(.+?)(?:[*×]\d+)?(?:\([^()]+\))?$/);
        if (found === null) {
            return false;
        }
        if (this.tag.value !== found[1]) {
            this.tag.value = found[1];
            this.onTagChange();
        }
        this.#route.value = found[2];
        this.#from.value = found[3];
        this.#to.value = found[4];
        this.editor.switchTo(this);
        return true;
    }

    /**
     * Validates the input in the tab panel.
     *
     * @return {boolean} true if valid, or false otherwise
     */
    validate() {
        let isValid = true;
        isValid = this.validateTag() && isValid;
        isValid = this.validateRoute() && isValid;
        isValid = this.validateFrom() && isValid;
        isValid = this.validateTo() && isValid;
        return isValid;
    }

    /**
     * Validates the tag input.
     *
     * @return {boolean} true if valid, or false otherwise
     * @override
     */
    validateTag() {
        return this.validateRequiredField(this.tag, this.tagError, A_("Please fill in the tag."));
    }

    /**
     * Validates the route.
     *
     * @return {boolean} true if valid, or false otherwise
     * @override
     */
    validateRoute() {
        return this.validateRequiredField(this.#route, this.#routeError, A_("Please fill in the route."));
    }

    /**
     * Validates the origin.
     *
     * @return {boolean} true if valid, or false otherwise
     * @override
     */
    validateFrom() {
        return this.validateRequiredField(this.#from, this.#fromError, A_("Please fill in the origin."));
    }

    /**
     * Validates the destination.
     *
     * @return {boolean} true if valid, or false otherwise
     * @override
     */
    validateTo() {
        return this.validateRequiredField(this.#to, this.#toError, A_("Please fill in the destination."));
    }
}

/**
 * The recurring transaction tab.
 *
 * @private
 */
class RecurringTab extends BaseDescriptionEditorTab {

    /**
     * The month names
     * @type {string[]}
     */
    #monthNames;

    /**
     * The buttons of the recurring items
     * @type {HTMLButtonElement[]}
     */
    #itemButtons;

    /**
     * Constructs a recurring transaction tab.
     *
     * @param editor {DescriptionEditor} the parent description editor
     * @override
     */
    constructor(editor) {
        super("recurring", editor);
        this.#monthNames = [
            "",
            A_("January"), A_("February"), A_("March"), A_("April"),
            A_("May"), A_("June"), A_("July"), A_("August"),
            A_("September"), A_("October"), A_("November"), A_("December"),
        ];
        // noinspection JSValidateTypes
        this.#itemButtons = Array.from(document.getElementsByClassName(`${this.prefix}-item`));
        for (const itemButton of this.#itemButtons) {
            itemButton.onclick = () => {
                this.reset();
                itemButton.classList.add("btn-primary");
                itemButton.classList.remove("btn-outline-primary");
                this.editor.description = this.#getDescription(itemButton);
                this.editor.updateCurrentSuggestedAccounts(itemButton);
            };
        }
    }

    /**
     * Returns the description for a recurring item.
     *
     * @param itemButton {HTMLButtonElement} the recurring item
     * @return {string} the description of the recurring item
     */
    #getDescription(itemButton) {
        const today = new Date(this.editor.lineItemEditor.form.date);
        const thisMonth = today.getMonth() + 1;
        const lastMonth = (thisMonth + 10) % 12 + 1;
        const lastBimonthlyFrom = ((thisMonth + thisMonth % 2 + 8) % 12 + 1);
        const lastBimonthlyTo = ((thisMonth + thisMonth % 2 + 9) % 12 + 1);
        return itemButton.dataset.template
            .replaceAll("{this_month_number}", String(thisMonth))
            .replaceAll("{this_month_name}", this.#monthNames[thisMonth])
            .replaceAll("{last_month_number}", String(lastMonth))
            .replaceAll("{last_month_name}", this.#monthNames[lastMonth])
            .replaceAll("{last_bimonthly_number}", `${String(lastBimonthlyFrom)}–${String(lastBimonthlyTo)}`)
            .replaceAll("{last_bimonthly_name}", `${this.#monthNames[lastBimonthlyFrom]}–${this.#monthNames[lastBimonthlyTo]}`);
    }

    /**
     * Resets the tab panel input.
     *
     * @override
     */
    reset() {
        for (const itemButton of this.#itemButtons) {
            itemButton.classList.remove("btn-primary");
            itemButton.classList.add("btn-outline-primary");
        }
    }

    /**
     * Populates the tab panel with the description input.
     *
     * @return {boolean} true if the description input matches this tab, or false otherwise
     * @override
     */
    populate() {
        for (const itemButton of this.#itemButtons) {
            if (this.#getDescription(itemButton) === this.editor.description) {
                itemButton.classList.add("btn-primary");
                itemButton.classList.remove("btn-outline-primary");
                this.editor.switchTo(this);
                return true;
            }
        }
        return false;
    }

    /**
     * @inheritDoc
     * @override
     */
    onActivated() {
        for (const itemButton of this.#itemButtons) {
            if (itemButton.classList.contains("btn-primary")) {
                this.editor.updateCurrentSuggestedAccounts(itemButton);
                return;
            }
        }
        this.editor.clearSuggestedAccounts();
    }

    /**
     * Validates the input in the tab panel.
     *
     * @return {boolean} true if valid, or false otherwise
     * @override
     */
    validate() {
        return true;
    }
}

/**
 * The annotation tab.
 *
 * @private
 */
class AnnotationTab extends BaseDescriptionEditorTab {

    /**
     * Constructs an annotation tab.
     *
     * @param editor {DescriptionEditor} the parent description editor
     * @override
     */
    constructor(editor) {
        super("annotation", editor);
        this.editor.number.onchange = () => this.updateDescription();
        this.editor.note.onchange = () => {
            this.editor.note.value = this.editor.note.value.trim();
            this.updateDescription();
        };
    }

    /**
     * Updates the description according to the input in the tab panel.
     *
     * @override
     */
    updateDescription() {
        const found = this.editor.description.match(/^(.*?)(?:[*×]\d+)?(?:\([^()]+\))?$/);
        if (found !== null) {
            this.editor.description = found[1];
        }
        if (parseInt(this.editor.number.value) > 1) {
            this.editor.description = `${this.editor.description}×${this.editor.number.value}`;
        }
        if (this.editor.note.value !== "") {
            this.editor.description = `${this.editor.description}(${this.editor.note.value})`;
        }
    }

    /**
     * Resets the tab panel input.
     *
     * @override
     */
    reset() {
        this.editor.number.value = "";
        this.editor.note.value = "";
    }

    /**
     * Populates the tab panel with the description input.
     *
     * @return {boolean} true if the description input matches this tab, or false otherwise
     * @override
     */
    populate() {
        const found = this.editor.description.match(/^(.*?)(?:[*×](\d+))?(?:\(([^()]+)\))?$/);
        this.editor.description = found[1];
        if (found[2] === undefined || parseInt(found[2]) === 1) {
            this.editor.number.value = "";
        } else {
            this.editor.number.value = found[2];
            this.editor.description = `${this.editor.description}×${this.editor.number.value}`;
        }
        if (found[3] === undefined) {
            this.editor.note.value = "";
        } else {
            this.editor.note.value = found[3];
            this.editor.description = `${this.editor.description}(${this.editor.note.value})`;
        }
        return true;
    }

    /**
     * Validates the input in the tab panel.
     *
     * @return {boolean} true if valid, or false otherwise
     * @override
     */
    validate() {
        return true;
    }
}
