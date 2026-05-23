# Install guide — Emy's setup

Step-by-step install for the Messel Pit Viewer on **Emy's** machine:

- Windows 11
- NVIDIA RTX 3090
- Meta Quest 3 (over Air Link)

You'll end up with the Messel Pit terrain visible on your monitor in
Omniverse Kit, and (optionally) the same scene rendered
stereoscopically in your Quest 3 headset. Plan on **45–90 minutes**
for the first install — most of it is unattended downloads.

This doc assumes you've never used Omniverse, Kit, or VR development
before. If you have, skim sections and go faster.

---

## 1. What you're installing

Three things, in order:

1. **The viewer code** (this repo + a sibling data repo) — a few MB,
   plus a large prebuilt USD file (~1 GB).
2. **NVIDIA Omniverse Kit SDK** — automatically downloaded on first
   build. ~10 GB.
3. **Meta Horizon Link** — only if you want VR on your Quest 3.
   Optional, but recommended for this project.

You do **not** need to install NVIDIA Omniverse Launcher or any
"Omniverse Apps" — Kit is bundled inside the build of this repo.

## 2. Prerequisites (check these first)

### Hardware

- **NVIDIA RTX GPU** — your 3090 is fine. RTX 20-series or newer
  works; GTX cards do not (Kit requires RTX raytracing).
- **~80 GB free disk space** total: ~40 GB for the Kit cache + ~10 GB
  for the build + ~1 GB for the data + scratch.
- **16+ GB RAM** recommended.
- **Quest 3** (optional, for VR). Quest 2 also works.

### Software

Check these are installed. If anything is missing, install it before
moving on.

- **Windows 11** — Windows 10 21H2+ also works.
- **NVIDIA Studio Driver, version ≥ 573.39** — newer = better. As of
  May 2026, NVIDIA recommends **581.42 or newer**. Older drivers in
  the range 570.0–573.39 *will* break Kit silently with no error
  message. Update at <https://www.nvidia.com/en-us/drivers/>.
- **Git for Windows** — <https://git-scm.com/downloads>. Make sure
  it's on your PATH (the installer's defaults are fine).
- **A GitHub account** with your SSH key set up (Mike already added
  `emwize` as a collaborator on both repos). If `ssh -T git@github.com`
  prints "Hi emwize! …", you're good.

