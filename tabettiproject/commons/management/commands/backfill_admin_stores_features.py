# commons/management/commands/backfill_admin_stores_features.py
from __future__ import annotations

import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from commons.models import Store, StoreOnlineReservation


class Command(BaseCommand):
    help = "adminで登録された店舗(ID範囲)に、予約枠(StoreOnlineReservation)を一括で作成して予約機能を有効化する"

    def add_arguments(self, parser):
        parser.add_argument("--id-from", type=int, default=209, help="対象Storeの開始ID")
        parser.add_argument("--id-to", type=int, default=390, help="対象Storeの終了ID")
        parser.add_argument("--days", type=int, default=90, help="今日から何日分の予約枠を作るか")
        parser.add_argument("--open-ratio", type=float, default=0.7, help="予約受付(true)にする割合")
        parser.add_argument("--min-seats", type=int, default=10, help="available_seatsの下限")
        parser.add_argument("--max-seats", type=int, default=40, help="available_seatsの上限")
        parser.add_argument("--seed", type=int, default=1234, help="乱数シード")
        parser.add_argument("--dry-run", action="store_true", help="DBに保存せずログだけ")

    @transaction.atomic
    def handle(self, *args, **opts):
        id_from = int(opts["id_from"])
        id_to = int(opts["id_to"])
        days = int(opts["days"])
        open_ratio = float(opts["open_ratio"])
        min_seats = int(opts["min_seats"])
        max_seats = int(opts["max_seats"])
        seed = int(opts["seed"])
        dry_run = bool(opts["dry_run"])

        random.seed(seed)

        qs = Store.objects.filter(id__gte=id_from, id__lte=id_to).order_by("id")
        if not qs.exists():
            self.stdout.write(self.style.WARNING("対象店舗が見つかりませんでした。"))
            return

        today = timezone.localdate()
        total_stores = qs.count()

        self.stdout.write(f"対象店舗: {total_stores}件 (ID {id_from}〜{id_to})")
        self.stdout.write(f"予約枠: 今日({today})から {days}日分 / open_ratio={open_ratio}")

        total_created = 0
        total_updated_store = 0

        for store in qs:
            # 予約可能に寄せる（UI表示の前提にする）
            if not store.reservable:
                if not dry_run:
                    store.reservable = True
                    store.save(update_fields=["reservable"])
                total_updated_store += 1

            created_for_store = 0

            store_seats = int(store.seats or 0)
            for i in range(days):
                d = today + timedelta(days=i)

                # 既にある日は作らない（上書きしない）
                if StoreOnlineReservation.objects.filter(store=store, date=d).exists():
                    continue

                is_open = (random.random() < open_ratio)
                if is_open:
                    upper = min(max_seats, store_seats) if store_seats > 0 else max_seats
                    lower = min_seats
                    if upper < lower:
                        lower = max(1, upper)
                    available = random.randint(lower, upper) if upper >= 1 else 1
                else:
                    available = 0

                if not dry_run:
                    StoreOnlineReservation.objects.create(
                        store=store,
                        date=d,
                        booking_status=is_open,
                        available_seats=available,
                    )
                created_for_store += 1

            if created_for_store:
                total_created += created_for_store
                self.stdout.write(f"store_id={store.id} 予約枠作成: +{created_for_store}日")

        if dry_run:
            self.stdout.write(self.style.WARNING(f"DRY-RUN 完了: 予約枠作成予定 合計 {total_created}日 / reservable補正 {total_updated_store}件"))
        else:
            self.stdout.write(self.style.SUCCESS(f"完了: 予約枠作成 合計 {total_created}日 / reservable補正 {total_updated_store}件"))
