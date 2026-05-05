# FUxA Integration Guide

This guide covers how to use **FUxA** (`@frangoteam/fuxa-min`) as a visualization front-end for Vox-Dispatcher's MQTT output. It includes project import/export instructions and Windows troubleshooting steps for `fuxa-min` version **1.3.1**.

---

## Contents

1. [Prerequisites](#prerequisites)
2. [Installing and Starting FUxA](#installing-and-starting-fuxa)
3. [Importing a Project JSON (e.g. SnakeMonitor.json)](#importing-a-project-json)
4. [Exporting a Project JSON](#exporting-a-project-json)
5. [Troubleshooting: Project Appears Locked](#troubleshooting-project-appears-locked)
6. [Troubleshooting: Resetting dbDir on Windows](#troubleshooting-resetting-dbdir-on-windows)
7. [MQTT Topics Used by This Integration](#mqtt-topics-used-by-this-integration)

---

## Prerequisites

| Requirement | Version |
|-------------|---------|
| Node.js | 18 LTS or later |
| npm | bundled with Node.js |
| `@frangoteam/fuxa-min` | 1.3.1 |
| MQTT broker | Mosquitto 2.x or any MQTT 3.1.1/5 broker |

Install FUxA globally (run once):

```powershell
npm install -g @frangoteam/fuxa-min@1.3.1
```

---

## Installing and Starting FUxA

### Verify the installation

```powershell
npm list -g --depth=0
```

You should see `@frangoteam/fuxa-min@1.3.1` in the list.

### Start FUxA

```powershell
npx @frangoteam/fuxa-min
```

Expected startup output:

```
FUXA V.1.3.1
FUXA init in  66ms.
'FUXA' created
'FUXA' start
FUXA started!
WebServer is running http://127.0.0.1:1881/
```

Open `http://127.0.0.1:1881/` in your browser (Chrome or Edge recommended).

---

## Importing a Project JSON

A FUxA project JSON (e.g. `SnakeMonitor.json`) captures all devices, tags, views, and dashboard layout.

### Step 1 — Open the project menu

In the FUxA UI (top toolbar):

- Click the **hamburger menu** (☰) in the top-left, then choose **Project** → **Open / Import**.

### Step 2 — Load the JSON file

In the dialog that appears:

1. Click **Browse** (or drag-and-drop `SnakeMonitor.json` onto the dialog).
2. Click **Open**.

FUxA will parse the file and load all devices and views.

### Step 3 — Confirm devices are active

After import, open the **Device** panel (left sidebar). Each device should show a green status indicator once the broker is reachable. If a device shows red:

- Confirm the MQTT broker is running (`127.0.0.1:1883` by default).
- Check that the broker address in the device settings matches your actual broker host/port.

### Step 4 — Save permanently

FUxA stores the imported project in its local DB automatically. You can also use **Project → Save** to force-persist.

---

## Exporting a Project JSON

Export creates a portable `<project-name>.json` snapshot you can share or version-control.

1. In the FUxA UI, click **☰ → Project → Export**.
2. A file download dialog will appear. Save the file (e.g. `SnakeMonitor.json`) to your preferred location.
3. Commit the exported JSON to your repository for reproducible setup.

> **Tip:** After adding even one MQTT device and one tag in the UI, export immediately. Use that exported file as the base for any bulk-editing (add more tags by duplicating the same structure). This avoids schema mismatch errors that occur when hand-crafting a project JSON from scratch.

---

## Troubleshooting: Project Appears Locked

**Symptom:** The FUxA UI loads but shows the project name (e.g. `snake-ai-scada`) with a **locked** badge and does not allow editing.

**Root cause:** FUxA stores the last-opened project in its local database (`dbDir`). A stale lock record (left from a previous crashed or force-closed FUxA session) causes this.

### Fix A — Clear browser site data (fastest)

1. Open `http://127.0.0.1:1881/` in Chrome or Edge.
2. Press **F12** → **Application** tab → **Storage** (left panel).
3. Click **Clear site data** (ensure Local Storage, IndexedDB, and Cache Storage are all ticked).
4. Close the DevTools, then close and reopen the tab.
5. Restart FUxA (`Ctrl+C` → `npx @frangoteam/fuxa-min`).

### Fix B — Rename the dbDir (guaranteed unlock)

Use this if Fix A does not work. See the [next section](#troubleshooting-resetting-dbdir-on-windows) for the full steps.

---

## Troubleshooting: Resetting dbDir on Windows

FUxA stores its project database in a `dbDir` folder. On Windows with a global npm install the default location is:

```
C:\Users\<YourUsername>\AppData\Roaming\fuxa\
```

### Step 1 — Find your exact dbDir path

With FUxA running, open PowerShell and run:

```powershell
$s = Invoke-RestMethod http://127.0.0.1:1881/api/settings
$s.dbDir
```

This prints the exact path FUxA is using, for example:

```
C:\Users\can.oz\AppData\Roaming\fuxa
```

### Step 2 — Stop FUxA

In the terminal where FUxA is running, press **Ctrl + C**.

### Step 3 — Rename (not delete) the dbDir

Replace `C:\Users\can.oz\AppData\Roaming\fuxa` with the path you retrieved above:

```powershell
Rename-Item `
  -Path  "C:\Users\can.oz\AppData\Roaming\fuxa" `
  -NewName "fuxa-backup-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
```

This renames the folder instead of deleting it so you can restore it later if needed.

### Step 4 — Restart FUxA

```powershell
npx @frangoteam/fuxa-min
```

FUxA will create a fresh, empty database. The UI will open cleanly with no locked project.

### Step 5 — Re-import your project

Follow [Importing a Project JSON](#importing-a-project-json) to reload `SnakeMonitor.json` (or any other project backup).

### Restoring the old database

If you need to recover the previous state, stop FUxA, rename the fresh `fuxa` folder out of the way, and rename your backup folder back to `fuxa`:

```powershell
# Stop FUxA first (Ctrl+C)
Rename-Item "C:\Users\can.oz\AppData\Roaming\fuxa" "fuxa-fresh"
Rename-Item "C:\Users\can.oz\AppData\Roaming\fuxa-backup-20260503-213057" "fuxa"
npx @frangoteam/fuxa-min
```

---

## MQTT Topics Used by This Integration

When Vox-Dispatcher and FUxA are used together, the following MQTT topics are in play:

| Direction | Topic | Description |
|-----------|-------|-------------|
| Vox-Dispatcher → broker | `vox/output/text` (default) | Structured JSON action payload from the LLM |
| FUxA subscription | configure per device in FUxA UI | FUxA subscribes to topics for tag values |
| Application → broker | e.g. `snake/score` | Application-specific telemetry topics |

Configure the FUxA MQTT device to subscribe to the same topics your application publishes. For the Snake AI example, create tags mapped to topics such as `snake/score`, `snake/state`, etc.

To override the Vox-Dispatcher output topic, set the environment variable before starting `app.py`:

```powershell
$env:MQTT_OUTPUT_TEXT_TOPIC = "vox/output/text"
python app.py
```
