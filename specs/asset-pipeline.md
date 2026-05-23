# Multi-Source Asset Pipeline for Omniverse Digital Twins — Reference Architecture

## Context

The Messel Pit Viewer (this repo) is the first concrete instance of a
pattern we expect to repeat: assemble an NVIDIA Omniverse Kit application
from USD assets produced by **different upstream pipelines on different
schedules by different people (or scripts)**. Current state is deliberately
minimal — one producer (the GIS pipeline in the sibling `messelpit` repo),
one consumer (this viewer), one stage handoff (`messel.usd` + co-located
`ortho.png`), filesystem-only, env-var override (`MESSEL_USD`) with a
`launch.bat` fallback.

That works for one project. It will not survive the second one. Before we
hard-code another bespoke loader, this document sketches what the
**generic** pattern looks like so that:

- New asset producers (a Blender modeler, a procedural building generator,
  a CFD sim writing USD timesamples) can plug into a twin without bespoke
  loader code per source.
- The Messel viewer stays a worked example of the pattern rather than a
  one-off.
- We don't accidentally foreclose **merging two twins** later (e.g., a
  Messel landscape twin and a separate fossil-collection twin composed
  into one scene). Secondary goal — must not be foreclosed, not actively
  built for.
- We can adopt Nucleus later without rewriting the contract. (Nucleus is
  parked due to licensing uncertainty as of 2026-05.)

**This is a reference architecture, not an implementation plan.** No
file-by-file edits, no code. The point is to pin down the seams — the
producer/consumer contract, the composition strategy, the coordinate
convention — and to name the problems we are explicitly **not** solving
yet.

Guiding constraint: *"I suspect we will need some kind of common underlying
library that we reuse, but I don't want that to restrict our agility too
much."* So: small surface area, vendorable, promoted to a real library only
after a second project actually exercises it.

Why Omniverse: USD composition is the right primitive for this problem
(layers, references, payloads, variants), and nothing comparable exists
outside the Pixar/NVIDIA stack at the moment. Stay Omniverse-based unless a
specific blocker forces otherwise.

---

## 1. Producer / consumer contract — the seam

Every asset producer hands the twin **a directory**, not a file. The
directory is the unit of versioning, identity, and relocation. Inside it,
the producer guarantees a known shape:

```
<producer_output>/
  <root>.usd               # entry-point layer (sublayer-able, reference-able)
  origin.json              # required metadata sidecar
  <textures, materials>/   # all asset deps, paths relative to <root>.usd
  variants/                # optional: LOD or quality variants as separate USDs
    <root>.lo.usd
    <root>.med.usd
  provenance.json          # optional: source data + build command + git SHA
```

**Hard rules:**

1. **Self-contained relative paths.** Nothing inside `<root>.usd` may
   reference anything outside its own directory by absolute path. This is
   what makes "rename the folder" / "move to Nucleus later" / "ship as
   `.usdz`" all trivial. Messel already does this for `ortho.png`; it
   needs to be a rule, not a happy accident.

2. **`origin.json` is mandatory.** Minimum fields:

   ```json
   {
     "asset_id":        "senckenberg.messel.terrain",
     "asset_version":   "2026.05.21",
     "up_axis":         "Z",
     "linear_units":    "meter",
     "coord_frame":     "local",
     "to_project_global": {
       "type":         "utm_offset",
       "utm_zone":     "32U",
       "easting":      461000.0,
       "northing":     5527000.0,
       "elevation":    0.0,
       "rotation_deg": 0.0
     },
     "bbox_local":      [0, 0, 0, 6000, 9000, 200],
     "default_prim":    "/World/Terrain",
     "producer":        "messelpit@a1b2c3d",
     "produced_at":     "2026-05-20T14:30:00Z"
   }
   ```

   This is the **only** thing the twin parses from the producer.
   Producer-specific extras (sim timesample range, color-map LUT, etc.)
   go in a separate `producer_meta.json` that the twin treats as opaque
   and forwards to UI/info panels.

3. **`<root>.usd` declares its `defaultPrim`, `upAxis`, and
   `metersPerUnit` metadata.** Already in USD. Producers must set them.
   The twin does not guess.

4. **Producer-side build variants are separate top-level files, not USD
   variant sets** (decimate=1/4/8 for Messel — different geometry,
   different file sizes, different build commands). USD variant sets are
   for *runtime* selection (see §3).

