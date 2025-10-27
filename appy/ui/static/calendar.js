// Sends an Ajax request for getting the calendar, at p_month

function askMonth(iid, name, month) {
  const hook = `${iid}${name}`,
        data = document.getElementById(hook)['ajax'];
        action = (data)? data.params['action']: null;
  if (action == 'storeFromAjax') {
     // Value for the field having this p_name must be transmitted
     let values = [];
     for (const hidden of getElementsHavingName('input', name)) {
       values.push(hidden.value);
     }
     data.params['fieldContent'] = values.join(',');
  }
  askAjax(hook, null, {'month': month.replace('/', '%2F')})
}

// Manages filters about a given calendar, for a given Appy object
class Filters {
  constructor(iid, name, filters) {
    /* A Filters object will be injected in the dom node corresponding to the
       current calendar view. */
    this.iid = iid
    this.name = name;
    this.hook = `${iid}${name}`; // The name of this node
    this.node = getNode(this.hook);
    this.node.appyFilters = this;
    // Dict of filters being applicable for the current view ~{s_name:s_type}~
    this.filters = filters;
  }

  static get(node) {
    // Get the Filters object being defined in one of p_node's parents
    let r=node, filters=null;
    while (true) {
      r = r.parentNode;
      if (!r) return; // We have reached the root node
      filters = r.appyFilters
      if (filters) return filters;
    }
  }

  ajaxParams() { return this.node['ajax'].params; }

  collectValues(name) {
    /* Get the selected values in the filter having this p_name and p_type and
       push them in the AjaxData object. */
    const filterId = `${this.iid}_${this.name}${name}`,
          filter = document.getElementById(filterId);
    let values = [], value = null;
    if (filter) {
      // Collect filter values
      if (this.filters[name] == 'checkbox') {
        for (const cb of filter.querySelectorAll('input[type="checkbox"]')) {
          if (cb.checked) {
            value = cb.id.split('_').pop();
            if (value !== 'all') values.push(value);
          }
        }
      }
    }
    this.ajaxParams()['filters'][name] = values;
  }

  static askOne(node, name) {
    // Ajax-refresh the filter having this p_name and widget p_type
    const filters = Filters.get(node);
    filters.collectValues(name);
    askAjax(filters.hook, null);
  }

  static askAll(node) {
    // Ajax-refresh the filter having this p_name and widget p_type
    const filters = Filters.get(node);
    for (const name in filters.filters) filters.collectValues(name);
    askAjax(filters.hook, null);
  }

  static cleanOne(node, name) {
    // Ajax-refresh the filter having this p_name, for cleaning it
    const filters = Filters.get(node);
    filters.ajaxParams()['filters'][name] = [];
    askAjax(filters.hook, null);
  }

  static cleanAll(node) {
    // Clean all filter values
    const filters = Filters.get(node);
    filters.ajaxParams()['filters'] = {};
    askAjax(filters.hook, null);
  }
}

function enableOptions(select, enabled, selectFirst, message){
  /* This function disables, in p_select, all options that are not in p_enabled.
     p_enabled is a string containing a comma-separated list of option names.
     If p_selectFirst is True, the first option from p_enabled will be selected
     by default. p_message will be shown (as "title") for disabled options. */
  // Get p_enabled as a dict
  const l = enabled.split(',');
  let d = {};
  for (let i=0; i < l.length; i++) d[l[i]] = true;
  // Remember if we have already selected the first enabled option
  let isSelected = false,
      options = select.options;
  // Disable options not being p_enabled
  for (let i=0; i<options.length; i++) {
    // Make sure the option is visible
    options[i].style.display = 'block';
    options[i].selected = false;
    if (!options[i].value) continue;
    if (options[i].value in d) {
      options[i].disabled = false;
      options[i].title = '';
      // Select it?
      if (selectFirst && !isSelected) {
        options[i].selected = true;
        isSelected = true;
      }
    }
    else {
      options[i].disabled = true;
      options[i].title = message;
    }
  }
}

