let guestData = {};

async function fetchNow() {
    try {
        const response = await fetch('https://worldtimeapi.org/api/timezone/Etc/UTC');
        const data = await response.json();
        return new Date(data.utc_datetime);
    } catch (error) {
        console.error("Failed to fetch time", error);
        return new Date();
    }
}

async function fetchGuests() {
    try {
        const response = await fetch('guests.json');
        guestData = await response.json();
        return guestData;
    } catch (error) {
        console.error("Failed to fetch guest data", error);
        return {};
    }
}

function validatePhoneNumber(phoneNumber) {
    const cleanedNumber = phoneNumber.replace(/\s+/g, '');
    const phoneRegex = /^\+49\d{10}$/;
    return phoneRegex.test(cleanedNumber);
}

async function updateGuestStatus() {
    const [now, guests] = await Promise.all([fetchNow(), fetchGuests()]);

    const guestContainer = document.querySelector(".guest-buttons");
    guestContainer.innerHTML = ""; // Clear existing buttons

    for (const guest in guests) {
        const button = document.createElement("button");
        button.className = "item left-align";
        button.dataset.guest = guest;
        button.onclick = () => showDetails(guest);

        const statusCircle = document.createElement("span");
        statusCircle.className = "status-circle";

        const fromDate = new Date(guests[guest].allowedFrom);
        const untilDate = new Date(guests[guest].allowedUntil);

        statusCircle.style.backgroundColor = (now >= fromDate && now <= untilDate) ? "green" : "red";

        button.appendChild(statusCircle);
        button.appendChild(document.createTextNode(guest));
        guestContainer.appendChild(button);
    }
}

async function showDetails(guest) {
    const guests = await fetchGuests();

    const detailsSection = document.querySelector(".details");
    if (guests[guest]) {
        detailsSection.innerHTML = `
            <div class="item">Phone Number: <span contenteditable="true" onblur="editPhoneNumber('${guest}', this.textContent)">${guests[guest].phone}</span></div>
            <div class="item">Allowed From: ${guests[guest].allowedFrom}</div>
            <div class="item">Allowed Until: ${guests[guest].allowedUntil}</div>
        `;
    } else {
        detailsSection.innerHTML = "<div class='item'>No details available</div>";
    }
}

function editPhoneNumber(guest, newPhoneNumber) {
    const cleanedNumber = newPhoneNumber.replace(/\s+/g, '');
    if (!validatePhoneNumber(cleanedNumber)) {
        alert("Invalid phone number format. Use +49 XXX XXX XXXX.");
        return;
    }
    guestData[guest].phone = cleanedNumber;
    console.log(`Updated phone number for ${guest}: ${cleanedNumber}`);
}

function addGuest() {
    const guestName = prompt("Enter guest name:");
    const phone = prompt("Enter phone number (+49 XXX XXX XXXX):");
    const cleanedPhone = phone.replace(/\s+/g, '');
    if (!guestName || !validatePhoneNumber(cleanedPhone)) {
        alert("Invalid input.");
        return;
    }
    guestData[guestName] = {
        phone: cleanedPhone,
        allowedFrom: "2024-12-01T09:00:00",
        allowedUntil: "2024-12-01T18:00:00"
    };
    saveGuestsToServer();
    updateGuestStatus();
}

async function saveGuestsToServer() {
    try {
        const response = await fetch('/save-guests', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(guestData)
        });
        if (!response.ok) throw new Error('Failed to save guests');
        console.log('Guest list saved successfully');
    } catch (error) {
        console.error('Error saving guest list:', error);
    }
}

function exportGuestList() {
    const blob = new Blob([JSON.stringify(guestData, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "guests.json";
    a.click();
    URL.revokeObjectURL(url);
}

function importGuestList() {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".json";
    input.onchange = (event) => {
        const file = event.target.files[0];
        const reader = new FileReader();
        reader.onload = async () => {
            try {
                guestData = JSON.parse(reader.result);
                await saveGuestsToServer(); // Save imported data
                updateGuestStatus();
            } catch (error) {
                console.error('Error importing guest list:', error);
            }
        };
        reader.readAsText(file);
    };
    input.click();
}

function updateTimeDisplay() {
    const nowDisplay = document.getElementById("now-display");
    setInterval(async () => {
        const now = await fetchNow();
        nowDisplay.textContent = `Current Time: ${now.toUTCString()}`;
    }, 1000);
}

document.addEventListener("DOMContentLoaded", () => {
    updateGuestStatus();
    updateTimeDisplay();
});