5. **No producer-side scene composition.** Producers do not reference
   each other. The twin owns composition. If two producers need to share
   an asset (a common material library, a shared coordinate origin
   definition), that shared thing is itself a producer.

**Why a sidecar instead of cramming everything into USD `customData`:**
the sidecar is parseable without USD libraries. CI, validation scripts, a
website that lists "what's in this twin", a future asset browser — none
of them should have to spin up usdview to answer "what coordinate system
is this in?". The USD file stays source of truth for geometry; the
sidecar is source of truth for metadata *about* the geometry.

---

## 2. Repo topology

Messel today is the simplest possible case: one producer, one consumer,
sibling directories. Generalize as follows.

### 2.1 Producer repos

One repo per producer. Each owns:

- Its source data (or scripts to fetch it).
- Its build pipeline (Python+GDAL for GIS, headless Blender for DCC,
  Houdini for sims, etc.).
- Its output directory under `out/` or `dist/`, conforming to §1.
- Its own versioning cadence. Producers release; they don't ask
  permission.

The Messel data repo (`MikeWise2718/messelpit`) is the model. Has its
own git, its own README, its own venv.

### 2.2 Twin (consumer) repo

The twin repo owns:

- The **Kit app** (`.kit` files, Kit-template scaffolding, twin-specific
  Kit extensions).
- The **composition layers** — the USDs that pull producer outputs in,
  position them, choose LODs, layer them. This is the twin's IP.
- A **manifest** declaring which producer asset bundles it consumes at
  what version (see §8).
- **No producer outputs.** The twin never checks in a `.usd` or `.png`
  from a producer. It references them.

```
<twin_repo>/
  apps/
    <twin>.explorer.kit          # desktop authoring
    <twin>.viewer.kit            # streaming
  extensions/
    <org>.<twin>/                # twin-specific UI, viewpoints, info
  stage/
    root.usd                     # top-level composition
    layers/
      terrain.usd                # sublayer: pulls in terrain producer
      buildings.usd              # sublayer: pulls in buildings producer
      sim_overlay.usd            # sublayer: pulls in CFD producer
  manifest/
    assets.toml                  # producer bundles + versions + paths
  specs/
```

### 2.3 How producer outputs reach the twin

Three options, in order of increasing infrastructure:

