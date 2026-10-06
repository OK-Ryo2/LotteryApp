import json
import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Prize:
    """prizes.json に定義される景品データ。"""

    prize_id: str
    rank: int
    list_name: str
    current_name: str
    description: str
    image_path: str
    stock: int


# Excelで編集する日本語CSVの見出しと、JSON内で使うキー名の対応表。
CSV_REQUIRED_FIELD_MAPPING = {
    "賞品ID": "id",
    "等級": "rank",
    "賞品名(一覧表示)": "list_name",
    "賞品名(中央表示)": "current_name",
    "画像ファイルパス": "image_path",
    "個数": "stock",
}
# 商品説明は任意列。CSVにない場合は賞品名から既定の説明文を補う。
CSV_DESCRIPTION_FIELD = "商品説明"


def sync_prize_json_from_csv(
    csv_path: str | Path, json_path: str | Path
) -> bool:
    """CSVがJSONより新しい場合にJSONへ変換する。変換時はTrueを返す。"""
    csv_file = Path(csv_path)
    json_file = Path(json_path)
    # CSVがない場合は、既存のJSONをそのまま利用する。
    if not csv_file.exists():
        return False

    # CSVがJSONより新しい場合だけ変換し、起動ごとの不要な上書きを防ぐ。
    if json_file.exists() and csv_file.stat().st_mtime <= json_file.stat().st_mtime:
        return False

    convert_prize_csv_to_json(csv_file, json_file)
    return True


def convert_prize_csv_to_json(csv_path: str | Path, json_path: str | Path):
    """日本語見出しの賞品CSVを、整形済みJSON配列へ変換する。"""
    # Windows版Excelで文字化けしないShift_JIS（CP932）形式を読み込む。
    with Path(csv_path).open(encoding="cp932", newline="") as csv_file:
        # Excelで編集・保存したWindows向けCSV（CP932）を読み込む。
        reader = csv.DictReader(csv_file)
        if not reader.fieldnames or not set(CSV_REQUIRED_FIELD_MAPPING).issubset(reader.fieldnames):
            headers = "、".join(CSV_REQUIRED_FIELD_MAPPING)
            raise ValueError(f"賞品CSVの見出しには「{headers}」が必要です。")

        raw_prizes = []
        for row_number, row in enumerate(reader, start=2):
            try:
                # CSVの各列をJSON用のキーへ変換し、数値列も型を揃える。
                raw_prizes.append(
                    {
                        json_key: _csv_value(row, csv_key, row_number)
                        for csv_key, json_key in CSV_REQUIRED_FIELD_MAPPING.items()
                    }
                )
                raw_prizes[-1]["description"] = (
                    row.get(CSV_DESCRIPTION_FIELD, "").strip()
                    or f"{raw_prizes[-1]['current_name']}を楽しめる賞品です。"
                )
                raw_prizes[-1]["rank"] = int(raw_prizes[-1]["rank"])
                raw_prizes[-1]["stock"] = int(raw_prizes[-1]["stock"])
            except ValueError as error:
                raise ValueError(f"賞品CSVの{row_number}行目が不正です: {error}") from error

    if not raw_prizes:
        raise ValueError("賞品CSVに景品が登録されていません。")

    # JSONとして保存する前に、ID・等級・個数などを既存の検証規則で確認する。
    # 重複・必須項目・数値の不正を検証してから、整形済みJSONとして保存する。
    _validate_raw_prizes(raw_prizes)
    Path(json_path).write_text(
        json.dumps(raw_prizes, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def load_prizes(json_path: str | Path) -> list[Prize]:
    """整形済みの景品JSONを読み込み、画面表示用に等級順へ並べ替える。"""
    path = Path(json_path)
    if not path.exists():
        raise FileNotFoundError(f"景品JSONが見つかりません: {path}")

    with path.open(encoding="utf-8") as json_file:
        # JSONの配列を読み込み、下の共通検証処理へ渡す。
        raw_prizes = json.load(json_file)

    if not isinstance(raw_prizes, list) or not raw_prizes:
        raise ValueError("景品JSONは、1件以上の景品を含む配列にしてください。")

    return _validate_raw_prizes(raw_prizes)


def _validate_raw_prizes(raw_prizes: list[dict]) -> list[Prize]:
    # JSON/CSV変換後のデータを同じルールで検証し、画面で扱うPrizeへ変換する。
    prizes: list[Prize] = []
    prize_ids: set[str] = set()
    ranks: set[int] = set()
    required_fields = {
        "id",
        "rank",
        "list_name",
        "current_name",
        "image_path",
        "stock",
    }

    for index, item in enumerate(raw_prizes, start=1):
        # まず各賞品に必要な項目がそろっているかを確認する。
        if not isinstance(item, dict) or not required_fields.issubset(item):
            raise ValueError(f"景品JSONの{index}件目に必要な項目がありません。")

        prize_id = item["id"]
        rank = item["rank"]
        list_name = item["list_name"]
        current_name = item["current_name"]
        image_path = item["image_path"]
        stock = item["stock"]

        if not isinstance(prize_id, str) or not prize_id.strip():
            raise ValueError(f"景品JSONの{index}件目のidが不正です。")
        if prize_id in prize_ids:
            raise ValueError(f"景品id「{prize_id}」が重複しています。")
        if not isinstance(rank, int) or rank < 1:
            raise ValueError(f"景品「{prize_id}」のrankが不正です。")
        if rank in ranks:
            raise ValueError(f"{rank}等が重複しています。")
        if not isinstance(list_name, str) or not list_name.strip():
            raise ValueError(f"景品「{prize_id}」のlist_nameが不正です。")
        if not isinstance(current_name, str) or not current_name.strip():
            raise ValueError(f"景品「{prize_id}」のcurrent_nameが不正です。")
        if not isinstance(image_path, str) or not image_path.strip():
            raise ValueError(f"景品「{prize_id}」のimage_pathが不正です。")
        if not isinstance(stock, int) or stock < 1:
            raise ValueError(f"景品「{prize_id}」のstockが不正です。")

        prize_ids.add(prize_id)
        ranks.add(rank)
        # 旧JSONとの互換性を保ちつつ、CSV変換後は必ず商品説明を持たせる。
        description = item.get("description", "忘年会を彩る特別な賞品です。")
        if not isinstance(description, str) or not description.strip():
            raise ValueError(f"景品「{prize_id}」のdescriptionが不正です。")

        # 検証済みの値だけを不変のPrizeデータとして追加する。
        prizes.append(
            Prize(prize_id, rank, list_name, current_name, description, image_path, stock)
        )

    # 表示・抽選処理で扱いやすいよう、等級の昇順で返す。
    return sorted(prizes, key=lambda prize: prize.rank)


def _csv_value(row: dict[str, str], key: str, row_number: int) -> str:
    # 必須CSV列が空欄の場合は、行番号付きで編集箇所を知らせる。
    value = row.get(key, "").strip()
    if not value:
        raise ValueError(f"「{key}」が空です")
    return value
