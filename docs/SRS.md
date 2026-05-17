# Software Requirements Specification - TFT Decision Companion

## 1. Mục tiêu

TFT Decision Companion là ứng dụng desktop hỗ trợ người chơi Teamfight Tactics ra quyết định trong trận. Ứng dụng chỉ đọc màn hình, phân tích trạng thái, hiển thị gợi ý và lý do. Ứng dụng không tự click, không bấm phím, không điều khiển game.

## 2. Phạm vi hiện tại

Ứng dụng hiện tập trung vào:

- Nhập và chỉnh trạng thái trận bằng tay.
- Đọc nhanh màn hình Android TFT qua ADB hoặc cửa sổ scrcpy.
- Đọc một số thông tin cơ bản: stage, gold, level.
- Hiển thị ảnh preview màn hình đã capture.
- Hiển thị thời gian chi tiết: capture, OCR/recognition, total.
- Sinh gợi ý heuristic về economy, roll/level, shop, item, positioning, risk.
- Generate dữ liệu tĩnh TFT thành file `.ini` từ CommunityDragon.

## 3. Phạm vi không làm

- Không xây bot tự động chơi thay người.
- Không tự thao tác trong TFT.
- Không né anti-cheat hoặc can thiệp client game.
- Không dùng cơ chế đọc memory/process game.

## 4. Người dùng mục tiêu

- Người chơi TFT muốn có companion app đưa gợi ý trong lúc chơi.
- Developer muốn mở rộng app thành công cụ phân tích board, item, trait.

## 5. Yêu cầu chức năng

### 5.1 UI nhập trạng thái

Ứng dụng phải cho nhập/sửa:

- Stage.
- Level.
- Gold.
- HP.
- Streak.
- Số pair.
- Số core unit còn thiếu.
- Board strength: weak/even/strong.
- Bench full.
- Contested comp.
- Target comp.

### 5.2 Đọc màn hình

Ứng dụng phải hỗ trợ các nguồn đọc:

- PC screenshot.
- Android screenshot qua ADB `screencap`.
- scrcpy mirror window ở chế độ `--no-control`.

Ứng dụng phải lưu ảnh vào thư mục `screenshots/`.

### 5.3 Structured read cho TFT Mobile

Ứng dụng phải crop vùng cố định trên screenshot/mirror để đọc:

- Stage.
- Gold.
- Level.

Android structured read không chạy full-screen OCR mặc định.

### 5.4 Timing breakdown

Mỗi lần đọc màn hình phải trả về:

- `Capture`: thời gian lấy ảnh/frame.
- `OCR`: thời gian crop/recognition/OCR.
- `Total`: tổng thời gian service xử lý.

UI phải hiển thị các thông tin này.

### 5.5 Static data `.ini`

Ứng dụng phải có script generate dữ liệu tĩnh từ CommunityDragon:

- `meta.ini`.
- `champions.ini`.
- `traits.ini`.
- `items.ini`.

Champion data phải gồm:

- Name.
- API name.
- Character name.
- Cost.
- Traits.
- Role.
- Icon paths.
- Local icon.
- HP.
- Armor.
- Magic resist.
- Attack damage.
- Attack speed.
- Range.
- Mana.
- Initial mana.
- Ability name.
- Ability description.
- Ability icon.
- Ability local icon.
- Ability variables JSON.
- Ability raw JSON.

Asset folders phải gồm:

- `assets/champions`.
- `assets/abilities`.
- `assets/traits`.
- `assets/items`.

### 5.6 Advice engine hiện tại

Ứng dụng phải sinh advice dựa trên `GameState`:

- Headline.
- Economy.
- Roll/Level.
- Shop.
- Item.
- Positioning.
- Risk.

Advice hiện dùng heuristic rules, chưa dùng board recognition.

## 6. Yêu cầu phi chức năng

- Chạy local trên Windows.
- Dùng Python 3.11+.
- UI dùng CustomTkinter.
- Không cần database server.
- Static data được load từ `.ini`.
- Không phụ thuộc internet khi đã generate data và assets.
- Code tổ chức theo MVP.

## 7. Kiến trúc

Project dùng MVP:

- `models`: data classes, không chứa logic UI.
- `services`: logic nghiệp vụ, screen capture, OCR, static data, decision rules.
- `presenters`: điều phối giữa view và service.
- `views`: UI CustomTkinter.

Entrypoint:

- `app.py`.

## 8. Dữ liệu đầu vào/đầu ra

### Input

- Ảnh màn hình từ PC/ADB/scrcpy.
- Manual game state.
- Static TFT data từ `.ini`.

### Output

- Advice text.
- Screen preview.
- Recognized fields.
- Timing breakdown.

## 9. Roadmap yêu cầu sắp tới

Ưu tiên tiếp theo là nhận diện bàn cờ:

1. Xác định board region.
2. Map board region sang hex grid.
3. Detect ô có unit.
4. Render debug overlay.
5. Crop từng ô.
6. Nhận diện champion bằng asset/template.
7. Nhận diện item trên unit.