1. **Sibling directories + env var** (Messel today). Manifest declares
   relative path `..\messelpit\out\`. Env var overrides. Zero infra.
2. **Git submodules or vendored snapshots.** Producer pinned to a SHA.
   Breaks at GB scale without LFS.
3. **Asset registry** (deferred — the Nucleus-shaped hole). A URL scheme
   that resolves `asset_id@version` to a path. Today's resolver is "look
   in `..\<asset_id>\out\`"; tomorrow's is Nucleus or S3+CDN or
   Perforce. The twin's manifest references **logical identity**, not
   physical path; a single resolver maps identity → location.

Messel is at option 1. The §1 contract means moving to option 3 later is
a resolver change, not a content rewrite.

### 2.4 Merging two twins

If twin A (Messel landscape) and twin B (a fossil-collection viewer)
both conform to this pattern, "merge them" means:

- A new twin repo C.
- C's `stage/root.usd` sublayers A's `root.usd` and B's `root.usd`, each
  under a transformable group prim (`/World/MesselLandscape`,
  `/World/FossilCollection`).
- C's manifest unions A's and B's producer bundles. Duplicate `asset_id`s
  must resolve to a single version — first hard governance problem (§8).
- C may add its own producers (signage, audio guides).

The merge works **because** producers never reference each other and the
twin owns composition. If producer B's USD silently referenced producer
A's, the merge would either double-load A or break. §1 rule 5 exists for
this reason.

---

## 3. Composition strategy

USD gives four composition arcs. Pick deliberately:

| Arc | When | Messel example |
|---|---|---|
| **Sublayer** | Twin-level overlays at the same prim path | `stage/root.usd` sublayers `terrain.usd`, `buildings.usd` |
| **Reference** | Pull a producer's `defaultPrim` into the twin under a new prim path with its own transform | `terrain.usd` references `..\messelpit\out\messel.usd` at `/World/Terrain` |
| **Payload** | Reference with deferred load. For heavy assets or toggleable overlays | Future: per-quadrant terrain tiles, individual fossil-find detail meshes |
| **Variant** | Runtime-selectable alternatives within one file | LOD selector over decimate=1/4/8 |

**Rules of thumb:**

- **Sublayers** compose *the twin*: terrain, buildings, sim overlay.
  Strength order matters; document it.
- **References** pull *producer outputs* in and place them. Wrap each in
  a transformable group prim carrying the producer's `to_project_global`
  from `origin.json`.
- **Payloads** are references with load/unload control. Use them once a
  twin has >1 GB of geometry, not before.
- **Variants** are for runtime choices the user (or app) makes. LOD is
  the canonical case. Time of day, season, "show annotation overlay" —
  all good fits.

**Messel today** does none of this — it loads a single USD by path. The
generalization is to introduce `stage/root.usd` as the entry point, with
`terrain.usd` as a sublayer that references the producer's output under
`/World/Terrain` with the UTM-derived transform applied. LOD selection
becomes a USD variant set rather than a launch-time file swap.

We do not need to do this for Messel today. We need to know it's the
path.

### 3.1 LOD as variants — sketch

```usda
def "Terrain" (
    variants = { string lod = "med" }
    add variantSets = "lod"
)
{
    variantSet "lod" = {
        "hi"  { references = @./terrain_hi.usd@ }
        "med" { references = @./terrain_med.usd@ }
        "lo"  { references = @./terrain_lo.usd@ }
    }
}
```

Kit sets the variant at runtime (cheap; no stage close/reopen). Streaming
variant defaults to `lo`; desktop to `med`; offline render to `hi`. The
three USDs are still produced as separate files by the producer's build
(§1 rule 4); the variant set is a runtime selector over them.

---

## 4. Coordinate system & units

The single highest-value convention in the whole architecture.

**Project-global frame.** Every twin declares one. For Messel-style
geospatial twins, the natural choice is **UTM** (zone declared) **+ a
project origin** (easting/northing/elevation chosen so the working volume
lives near the origin and fits in float32 precision). Z-up, meters. For
non-geospatial twins (factory floor, museum interior) it's whatever the
twin says it is — but **declared once, in the twin repo**, and producers
either output in it or declare a transform to it.

**Producer-local frames.** A producer's `<root>.usd` is authored
wherever convenient — often (0,0,0) at the SW corner of the asset's
bbox (Messel does this). `origin.json` `to_project_global` carries the
transform.

**Twin composition.** Each producer reference is wrapped in an `Xform`
prim whose transform comes from `to_project_global`. The producer's USD
never knows the twin's frame; the twin never reaches inside the producer's
USD to retransform anything.

```
/World
    /Terrain (Xform, xformOp:translate from origin.json)
        ...references messel.usd...
    /Buildings (Xform, xformOp:translate from its own origin.json)
        ...references blender_export.usd...
