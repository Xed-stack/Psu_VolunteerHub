
document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById('field-date')?.form;
    const fields = {
        date: document.getElementById("field-date"),
        end_date: document.getElementById("field-end_date")
    };
    const displays = {
        date: document.getElementById("schedule-start-display"),
        end_date: document.getElementById("schedule-end-display")
    };
    const errors = {
        date: document.getElementById("start-date-error"),
        end_date: document.getElementById("end-date-error")
    };
    const dialog = document.getElementById("schedule-picker");
    const pickerDate = document.getElementById("schedule-picker-date");
    const hourInput = document.getElementById("schedule-picker-hour");
    const minuteInput = document.getElementById("schedule-picker-minute");
    const periodInput = document.getElementById("schedule-picker-period");
    const timeInputs = {hour:hourInput, minute:minuteInput};
    const timeOptions = {
        hour: document.getElementById("schedule-hour-options"),
        minute: document.getElementById("schedule-minute-options")
    };
    let openTimeList = null;
    const pickerError = document.getElementById("schedule-picker-error");
    let active = null;
    if (!form || !fields.date || !fields.end_date || !dialog) return;
    for (const key of ['date','end_date']) {
        fields[key].hidden = true;
        fields[key].required = false;
        displays[key].hidden = false;
        form.querySelector(`[data-schedule-label="${key}"]`)?.setAttribute('for', displays[key].id);
    }
    pickerDate.required = false;

    // Calendar components in Asia/Manila. Philippine civil time is UTC+08:00.
    const phParts = new Intl.DateTimeFormat("en-CA", {
        timeZone: "Asia/Manila", year:"numeric", month:"2-digit", day:"2-digit",
        hour:"2-digit", minute:"2-digit", hourCycle:"h23"
    });
    function philippineNow() {
        const p = Object.fromEntries(phParts.formatToParts(new Date()).filter(x => x.type !== "literal").map(x => [x.type,x.value]));
        return `${p.year}-${p.month}-${p.day}T${p.hour}:${p.minute}`;
    }
    function futureMinimum() {
        // Next whole minute in Philippine time.
        const p = Object.fromEntries(phParts.formatToParts(new Date(Date.now()+60000)).filter(x => x.type !== "literal").map(x => [x.type,x.value]));
        return `${p.year}-${p.month}-${p.day}T${p.hour}:${p.minute}`;
    }
    function human(iso) {
        if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(iso || "")) return "";
        const [d,t] = iso.split("T");
        const [y,m,day] = d.split("-").map(Number);
        const [hh,mm] = t.split(":").map(Number);
        const month = new Intl.DateTimeFormat("en-US",{month:"short",timeZone:"UTC"}).format(new Date(Date.UTC(y,m-1,day)));
        return `${month} ${day}, ${y}, ${hh%12 || 12}:${String(mm).padStart(2,"0")} ${hh<12?"AM":"PM"}`;
    }
    function clockText(iso) {
        if (!iso) return "";
        const [hh,mm] = iso.slice(11).split(":").map(Number);
        return `${hh%12||12}:${String(mm).padStart(2,"0")} ${hh<12?"AM":"PM"}`;
    }
    function validTime() {
        const h = hourInput.value.trim();
        const m = minuteInput.value.trim();
        if (!/^\d{1,2}$/.test(h) || !/^\d{1,2}$/.test(m)) return null;
        const hour = Number(h), minute = Number(m);
        if (hour < 1 || hour > 12 || minute < 0 || minute > 59) return null;
        const hour24 = hour % 12 + (periodInput.value === "PM" ? 12 : 0);
        return `${String(hour24).padStart(2,"0")}:${String(minute).padStart(2,"0")}`;
    }
    function closeTimeList() {
        for (const unit of ["hour","minute"]) {
        timeOptions[unit].hidden = true;
        timeInputs[unit].setAttribute("aria-expanded","false");
        }
        openTimeList = null;
    }
    function renderTimeList(unit) {
        const input = timeInputs[unit];
        const options = timeOptions[unit];
        const max = unit === "hour" ? 12 : 59;
        const min = unit === "hour" ? 1 : 0;
        const filter = input.value.trim();
        options.replaceChildren();
        for (let n = min; n <= max; n++) {
        const value = String(n).padStart(2,"0");
        // When editing, allow an exact match or partially typed number.
        if (filter && !value.includes(filter) && String(n) !== filter) continue;
        const option = document.createElement("button");
        option.type = "button";
        option.tabIndex = -1;
        option.setAttribute("role","option");
        option.setAttribute("aria-selected",String(Number(filter)===n));
        option.textContent = value;
        option.addEventListener("click", () => {
            input.value = value;
            showPickerError("");
            input.focus();
            closeTimeList();
        });
        option.addEventListener('keydown', event => {
            const items = [...options.children], index = items.indexOf(option);
            if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
                event.preventDefault();
                items[(index + (event.key === 'ArrowDown' ? 1 : items.length-1)) % items.length].focus();
            } else if (event.key === 'Escape') {
                event.preventDefault(); event.stopPropagation(); input.focus(); closeTimeList();
            }
        });
        options.appendChild(option);
        }
        options.hidden = false;
        input.setAttribute("aria-expanded","true");
        openTimeList = unit;
    }
    for (const unit of ["hour","minute"]) {
        const input = timeInputs[unit];
        input.addEventListener("focus", () => {closeTimeList();renderTimeList(unit);});
        input.addEventListener("input", () => {
        input.value = input.value.replace(/\D/g,"").slice(0,2);
        showPickerError("");
        closeTimeList();
        renderTimeList(unit);
        });
        input.addEventListener("keydown", event => {
        if (event.key === 'ArrowDown') {
            event.preventDefault(); renderTimeList(unit); timeOptions[unit].firstElementChild?.focus();
        }
        if (event.key === "Escape") { closeTimeList(); event.stopPropagation(); }
        if (event.key === "Enter") { event.preventDefault(); closeTimeList(); confirmPicker(); }
        });
        document.querySelector(`[data-time-toggle="${unit}"]`).addEventListener("click", () => {
        if (openTimeList === unit) {closeTimeList();return;}
        closeTimeList();
        // Show entire list on explicit arrow click even when value is present.
        const saved = input.value;
        input.value = "";
        renderTimeList(unit);
        input.value = saved;
        });
    }
    document.addEventListener("pointerdown", event => {
        if (!event.target.closest(".schedule-time-combo")) closeTimeList();
    });
    periodInput.addEventListener("change",()=>showPickerError(""));
    function message(field, text) {
        errors[field].textContent = text;
        errors[field].hidden = !text;
        displays[field].setAttribute("aria-invalid",text ? "true":"false");
    }
    function validate(showRequired=false) {
        const now = futureMinimum();
        const start = fields.date.value;
        const end = fields.end_date.value;
        const current = human(philippineNow());
        let startError = "", endError = "";
        if (!start && showRequired) startError = "Choose a Start Date and Time.";
        if (start && start < now) startError = `Start must be in the future. Current Philippine time: ${current}.`;
        if (!end && showRequired) endError = "Choose an End Date and Time.";
        if (start && end && end <= start) endError = `End must be later than the Start Date and Time (${human(start)}).`;
        message("date",startError);
        message("end_date",endError);
        return !(startError || endError || !start || !end);
    }
    function refreshDisplays() {
        for (const key of ["date","end_date"]) {
        displays[key].textContent = human(fields[key].value) || `Select ${key==="date"?"start":"end"} date and time`;
        }
        validate(false);
    }
    function showPickerError(text) {
        pickerError.textContent = text;
        pickerError.hidden = !text;
    }
    function openPicker(which) {
        active = which;
        const existing = fields[which].value;
        document.getElementById("schedule-picker-heading").textContent = which==="date"?"Choose Start Date and Time":"Choose End Date and Time";
        pickerDate.value = existing ? existing.slice(0,10) : (which==="end_date" && fields.date.value ? fields.date.value.slice(0,10) : philippineNow().slice(0,10));
        const displayTime = clockText(existing || (which === "date" ? futureMinimum() : (fields.date.value || futureMinimum())));
        const parts = displayTime.match(/^(\d{1,2}):(\d{2}) (AM|PM)$/);
        hourInput.value = parts ? parts[1].padStart(2,"0") : "08";
        minuteInput.value = parts ? parts[2] : "00";
        periodInput.value = parts ? parts[3] : "AM";
        closeTimeList();
        pickerDate.min = which==="date" ? philippineNow().slice(0,10) : (fields.date.value || philippineNow()).slice(0,10);
        showPickerError("");
        dialog.showModal();
    }
    displays.date.addEventListener("click",()=>openPicker("date"));
    displays.end_date.addEventListener("click",()=>openPicker("end_date"));
    document.getElementById("schedule-picker-cancel").addEventListener("click",()=>{closeTimeList();dialog.close();});
    function confirmPicker() {
        if (!pickerDate.value) return showPickerError("Select a calendar date.");
        const time = validTime();
        if (!time) return showPickerError("Enter an hour from 01 to 12 and a minute from 00 to 59.");
        const value = `${pickerDate.value}T${time}`;
        if (active==="date" && value < futureMinimum()) {
        return showPickerError(`Start must be in the future. Current Philippine time: ${human(philippineNow())}.`);
        }
        if (active==="end_date" && fields.date.value && value <= fields.date.value) {
        return showPickerError(`End must be later than Start (${human(fields.date.value)}).`);
        }
        fields[active].value = value;
        fields[active].dispatchEvent(new Event("input",{bubbles:true}));
        fields[active].dispatchEvent(new Event("change",{bubbles:true}));
        refreshDisplays();
        closeTimeList();
        dialog.close();
    }
    document.getElementById("schedule-picker-confirm").addEventListener("click",confirmPicker);
    pickerDate.addEventListener("input",()=>showPickerError(""));
    for (const field of Object.values(fields)) field.addEventListener("change",refreshDisplays);
    form.addEventListener("submit",event=>{
        if (event.submitter?.formNoValidate) return;
        if (!validate(true)) {
        event.preventDefault();
        event.stopImmediatePropagation();
        const first = errors.date.hidden ? "end_date":"date";
        displays[first].focus();
        displays[first].scrollIntoView({block:'center'});
        }
    },true);
    window.addEventListener("focus",()=>validate(false));
    refreshDisplays();
    // Draft restoration may run after this script. Recheck after page becomes fully loaded.
    window.addEventListener("load",refreshDisplays);
    form.addEventListener('draft:restored',refreshDisplays);
    for (const field of Object.values(fields)) field.addEventListener('input',refreshDisplays);
});
