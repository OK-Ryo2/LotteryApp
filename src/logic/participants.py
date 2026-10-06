import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Participant:
    """抽選対象の参加者。CSVの行番号を内部的な一意識別子として扱う。"""

    participant_id: str
    name: str
    department: str = ""

    def to_dict(self) -> dict[str, str]:
        # UIウィジェットへ渡すため、データクラスを辞書形式へ変換する。
        return {
            "id": self.participant_id,
            "name": self.name,
            "department": self.department,
        }


def load_participants(csv_path: str | Path) -> list[Participant]:
    """department,name の参加者CSVを読み込み、不正な行を検出する。"""
    path = Path(csv_path)
    # 起動時に指定CSVが存在するかを先に確認する。
    if not path.exists():
        raise FileNotFoundError(f"参加者CSVが見つかりません: {path}")

    # Excelで編集した日本語CSV（Shift-JIS/CP932）を読み込む。
    with path.open(encoding="cp932", newline="") as csv_file:
        # UTF-8 BOM付きCSVにも対応し、列名をキーに各行を読み込む。
        reader = csv.DictReader(csv_file)
        if not reader.fieldnames:
            raise ValueError("CSVの見出し行がありません。")

        participants: list[Participant] = []
        for row_number, row in enumerate(reader, start=2):
            # 日本語見出し・英語見出しのどちらでも参加者CSVを扱えるようにする。
            name = _value(row, "氏名", "name")
            department = _value(row, "部署", "department")

            if not name:
                raise ValueError(f"{row_number}行目の氏名が空です。")
            if not department:
                raise ValueError(f"{row_number}行目の部署が空です。")

            # CSVには個人を特定するIDを含めないため、行番号を内部IDとして使う。
            # CSVの行番号から一意な内部IDを作成する。
            participant_id = f"row-{row_number}"
            participants.append(Participant(participant_id, name, department))

    if not participants:
        raise ValueError("参加者CSVに参加者が登録されていません。")
    return participants


def _value(row: dict[str, str], *keys: str) -> str:
    # 指定された候補見出しを順に確認し、最初に見つかった値を返す。
    for key in keys:
        value = row.get(key)
        if value:
            return value.strip()
    return ""
