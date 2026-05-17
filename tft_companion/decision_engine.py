from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


BoardStrength = Literal["weak", "even", "strong"]


@dataclass(frozen=True)
class GameState:
    stage: str = "2-1"
    level: int = 4
    gold: int = 0
    hp: int = 100
    streak: int = 0
    pairs: int = 0
    missing_core_units: int = 0
    board_strength: BoardStrength = "even"
    bench_full: bool = False
    contested: bool = False
    target_comp: str = ""


@dataclass(frozen=True)
class Advice:
    headline: str
    economy: str
    roll_level: str
    shop: str
    items: str
    positioning: str
    risk: str


def _stage_number(stage: str) -> tuple[int, int]:
    try:
        left, right = stage.strip().split("-", 1)
        return int(left), int(right)
    except (ValueError, AttributeError):
        return 2, 1


def build_advice(state: GameState) -> Advice:
    stage_major, stage_round = _stage_number(state.stage)
    low_hp = state.hp <= 35
    critical_hp = state.hp <= 20
    rich = state.gold >= 50
    healthy_econ = state.gold >= 30
    many_pairs = state.pairs >= 2

    headline = _headline(state, stage_major, critical_hp, low_hp, rich, many_pairs)
    economy = _economy_advice(state, rich, healthy_econ, low_hp)
    roll_level = _roll_level_advice(state, stage_major, stage_round, low_hp, critical_hp, rich, many_pairs)
    shop = _shop_advice(state, many_pairs)
    items = _item_advice(state)
    positioning = _positioning_advice(state, stage_major)
    risk = _risk_note(state, low_hp, critical_hp)

    return Advice(
        headline=headline,
        economy=economy,
        roll_level=roll_level,
        shop=shop,
        items=items,
        positioning=positioning,
        risk=risk,
    )


def _headline(
    state: GameState,
    stage_major: int,
    critical_hp: bool,
    low_hp: bool,
    rich: bool,
    many_pairs: bool,
) -> str:
    if critical_hp:
        return "Ưu tiên sống sót: roll xuống để mạnh ngay."
    if low_hp and state.board_strength == "weak":
        return "Board yếu và máu thấp: cần stabilize trong round này."
    if stage_major <= 2 and rich and state.board_strength != "weak":
        return "Giữ economy, đừng roll sớm nếu không cần."
    if many_pairs and state.gold >= 20:
        return "Có nhiều pair: roll nhẹ để nâng cấp nếu board đang hụt sức."
    if state.board_strength == "strong" and state.streak > 0:
        return "Đang có tempo: giữ streak và lên cấp đúng mốc."
    return "Chơi cân bằng: giữ vàng, chỉ roll khi có lý do rõ."


def _economy_advice(state: GameState, rich: bool, healthy_econ: bool, low_hp: bool) -> str:
    if low_hp and state.board_strength == "weak":
        return "Có thể phá mốc lãi để cứu máu. Đừng giữ 50 vàng nếu thua nặng liên tục."
    if rich:
        return "Giữ 50 vàng sau mỗi round nếu board không quá yếu. Dùng phần vàng dư để lên cấp hoặc roll theo mốc."
    if healthy_econ:
        return "Cố giữ ít nhất 30 vàng. Chỉ mua unit thật sự liên quan hoặc tạo pair quan trọng."
    return "Tập trung tạo lại economy. Bán unit phụ để chạm mốc 10/20 vàng nếu không làm yếu board chính."


