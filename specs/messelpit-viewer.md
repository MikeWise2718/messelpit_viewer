# Messel Pit Omniverse Viewer — Handoff Brief

## Purpose

Build an NVIDIA Omniverse Kit application that loads `messel.usd` (textured
LiDAR heightfield of the Grube Messel UNESCO fossil site near Darmstadt),
presents a fixed-feature viewport with preset cameras, and supports streaming
to a browser — including the **Meta Quest 2 / Quest 3 browser** via the
built-in CloudXR.js / WebXR pipeline.

This repo is the **viewer**. The **data pipeline** that produces the USD lives
in a sibling repo: `D:\senckenberg\messelpit\`. The viewer references the
produced files; it does not copy them.

## Companion repo (data pipeline)

```
D:\senckenberg\messelpit\
  out\messel.usd        258 MB, ~13.5M verts, ~27M tris (decimate=2 @ 1 m DEM)
  out\messel.usdz       444 MB, portable variant
  out\ortho.png         186 MB, 12000x18000 RGB orthophoto
  data\prep\origin.json UTM origin + DEM stats (104..228 m elevation)
  specs\messel-pit-usd.md
```

`messel.usd` references `./ortho.png` as a relative path; both must stay
co-located. Stage is **Z-up**, **meters**, default prim `/World`, mesh at
`/World/Terrain` with a `UsdPreviewSurface` material reading `ortho.png` via
`UsdUVTexture`. `MaterialBindingAPI` is applied (no validation warnings as of
the latest rebuild).

The bbox is 6 km E-W × 9 km N-S, centered roughly on Gemeinde Messel. About
46% of the rectangle is interpolated fill where Gemeinde Messel's irregular
boundary excluded data — this is documented and intentional (decision made
during data prep).

## Recommended architecture

```
D:\senckenberg\messelpit_viewer\          (this repo)
  kit-app-template\                       (cloned upstream — its own .git)
    repo.toml, repo.bat, repo.sh
    premake5.lua
    source\apps\
      senckenberg.messelpit.explorer.kit  (desktop variant, current focus)
      senckenberg.messelpit.viewer.kit    (Viewer scaffolding from earlier
                                           pass; keep for later streaming
                                           experiments or delete)
    source\extensions\
      senckenberg.messelpit.explorer.setup\  (Explorer's setup extension)
      senckenberg.messelpit.viewer.setup\    (Viewer's setup, unused)
      senckenberg.messelpit.viewer.messaging\ (Viewer's messaging, unused)
    .vscode\replay_files\
      messelpit_explorer                  (drives non-interactive scaffolding)
      messelpit_viewer                    (drives Viewer scaffolding)
  specs\messelpit-viewer.md               (this file)
```

`kit-app-template/` is the upstream scaffold; we work inside it. The viewer
repo's own git (when initialized) ignores `kit-app-template/_build/` and
`kit-app-template/.git/` but tracks our `replay_files/`, the `source/apps/`
and `source/extensions/` directories we authored, and this `specs/` tree.

### Why these choices

- **kit-app-template** is the current (2026) supported scaffolding from NVIDIA
  for building Omniverse Kit apps. Repo: `NVIDIA-Omniverse/kit-app-template`.
- **USD Explorer template** — has the Stage hierarchy panel, default lighting,
  File menu, and other authoring affordances we need for desktop iteration.
  Originally chose USD Viewer for streaming-readiness, but its "viewport-only,
  no UI" stance made it unusable for local development (no way to add lights
  to a USD that doesn't author them, no hierarchy panel for inspection).
  Explorer can still stream, just with more UI weight.
- **One custom extension** (`senckenberg.messelpit`) — keeps the
  Messel-specific logic in one named, versioned package separate from the
  template boilerplate. Makes future updates of the template painless.
- **Two `.kit` app variants** — same extension, different runtime: one
  desktop-windowed for local iteration, one streaming-enabled for the Quest.

## Streaming to Meta Quest

- Kit SDK **109.0.2+** ships with the **CloudXR WebRTC runtime integrated**.
  No separate CloudXR Server install required.
- Client = **CloudXR.js running in the Quest browser** over **WebXR + WebRTC**.
  No APK sideload, no Meta dev mode required.
- Quest 3 will look noticeably better than Quest 2 (higher-res displays,
  full-color passthrough). The streaming pipeline is identical.
- Network: server (Windows / Linux box with RTX GPU + Kit app) and Quest
  must be on the same LAN, or a TURN server must be configured for WAN.
- Reference: <https://docs.omniverse.nvidia.com/xr/omniverse-spatial-docs/latest/clients/meta/01-overview.html>

## Suggested build sequence

1. ~~**Clone & launch the stock USD Viewer template unmodified.**~~ **DONE,
   revised.** Cloned `kit-app-template`, scaffolded both Viewer and Explorer
   variants via `repo template replay`. Viewer's empty-by-design UI (no Stage
   panel, no lights, no menus) made local iteration impossible — switched to
   USD Explorer. Explorer launches, opens `messel.usd` from File → Open, mesh
   renders with default lighting.

1.5. ~~**Resolve the orthophoto texture-size blocker.**~~ **DONE.** Added a
   `--max-tex-dim` flag to the data repo's `tools/prep_rasters.py` (default
   16384). Rebuilt `ortho.png` at 10922×16384, which fits under D3D12's
   `Texture2D` cap. Texture now uploads in Kit.

2. ~~**Add `senckenberg.messelpit` extension** that auto-loads the USD on
   startup and adds a viewpoints menu.~~ **DONE.** Built the extension at
   `kit-app-template/source/extensions/senckenberg.messelpit/`. MVC split
   across `extension.py` (lifecycle), `controls.py` (logic), `ui_desktop.py`
   (docked tabbed panel), `ui_vr.py` (stub), `viewpoints.py` (preset
   coords). The extension reads `--/app/messelpit/load_usd=<path>` and opens
   the stage asynchronously; both Explorer and Viewer kit apps declare it as
   a dependency (`order = 11000`). Panel docks next to Stage by default,
   tabs: Viewpoints (placeholder coords; real coords still in the open
   decisions section) and Info.

2.5. **Generate a lower-poly variant for desktop iteration.** The current
   full-res `messel.usd` is ~108 M tris and triggers a `device lost` GPU
   crash on RTX 4080-class hardware ~30 s after stage open. Run in the data
   repo:
   ```powershell
   cd D:\senckenberg\messelpit
   .venv\Scripts\python.exe -m messelpit.build_usd --decimate 4 \
       --out out\messel_med.usd --usdz
   ```
   `--decimate 4` gives ~6.75 M tris which the GPU eats comfortably. Use the
   med variant as the default `MESSEL_USD` for desktop iteration; keep the
   full-res for offline renders only.

3. **Generate a low-poly variant for streaming.** (Same pattern as 2.5, more
   aggressive decimate for Quest streaming.) Run in the data repo:
   ```powershell
   cd D:\senckenberg\messelpit
   .venv\Scripts\python.exe -m messelpit.build_usd --decimate 8 --out out\messel_lo.usd --usdz
   ```
   Result: ~1.5 M tris instead of 27 M, ~50 MB instead of 258 MB. Use this
   variant for Quest streaming; keep the full-res for desktop.

4. **Flip to `messelpit.viewer_streaming.kit`.** Test from Chrome on the
   desktop first (WebRTC sanity check), *then* from the Quest 3 browser.

5. **Iterate.** Likely candidates: scale bar, info hotspots over key
   fossil-find locations (Senckenberg has documented coords for major
   excavations), time-slider for historical excavation extents,
   sky/lighting presets.

## Decisions already made (don't re-litigate)

| Decision | Choice | Rationale |
|---|---|---|
| Repo location | sibling at `D:\senckenberg\messelpit_viewer\` | keeps Python/uv data tooling separate from Kit/premake viewer tooling |
| Template | USD Explorer (revised from USD Viewer) | Viewer's "viewport-only" was a non-starter for local iteration (no Stage panel, no lights). Explorer still streams, just with more UI weight |
| Extension name | `senckenberg.messelpit` | Senckenberg Research Institute runs Messel; namespace it |
| Texture path | relative (`./ortho.png`) | works for both .usd and .usdz; viewer references via relative-to-data-repo path |
| Streaming client | CloudXR.js / WebXR in Quest browser | no APK build, no sideload, Kit SDK 109.0.2+ handles server side natively |
| Low-poly variant | decimate=8 rebuild from existing data | one command in data repo, no new pipeline code |

## Open decisions for next session

- Specific preset camera positions (need pit centerline lat/lon in local
  meters — derivable from `data\prep\origin.json` plus the known pit
  coordinates ~49.917°N 8.755°E).
- Whether to bake a hillshade overlay layer for the no-data fill regions so
  they're visually distinct from real DGM1 coverage.
- Whether the streaming variant should expose a minimal HTML control panel
  (preset selector) or rely entirely on Quest controller gestures.

## How to resume

From a new shell:

```powershell
cd D:\senckenberg\messelpit_viewer
claude
```

Then: *"Continue from `specs\messelpit-viewer.md` — start with step 1, cloning
kit-app-template and getting the stock USD Viewer to render
`..\messelpit\out\messel.usd`."*

## References

- Kit App Template: <https://github.com/NVIDIA-Omniverse/kit-app-template>
- USD Viewer template README: <https://github.com/NVIDIA-Omniverse/kit-app-template/blob/main/templates/apps/usd_viewer/README.md>
- Kit SDK overview: <https://docs.omniverse.nvidia.com/kit/docs/kit-app-template/latest/docs/kit_sdk_overview.html>
- Omniverse Spatial / XR docs: <https://docs.omniverse.nvidia.com/xr/omniverse-spatial-docs/latest/>
- CloudXR.js Meta client: <https://docs.omniverse.nvidia.com/xr/omniverse-spatial-docs/latest/clients/meta/01-overview.html>
- CloudXR 6.0 SDK: <https://developer.nvidia.com/topics/ai/xr/cloudxr-sdk>
