/* The Mia! Accounting Flask Project
 * drag-and-drop-reorder.js: The JavaScript for the reorder a list with drag-and-drop
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
 * First written: 2023/2/3
 */

/**
 * Initializes the drag-and-drop reordering on a list.
 *
 * @param list {HTMLElement} the list to be reordered
 * @param onReorder {(function())|*} The callback to reorder the items
 */
function initializeDragAndDropReordering(list, onReorder) {
    initializeMouseDragAndDropReordering(list, onReorder);
    initializeTouchDragAndDropReordering(list, onReorder);
}

/**
 * Initializes the drag-and-drop reordering with mouse.
 *
 * @param list {HTMLElement} the list to be reordered
 * @param onReorder {(function())|*} The callback to reorder the items
 * @private
 */
function initializeMouseDragAndDropReordering(list, onReorder) {
    const items = Array.from(list.children);
    let dragged = null;
    items.forEach(function (item) {
        item.draggable = true;
        item.addEventListener("dragstart", function () {
            dragged = item;
            dragged.classList.add("list-group-item-dark");
        });
        item.addEventListener("dragover", function () {
            onDragOver(dragged, item);
            onReorder();
        });
        item.addEventListener("dragend", function () {
            dragged.classList.remove("list-group-item-dark");
            dragged = null;
        });
    });
}

/**
 * Initializes the drag-and-drop reordering with touch devices.
 *
 * @param list {HTMLElement} the list to be reordered
 * @param onReorder {(function())|*} The callback to reorder the items
 * @private
 */
function initializeTouchDragAndDropReordering(list, onReorder) {
    const items = Array.from(list.children);
    items.forEach(function (item) {
        item.addEventListener("touchstart", function () {
            item.classList.add("list-group-item-dark");
        });
        item.addEventListener("touchmove", function (event) {
            const touch = event.targetTouches[0];
            const target = document.elementFromPoint(touch.pageX, touch.pageY);
            onDragOver(item, target);
            onReorder();
        });
        item.addEventListener("touchend", function () {
            item.classList.remove("list-group-item-dark");
        });
    });
}

/**
 * Handles when an item is dragged over the other item.
 *
 * @param dragged {Element} the item that was dragged
 * @param target {Element} the other item that was dragged over
 */
function onDragOver(dragged, target) {
    if (target.parentElement !== dragged.parentElement || target === dragged) {
        return;
    }
    let isBefore = false;
    for (let p = target; p !== null; p = p.previousSibling) {
        if (p === dragged) {
            isBefore = true;
        }
    }
    if (isBefore) {
        target.parentElement.insertBefore(dragged, target.nextSibling);
    } else {
        target.parentElement.insertBefore(dragged, target);
    }
}
