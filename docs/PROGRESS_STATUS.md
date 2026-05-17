# Progress Status - Resume Checkpoint

Last updated: 2026-05-17

## Current Working State

App chạy bằng:

```powershell
cd "d:\Project\Auto TFT"
.\.venv\Scripts\python.exe app.py
```

Hoặc:

```powershell
run_app.bat
```

UI hiện dùng CustomTkinter, tổ chức MVP.

## Important Files

Entrypoint:

- `app.py`

View:

- `tft_companion/views/main_window.py`
- `tft_companion/views/workspace.py`
- `tft_companion/views/sidebar.py`
- `tft_companion/views/advisor_tab.py`
- `tft_companion/views/screen_tab.py`
- `tft_companion/views/data_browser.py`
- `tft_companion/views/widgets.py`
- `tft_companion/views/constants.py`

Presenter:

- `tft_companion/presenters/main_presenter.py`

Models:

- `tft_companion/models/game.py`
- `tft_companion/models/screen.py`

Services:

- `tft_companion/services/screen_service.py`
- `tft_companion/services/decision_engine.py`
- `tft_companion/services/data_service.py`

Data generator:

- `scripts/generate_tft_ini.py`

Generated data:

- `data/generated/set17/meta.ini`
- `data/generated/set17/champions.ini`
- `data/generated/set17/traits.ini`
- `data/generated/set17/items.ini`

Generated assets:

- `data/generated/set17/assets/champions`: 83 images.
- `data/generated/set17/assets/abilities`: 82 images.
- `data/generated/set17/assets/traits`: 44 images.
- `data/generated/set17/assets/items`: 688 images.

## Environment

Installed/used:

- Python 3.12.10.
- `.venv`.
- CustomTkinter 5.2.2.
- Pillow.
- MSS.
- pytesseract.
- Tesseract installed at `C:\Program Files\Tesseract-OCR\tesseract.exe`.
- ADB/platform-tools installed through winget.
- scrcpy 4.0 installed through winget.

Known Android device:

```text
69FYWKXS6HBMOBFU
model: 2506BPN68G
Android 16
```

## Working Features

- Manual game state input.
- Advice generation.
- PC screenshot.
- Android ADB screenshot.
- scrcpy mirror start.
- scrcpy window read.
- Screen preview.
- Timing breakdown:
  - Capture.
  - OCR.
  - Total.
- TFT Mobile structured read:
  - Stage.
  - Gold.
  - Level.
- Static `.ini` data generation from CommunityDragon.
- Asset download for champion/ability/trait/item images.
- Sidebar is navigation-only.
- Advisor tab contains manual Game State and advice.
- Screen tab contains capture controls, preview, and readout.
- Champions, Items, and Traits tabs display generated INI records with icons/details.

## Recent Fixes

- Replaced old scrcpy 1.25 with scrcpy 4.0 because Android 16 crashed old scrcpy.
- `champions.ini` now uses `stats.hp`, not `stats.health`.
- Added ability data to `champions.ini`.
- Added local asset folders.
- Project refactored to MVP.
- UI rebuilt as a modern dashboard with metric cards and Advisor/Screen/Data tabs.
- UI adjusted so sidebar only contains main menus; Game State moved into Advisor and capture actions moved into Screen.
- Added static data browsers for Champions, Items, and Traits.
- Split view code into focused modules so `main_window.py` only owns app state and presenter callbacks.

## Known Limitations

- Champion recognition is not implemented.
- Board grid detection is not implemented.
- Item recognition on units is not implemented.
- Trait calculation from live board is not implemented.
- Full game engine is not implemented yet.
- Current advice uses manual/structured fields only.
- OCR/structured read may fail if TFT screen state differs from expected crop regions.

## Next Recommended Task

Start Phase 2: Board Detection MVP.

Suggested first files:

- `tft_companion/models/board.py`
- `tft_companion/services/board_detector.py`
- `tft_companion/services/debug_renderer.py`

Suggested first UI action:

- Add button `Detect Board`.

Expected first result:

- Read `screenshots/latest_scrcpy_screen.png`.
- Draw grid overlay.
- Save `screenshots/board_debug.png`.
- Show debug image in app.

## Useful Commands

Compile check:

```powershell
.\.venv\Scripts\python.exe -m py_compile app.py scripts\generate_tft_ini.py tft_companion\models\game.py tft_companion\models\screen.py tft_companion\services\data_service.py tft_companion\services\decision_engine.py tft_companion\services\screen_service.py tft_companion\presenters\main_presenter.py tft_companion\views\main_window.py
```

Generate latest data:

```powershell
.\.venv\Scripts\python.exe scripts\generate_tft_ini.py --output-dir data\generated
```

Generate set17 with assets:

```powershell
.\.venv\Scripts\python.exe scripts\generate_tft_ini.py --set-number 17 --output-dir data\generated --download-assets --asset-kinds champions traits items
```

Check generated data:

```powershell
.\.venv\Scripts\python.exe -c "from pathlib import Path; from tft_companion.services.data_service import load_tft_static_data; d=load_tft_static_data(Path('data/generated/set17')); print(len(d.champions), len(d.traits), len(d.items)); print(d.champions['TFT17_Aatrox']['ability_name'])"
```

Run app:

```powershell
.\.venv\Scripts\python.exe app.py
```
