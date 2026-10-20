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
