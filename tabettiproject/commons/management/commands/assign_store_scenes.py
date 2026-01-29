from __future__ import annotations

from dataclasses import dataclass
from collections import Counter
from typing import Iterable

from django.core.management.base import BaseCommand
from django.db import transaction

from commons.models import Store, Scene


@dataclass(frozen=True)
class Rule:
    scene_name: str
    keywords: tuple[str, ...]
    weight: int = 1


# 店名・ジャンルに入りがちな単語から推定（必要なら増やしてOK）
RULES: tuple[Rule, ...] = (
    Rule("接待", ("料亭", "割烹", "懐石", "会席", "鮨", "寿司", "高級", "会員制", "ホテル", "個室", "銀座"), 3),
    Rule("家族・こどもと", ("ファミリー", "キッズ", "こども", "子供", "お子様", "ファミレス", "食堂", "ビュッフェ", "回転寿司"), 3),
    Rule("お一人様", ("一人", "おひとり", "ソロ", "カウンター", "立ち食い", "立ち飲み", "定食", "ラーメン", "そば", "うどん", "丼"), 2),
    Rule("デート", ("ビストロ", "イタリアン", "フレンチ", "ワイン", "夜景", "テラス", "バル", "ダイニング", "焼鳥", "焼き鳥"), 2),
    Rule("女子会", ("カフェ", "スイーツ", "パンケーキ", "アフタヌーンティー", "パフェ", "チーズ", "ジェラート"), 2),
    Rule("合コン", ("個室居酒屋", "居酒屋", "バー", "ラウンジ", "肉バル", "バル", "ダイニング"), 2),
)

# 同点のときの優先（上ほど優先）
TIE_BREAK_PRIORITY: tuple[str, ...] = ("接待", "家族・こどもと", "デート", "女子会", "合コン", "お一人様", "食事")


def normalize(text: str) -> str:
    return (text or "").strip().lower()


def build_scene_map() -> dict[str, Scene]:
    scenes = {s.scene_name: s for s in Scene.objects.all()}
    required = {"食事", "お一人様", "家族・こどもと", "接待", "デート", "女子会", "合コン"}
    missing = sorted(required - set(scenes.keys()))
    if missing:
        raise RuntimeError(f"Scene が不足しています: {missing}")
    return scenes


def score_for(rule: Rule, text: str) -> int:
    s = 0
    for kw in rule.keywords:
        if kw.lower() in text:
            s += rule.weight
    return s


def choose_scene_name_by_rules(store: Store) -> tuple[str, int]:
    """
    ルールで推定したシーン名とスコアを返す。
    スコア0のときは '食事' を返す（後段で分散割当する）
    """
    text = normalize(f"{store.store_name} {store.branch_name} {store.genre}")

    best_scene = "食事"
    best_score = 0

    for rule in RULES:
        sc = score_for(rule, text)
        if sc > best_score:
            best_score = sc
            best_scene = rule.scene_name
        elif sc == best_score and sc > 0:
            if TIE_BREAK_PRIORITY.index(rule.scene_name) < TIE_BREAK_PRIORITY.index(best_scene):
                best_scene = rule.scene_name

    return best_scene, best_score


def pick_least_used_scene(counts: Counter, candidates: list[str]) -> str:
    """
    counts が一番少ないシーンを返す（同点なら名前順で安定化）
    """
    candidates_sorted = sorted(candidates, key=lambda n: (counts.get(n, 0), n))
    return candidates_sorted[0]


class Command(BaseCommand):
    help = "店舗名（+ジャンル）から利用シーンを推定して Store.scene を一括更新します。"

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="実際にDBへ反映します（指定しない場合は dry-run）。",
        )
        parser.add_argument(
            "--only-default",
            action="store_true",
            help="現在の scene が「食事」の店舗だけを対象にします（おすすめ）。",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="処理件数を制限します（デバッグ用、0=制限なし）。",
        )
        parser.add_argument(
            "--no-meal",
            action="store_true",
            help="最終的に「食事」を0件にする（ルールで判定不能な店は均等分散で他シーンへ割当）。",
        )

    def handle(self, *args, **options):
        apply = bool(options["apply"])
        only_default = bool(options["only_default"])
        limit = int(options["limit"] or 0)
        no_meal = bool(options["no_meal"])

        scene_map = build_scene_map()

        # 分散先候補（食事を除外）
        non_meal_scenes = [n for n in scene_map.keys() if n != "食事"]

        qs = Store.objects.select_related("scene").all().order_by("id")
        if only_default:
            qs = qs.filter(scene__scene_name="食事")
        if limit > 0:
            qs = qs[:limit]

        total = qs.count()
        if total == 0:
            self.stdout.write(self.style.WARNING("対象店舗がありません。"))
            return

        # 現在のシーン件数（分散用）
        current_counts = Counter(
            Store.objects.select_related("scene").values_list("scene__scene_name", flat=True)
        )

        changes: list[tuple[Store, str, str]] = []
        assigned_by_balance = 0

        for store in qs:
            before = store.scene.scene_name if store.scene_id else "(None)"

            guessed_name, score = choose_scene_name_by_rules(store)

            # ルール判定できない（score=0）→ no_mealなら均等分散で非食事へ
            if no_meal and (guessed_name == "食事" or score == 0):
                picked = pick_least_used_scene(current_counts, non_meal_scenes)
                new_name = picked
                assigned_by_balance += 1
            else:
                new_name = guessed_name

            if before != new_name:
                changes.append((store, before, new_name))

                # 次の分散に効かせるため、カウントを先に更新
                current_counts[new_name] += 1
                current_counts[before] -= 1  # before が負になることもあるが分散ロジックには影響ほぼ無し

        self.stdout.write(f"対象: {total}件 / 変更予定: {len(changes)}件 / 均等分散割当: {assigned_by_balance}件")
        for store, before, after in changes[:80]:
            self.stdout.write(f"- [{store.id}] {store.store_name} ({before} -> {after})")
        if len(changes) > 80:
            self.stdout.write(f"... 省略（{len(changes) - 80}件）")

        if not apply:
            self.stdout.write(self.style.WARNING("dry-run です。反映するには --apply を付けて実行してください。"))
            return

        with transaction.atomic():
            for store, _before, after in changes:
                store.scene = scene_map[after]
                store.save(update_fields=["scene"])

        self.stdout.write(self.style.SUCCESS(f"更新完了: {len(changes)}件"))

        # 念のため「食事」残数チェック
        if no_meal:
            remain = Store.objects.filter(scene__scene_name="食事").count()
            if remain != 0:
                self.stdout.write(self.style.ERROR(f"注意: 食事が {remain} 件残っています（想定外）。"))
            else:
                self.stdout.write(self.style.SUCCESS("確認: 食事は 0 件です。"))