```

**Precision.** USD stores transforms as double, but **GPU rendering is
single-precision**. A UTM coordinate (~500000 easting, ~5500000 northing)
as a vertex position is already in float32-precision-loss territory.
Producers must author in a **local** frame near the origin; the twin
applies the big translation at the group level. Non-negotiable for
anything beyond toy scales.

**Time.** Same discipline as space: producers declare their time origin
and units (seconds since epoch, frame N of a sim, geological year BP) in
`origin.json`; the twin composes them. Most twins have one time axis;
some (geological + wall-clock) will have two and the UI must expose both.
Not solving in detail yet — see §5.

---

## 5. Time-varying / simulation outputs

Four mechanisms, increasing pain:

1. **USD timesamples on attributes.** Native; animated transforms,
   deforming meshes (blend shapes / skinned skeletons), varying colors.
   Producers write `.usd` with `timeSamples` + `timeCodesPerSecond`. Twin
   composes them like any reference.

2. **USD point caches / Alembic references.** For dense per-frame
   geometry that doesn't compress as timesamples — particles, fluid
   surfaces. Producer outputs `.abc` or per-frame `.usd` sequence; its
   `<root>.usd` wraps it.

3. **OpenVDB volumes.** Smoke, fire, scalar/vector fields from CFD. USD
   has volume schema; producer outputs `.vdb` + a wrapping `.usd`.

4. **Live / streamed sidecars.** A simulation running *now* feeding the
   twin *now*. Omniverse Fabric / live-sync territory — separate
   process, separate protocol, separate failure modes. For our pattern:
   a live producer publishes to a known channel (live-update layer on
   Nucleus, or a Fabric stage); twin sublayers it like any other
   producer. Defer until a project needs it.

**Contract addition** for time-varying producers (`origin.json`):

```json
"time": {
  "samples_per_second": 24,
  "start_time":         0.0,
  "end_time":           120.0,
  "wallclock_unit":     "second"
}
```

Naming the four mechanisms and the schema extension is enough for now.

---

## 6. The "common library" question

There **will** be shared code. The user is right to be wary of premature
extraction. Strategy:

**Phase 0 (now, Messel only):** Shared code lives inside the Messel Kit
extension at `kit-app-template/source/extensions/senckenberg.messelpit/`.
`viewpoints.py`, `ui_desktop.py`, `controls.py`, `extension.py`, plus the
(not-yet-written) `origin.json` loader. No effort to make it reusable. No
package boundary. If it's used only by Messel, it's *part of* Messel.

**Phase 1 (second project starts):** Identify what duplicates. Candidates
already visible in `senckenberg.messelpit`:

| Candidate | Why it's likely shared | Why it might not be |
|---|---|---|
| `origin.json` parser + schema | Every twin needs it | Schema may evolve |
| Producer asset resolver (id → path) | Every twin needs it | Backend differs (fs / submodule / Nucleus) |
| Coord-frame helpers (UTM → project Xform) | Geospatial twins all need it | Non-geospatial twins don't |
| Viewpoint preset framework (`viewpoints.py`) | UX pattern is generic | Preset *content* is per-project |
| Info-panel docking pattern (`ui_desktop.py`) | UX pattern is generic | Content is per-project |
| LOD variant selector | Generic | Trivial enough to duplicate |
| VR/streaming control stubs (`ui_vr.py`) | All XR twins need it | Currently a stub |

The pattern: **frameworks shared, content per-project.** A
`twin_kit_common` package eventually exposes the parser, resolver
protocol, coord helpers, panel base class. Messel-specific viewpoints,
info-panel text, branding stay in `senckenberg.messelpit`.

**Phase 2 (third project, or first sign of pain):** Promote to a real
versioned package — likely a Python package vendored as a Kit extension
(`org.twin_common` or similar). Until then: **copy-paste with intent**.
Mark candidate functions with `# CANDIDATE: extract to twin_kit_common
once a second user exists`. Cost of two copies is small; cost of a
premature abstract base class with the wrong shape is large.

**Never in the shared library:** Kit `.kit` files, producer-specific
paths, per-twin UI text, per-twin viewpoint coordinates. It's a toolkit,
not a framework.

---

## 7. What it means for Messel concretely

Worked example, not a refactoring plan. If the pattern were applied
today, the deltas would be:

| Today | Under the pattern | Urgency |
|---|---|---|
| `MESSEL_USD` env var → one `.usd` path | `assets.toml` manifest declares `senckenberg.messel.terrain@<ver>` with a resolver; env var overrides | Pattern delta, not urgent |
| Kit extension opens `messel.usd` directly | Opens `stage/root.usd`; root sublayers `terrain.usd`; terrain references producer output with UTM-derived Xform | Pattern delta, not urgent |
| Three LOD `.usd` files swapped at launch | Three LOD `.usd` files exposed via USD variant set on `/World/Terrain`; runtime switch | Nice-to-have |
| `origin.json` is a build artifact | `origin.json` is part of the **contract**; twin parses it; missing/invalid is an error | Pin schema before locking |
| Extension owns everything | Extension keeps Messel-specific bits; framework bits are **candidates** for extraction once a second project exists | Don't extract yet |
| No provenance tracking | Producer optionally writes `provenance.json` | Defer |
| Producer and twin are sibling dirs | Same, but the convention is one of several resolver backends | No change |

**Stays the same:** the Messel data repo's pipeline (already conforms in
spirit), the explorer/viewer kit split, `kit-app-template` scaffolding,
relative texture paths.

**Leave alone until project #2 forces them:** extracting the shared
library, manifest/resolver layer, LOD variant set, `provenance.json`.

Point of writing this down now: when project #2 appears, the refactor is
mechanical, not a rethink.

---

## 8. Governance / versioning — problem statement only

Not picking tools. Naming them so we know they exist:

- **Asset versioning.** SemVer is wrong for data (what's a breaking
  change in an orthophoto?). DateVer (`2026.05.21`) is honest but
  doesn't express compatibility. Content hashing is reproducible but
  unreadable. Probably: DateVer + content hash, with a producer-declared
  schema version for the `origin.json` shape.
- **Schema validation.** `origin.json` will drift. Versioned schema
  (Pydantic / JSON Schema) + CI on producer repos that fails the build
  if it doesn't validate.
- **Asset bundle identity.** `asset_id` must be unique across all
  producers that might end up in the same twin. Namespacing convention
  needed (`org.project.asset`, e.g., `senckenberg.messel.terrain`).
- **Manifest resolution.** When twin C unions A and B and both pull
  `senckenberg.fossils.specimens@2026.03`, that's fine. When A wants
  `@2026.03` and B wants `@2026.06`, what happens? Pin in C's manifest;
  fail if either A or B encodes a hard incompatibility.
- **Reproducibility.** Given a twin repo at a SHA + a manifest, can we
  reconstruct the exact stage that shipped? Today: no (producer outputs
  aren't pinned by hash). Eventually: yes, via content-hashed bundles.
- **License / attribution propagation.** DGM1, DOP20, CC-BY assets —
  twin must surface attribution. Per-producer `LICENSE` + a twin-side
  aggregator script. Defer.

Pick none of these now. Reopen when project #2 starts.

---

## 9. Open questions

1. **Project-global frame for Messel.** Today the producer authors with
   SW corner at (0,0,0) and UTM origin in `origin.json`. Set the
   convention now to compose under a UTM-origin-translated Xform, even
   though Messel is the only producer? *(Recommendation: yes.)*

2. **Manifest format.** TOML, YAML, or JSON? Bias TOML for human
   editing (matches `repo.toml`); JSON if mostly machine-generated.

3. **Resolver protocol.** Python callable, shell command, or URL scheme
   (`twin://senckenberg.messel.terrain@latest`)? URL scheme is most
   future-proof (maps to Nucleus naturally) but heavier upfront.

