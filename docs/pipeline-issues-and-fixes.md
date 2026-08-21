# Pipeline Issues & Fixes Log

Living log of pipeline/config issues investigated on this project, their root
causes, and what was done about them. Append new entries at the top. See
[team/ROSTER.md](../team/ROSTER.md) for who's who — technical entries below
were investigated as [Tom](../team/tom.md); staffing/policy calls are flagged
for [Vikki](../team/vikki.md).

---

## 2026-08-20 — Asset-context Maya session: menu loss, publish failure, cross-version scene corruption

**Reported by:** Adam Benson, working the `FrootLoopEyes` asset (PRP), Rig step,
then `LPG102_002_080` shot, Lighting step.

### Issue 1 — Publish/Loader/Snapshot/File Save menus disappear after File Open

**Symptom:** Launching Maya from a Task (with Step assigned) showed the full
toolkit menu correctly. The instant `File Open` was used to open the asset's
work file, the menu collapsed to just `File Open` — Publish, Loader, Snapshot,
File Save all vanished.

**Root cause:** Case mismatch between the folder-creation schema and the path
templates:
- `config/core/templates.yml` → `asset_root: Assets/{sg_asset_type}/{Asset}/{Step}` (capital **A**)
- `config/core/schema/project/assets` (folder-creation schema, pre-fix) was lowercase **a**ssets

Windows' case-insensitive filesystem let folders/files save and open fine, but
Toolkit's **path cache** (SQLite db mapping disk paths back to ShotGrid
entities) stores paths exactly as the schema created them — lowercase. When
`tk-multi-workfiles2` opens a file, it builds the path via `templates.yml`
(capital `Assets`) and asks `sgtk.context_from_path()` to resolve context from
it. That's a case-sensitive lookup against the path cache, so `Assets` ≠
`assets` → no match → context silently degrades to Project-only → engine
reloads into the bare `project` environment, which only has `File Open`.

Confirmed via `tk-maya.log` with `debug_logging` temporarily enabled: the
engine explicitly logged switching from the full `asset_step` context down to
`Entity: None / Step: None / Task: None` right after the File Open action,
with no error — a silent degrade, not a crash.

**Fix applied:**
- Renamed `config/core/schema/project/assets` → `Assets` (git-tracked, matches
  `templates.yml` capitalization for all future folder creation).
- Patched the local `path_cache.db`
  (`%APPDATA%\Shotgun\<site>\p91c67\path_cache.db`) additively — inserted
  corrected-case (`/Assets/...`) rows alongside the existing stale lowercase
  rows for every Asset-side entry, for `FrootLoopEyes` first, then swept the
  rest (53 lowercase rows found, 30 needed a new corrected row inserted; 23
  already had one from an earlier partial fix). No rows deleted, nothing on
  the Shot side touched (Shots use a different schema branch and were
  unaffected throughout).

**Follow-up:** New assets created from here on are fine automatically. Any
*other* pipeline configuration / artist machine's local path cache that still
only has the lowercase rows for older assets will need the same treatment —
either re-run **Create Folders** in ShotGrid on the affected Task/Asset (the
supported route; also fixes ShotGrid's event log so other machines sync
correctly), or a manual cache patch like the one done here.

### Issue 2 — File Open not auto-launching at Maya startup

**Symptom:** Separate from Issue 1 — File Open used to auto-launch when
entering an asset/shot context in some environments but not others.

**Root cause:** `settings.tk-multi-workfiles2.maya.asset_step` and
`.shot_step` (in `config/env/includes/settings/tk-multi-workfiles2.yml`) were
missing `launch_at_startup: true`, unlike the plain `asset`/`shot`/`project`
environments which reference a dedicated `launch_at_startup` settings block.

**Fix applied:** Added `launch_at_startup: true` directly to both the
`maya.asset_step` and `maya.shot_step` blocks.

### Issue 3 — Publish fails: "missing keys required for the publish template: ['name']"

**Symptom:** Publishing a Maya asset session failed validation on the
"Publish Session Geometry" (Alembic cache) plugin.

**Root cause:** Template field mismatch in `config/core/templates.yml`:
- `maya_asset_work` → `{code}_{Asset}_{sg_asset_type}_{Step}_v{version}.{maya_extension}` (no `{name}` field)
- `asset_alembic_cache` (old) → `{name}.v{version}.abc` (**requires** `{name}`)

The stock `publish_session_geometry.py` hook extracts fields from the current
scene path via the *work* template, then applies those same fields to the
*publish* template — it never supplies a `name` itself (unlike Nuke/Houdini/AE
templates elsewhere in this config, which get `{name}` from a node/comp name
via their own collectors). Since `maya_asset_work` never produces `name`,
`asset_alembic_cache` could never resolve — every asset geometry publish hit
this error. Confirmed the same broken reference exists in
`settings.tk-multi-publish2.3dsmax.asset_step`.

**Fix applied:** Redefined `asset_alembic_cache` to
`{code}_{Asset}_{sg_asset_type}_{Step}_v{version}.abc`, matching every other
asset-side publish template's naming convention (e.g. `maya_asset_publish`)
and using only fields `maya_asset_work` actually produces.

**Noted, not fixed (out of scope):** `settings.tk-multi-publish2.3dsmax.asset_step`
references a `Work Template: max_asset_work` that **does not exist anywhere**
in `templates.yml` — 3ds Max asset publishing is broken independently of the
above and was not touched this session.

### Issue 4 — Maya cross-version scene corruption (2025.1 ↔ 2025.3)

**Symptom:** Opening a scene last saved on a 2025.3 install into a 2025.1
install (and then reopening that same file back on 2025.1 later) produced:
a Maya "file could not be verified as safe" PySide/Qt security popup (never
seen before on that machine), `Invalid flag '-tangentScale'` errors, dependency
graph `Cycle` warnings, and an explicit `Errors have occurred while reading
this scene that may result in data loss` warning. The Maya log's key line:

```
# Error: file: .../LPG102_002_080_LGT_v001.ma line 13: Unknown Maya file version: 2025ff03.
```

**Root cause:** Maya forward/backward file-format compatibility limitation
between point releases — `2025ff03` is a file-format version stamp written by
2025.3 that 2025.1 doesn't recognize. Maya force-parses the file best-effort
anyway, producing the cascading flag/cycle/data-loss errors. **Not a tk-config
issue** — nothing in this repo touches Maya's own file format or its scene
security scanning. Separately reported render failures (EXR/PNG both failing
immediately with "Permission Denied," on a newly-migrated render server) are
still unconfirmed/pending a clean re-test — not yet tied to this or any other
root cause.

**Status: Resolved (2026-08-21).** No config changes made or needed — this
was never a tk-config issue. Adam upgraded both machines so all Maya
installs on this project are now on a consistent version, closing the
version-pinning gap that caused the cross-version corruption. Recommendations
for the record:
- **Technical (Tom):** the specific file that got touched by the version
  mismatch (`LPG102_002_080_LGT_v001.ma`) may still carry the flag/cycle
  data-loss damage logged above from the 2025.1 force-parse — worth a scene
  health check (re-open, check Script Editor for residual errors, verify the
  rig connections that threw the Cycle warnings) next time it's opened, rather
  than assuming the version fix alone repaired already-written data.
- **Policy (Vikki):** worth keeping as a standing rule going forward — as new
  machines/artists join, confirm Maya point-release matches the rest of the
  team before they start opening scenes, rather than discovering a mismatch
  after the fact.
