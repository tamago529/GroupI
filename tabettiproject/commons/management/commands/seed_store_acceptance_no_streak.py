# commons/management/commands/seed_store_acceptance_no_streak.py
from django.core.management.base import BaseCommand
from django.db import transaction
from datetime import date, timedelta
import random

from commons.models import Store, StoreOnlineReservation


class Command(BaseCommand):
    help = "店舗×日付の受付状況をバラつかせて作成/更新（連続停止なし・高速版）"

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=30)
        parser.add_argument("--seed", type=int, default=1234)

        parser.add_argument("--weekday_p", type=float, default=0.85)
        parser.add_argument("--weekend_p", type=float, default=0.60)

        parser.add_argument("--store_spread", type=float, default=0.15)
        parser.add_argument("--weekly_closed", action="store_true")

        parser.add_argument("--batch_size", type=int, default=5000)

    def handle(self, *args, **opts):
        days = int(opts["days"])
        seed = int(opts["seed"])
        rng = random.Random(seed)

        weekday_p = float(opts["weekday_p"])
        weekend_p = float(opts["weekend_p"])
        spread = float(opts["store_spread"])
        weekly_closed = bool(opts["weekly_closed"])
        batch_size = int(opts["batch_size"])

        today = date.today()
        dates = [today + timedelta(days=i) for i in range(days)]
        date_min = dates[0]
        date_max = dates[-1]

        stores = list(Store.objects.all().only("id"))

        # 既存行を一括で取って dict 化（store_id, date -> obj）
        existing_qs = StoreOnlineReservation.objects.filter(date__range=(date_min, date_max))
        existing = {(r.store_id, r.date): r for r in existing_qs}

        to_create = []
        to_update = []

        for idx, store in enumerate(stores, start=1):
            # 店舗ごとに固定の乱数系列（再現性）
            store_rng = random.Random(f"{seed}:{store.id}")
            store_bias = store_rng.uniform(-spread, +spread)
            closed_weekday = store_rng.randint(0, 6) if weekly_closed else None

            prev_false = False

            for d in dates:
                is_weekend = d.weekday() >= 5
                base_p = weekend_p if is_weekend else weekday_p
                p = max(0.0, min(1.0, base_p + store_bias))

                booking_status = (rng.random() < p)

                if closed_weekday is not None and d.weekday() == closed_weekday:
                    booking_status = False

                # 連続停止禁止：前日が停止なら当日は必ず受付中
                if prev_false and booking_status is False:
                    booking_status = True

                key = (store.id, d)
                row = existing.get(key)

                if row is None:
                    to_create.append(StoreOnlineReservation(
                        store_id=store.id,
                        date=d,
                        booking_status=booking_status,
                    ))
                else:
                    if bool(row.booking_status) != bool(booking_status):
                        row.booking_status = booking_status
                        to_update.append(row)

                prev_false = (booking_status is False)

            # 進捗（任意）
            if idx % 50 == 0:
                self.stdout.write(f"{idx}/{len(stores)} stores processed...")

        with transaction.atomic():
            if to_create:
                StoreOnlineReservation.objects.bulk_create(
                    to_create,
                    batch_size=batch_size,
                )
            if to_update:
                StoreOnlineReservation.objects.bulk_update(
                    to_update,
                    fields=["booking_status"],
                    batch_size=batch_size,
                )

        self.stdout.write(self.style.SUCCESS(
            f"完了: create={len(to_create)} / update={len(to_update)} "
            f"(days={days}, seed={seed}, weekly_closed={weekly_closed})"
        ))
