# TFT Decision Companion

Desktop companion app for TFT decisions. The app reads screenshots and shows advice; it does not click, press keys, or control the game.

## Features

- Manual game-state input: stage, level, gold, HP, streak, pairs, board strength.
- PC screenshot capture saved to `screenshots/latest_screen.png`.
- Android screenshot capture through ADB saved to `screenshots/latest_android_screen.png`.
- Faster Android reading through a `scrcpy` mirror window in `--no-control` mode.
- Image preview inside the app after each PC or Android capture.
- Optional OCR with Tesseract to prefill visible fields.
- TFT Mobile fast structured reading: crops fixed UI regions for stage, gold, and level. Android does not run full-screen OCR.
- Heuristic advice for economy, roll/level, shop, items, positioning, and risk.
- Modern dark UI built with CustomTkinter.

## Project Structure

The app is organized with a small MVP split:

- `tft_companion/models`: plain data models such as game state, advice, screen read results, and timing.
- `tft_companion/services`: screen capture/OCR/scrcpy integration and decision logic.
- `tft_companion/presenters`: coordination layer between UI actions and services.
- `tft_companion/views`: CustomTkinter UI.
- `app.py`: thin entry point.

Screen reads now report detailed timing:

- `Capture`: time spent getting the screenshot/frame.
- `OCR`: time spent reading/cropping/OCRing the image.
- `Total`: full button-to-result time measured inside the screen service.

## Install

Requires Python 3.11+ in PATH. If `python --version` opens Microsoft Store or fails, install Python from python.org and enable `Add python.exe to PATH`.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

OCR requires Tesseract on Windows. The app still runs without it, but you will need to enter or correct fields manually.

## Android Screen Reading

To read a phone screen:

1. Install Android platform-tools so `adb` is available in PATH.
2. Enable Developer options on the phone.
3. Enable USB debugging.
4. Connect the phone by USB.
5. Accept the USB debugging authorization prompt on the phone.
6. Run:

```powershell
adb devices
```

The device should show as `device`, not `unauthorized`.

In the app, click `Find Android devices`. If one device is connected, you can leave `Android device id` blank. If multiple devices are connected, use the detected id.

For faster reads, click `Start scrcpy mirror`, wait for the mirror window, then use `Read scrcpy window`. This avoids the slow `adb screencap` step.

## Run

```powershell
python app.py
```

## Usage

1. Open TFT on PC or Android.
2. Click `Capture PC screen + OCR` or `Read Android screen + OCR`.
3. Check and correct the fields on the left.
4. Click `Update advice`.
5. Play manually based on the advice shown.

## Current Limits

- OCR over a full screen is not reliable for every TFT layout.
- Champion, item, and trait recognition are not implemented yet.
- The decision engine uses simple heuristics, not live patch meta data.

Good next upgrades:

- Configurable crop zones for gold, level, HP, shop, and stage.
- Android wireless ADB support notes.
- Champion/item/trait database for the current TFT set.
- Template matching for static UI icons from screenshots.
