# Per-SSD collection diagnostics in 0.3.6

Integration-only update; compatible with the existing app 0.3.5. Update through
HACS and restart Home Assistant Core. No app rebuild, new hardware request,
permission change or API token change is needed. Old entities keep their IDs.

Two enabled diagnostic sensors are added to each known SSD device:

- StarTech SSD port 0 SSD collection status
- StarTech SSD port 0 SSD collection error
- StarTech SSD port 1 SSD collection status
- StarTech SSD port 1 SSD collection error

Status is Complete, Error, Disabled, Paused or Unknown. Complete requires verified
SSD identity and valid SMART data and thresholds. Error exposes the current
collector message exactly. None reported is used only after a complete sample.
Stale samples and failed API updates make the sensors unavailable. No last-good
or last-error message is carried forward into a later sample.

When IDENTIFY fails, the port error may have no SSD serial. It is associated
with a uniquely last-known SSD on that port, with identity_verified=false and
attribution=last_known_port. This reports a port observation, not verified drive
identity or drive failure. Ambiguous/replaced identities and controller-wide
query failures produce Unknown rather than assigning an error to the wrong SSD.
On later RAID-only samples after SMART polling pauses, the status is Paused;
restart the app to resume its existing polling policy after investigation.

Attributes include error_message, status, port, identity_verified, attribution
and sample_time_unix. Messages over HA's 255-character state limit use a short
state; the full message remains in error_message. No raw SMART sector is exposed.

## Dashboard instructions for ChatGPT

Use the actual entity IDs exported from HA; never infer IDs from display names.
Add the two diagnostics alongside each SSD, with Error red, Paused/Disabled amber,
Unknown/Unavailable gray, and Complete described as collection succeeded.
Do not equate Complete or None reported with drive health. Keep RAID state,
SMART error warnings and collection reliability separate. For a long message,
display the collection error sensor's error_message attribute in an entity
attribute row or a Markdown card. Treat missing data as Unknown, never healthy.
If attribution=last_known_port, label the message as a port observation with
unverified current SSD identity. Historical states are available through Recorder.

Export the real IDs in Developer tools > Template:

```jinja
{% for entity_id in integration_entities('startech_raid') | sort %}
{{ entity_id }} | {{ state_attr(entity_id, 'friendly_name') or '(disabled/not loaded)' }} | {{ states(entity_id) }}
{% endfor %}
```

The built-in app panel is HTML/JavaScript/CSS, not Lovelace YAML. Its source is
https://github.com/laxity00/startech-raid-app/tree/v0.3.5/startech_raid/web
Use it as a reference when creating ordinary HA dashboard cards.

No live Home Assistant/HAOS validation was performed for this release.


---

# StarTech RAID Monitor 0.3.5 — experimental

Independent read-only RAID and SSD monitoring for the narrowly supported
StarTech SM22BU31C3R / ASM1352R profile. Not affiliated with StarTech or ASMedia.

## Install through Home Assistant

1. Open Settings → Apps → App Store → menu → Repositories. Add:
   https://github.com/laxity00/startech-raid-app
2. Install StarTech RAID Monitor. The app builds its image from the supplied
   source using the official Home Assistant base and Alpine packages.
3. Start it and inspect its logs. Open Web UI → Configuration and note the
   internal hostname, port 8098 and generated token. Keep that token private.
4. In HACS → menu → Custom repositories, add https://github.com/laxity00/startech-raid-integration, category
   Integration. Download StarTech RAID Monitor and restart Home Assistant Core.
5. Settings → Devices & services → Add integration → StarTech RAID Monitor.
   Enter the hostname shown by the app, port and token. Enable Start on boot
   only after the app has collected a fresh valid sample.

Do not run older collectors concurrently. Preserve backups and previous versions.
The repositories must actually be published before these links can be installed.

## Supported profile and limitations

