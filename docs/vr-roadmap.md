# Roadmap: from 2D stream → walking in VR on MQ2

What we have today (2026-05-21): a flat 2D WebRTC video of the Messel
terrain rendered in the Quest 2 browser. You can see it but you can't
navigate inside it.

What "walking in VR on the MQ2" means concretely:
- Stereoscopic rendering (left/right eye views, parallax correct)
- Head-tracked camera (you turn your head, the view follows)
- Some way to translate yourself through the scene (teleport, smooth
  locomotion, or pre-positioned viewpoints)

There are **three architectural paths** to get there. They are not
incremental — picking one means committing to a different streaming
stack than the one we just got working.

> **Update 2026-05-21 (after Kit XR audit):** the path comparison below
> reflects the initial framing, but a closer look at Kit SDK 110.1.1
> revealed three things that change the picture. See
> **[Audit findings](#audit-findings-2026-05-21)** at the bottom of this
> doc before acting on the path comparison. Short version: Path B and
> Path C may collapse into the same path, and a registry-pull experiment
> is the next step to find out.

## Path comparison

| Aspect | Path A: WebXR over WebRTC | Path B: CloudXR (native) | Path C: SteamVR + Air Link |
|---|---|---|---|
| Where it runs on Quest | Quest browser | Sideloaded APK | Built into Quest OS |
| Quest 2 supported? | Yes, via Quest Browser WebXR | Yes (older CloudXR versions) | Yes (Air Link is free, official) |
| What's installed on the headset | Nothing extra | CloudXR client APK (sideload, dev mode) | Nothing extra |
| PC-side runtime | Kit + web-viewer-sample (what we have) + WebXR client | Kit + CloudXR runtime (separate) | SteamVR + Kit with OpenXR output enabled |
| Stereoscopic? | Yes | Yes | Yes |
| Latency | Highest (browser stack adds ~80-120ms) | Lowest (purpose-built, ~30-50ms) | Mid (~50-80ms over Air Link) |
| Setup complexity | Highest | High | Medium |
| Closest to "what visitors would do" | Yes (URL on Wi-Fi, no install) | No (requires APK install) | No (requires SteamVR account/install) |
| NVIDIA recommends for Senckenberg use case | Yes (CloudXR.js, the modernized stack) | Was the answer pre-2024 | No |

## Path recommendation

For the **eventual Senckenberg deliverable** (visitors at the museum
with a Quest, no IT setup): Path A (WebXR over WebRTC) is the only
viable option. Visitors won't sideload apps or install SteamVR.

For **getting working stereo VR onto your Quest 2 this week** as a
proof-of-concept: Path C (SteamVR + Air Link) is the fastest. It
sidesteps the streaming layer we just built but proves the scene
renders correctly in VR.

**My recommendation: try Path C first** to validate that Kit can
output stereoscopic VR at all with our scene, then commit to Path A
for the real work.

## Path A: WebXR over WebRTC (CloudXR.js model)

This is the future-state architecture documented in NVIDIA's
[Omniverse Spatial docs](https://docs.omniverse.nvidia.com/xr/omniverse-spatial-docs/latest/).
Same WebRTC transport we're already using, but the browser-side
client renders stereoscopically into the Quest's WebXR API.

### Outstanding work

1. **Confirm CloudXR.js / WebXR support in our Kit SDK version**
   (110.1.1). Check whether the streaming layer needs an additional
   extension or settings to emit stereo viewports.
2. **Replace or extend web-viewer-sample with a WebXR-capable client.**
   The sample we use today is 2D-only. NVIDIA publishes a
   CloudXR.js Meta client; we'd need to evaluate whether it fits
   our setup or we wire it up ourselves.
3. **Update `senckenberg.messelpit.viewer_streaming.kit`** to enable
   stereo rendering and HMD pose input.
4. **Add WebXR session handling on the client side**: request a
   VR session, route head pose back to Kit via the messaging
   channel, render the stereo video stream into the WebXR layer.
5. **Add a locomotion UX** — Quest 2 controllers have joysticks,
   triggers, and grip buttons. Decide: teleport, smooth locomotion,
   or "viewpoint teleport" (jump between Overview / Pit Rim / Pit
   Floor presets we already have).
6. **Performance tuning** — stereoscopic doubles the GPU load on the
   RTX 4090 (two viewports), and the WebRTC encode now has to
   handle stereo frames. May need to drop to `messel_lo.usd`
   (decimate 8) or accept lower frame rate.
7. **Test on Quest 2 specifically** — Quest 2 has weaker mobile
   hardware than Quest 3, and its browser may have older WebXR
   features. Some experiments may only work on Quest 3.

Estimated effort: **2-4 weeks** of focused work, with several
unknowns.

## Path B: CloudXR native client

The "classic" NVIDIA VR streaming product. Quest gets a sideloaded
APK that talks to a CloudXR runtime on the PC. Lower latency,
purpose-built for VR.

### Outstanding work

1. **Enable developer mode on the Quest 2** (already documented in
   `quest2-setup.md` step 8). Requires Meta developer org setup
   and the phone-app toggle.
2. **Sideload the CloudXR client APK.** NVIDIA distributes this via
   their CloudXR program. May require registration / NDA.
   Quest 2 support in current CloudXR releases needs verification —
   it's possible only older CloudXR releases support Quest 2.
3. **Install CloudXR runtime on PC.** Separate from kit-app-template.
4. **Configure Kit to output via CloudXR** instead of (or alongside)
   WebRTC. This is settings + extensions in the .kit file. Not
   well-documented in current kit-app-template — the streaming
   layer we used is WebRTC-only.
5. **Network config** — CloudXR uses different ports than WebRTC.
   Update firewall.
6. **Locomotion UX** — same as Path A.

Estimated effort: **1-2 weeks**, mostly dominated by figuring out
the CloudXR setup and confirming Quest 2 support.

Risk: NVIDIA has been steering people toward CloudXR.js (Path A) since
2024. CloudXR native may be in maintenance mode. Investment here may
become obsolete.

## Path C: SteamVR + Air Link (fastest to validate)

Skip Kit's streaming layer entirely. Use Air Link to make the Quest 2
act as a wireless PCVR headset. Kit runs as a normal desktop app
with OpenXR output enabled, SteamVR routes the stereo output to the
Quest.

### Outstanding work

1. **Verify Kit supports OpenXR output** with our `omni.usd_explorer`
   or `omni.usd_viewer` base. There's an `omni.kit.xr.*` extension
   family in newer Kit releases — need to check if it's in 110.1.1
   and whether it's enabled by default.
2. **Install SteamVR on the PC.** Free, from Steam.
3. **Set up Air Link on Quest 2.** Free, built into Quest OS.
   Settings → Quest Link → Air Link. The PC needs the Oculus PC
   app installed (also free).
4. **Configure Kit to use OpenXR / VR mode.** This is a `.kit`
   settings + extension change — load the XR extensions, set the
   renderer to output stereo.
5. **Locomotion UX** — Kit's XR extensions usually include basic
   teleport / smooth movement out of the box. May or may not be
   adequate for our scene.

Estimated effort: **2-5 days**, IF Kit's XR extensions actually work
with the Viewer or Explorer base. Could be longer if we hit Kit-side
bugs.

This path produces a one-PC tethered-via-Wi-Fi setup that's NOT
suitable for a museum, but IS a great way to confirm:
- The scene renders OK in stereo VR
- The locomotion feels right
- The performance budget is real (FPS, comfort)

If all of those work, we have confidence to invest in Path A.

## Recommended next actions

If you want to keep momentum, in priority order:

1. **Investigate Path C first (1-2 days).** Find out if Kit's XR
   extensions are usable in our current build. If yes, get the
   Messel pit into the Quest 2 in real VR via Air Link this week.
2. **Decide based on what we learn.** If Path C works smoothly →
   commit to Path A for the real deliverable. If Path C reveals
   Kit-side issues (e.g. our shaders break in stereo) → those are
   the same issues Path A would hit, and we now know to fix them
   first.
3. **In parallel**, capture the work item to add viewpoint buttons
   to the existing web-viewer-sample. Even without VR, "click to
   jump to Pit Rim" is a real interaction that works in the
   Quest browser today.

## Tracker

| Item | Status | Path | Notes |
|---|---|---|---|
| Investigate Kit XR extension support in 110.1.1 | **done** | C | See [Audit findings](#audit-findings-2026-05-21). XR exts exist but uncached. |
| Probe XR registry availability (throwaway .kit) | next | B/C | ~10 min; answers whether `omni.kit.xr.bundle.generic` even fetches |
| Inspect `bundle.generic`'s `extension.toml` post-fetch | next | B/C | Tells us SteamVR-OpenXR vs CloudXR-only |
| Install SteamVR + Oculus PC app, set up Air Link | gated on probe | C | Skip if probe shows bundle is CloudXR-only |
| Build `viewer_xr.kit` (sibling, not modifying streaming kit) | not started | B or C | Streaming and XR cannot share a `.kit` |
| Test end-to-end with Messel scene | not started | B or C | The actual demo |
| Add viewpoint buttons to web-viewer-sample | not started | side | Works without VR, useful regardless |
| Evaluate CloudXR.js / WebXR client options | not started | A | Big read of NVIDIA spatial docs |
| Wire CloudXR.js into streaming kit | not started | A | Depends on previous |
| Stereo rendering perf budget on RTX 4090 | not started | A or B | Likely need `messel_lo.usd` |
| Locomotion UX design (teleport vs smooth vs viewpoint) | not started | any | Worth a small spec |

---

## Audit findings (2026-05-21)

After a local audit of `kit-app-template/_build/.../extscache/` and the
Kit SDK kernel manifest, here's what we actually know vs. the assumptions
in the path comparison above:

### What's present in Kit SDK 110.1.1

Kit's kernel declares paths for XR extensions, meaning they exist and
can be pulled from the NVIDIA registry on demand:

- `omni.kit.xr.core`
- `omni.kit.xr.system.openxr` (the SteamVR-relevant one, in name)
- `omni.kit.xr.bundle.generic` (probable SteamVR/OpenXR bundle)
- `omni.kit.xr.bundle.apple_vision_pro`
- `omni.kit.xr.bundle.ipad`
- `omni.kit.xr.ui.*`, `omni.kit.scene_view.xr*`

Source: `kit-app-template/_build/windows-x86_64/release/kit/site/sitecustomize.py`
lines 567-586.

### What's NOT present

- **No XR extensions in `extscache/`** — none have been pulled yet.
  Build adds them when something depends on them.
- **None of our `.kit` files mention XR** —
  `senckenberg.messelpit.{explorer,viewer,viewer_streaming}.kit` are
  all XR-free.
- **No SteamVR/Quest sample app ships with kit-app-template.** Only
  `omni.app.dev.xr.avp.kit` (Apple Vision Pro) and
  `omni.app.dev.xr.ipad.kit` (iPad AR) exist as references — both
  using `persistent.xr.profile.ar.simulatedxr.*` settings, which
  **points at NVIDIA's CloudXR runtime, not SteamVR**.
- **No mention of OpenXR, SteamVR, headset, stereoscopic, or VR**
  in any of `readme-assets/additional-docs/*.md` or template READMEs.

### The pivotal unknown

**Does `omni.kit.xr.bundle.generic` actually drive a SteamVR OpenXR
runtime, or does it require CloudXR Server (NVIDIA's own stack)?**

The naming says OpenXR — which is an open standard SteamVR implements.
But the AVP sample's `simulatedxr` settings hint that the whole
`omni.kit.xr.*` family may assume CloudXR as the transport. If that's
the case, Path C (SteamVR + Air Link, no NVIDIA software on the Quest)
collapses, and the "real VR" choice becomes:

- **Path A** (WebXR over WebRTC) — what we want for the museum
- **Path B** (CloudXR with sideloaded Quest client app) — the only
  pre-museum option for stereo VR on this hardware

You can't tell which from the manifest alone. We need to fetch
`omni.kit.xr.bundle.generic` and read its `extension.toml` to see
what runtimes it links against. That's the next concrete step.

### Streaming and XR can't share a `.kit`

Both `omni.kit.livestream.app` and the XR extensions want to drive
the Hydra renderer. They expect different swapchain shapes (2D vs.
stereo). So a "VR-capable" build is a *third* sibling app, not a
flag on `viewer_streaming.kit`:

- `senckenberg.messelpit.explorer.kit` — desktop iteration (have)
- `senckenberg.messelpit.viewer.kit` — base for streaming (have)
- `senckenberg.messelpit.viewer_streaming.kit` — adds WebRTC (have)
- `senckenberg.messelpit.viewer_xr.kit` — adds XR (future, separate)

This is actually clean — it means the streaming work we did isn't
wasted, and the VR work won't break it.

### Concrete next step: registry probe

Create a throwaway `.kit` that depends on `omni.kit.xr.bundle.generic`
and `omni.kit.xr.system.openxr`, run `repo.bat build`, observe:

1. **Does packman fetch from the public registry?** If yes (no 401),
   we have access. If no, we need NVIDIA Enterprise registry credentials
   and the whole XR path may be gated behind a license.
2. **What is `bundle.generic`'s `extension.toml`?** Look for runtime
   linkage: SteamVR? Monado? Native OpenXR? CloudXR Server?
3. **What other extensions get pulled in transitively?** If something
   called `cloudxr-server` or `nvidia-cloudxr-runtime` shows up, that's
   the answer.

Time budget: ~10 minutes if registry pull works, then ~5 minutes of
file inspection. After that we can update this doc with a definitive
B-vs-C verdict.
