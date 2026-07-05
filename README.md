<div align="center">

<h1>
  <img src="https://raw.githubusercontent.com/Wheemer/silence-midealan/main/custom_components/silence_midea_lan/icon.png" width="64" alt="Silence MideaLAN icon" align="center">
  Silence MideaLAN
</h1>

### Keep selected MideaLAN air conditioners quiet in Home Assistant

[![HACS Custom](https://img.shields.io/badge/HACS-CUSTOM-41BDF5?style=for-the-badge&logo=home-assistant&logoColor=white&labelColor=555555)](https://github.com/hacs/integration)
[![Home Assistant Custom Integration](https://img.shields.io/badge/HOME%20ASSISTANT-CUSTOM%20INTEGRATION-41BDF5?style=for-the-badge&logo=home-assistant&logoColor=white&labelColor=555555)](https://www.home-assistant.io/)
[![Latest release](https://img.shields.io/github/v/release/Wheemer/silence-midealan?style=for-the-badge&logo=github&logoColor=white&label=RELEASE&labelColor=555555&color=22C55E)](https://github.com/Wheemer/silence-midealan/releases/latest)
[![Downloads](https://img.shields.io/github/downloads/Wheemer/silence-midealan/total?style=for-the-badge&logo=github&logoColor=white&label=DOWNLOADS&labelColor=555555&color=8A2BE2)](https://github.com/Wheemer/silence-midealan/releases)
[![License: MIT](https://img.shields.io/badge/LICENSE-MIT-64748B?style=for-the-badge&labelColor=555555)](LICENSE)

</div>

## Overview

Silence MideaLAN is a small companion integration for Home Assistant systems
that already use [Midea AC LAN](https://github.com/wuwentao/midea_ac_lan).

Some Midea window air conditioners expose prompt-tone, buzzer, and display
controls, but normal commands or reconnects can allow those settings to drift
back on. Silence MideaLAN adds a guard layer for selected AC device IDs so Home
Assistant keeps the prompt tone, buzzer/sound, and display attributes off.

It is meant for rooms where beeps or panel lights are disruptive, such as a
bedroom AC controlled by a thermostat automation.

## Features

- UI setup and Configure flow.
- Protect one or more MideaLAN AC device IDs.
- Force outgoing Midea AC commands to keep prompt tone, sound, and alternate
  display controls off.
- Watch reported AC state and send a correction if the protected device reports
  sound or alternate display back on.
- Watch MideaLAN prompt-tone and screen-display switches and turn them back off
  when they report on.
- Startup retry guard for reconnect windows after Home Assistant starts.
- Five-minute watchdog for protected prompt-tone and display switches.
- Optional quiet-condition fan guard that keeps a selected climate entity on
  MideaLAN's `silent` fan mode while configured entities are on.

## Requirements

- Home Assistant with custom integrations enabled.
- [Midea AC LAN](https://github.com/wuwentao/midea_ac_lan) installed and working.
- A Midea AC entity backed by Midea AC LAN.
- The MideaLAN numeric device ID for the AC you want to protect.

This integration does not replace Midea AC LAN. It patches the local
`midealocal` AC command path at runtime and uses the entities that Midea AC LAN
already exposes.

## Installation via HACS

[![Open your Home Assistant instance and add this repository to HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Wheemer&repository=silence-midealan&category=integration)

1. Open HACS in Home Assistant.
2. Add this repository as a custom integration repository.

   Repository URL:

   ```text
   https://github.com/Wheemer/silence-midealan
   ```

   Category:

   ```text
   Integration
   ```

3. Download **Silence MideaLAN**.
4. Restart Home Assistant once so the custom integration is loaded.

## Manual Installation

Copy the integration folder into Home Assistant:

```text
/config/custom_components/silence_midea_lan
```

Restart Home Assistant, then add **Silence MideaLAN** from:

```text
Settings > Devices & services > Add integration
```

## Configuration

During setup, enter:

- **Protected MideaLAN device IDs:** one or more numeric Midea device IDs,
  separated by commas or spaces.
- **AC climate entity:** the Midea AC LAN climate entity to keep on silent fan
  mode when the quiet-condition entities are on.
- **Keep silent while these entities are on:** one or more binary sensors,
  input booleans, or other entities that mean the room should stay quiet.

The fan mode is intentionally not configurable. Silence MideaLAN always uses
MideaLAN's `silent` fan mode for the quiet-condition fan guard.

The same fields are available later from:

```text
Settings > Devices & services > Silence MideaLAN > Configure
```

## How It Works

Silence MideaLAN protects selected Midea AC device IDs in a few places:

1. It patches Midea AC LAN's underlying `midealocal` AC device class so outgoing
   AC command messages do not re-enable prompt tone, sound, or alternate display
   controls for protected device IDs.
2. It watches AC status reports. If a protected device reports prompt tone,
   alternate display, or sound back on, it sends a real off command instead of
   falsifying the reported state.
3. It watches the MideaLAN prompt-tone and screen-display switch entities and
   turns them back off when they report on.
4. It retries during startup and checks again every five minutes to cover
   reconnect and power-recovery windows.
5. If configured quiet-condition entities are on and the AC climate entity is
   not off, it sets the AC fan mode to `silent`.

## Power Outages and Limits

Home Assistant can only command the AC after the AC, Wi-Fi, MideaLAN, and Home
Assistant are online enough to communicate. Silence MideaLAN is designed to
correct the AC as soon as Home Assistant can see and command it again.

It cannot prevent any sound or display behavior that the AC firmware performs
before Home Assistant has a network path to the device.

## Troubleshooting

If the AC still beeps:

- Confirm the correct numeric Midea device ID is configured.
- Confirm the Midea AC LAN prompt-tone switch exists and belongs to that device.
- Check whether the beep happened during a power restore before Home Assistant
  could communicate with the AC.
- Enable debug logging for `custom_components.silence_midea_lan` and
  `custom_components.midea_ac_lan` if you need to inspect command timing.

If the fan guard does not switch to `silent`:

- Confirm the configured climate entity supports `silent` in its fan modes.
- Confirm at least one configured quiet-condition entity is currently `on`.
- Confirm the climate entity is not `off`, `unknown`, or `unavailable`.

## Compatibility

Silence MideaLAN depends on Midea AC LAN's current use of the `midealocal`
Python package and its AC device command methods. If Midea AC LAN or
`midealocal` changes those internals, this companion integration may need an
update.

