/* The Mia! Accounting Project
 * timezone.js: The JavaScript for the timezone
 */

/*  Copyright (c) 2024 imacat.
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
 * First written: 2024/6/4
 */
"use strict";

// Initializes the page JavaScript.
document.addEventListener("DOMContentLoaded", () => {
    setTimeZone();
});

/**
 * Sets the time zone.
 *
 * @private
 */
function setTimeZone() {
    document.cookie = `accounting-tz=${Intl.DateTimeFormat().resolvedOptions().timeZone}; SameSite=Strict`;
}
