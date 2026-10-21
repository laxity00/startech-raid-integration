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
