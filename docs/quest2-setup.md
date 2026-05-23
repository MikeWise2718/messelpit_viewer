# Meta Quest 2 Setup Checklist

Steps to take a long-stored Meta Quest 2 (gifted ~3-4 years ago, never
used by current owner) from cold to ready-to-test-streaming. Aimed at
the WebRTC 2D streaming smoke test (Path A in the conversation log) and
also preps the headset for any future CloudXR / sideload work.

Do these in order — don't try to debug streaming until the headset
itself is verified working.

## Status tracker

| Step | Status | Notes |
|---|---|---|
| 1. Charge the headset | not started | |
| 2. Power on, initial setup with phone app | not started | |
| 3. Sign in / create Meta account | not started | |
| 4. Set up Guardian (play area) | not started | |
| 5. Run system firmware updates | not started | May chain multiple updates |
| 6. Verify it works (First Steps or built-in demo) | not started | |
| 7. Open Quest browser, hit any HTTPS site | not started | Sanity check before LAN test |
| 8. (Optional) Enable Developer Mode | not started | Needed for CloudXR / sideloading later |

Update the status column as you go — same pattern as
`specs/messelpit-viewer.md`.

## 1. Charge the headset

- USB-C cable in the box (or any USB-C PD charger you have).
- A long-stored Li-ion battery may be deeply discharged — plug it in for
  **at least 15 minutes** before trying to power on.
- Full charge from empty: ~2.5 hours.
- Battery in use: ~2 hours, so keep a charger nearby for the setup
  session.

## 2. Power on, initial setup with phone app

- Power button is on the right side of the headset (long press).
- The Quest 2 setup wizard *requires* the **Meta Quest mobile app**
  (iOS or Android) for Wi-Fi credentials and pairing. Install it on
  your phone first.
- In the phone app: Devices → Pair New Headset → follow the prompts.
- The headset will display a 5-digit pairing code; type it into the
  phone app.

## 3. Sign in / create Meta account

- A Meta account is required. If you have a Facebook account, a
  3-4-year-old Quest 2 may still accept the old FB-login flow, but
  newer firmware forces a separate Meta account.
- If asked, create a Meta account at <https://www.meta.com/> (free,
  ~2 minutes).
- Your daughter's headset would use her own account — don't share
  accounts between the two Quest devices.

## 4. Set up Guardian (play area)

- The Guardian is a virtual boundary that warns you when you walk into
  furniture.
- Two modes:
  - **Stationary**: a 1 m radius around where you're standing/sitting.
    Fine for desk use, fine for "look at the Messel pit while standing
    still."
  - **Roomscale**: trace your real play area with the controller. Worth
    2 minutes if you've got open floor space.
- Can be changed later from headset settings.

## 5. Run system firmware updates

- After initial setup, go to **Settings → System → Software Update**.
- A device from this vintage will probably chain through **several**
  updates (each ~5-15 min). Possibly 30-60 min total wall-clock.
- Leave it plugged in. Don't power it off mid-update.
- Re-check for updates after each one completes — sometimes the next
  update only becomes available once the previous one is applied.

## 6. Verify it works

- Run the built-in tour / "First Steps" experience (free, comes
  pre-installed or available in the store).
- Things to verify:
  - Lenses are clean (a microfiber cloth — paper towels can scratch them).
  - **IPD** (interpupillary distance) is set correctly. The Quest 2 has
    a physical slider on the bottom of the headset with three discrete
    positions (58 mm, 63 mm, 68 mm). Wrong IPD causes eye strain fast.
    Pick the position that gives the sharpest image when you look at
    text in the menus.
  - Controllers track properly (passthrough mode shows them in real
    space; the LEDs on the tracking rings should be visible to the
    headset cameras).
  - Audio: built-in spatial speakers should work without earphones.

## 7. Open Quest browser, hit any HTTPS site

- This is a sanity check before our streaming test.
- From the home dashboard, find the **Browser** app.
- Visit any HTTPS site (e.g. <https://google.com>). Confirm it loads
  and is usable.
- **Note for later**: WebXR features need HTTPS or `localhost`. Plain
  HTTP works for non-XR pages like our WebRTC client — but if we hit
  any "secure context required" errors during the streaming test,
  that's the cause.

## 8. (Optional) Enable Developer Mode

- **Not required for the WebRTC browser streaming test** (Path A).
- **Required for**:
  - Sideloading APKs
  - CloudXR client app (future Path B for real stereoscopic VR)
  - ADB access for debugging
- Steps:
  1. Go to <https://developers.meta.com/> and create a developer
     organization (free, ~2 minutes). You only need to provide an
     org name; no review or approval needed.
  2. In the **Meta Quest mobile app** on your phone: Devices → select
     your headset → Headset Settings → **Developer Mode** → toggle on.
  3. Restart the headset.
- Do this now if you might want to try CloudXR later this week. Skip
  if you only care about the browser-streaming test.

## What's next after these steps

Once the Quest 2 is set up and confirmed working:

1. Find your PC's LAN IP: `ipconfig` → IPv4 of the active Wi-Fi adapter.
2. Edit `D:\senckenberg\web-viewer-sample\stream.config.json`: change
   `"server": "127.0.0.1"` to `"server": "<your-PC-IP>"`.
3. Open Windows Firewall for port 49100 (WebRTC signaling) on the
   private network.
4. Launch as for desktop testing: `launch_stream.bat` in one terminal,
   `npm run dev` in another (in `web-viewer-sample/`).
5. On the Quest 2 browser, navigate to `http://<your-PC-IP>:5173`.

What you'll see: the Messel pit as a flat 2D video floating in the
Quest's virtual browser window. This is the WebRTC milestone, not
stereoscopic VR — real VR needs CloudXR or SteamVR + OpenXR, which is
a separate effort.