function openEventPopup(hookId, action, day, timeslot, spansDays,
                        applicableEventTypes, message, freeSlots) {
  /* Opens the popup for creating (or deleting, depending on p_action) a
     calendar event at some p_day. When action is "del", we need to know the
     p_timeslot where the event is assigned and if the event spans more days
     (from p_spansDays), in order to propose a checkbox allowing to delete
     events for those successive days. When action is "new", a possibly
     restricted list of applicable event types for this day is given in
     p_applicableEventTypes; p_message contains an optional message explaining
     why not applicable types are not applicable. When "new", p_freeSlots may
     list the available timeslots at p_day. */
  const popupId = `${hookId}_${action}`,
        f = document.getElementById(`${popupId}Form`);
  f.day.value = day;
  if (action == 'del') {
    if (f.timeslot) f.timeslot.value = timeslot;
    // Show or hide the checkbox for deleting the event for successive days
    let elem = document.getElementById(`${hookId}_DelNextEvent`),
        cb = elem.getElementsByTagName('input');
    cb[0].checked = false;
    cb[1].value = 'False';
    elem.style.display = (spansDays == 'True')? 'block': 'none'
  }
  else if (action == 'new') {
    // Reinitialise field backgrounds
    f.eventType.style.background = '';
    if (f.eventSpan) f.eventSpan.style.background = '';
    // Disable unapplicable events and non-free timeslots
    enableOptions(f.eventType, applicableEventTypes, false, message);
    if (f.timeslot) enableOptions(f.timeslot, freeSlots, true, '🛇');
  }
  openPopup(popupId);
}

function triggerCalendarEvent(hook, action, maxEventLength) {
  /* Sends an Ajax request for triggering a calendar event (create or delete an
     event) and refreshing the view month. */
  const popupId = `${hook}_${action}`,
        formId = `${popupId}Form`,
        f = document.getElementById(formId);
  if (action == 'new') {
    // Check that an event span has been specified
    if (f.eventType.selectedIndex == 0) {
      f.eventType.style.background = wrongTextInput;
      return;
    }
    if (f.eventSpan) {
      // Check that eventSpan is empty or contains a valid number
      let spanNumber = f.eventSpan.value.replace(' ', '');
      if (spanNumber) {
        spanNumber = parseInt(spanNumber);
        if (isNaN(spanNumber) || (spanNumber > maxEventLength)) {
          f.eventSpan.style.background = wrongTextInput;
          return;
        }
      }
    }
    // Copy the poor comment to the inner textarea
    const comment = f.elements['comment'];
    if (comment) comment.value = comment.previousSibling.innerHTML;
  }
  closePopup(popupId);
  askAjax(hook, formId);
}

// Manages the calendar event validation process
class CalValidator {

  // Update popup visibility
  static setPopup(hook, view) {
    const popup = document.getElementById(`${hook}_valPopup`);
    popup.style.display = view;
  }

  // Function that collects the status of all validation checkboxes
  static getCheckboxesStatus(hook) {
    let r = {'validated': [], 'discarded': []},
        node = document.getElementById(`${hook}_cal`),
        cbs = node.getElementsByTagName('input'),
        key = null;
    for (const cb of cbs) {
      if (cb.type != 'checkbox') continue;
      key = (cb.checked)? 'validated': 'discarded';
      r[key].push(cb.id);
    }
    // Convert lists to comma-separated strings
    for (key in r) r[key] = r[key].join();
    return r;
  }

  // Send (un)selected events, for a specific month, to the Appy server
  static validate(hook) {
    // Collect checkboxes within p_hook and identify checked and unchecked ones
    askAjax(hook, `${hook}_valForm`, this.getCheckboxesStatus(hook));
  }
}

// Function for (un)-checking checkboxes automatically
function onCheckCbCell(cb, hook, totalRows, totalCols) {
  // Is automatic selection on/off ?
  const auto = document.getElementById(`${hook}_auto`);
  if (auto.checked) {
    // Are we on a multiple calendar view ?
    let mult = document.getElementById(hook)['ajax'].params['multiple'],
        multiple = mult == '1',
        elems = cb.id.split('_'),
        date, part;
    /* Change the state of every successive checkbox. From the checkbox id,
       extract the date and the remaining part. */
    if (multiple) {
      date = elems[2];
      part = `${elems[0]}_${elems[1]}_`;
    }
    else {
      date = elems[0];
      part = `_${elems[1]}_${elems[2]}`;
    }
    // Create a Date instance
    let year = parseInt(date.slice(0,4)),
        month = parseInt(date.slice(4,6))-1,
        day = parseInt(date.slice(6,8)),
        next = new Date(year, month, day),
        checked = cb.checked, nextId, nextCb;
    // Change the status of successive checkboxes if found
    while (true) {
      // Compute the date at the next day
      next.setDate(next.getDate() + 1);
      month = (next.getMonth() + 1).toString();
      if (month.length == 1) month = `0${month}`;
      day = next.getDate().toString();
      if (day.length == 1) day = `0${day}`;
      date = `${next.getFullYear().toString()}${month}${day}`;
      // Find the next checkbox
      if (multiple) nextId = `${part}${date}`;
      else          nextId = `${date}${part}`;
      nextCb = document.getElementById(nextId);
      if (!nextCb) break;
      nextCb.checked = checked;
    }
  }
  // Refresh the total rows if requested
  if (totalRows || totalCols) {
    let params = CalValidator.getCheckboxesStatus(hook);
    if (totalRows) {
      params['totalType'] = 'rows';
      params['mode'] = 'POST'; // askAjax removes key 'mode' from params
      askAjax(`${hook}_trs`, null, params);
    }
    if (totalCols) {
      params['totalType'] = 'cols';
      params['mode'] = 'POST'; // askAjax removes key 'mode' from params
      askAjax(`${hook}_tcs`, null, params);
    }
  }
}

 // Switches a layer on/off within a calendar
