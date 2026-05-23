# Quest 2 Streaming Test — Result

**Date:** 2026-05-21
**Branch:** `streaming-experiment`
**Outcome:** Success — Messel pit terrain rendered in Meta Quest 2 browser over home Wi-Fi.

## What worked

End-to-end pipeline:

```
DGM1 LiDAR + DOP20 ortho
    └─> messel_med.usd  (data repo, --decimate 4, ~6.75M tris)
         └─> Kit headless (--no-window), RTX rendering on RTX 4090
              └─> omni.kit.livestream.webrtc encode
                   └─> Home Wi-Fi (192.168.25.0/24, Fritzbox)
                        └─> Quest 2 browser
                             └─> web-viewer-sample React UI in flat browser window
```

The Quest 2 displayed the Messel terrain inside a flat browser window
floating in 3D space — the same 2D video stream that worked on desktop
Chrome, just delivered to the headset over LAN instead of localhost.

## Configuration used

| Piece | Value |
|---|---|
| PC LAN IP (spearow, Ethernet) | `192.168.25.5` |
| Quest 2 connection | Wi-Fi to same Fritzbox |
| Kit streaming kit | `senckenberg.messelpit.viewer_streaming.kit` |
| Light rig | `Sunny Sky` (auto-applied via .kit settings) |
| USD asset | `D:/senckenberg/messelpit/out/messel_med.usd` (selected from dropdown) |
| Browser client | `D:\senckenberg\web-viewer-sample\` (Vite dev server, port 5173) |
| Vite `stream.config.json` | `server: "192.168.25.5"`, signalingPort `49100`, source `"local"` |
| Vite `vite.config.ts` | `server.host: true` (binds to all interfaces) |
| Firewall rules (Private profile only) | TCP 49100, UDP for `kit.exe`, TCP 5173 |
| Firewall script | `tools/add-firewall-rules.ps1` (idempotent, self-elevating) |

## Launch sequence

PC, **Terminal 1** (`cmd.exe` in `D:\senckenberg\messelpit_viewer`):
```
launch_stream.bat
```

PC, **Terminal 2** (`cmd.exe` in `D:\senckenberg\web-viewer-sample`):
```
npm run dev
```
(Note: requires the `server.host: true` setting in `vite.config.ts`,
otherwise Vite binds to localhost only and the Quest can't reach it.)

Quest 2:
1. Meta button → universal menu → Browser app
2. Navigate to `http://192.168.25.5:5173`
3. Select "Messel Pit" from the USD Asset dropdown

## What didn't work

- **Camera navigation**: The web-viewer-sample is built around
  mouse-drag-to-orbit and WASD-to-fly. The Quest 2 browser doesn't
  synthesize those input events from the controller pointer, so the
  view is stuck on the default camera. You can see the terrain but
  can't move around inside it.
- **Stereoscopic VR**: The stream is 2D — a flat video texture
  inside the Quest's browser window. Head tracking moves you around
  the floating window but doesn't reproject the scene. This is by
  design of the WebRTC stack we're using; real VR is a separate path
  (see [vr-roadmap.md](vr-roadmap.md)).

## Surprises / gotchas captured

1. **Vite binds to `localhost` by default** — needs `server.host: true`
   (or `npm run dev -- --host`) for LAN devices. Fixed in
   `vite.config.ts` on local clone of web-viewer-sample.
2. **Hardcoded Windows path in client** — `Window.tsx` has
   `D:/senckenberg/messelpit/out/messel_med.usd` baked in. Won't
   work on another machine without editing. Future task: pull from
   `stream.config.json`.
3. **First load was very slow** — Kit takes ~10s to start, then USD
   parse + texture upload + initial frame render is another few
   seconds. Patience is required before assuming something's broken.
4. **Light rig is required** — the base Viewer kit doesn't apply one
   automatically (Explorer does). We added `omni.light_rigs` +
   `omni.kit.viewport.menubar.lighting` deps + `Sunny Sky` default
   in `viewer_streaming.kit`. Without that the terrain renders solid
   black.

## What this proves

- Kit's WebRTC streaming layer is correctly configured for our scene.
- The Messel `.usd` + `.png` data is portable enough to stream live.
- The home Wi-Fi has enough bandwidth (and low enough latency) for a
  passable 1080p stream from spearow to the Quest.
- The Senckenberg deliverable concept is feasible: visitors with a
  Quest could load a URL on Wi-Fi and see the pit. No app install
  required.

## What's still missing for a real demo

Camera navigation. Without it, you can see the terrain but can't
"visit" the pit. See [vr-roadmap.md](vr-roadmap.md) for the path to
walking-in-VR.