4. **Variant set vs file swap for LOD.** Variant set is cleaner but
   means the producer emits a wrapper `.usd`. Worth the producer-side
   complexity?

5. **Shared library — start now or wait?** "Don't restrict agility"
   suggests wait. Counter: an `origin.json` parser is ~30 lines and
   writing it once correctly costs less than writing it twice
   approximately. *(Suggest: write it in `senckenberg.messelpit` now,
   copy-paste at #2, extract at #3.)*

6. **Twin-merging — explicit goal or just "don't foreclose"?** Affects
   how strictly we enforce `asset_id` global uniqueness from day one.

7. **Nucleus posture.** Revisit when licensing clears, or commit to
   filesystem + git long-term and treat Nucleus as a possible future
   resolver backend only?

8. **Time-varying producer in the near term?** If yes, pin the
   `origin.json` time schema now. If sims are 6+ months out, defer.

9. **Streaming vs desktop variant divergence.** Today nearly the same
   `.kit` with different runtime config. As the twin gets more layers,
   will streaming want to *omit* layers (heavy annotation overlays)?
   If yes, the manifest needs another axis.

---

## Verification

This is a design doc, not code. "Verification" here means:

- **User sign-off on §9.** No work product until those answers exist.
- **Schema-pin step**: when the answers exist, write a JSON Schema for
  `origin.json` v1 and check the existing
  `messelpit/data/prep/origin.json` validates against it. That's the
  first concrete validation.
- **Second-project trigger**: when project #2 is identified, revisit §6
  to decide what to extract.

---

## Critical existing files (anchors, not edits)

- `specs/messelpit-viewer.md` — existing worked-example spec;
  tone/conventions reference.
- `kit-app-template/source/extensions/senckenberg.messelpit/extension.py`
  lines 29–41 — current stage-loading code; the seam where the
  manifest/resolver would slot in.
- `kit-app-template/source/extensions/senckenberg.messelpit/viewpoints.py`
  — candidate for shared-library extraction (framework, not content).
- `kit-app-template/source/extensions/senckenberg.messelpit/ui_desktop.py`
  — candidate for shared-library info-panel base class.
- `..\messelpit\data\prep\origin.json` (sibling data repo) — de facto
  schema that §1 formalizes; pin its shape before locking the contract.