def _roll_level_advice(
    state: GameState,
    stage_major: int,
    stage_round: int,
    low_hp: bool,
    critical_hp: bool,
    rich: bool,
    many_pairs: bool,
) -> str:
    if critical_hp:
        return "Roll sâu tới khi có nâng cấp lớn hoặc board đủ thắng round kế tiếp."
    if stage_major == 2:
        if state.level < 5 and state.gold >= 8 and state.board_strength == "strong":
            return "Có thể lên level 5 để giữ win streak. Nếu không streak, giữ vàng."
        return "Không roll ở stage 2 trừ khi có pair quá quan trọng và board rất yếu."
    if stage_major == 3:
        if low_hp and state.board_strength == "weak":
            return "Roll ở level 6/7 để tìm 2 sao và core unit, ưu tiên stabilize hơn greedy."
        if state.level < 6 and stage_round >= 2 and state.gold >= 20:
            return "Lên level 6 theo nhịp stage 3 nếu vẫn giữ được mốc lãi hợp lý."
        if many_pairs and state.gold >= 30:
            return "Roll nhẹ 10-20 vàng để hoàn thiện pair, dừng khi còn mốc lãi tốt."
        return "Giữ vàng và lên cấp theo curve. Chưa cần roll sâu."
    if stage_major == 4:
        if state.level < 7 and state.gold >= 20:
            return "Lên level 7 trước, sau đó roll để ổn định đội hình."
        if state.level >= 7 and (state.board_strength == "weak" or state.missing_core_units > 1):
            return "Roll ở level 7/8 để tìm core 4-cost và nâng cấp tuyến trước/tuyến sau."
        if rich and state.board_strength == "strong":
            return "Ưu tiên lên level 8 rồi roll cho carry 4-cost/5-cost."
        return "Roll có kiểm soát để board không tụt tempo ở stage 4."
    if state.level < 8 and state.gold >= 30:
        return "Lên level 8/9 nếu board đủ sống. Nếu yếu, roll trước để không mất quá nhiều máu."
    return "Roll tìm nâng cấp cuối, unit legendary hoặc trait breakpoint quan trọng."


def _shop_advice(state: GameState, many_pairs: bool) -> str:
    actions: list[str] = []
    if many_pairs:
        actions.append("Giữ các pair đang gần lên 2 sao.")
    if state.missing_core_units > 0:
        actions.append("Ưu tiên mua core unit còn thiếu hơn unit phụ.")
    if state.bench_full:
        actions.append("Bench đầy: bán unit ít liên quan để tránh bỏ lỡ shop tốt.")
    if state.contested:
        actions.append("Comp bị tranh: cân nhắc chuyển sang carry/trait dùng chung item.")
    if not actions:
        actions.append("Mua unit tăng sức mạnh ngay hoặc mở trait rõ ràng; tránh ôm quá nhiều hướng.")
    return " ".join(actions)


def _item_advice(state: GameState) -> str:
    if state.board_strength == "weak" or state.hp <= 40:
        return "Ghép item mạnh dùng được ngay cho carry/tank hiện tại. Đừng chờ BiS nếu đang mất máu."
    if state.target_comp:
        return f"Giữ component phù hợp với {state.target_comp}, nhưng ghép item linh hoạt nếu có thể giữ streak."
    return "Ưu tiên item linh hoạt: damage cho carry chính, tank item cho frontline, utility nếu đã đủ sát thương."


def _positioning_advice(state: GameState, stage_major: int) -> str:
    if stage_major <= 2:
        return "Đặt frontline che carry, scout nhanh nhà mạnh nhất nếu đang giữ streak."
    if state.board_strength == "weak":
        return "Dồn unit 2 sao và carry vào vị trí an toàn. Tránh để carry bị focus hoặc hook."
    return "Scout 2-3 đối thủ có thể gặp, đổi góc carry và đặt tank chính đối diện nguồn sát thương lớn."


def _risk_note(state: GameState, low_hp: bool, critical_hp: bool) -> str:
    if critical_hp:
        return "Rủi ro cao: một round thua lớn có thể kết thúc trận. Quyết định greedy không còn phù hợp."
    if low_hp:
        return "Máu thấp: ưu tiên top 4 bằng cách giảm rủi ro, không giữ quá nhiều vàng chết."
    if state.contested:
        return "Theo dõi số người tranh bài. Nếu nhiều người giữ cùng carry, pivot sớm sẽ rẻ hơn pivot muộn."
    return "Rủi ro thấp: có thể chơi greed vừa phải nếu vẫn giữ được board không quá yếu."