You do **not** need Visual Studio installed. The current project is
pure Python — no C++ compilation. (If you ever extend this with
custom C++ extensions, you'd need VS 2022 with the C++ workload, but
that's well past first-launch.)

## 3. Clone the repos

The viewer needs **two repos as siblings** on disk:

- `messelpit_viewer` (this repo — the Kit application)
- `messelpit` (the data pipeline that produces the terrain USD)

Open a normal command prompt (cmd.exe — not PowerShell, not WSL) and
pick a parent directory. Mike uses `D:\senckenberg\`; anywhere with
~80 GB free is fine. Example:

```cmd
mkdir D:\senckenberg
cd D:\senckenberg
git clone git@github.com:MikeWise2718/messelpit_viewer.git
git clone git@github.com:MikeWise2718/messelpit.git
```

After this, you should have:

```
D:\senckenberg\
├── messelpit\          (data pipeline)
└── messelpit_viewer\   (this repo, the viewer)
```

If Git asks for a username/password, your SSH key isn't set up — fix
that first via <https://docs.github.com/en/authentication/connecting-to-github-with-ssh>
or use the HTTPS URLs with a Personal Access Token (then `git clone
https://github.com/MikeWise2718/messelpit_viewer.git` etc).

## 4. Get the terrain data (`messel.usd`)

The terrain USD + orthophoto are too large for GitHub (>1 GB each), so
the data repo only ships the pipeline that produces them. You have
two options:

### Option A — Mike sends you `messel_med.usd` + `ortho.png`

Easiest. Mike copies the contents of `D:\senckenberg\messelpit\out\`
from his machine via Dropbox / a USB stick / `scp`. You drop them
into `D:\senckenberg\messelpit\out\` on your side. Done.

Verify with:

```cmd
dir D:\senckenberg\messelpit\out
```

You want at least `messel_med.usd` (~50 MB) and `ortho.png` (~150 MB).

### Option B — Rebuild from raw tiles

Takes ~30 minutes including a manual download step. Follow the README
in the `messelpit` repo (`D:\senckenberg\messelpit\README.md`). You'll
download 29 DGM1 + 29 DOP20 tiles from the Hessian state geodata shop
(free, but requires registration and accepting a click-through
license), then run `python prep_rasters.py` + `python build_usd.py`.
Save Option B for when you want to learn how the data pipeline works.

## 5. Build the viewer

```cmd
cd D:\senckenberg\messelpit_viewer\kit-app-template
repo.bat build
```

**This takes 5–15 minutes on first build.** It downloads the Kit SDK
(~3 GB) plus ~300 extensions (~5 GB more) into
`%LOCALAPPDATA%\ov\data\`. The terminal output will scroll quickly;
that's normal.

If it fails partway through with a "kit SDK not found" or network
error, just run `repo.bat build` again — the download is resumable.

After the build, you'll have:

- Symlinked app shells in
  `kit-app-template\_build\windows-x86_64\release\apps\` for each of
  the four `.kit` variants (explorer, viewer, viewer_streaming,
  viewer_xr).
- A `~10 GB` symlinked cache that should NOT be backed up or moved.

## 6. First launch — desktop only

Run from `D:\senckenberg\messelpit_viewer\` (the repo root, **not**
inside `kit-app-template\`):

```cmd
launch.bat
```

**First launch takes 5–8 minutes** because RTX shaders compile on
demand and get cached. There's no progress bar — the window will sit
mostly black for a while. Subsequent launches are 10–20 seconds.

When it finishes, you should see:

- A "Messel Pit Explorer" window with the terrain visible in the
  center viewport.
- A "Messel Pit Controls" panel docked on the left with three
  viewpoint buttons (Overview, Pit Rim, Pit Floor).
- The Stage hierarchy (`/World`, `/Terrain`, etc.) docked on the right.

Click each viewpoint button. The camera should snap to that location.
If that works, the desktop install is complete.

**Troubleshooting**: see the *Troubleshooting* section in
`D:\senckenberg\messelpit_viewer\README.md`. Most common gotchas:

- Black viewport for >10 minutes → driver issue, see #2.
- `device lost` crash after 30 s → you're loading the full-res
  `messel.usd` instead of `messel_med.usd`. The launch script picks
  `messel_med.usd` automatically if present, so make sure that file
  exists in `D:\senckenberg\messelpit\out\`.
- Texture appears as solid grey → `ortho.png` is missing or oversized.

## 7. Set up VR (Quest 3)

If you don't want VR yet, skip this section. Desktop alone is enough
to explore + iterate. Come back to this when you're ready.

### 7a. Install Meta Horizon Link

Download from <https://www.meta.com/quest/setup/> ("Quest Link app"
for PC). This installs:

- **Meta Horizon Link** — the PC-side bridge to your Quest.
- **Meta's OpenXR runtime** — automatically registered in the
  Windows registry. Kit talks to this.

Verify the runtime registered:

```cmd
reg query "HKLM\SOFTWARE\Khronos\OpenXR\1" /v ActiveRuntime
```

You should see something like
`C:\Program Files\Meta Horizon\Support\oculus-runtime\oculus_openxr_64.json`.

### 7b. Allow Unknown Sources

Open Meta Horizon Link → gear icon → **Settings** → **General** tab →
toggle **"Unknown Sources"** ON. Confirm the warning prompt.

Without this, Kit will run but the headset will show an "Unknown
Source" banner instead of the terrain. This is a one-time toggle.

### 7c. Pair the Quest 3

If you haven't already:

1. Install the **Meta Horizon mobile app** on your phone.
2. Power on the Quest 3, follow the in-headset setup (Wi-Fi, account
   login, Guardian setup).
3. In the mobile app: pair with the Quest, finish account linking.
4. **Connect Quest 3 to the same Wi-Fi as your PC.** Wired Ethernet
   from PC to router + Quest 3 on the **5 GHz** band gives best
   latency.

### 7d. Engage Air Link

Each session:

1. Put on the Quest 3.
2. Press the **Meta button** (the oval logo button on the right
   controller) → opens the Universal Menu dock.
3. Find **Quick Settings** (click the time/Wi-Fi indicator).
4. Click the **Quest Link** tile.
5. Toggle **Air Link** ON (vs. cable).
6. Select your PC (it should appear in the list since MHL is running).
7. Click **Launch**.
8. The headset switches to the Oculus Link / Air Link home environment
   — a virtual lobby with a screen showing your PC's desktop.

### 7e. Launch the XR kit

On your PC (in cmd.exe, from the repo root):

```cmd
launch_xr.bat
```

Wait for the "Messel Pit Explorer" window to appear (it'll say
"Explorer" in the title — that's expected; we inherit the title from
the Explorer kit it's based on).

### 7f. Start the XR session

In the Kit window's top menubar:

1. Click **Window** → **Rendering** → **XR**.
2. An XR settings panel opens on the right.
3. Click the blue **Start XR** button at the top of that panel.

**In the headset**: the Air Link home dissolves into the Messel scene
rendered stereoscopically. You're standing high above the bbox (the
Overview default position).

### 7g. Move around

- **Right thumbstick forward, hold** → a curved teleport arc appears.
  Aim where you want to go, **release** to teleport.
- **Left thumbstick** → smooth walking (be warned: can cause motion
  sickness if you're not used to VR locomotion).
- **Right thumbstick left/right (quick flick)** → snap-turn ~30°.
- **Look at your hands** → you should see the Quest 3 controller
  models in the virtual world.

### 7h. Teleport to named viewpoints

In the desktop **Messel Pit Controls** panel (on your monitor, not in
the headset), click **Overview**, **Pit Rim**, or **Pit Floor**. The
headset view snaps to that pose.

Heads-up: the current viewpoints were calibrated for *camera flyovers*
not *standing in VR*. Overview puts your VR body 3 km in the sky,
which is fun but disorienting. Better VR viewpoints (rim walk, floor
ground-level) are a future task.

### 7i. Stopping cleanly

When you're done:

1. In the XR panel, click the orange **Stop XR** button. This releases
   the OpenXR session cleanly.
2. Close Kit.

Closing Kit *without* stopping XR sometimes leaves Meta Horizon Link
in a stuck "session active" state, requiring you to restart MHL.

## 8. Daily workflow

Now that everything is installed, your daily startup is:

```cmd
cd D:\senckenberg\messelpit_viewer

REM Desktop only
launch.bat

REM Or, for VR
launch_xr.bat
```

Pull updates with:

```cmd
git -C D:\senckenberg\messelpit_viewer pull
git -C D:\senckenberg\messelpit pull
```

If pull says "merge conflict" or "branch diverged", ping Mike before
trying to resolve — there's a rebase pending between the main and
streaming-experiment branches that we'll sort out together.

## 9. Editing code

The interesting code lives in:

```
D:\senckenberg\messelpit_viewer\
└── kit-app-template\source\extensions\senckenberg.messelpit\
    └── senckenberg\messelpit\
        ├── controls.py    domain logic (viewpoints, XR teleport)
        ├── viewpoints.py  the named camera presets (Overview etc.)
        ├── ui_desktop.py  the controls panel docked on the left
        └── extension.py   lifecycle (startup / shutdown)
```

To add a new viewpoint:

1. Open `viewpoints.py`.
2. Append a `Viewpoint(name="...", description="...", position=..., target=...)` to `DEFAULT_VIEWPOINTS`.
3. Save, restart Kit, the new button appears automatically.

Coordinates are in **local meters** with the origin at the SW corner
of the data bbox. Z is up. The pit center is at approximately
(2411, 3431, 120), the rim is around z=180.

Editing `.py` files **does not require a rebuild** — just restart Kit
to pick up changes. Editing `.kit` files or adding new extensions
does require a rebuild (`repo.bat build`).

## 10. Asking for help

- **Project context**: `D:\senckenberg\messelpit_viewer\CLAUDE.md`
  has the architectural overview, decisions log, and quirks.
- **VR-specific quirks**: `D:\senckenberg\messelpit_viewer\docs\vr-walkthrough.md`.
- **Data pipeline**: `D:\senckenberg\messelpit\README.md`.
- **Anything you can't figure out from the docs**: ping Mike.

If you're using Claude Code in this repo, it auto-loads `CLAUDE.md`
into its context — so it knows the project conventions. The global
`~/.claude/CLAUDE.md` (Mike's personal one) doesn't apply on your
machine, which is fine.

---

## Reminder for Mike

A rebase is pending between Emy's branch and `streaming-experiment`
(this branch). Don't have Emy `git pull` blindly before that's sorted
or she'll hit merge conflicts. Coordinate the rebase together when
she's ready.
