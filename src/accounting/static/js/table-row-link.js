/* The Mia! Accounting Flask Project
 * table-row-link.js: The JavaScript for table rows as links.
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

// Initializes the page JavaScript.
document.addEventListener("DOMContentLoaded", () => {
    initializeTableRowLinks();
});

/**
 * Initializes the table rows as links.
 *
 * @private
 */
function initializeTableRowLinks() {
    const rows = Array.from(document.getElementsByClassName("accounting-clickable accounting-table-row-link"));
    for (const row of rows) {
        row.onclick = () => {
            window.location = row.dataset.href;
        };
    }
}
