from .participants import Participant


class Lottery:
    """当選者を管理し、同じ参加者を重複当選させない抽選状態。"""

    def __init__(self, participants: list[Participant]):
        self._all_participants = participants
        self._winner_ids: set[str] = set()

    @property
    def available_participants(self) -> list[Participant]:
        return [
            participant
            for participant in self._all_participants
            if participant.participant_id not in self._winner_ids
        ]

    @property
    def has_available_participant(self) -> bool:
        return bool(self.available_participants)

    def confirm_winner(self, participant_id: str) -> Participant:
        """ルーレット中央の参加者を当選者として確定する。"""
        for participant in self.available_participants:
            if participant.participant_id == participant_id:
                self._winner_ids.add(participant_id)
                return participant
        raise ValueError("選択した参加者は抽選対象ではありません。")

    def reset(self):
        """当選履歴を消去し、全員を抽選対象へ戻す。"""
        self._winner_ids.clear()
