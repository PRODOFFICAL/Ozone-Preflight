import os
import csv
import requests
from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from datetime import datetime

app = Flask(__name__)
app.secret_key = "your_secret_key"

# The Blue Alliance API settings
TBA_API_KEY = "your_tba_api_key"  # Replace with your TBA API key
TBA_TEAM_KEY = "frc4611"  # Replace with your team key
TBA_URL = f"https://www.thebluealliance.com/api/v3/team/{TBA_TEAM_KEY}/events/2024/matches"  # Replace 2024 with the current year

# Initialize checklist items
checklist = {
    "can_dust": False,
    "ratchet_pins": False,
    "rope": False,
    "funnel_down": False,
    "barb_wiggle": False,
    "wheel_alignment": False,
    "elevator_down": False,
    "fresh_battery": False,
    "battery_beaked": False,
    "intake_funnel": False,
    "intake_arm": False,
}

# Initialize initial section items
initial_checks = {
    "robot_powered": False,
    "radio_connected": False,
    "driver_station_ready": False,
}

# Ensure logs directory exists
if not os.path.exists("logs"):
    os.makedirs("logs")

def get_matches(manual_selection=False):
    """Fetch matches for team 4611 or generate matches for manual selection."""
    headers = {"X-TBA-Auth-Key": TBA_API_KEY}
    if not manual_selection:
        # Fetch matches where team 4611 is participating
        response = requests.get(TBA_URL, headers=headers)
        if response.status_code == 200:
            matches = response.json()
            filtered_matches = []
            for match in matches:
                if TBA_TEAM_KEY in match["alliances"]["red"]["team_keys"] or TBA_TEAM_KEY in match["alliances"]["blue"]["team_keys"]:
                    filtered_matches.append(match)
            return filtered_matches
    else:
        # Generate matches for manual selection
        matches = []
        # Add 60 qualification matches
        for i in range(1, 61):
            matches.append({
                "key": f"qm{i}",
                "comp_level": "qm",
                "match_number": i,
            })
        # Add 5 playoff rounds (quarterfinals, semifinals, finals)
        for level in ["qf", "sf", "f"]:
            for i in range(1, 6 if level != "f" else 4):  # 5 matches for qf/sf, 3 for finals
                matches.append({
                    "key": f"{level}m{i}",
                    "comp_level": level,
                    "match_number": i,
                })
        return matches
    return []
@app.route("/", methods=["GET", "POST"])
def index():
    manual_selection = request.form.get("manual_selection") == "on"
    matches = get_matches(manual_selection)
    selected_match = None

    if request.method == "POST":
        if "reset" in request.form:
            # Reset checklist and initial checks
            for item in checklist:
                checklist[item] = False
            for item in initial_checks:
                initial_checks[item] = False
            flash("Checklist and initial checks reset.", "info")
        else:
            # Update checklist and initial checks based on form submission
            for item in checklist:
                checklist[item] = request.form.get(item) == "on"
            for item in initial_checks:
                initial_checks[item] = request.form.get(item) == "on"

            # Get the selected match
            selected_match = request.form.get("match_select")
            if selected_match:
                selected_match = next((m for m in matches if m["key"] == selected_match), None)

            # Log the checklist and initial checks status to a CSV file
            log_filename = f"logs/preflight_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            with open(log_filename, "w", newline="") as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(["Match", "Timestamp", "Section", "Checklist Item", "Status"])
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                for item, status in initial_checks.items():
                    writer.writerow([
                        selected_match["key"] if selected_match else "N/A",
                        timestamp,
                        "Initial Checks",
                        item.replace("_", " ").title(),
                        "Completed" if status else "Not Completed",
                    ])
                for item, status in checklist.items():
                    writer.writerow([
                        selected_match["key"] if selected_match else "N/A",
                        timestamp,
                        "Preflight Checklist",
                        item.replace("_", " ").title(),
                        "Completed" if status else "Not Completed",
                    ])

            # Check if all items are completed
            if all(checklist.values()) and all(initial_checks.values()):
                flash("All checks completed! Robot is ready.", "success")
            else:
                flash("Please complete all checks before confirming.", "warning")

        return redirect(url_for("index"))

    return render_template("index.html", checklist=checklist, initial_checks=initial_checks, matches=matches, manual_selection=manual_selection)

@app.route("/download_logs")
def download_logs():
    """Download all logs as a ZIP file."""
    import zipfile
    from io import BytesIO

    memory_file = BytesIO()
    with zipfile.ZipFile(memory_file, "w") as zipf:
        for root, _, files in os.walk("logs"):
            for file in files:
                zipf.write(os.path.join(root, file), file)
    memory_file.seek(0)
    return send_file(memory_file, download_name="preflight_logs.zip", as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")