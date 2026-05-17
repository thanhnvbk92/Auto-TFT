# Implementation Plan - TFT Decision Companion

## Phase 0 - Baseline đã hoàn thành

Mục tiêu: có app desktop chạy được và đọc trạng thái cơ bản.

Hoàn thành:

- CustomTkinter UI.
- MVP split cơ bản.
- PC screenshot.
- Android ADB screenshot.
- scrcpy mirror capture.
- TFT Mobile structured read cho stage/gold/level.
- Timing breakdown capture/OCR/total.
- Heuristic advice engine.
- Static TFT `.ini` generator từ CommunityDragon.
- Download champion/ability/trait/item assets.

## Phase 1 - Static Data Stabilization

Mục tiêu: dữ liệu `.ini` sạch, dễ load, dễ dùng cho engine và recognition.

Tasks:

- [x] Generate `champions.ini`, `traits.ini`, `items.ini`, `meta.ini`.
- [x] Thêm HP đúng từ `stats.hp`.
- [x] Thêm ability data vào `champions.ini`.
- [x] Tải ảnh champion, ability, trait, item.
- [ ] Tách `items.ini` thành nhóm:
  - `items_components.ini`.
  - `items_completed.ini`.
  - `items_emblems.ini`.
  - `items_internal.ini`.
- [ ] Thêm model typed cho Champion/Trait/Item thay vì dict raw.
- [ ] Thêm search/index service theo name/api_name.

## Phase 2 - Board Detection MVP

Mục tiêu: nhận diện grid bàn cờ và ô có unit, chưa cần biết unit là ai.

Files dự kiến:

- `tft_companion/models/board.py`.
- `tft_companion/services/board_detector.py`.
- `tft_companion/services/debug_renderer.py`.
- `tft_companion/presenters/board_presenter.py` hoặc mở rộng `MainPresenter`.

Tasks:

- [ ] Tạo model:
  - `BoardTile`.
  - `BoardGrid`.
  - `DetectedUnitSlot`.
  - `BoardDetectionResult`.
- [ ] Xác định board region cho ảnh scrcpy 2772x1280 và scale theo kích thước ảnh.
- [ ] Tạo danh sách tọa độ hex/tile.
- [ ] Crop từng tile.
- [ ] Detect tile occupied bằng rule đơn giản:
  - edge density.
  - color/brightness difference.
  - unit health bar detection.
- [ ] Render debug image:
  - vẽ grid.
  - đánh số tile.
  - tô màu tile occupied.
- [ ] Thêm nút UI `Detect Board`.
- [ ] Hiển thị debug overlay trong preview.
- [ ] Lưu debug vào `screenshots/board_debug.png`.

Acceptance criteria:

- Bấm `Read scrcpy window`.
- Bấm `Detect Board`.
- App hiển thị ảnh board có grid.
- Ít nhất 70% ô có unit được đánh dấu đúng ở màn hình test đơn giản.

## Phase 3 - Champion Recognition MVP

Mục tiêu: từ ô có unit, dự đoán champion.

Tasks:

- [ ] Chuẩn bị asset cache:
  - resize champion icons.
  - normalized grayscale/color histograms.
- [ ] Crop unit portrait/visual area từ tile.
- [ ] Thử template matching đơn giản bằng OpenCV hoặc PIL.
- [ ] Tính confidence.
- [ ] Output:
  - tile id.
  - champion id.
  - champion name.
  - confidence.
- [ ] UI debug: hiển thị danh sách detected champions.

Ghi chú:

- Nếu template matching không đủ tốt, chuyển sang image embedding hoặc classifier nhẹ.

## Phase 4 - Trait Calculator

Mục tiêu: từ detected champions tính trait active/missing.

Tasks:

- [ ] Tạo `trait_calculator.py`.
- [ ] Load champion traits từ `.ini`.
- [ ] Count unique champions trên board.
- [ ] Tính breakpoints từ `traits.ini`.
- [ ] Output:
  - active traits.
  - next breakpoint.
  - missing count.
- [ ] UI hiển thị trait summary.

## Phase 5 - Item Recognition

Mục tiêu: nhận diện item trên unit.

Tasks:

- [ ] Xác định vị trí item icon quanh unit trong tile.
- [ ] Crop item slots.
- [ ] Match với `assets/items`.
- [ ] Output item id/name/confidence.
- [ ] UI debug item.

## Phase 6 - Engine nâng cấp

Mục tiêu: dùng board state thật để ra quyết định.

Tasks:

- [ ] `shop_evaluator.py`.
- [ ] `economy_engine.py`.
- [ ] `item_engine.py`.
- [ ] `positioning_engine.py`.
- [ ] `game_engine.py`.
- [ ] Advice có reason + confidence.

Example output:

```text
Buy Aatrox: +Bastion, improves frontline, 1-cost pair.
Do not roll: stage 2-1, HP safe, gold low.
```

## Technical Notes

- ADB `screencap` chậm khoảng 1.4s trên thiết bị hiện tại.
- scrcpy capture nhanh hơn nhưng hiện vẫn phụ thuộc OCR vùng.
- Để xuống rất nhanh cần giảm Tesseract hoặc thay bằng template/digit recognition riêng.
- Recognition nên luôn có debug overlay để dễ chỉnh.