function switchCalendarLayer(hookId, checkbox) {
  /* Update the ajax data about active layers from p_checkbox, that represents
     the status of some layer */
  let layer = checkbox.id.split('_').pop(),
      d = getNode(hookId)['ajax'],
      activeLayers = d.params['activeLayers'];
  if (checkbox.checked) {
    // Add the layer to active layers
    activeLayers = (!activeLayers)? layer: `${activeLayers},${layer}`;
  }
  else {
    // Remove the layer from active layers
    let r = [],
        splitted = activeLayers.split(',');
    for (let i=0; i<splitted.length; i++) {
      if (splitted[i] != layer) r.push(splitted[i]);
    }
    activeLayers = r.join();
  }
  askAjax(hookId, null, {'activeLayers': activeLayers});
}

function blinkTd(td, tdId, selectDict, unblinkOnly) {
  // Must the cell be selected or deselected?
  if (td.className && (td.className.indexOf('blinkBg') > -1)) {
    // Stop blinking
    td.className = (td.className == 'blinkBg')? '': td.className.substring(8);
    // Remove entry in the select dict
    if (selectDict) delete selectDict[tdId];
  }
  else if (!unblinkOnly) {
    // Blink
    td.className = (td.className)? `blinkBg ${td.className}`: 'blinkBg';
    // Add entry in the select dict
    if (selectDict) selectDict[tdId] = true;
  }
}

// Called when the user selects a cell in a timeline
function onCell(td, date) {
  // Get the cell ID
  let tr = td.parentNode,
      cellId = `${tr.id}_${date}`,
      // Get the data structure where to store selected cells
      table = tr.parentNode.parentNode,
      selectDict = table['selected'];
  if (!selectDict) {
    selectDict = {};
    table['selected'] = selectDict;
  }
  // (Un)select the cell
  blinkTd(td, cellId, selectDict, false);
}

// Executes a calendar action
function calendarAction(hook, actionName, comment) {
  // Get the calendar table: we have stored select cells on it
  const table = document.getElementById(`${hook}_cal`),
        selectDict = table['selected'],
        selected = (selectDict)? stringFromDict(selectDict, true): '',
        params = {'action': 'executeAction', 'actionName': actionName,
                  'selected': selected,
                  'comment': encodeURIComponent(comment || '')};
  askAjax(hook, null, params);
}

// Unselect all cells in a calendar
function calendarUnselect(hook) {
  // Get the table where selected cells are stored
  let table = document.getElementById(`${hook}_cal`),
      selectDict = table['selected'];
  if (!selectDict) return;
  let elems = null;
  for (let key in selectDict) {
    elems = key.split('_'); // (tr id, date)
    // Get the row containing this cell
    let tr = document.getElementById(elems[0]),
        cells = tr.getElementsByTagName('td');
    for (let i=0; i < cells.length; i++){
      blinkTd(cells[i], null, null, true);
    }
  }
  delete table['selected']; // Delete the whole selectDict
}

function updatePicked(box) {
  // Update the companion, hidden field corresponding to this (check)p_box
  const suffix = (box.checked)? 'on': 'off';
  box.previousSibling.value = `${box.value}_${suffix}`;
}

// Complete and post a "create object" form
function postAndClick(formName, attrs) {
  const f = document.forms[formName];
  f['template_'].value = attrs;
  /* In addition to submitting the form, also evaluate the submit buttons'
     "onclick" expression. */
  f.querySelector('input[type=submit]').onclick();
  f.submit();
}
