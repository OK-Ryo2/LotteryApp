from .participants import Participant


class Lottery:
    """当選者を管理し、同じ参加者を重複当選させない抽選状態。"""

    def __init__(self, participants: list[Participant]):
        # 読み込んだ参加者一覧は保持したまま、当選者IDだけを別管理する。
        self._all_participants = participants
        self._winner_ids: set[str] = set()

    @property
    def available_participants(self) -> list[Participant]:
        # 当選済みの参加者を除外した、次回抽選で使える候補一覧を返す。
        return [
            participant
            for participant in self._all_participants
            if participant.participant_id not in self._winner_ids
        ]

    @property
    def has_available_participant(self) -> bool:
        # 抽選を継続できる参加者が残っているかを画面側で判定するためのプロパティ。
        return bool(self.available_participants)

    def confirm_winner(self, participant_id: str) -> Participant:
        """ルーレット中央の参加者を当選者として確定する。"""
        for participant in self.available_participants:
            if participant.participant_id == participant_id:
                # 当選確定時にIDを記録し、以降の抽選候補から除外する。
                self._winner_ids.add(participant_id)
                return participant
        raise ValueError("選択した参加者は抽選対象ではありません。")

    def reset(self):
        """当選履歴を消去し、全員を抽選対象へ戻す。"""
        # 当選履歴の判定だけを初期状態へ戻す。参加者CSVの内容は変更しない。
        self._winner_ids.clear()

    def winner_ids(self) -> set[str]:
        """画面状態を復元するため、確定済み参加者IDのコピーを返す。"""
        # 呼び出し元が内部のsetを直接変更できないようコピーを返す。
        return set(self._winner_ids)

    def restore_winner_ids(self, winner_ids: set[str]):
        """保存済みの抽選状態へ戻す。"""
        participant_ids = {participant.participant_id for participant in self._all_participants}
        # 再抽選・初期化の復元時は、現在の参加者一覧に存在するIDだけを採用する。
        self._winner_ids = set(winner_ids) & participant_ids