Only aarch64 HAOS and the fixed /dev/sda, USB 174c:55aa, factory-style USB serial
of nineteen zeroes followed by one, SCSI StarTech / RAID 1 / revision 0 and
firmware 161028_B5_30_81 are supported. Identity mismatch stops collection.
This is not a general ASM1352R firmware scanner or autodiscovery tool.

RAID states: 1 - Healthy; 2 - Degraded; 3 - Failed; 4 - Rebuilding;
other values - Unknown. Labels come from static firmware analysis. Only raw state
1 has runtime evidence; degraded/failed/rebuilding physical conditions remain
untested. A matching version does not verify complete firmware identity.
SMART overall remains Unknown. Pre-fail thresholds and provisional temperatures
are reported separately. There are no self-tests, writes, firmware operations,
arbitrary commands or automatic retries. See the full app guide for details.

## Validation status

The original fixed monitor reads succeeded on one installation. Offline mock,
CLI, app HTTP and integration contract tests passed for the clean source subset.
The GitHub workflow builds and smoke-tests the ARM64 app image without devices.
That workflow's result, HAOS permissions, integration lifecycle and physical
installation must be verified before calling this a validated public release.
No successful cloud build or physical app installation is implied by this README.

## Data and licensing

Published source contains no original device captures, SSD identities, credentials,
vendor firmware or utilities. Runtime SSD serials and credentials are private data;
do not attach backups, raw logs or tokens to issues. Authored code is MIT licensed.
See LICENSE and THIRD_PARTY.md. The source is original interoperability code;
the container's third-party components retain their own licences.

## Documentation

Full app guide: https://github.com/laxity00/startech-raid-app/blob/main/startech_raid/DOCS.md
App issues: https://github.com/laxity00/startech-raid-app/issues
Integration issues: https://github.com/laxity00/startech-raid-integration/issues

## SMART labels and warning entities in 0.3.5

Update both the app and HACS integration, then restart Home Assistant Core.
The app reads the controller signature from the already collected SMART sector;
no additional hardware commands or permissions are added. Labels apply only to
the SMI2259XT signature with SSD firmware Y0507A0. They are inferred from family
documentation, not an Integral-certified attribute specification. Other drives
retain generic raw labels and these extra warning states remain Unknown.

All 30 attributes receive candidate names for this profile. Raw values stay raw:
241/242/245 are not converted into bytes, and no write amplification is calculated.
The candidate life percentage is raw attribute 169, not normalized Current=100.
Initial bad blocks (163), rated erase ceiling (168), corrected ECC (195), power
events (192), and workload counters do not alone trigger media failure warnings.

Enabled by default per SSD: media error indicators (any nonzero value among
5/160/175/176/178/181/182/196/197/198), interface CRC errors (199), and estimated
remaining life at or below 20% (169, valid range 0..100). These supplement the
existing pre-fail threshold and user temperature warnings. Counters may record
historical events: an On warning means investigate, not that failure is imminent.
Missing or invalid evidence is Unknown/unavailable. SMART overall stays Unknown.

Raw counters 5/9/160/161/169/175/176/178/181/182/196/197/198/199 are now enabled
for matched drives. Existing unique IDs and entity IDs are preserved. Counters
disabled by the integration are enabled on update; user-disabled entities stay
disabled. No notifications are sent automatically. Select these problem entities
in an HA automation if you want alerts, including collection and RAID problems.
Add any sensor to an editable dashboard through Add card > By entity. Temperature
already supports history/statistics; raw vendor counters have no invented units.

SMART table expansion is preserved independently for each port across the
15-second page refresh and navigation within the current page session.

Sources: [Transcend MTS960T v1.4 tables 18/19](https://docs.rs-online.com/3aeb/A700000012186708.pdf),
[smartmontools database](https://github.com/smartmontools/smartmontools/blob/master/smartmontools/drivedb.h).
No vendor firmware, captures, identifiers or third-party implementation is bundled.
