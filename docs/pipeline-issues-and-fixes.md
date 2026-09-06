# Pipeline Issues & Fixes Log

Living log of pipeline/config issues investigated on this project, their root
causes, and what was done about them. Append new entries at the top. See
[team/ROSTER.md](../team/ROSTER.md) for who's who — technical entries below
were investigated as [Tom](../team/tom.md); staffing/policy calls are flagged
for [Vikki](../team/vikki.md).

---

## 2026-09-06 — Nuke Indie integration: File Save/Open failure + Nuke Studio scaffolding

**Reported by:** Adam Benson, comping in Nuke Indie against `LPG101_003_210`, CMP step.

### Issue 1 — File Save fails with "Please select a single Project!"

**Symptom:** Every "File Save" from the Flow Production Tracking panel while
comping in Nuke Indie failed with a `TankError` popup reading "Failed to save
file: Please select a single Project!" File Open had the same class of
problem. No plain-NukeX-only mode exists to fall back to — Nuke Indie always
opens a Nuke Studio Timeline alongside the NukeX comp session.

**Root cause:** Nuke Indie always runs Foundry's "Studio" application shell —
`nuke.env['studio']` is `True` for this license tier regardless of whether the
artist is doing comp-only work. The stock `tk-multi-workfiles2` hook for
`tk-nuke` (`scene_operation_tk-nuke.py`) branches on the engine's
`studio_enabled` flag: if true, it treats File Save/Open as a **Hiero Project**
operation (`project.saveAs()`), not a plain Nuke script save. That path calls
`_get_current_hiero_project()`, which requires exactly one Project Bin
selected in the Timeline UI to know *which* project to act on. Comp-only work
never has a meaningfully "selected" project — only Indie's always-present
default blank Studio project — so the selection count check
(`len(selection) != 1`) always failed. This is a structural mismatch between
the stock hook (built for real Nuke-Studio-driven editorial) and a comp-only
Indie workflow, not a template/schema bug — confirmed by reading the vendored
hook source directly (`install/app_store/tk-multi-workfiles2/v0.16.0/hooks/
scene_operation_tk-nuke.py`).

**Fix applied:** Added `hooks/tk-multi-workfiles2/
scene_operation_tk-nuke_comp_only.py` — the stock hook's classic-Nuke branch
(`nuke.scriptSave()` / `scriptOpen()` / `scriptSaveAs()`) with the
`studio_enabled` → Hiero-project routing removed entirely. Wired in via
`hook_scene_operation` on the two comp contexts that do real File Save/Open
(`settings.tk-multi-workfiles2.nuke.asset_step` and `.shot_step`). Save/Open
now always act on the actual `.nkind` comp script and ignore Indie's default
Studio project completely.

Also done in the same session, as prerequisite/adjacent work:
- Added `--indie` to the Nuke launcher's args (single icon — no plain-Nuke
  mode exists on this license tier to justify a second one).
- Activated the `tk-nukestudio` engine instance at the `asset_step`/
  `shot_step` level (it existed fully written but commented out in
  `tk-nuke.yml`/`env/*.yml` — stock scaffolding nobody had finished), plus the
  templates it depends on (`hiero_project_work`/`publish`/`_area`/`snapshot`,
  new `editorial_root: Editorial/NukeStudio`) and `tk-multi-snapshot.hiero`.

**Status: Resolved (2026-09-06).** File Save and File Open both confirmed
working by Adam against a real shot comp. Committed on
`feature/publish-schema-restructure` (`2a60243`), pushed.

- **Technical (Tom):** the `tk-nukestudio` engine instance is scaffolded but
  currently **unreachable** — the single "Nuke" launcher hardcodes
  `engine: tk-nuke`, so Toolkit never bootstraps as `tk-nukestudio` regardless
  of Indie/Studio mode. Reaching it later would need a second launcher entry
  (`engine: tk-nukestudio`), which reopens the single-icon-vs-two-icon
  tradeoff. The deferred Project-level block in `tk-nuke.yml` (full
  EDL-driven editorial) also still needs `tk-hiero-export`'s own templates
  (`hiero_plate_path`, `hiero_render_path`) audited against the current
  schema before it's safe to activate — not done, not attempted.
- **Policy (Vikki):** comp-only Nuke Indie is the sanctioned workflow for now.
  Adam tried real Nuke-Studio-driven editorial (EDL out of DaVinci → shot
  work/comp in the Studio timeline → renders back to DaVinci) previously and
  moved off it — EDL-driven naming/conform drift plus a non-working ShotGrid
  install at the time. Revisit only with a concrete plan for the naming-drift
  problem, not just because the engine scaffolding now exists.

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
