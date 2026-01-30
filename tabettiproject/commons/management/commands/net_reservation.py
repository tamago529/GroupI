# commons/management/commands/net_reservation.py
from __future__ import annotations

import calendar
from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from commons.models import Store, StoreOnlineReservation


AUTO_RESERVATION_STORE_ID_MIN = 209
AUTO_RESERVATION_STORE_ID_MAX = 390


def is_auto_reservation_store_id(store_id: int) -> bool:
    return AUTO_RESERVATION_STORE_ID_MIN <= int(store_id) <= AUTO_RESERVATION_STORE_ID_MAX


def default_available_seats(store: Store) -> int:
    seats = int(getattr(store, "seats", 0) or 0)
    return seats if seats > 0 else 999


def ensure_month_online_settings(store: Store, year: int, month: int) -> int:
    """
    指定store の指定月について、今日以降の未来日分の StoreOnlineReservation を作成する。
    既にある日はスキップ。
    戻り値：作成件数
    """
    today = timezone.localdate()
    start = date(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]
    end = date(year, month, last_day)

    # 未来日だけ
    dates = [start + timedelta(days=i) for i in range((end - start).days + 1)]
    dates = [d for d in dates if d >= today]
    if not dates:
        return 0

    existing = set(
        StoreOnlineReservation.objects.filter(store=store, date__range=(start, end))
        .values_list("date", flat=True)
    )
    to_create = [d for d in dates if d not in existing]
    if not to_create:
        return 0

    StoreOnlineReservation.objects.bulk_create(
        [
            StoreOnlineReservation(
                store=store,
                date=d,
                booking_status=True,
                available_seats=default_available_seats(store),
            )
            for d in to_create
        ],
        ignore_conflicts=True,
    )
    return len(to_create)


class Command(BaseCommand):
    help = "ID209-390店舗のネット予約枠（StoreOnlineReservation）を当月/指定月の未来日分だけ自動生成します。"

    def add_arguments(self, parser):
        parser.add_argument(
            "--ym",
            type=str,
            default="",
            help="対象月（YYYY-MM）。未指定なら今月。",
        )
        parser.add_argument(
            "--store-id",
            type=int,
            default=0,
            help="対象店舗IDを1つだけ指定（未指定ならID209-390全部）。",
        )

    def handle(self, *args, **options):
        ym = (options.get("ym") or "").strip()
        store_id = int(options.get("store_id") or 0)

        today = timezone.localdate()
        if ym:
            try:
                y, m = ym.split("-")
                year, month = int(y), int(m)
            except Exception:
                self.stderr.write(self.style.ERROR("ym は YYYY-MM 形式で指定してください。例: --ym 2026-02"))
                return
        else:
            year, month = today.year, today.month

        # 過去月は今月に丸め
        if (year, month) < (today.year, today.month):
            year, month = today.year, today.month

        if store_id:
            qs = Store.objects.filter(pk=store_id)
        else:
            qs = Store.objects.filter(pk__gte=AUTO_RESERVATION_STORE_ID_MIN, pk__lte=AUTO_RESERVATION_STORE_ID_MAX)

        total_created = 0
        count_store = 0

        for store in qs:
            count_store += 1
            if not is_auto_reservation_store_id(store.pk):
                continue
            created = ensure_month_online_settings(store, year, month)
            total_created += created
            self.stdout.write(f"[store:{store.pk}] created={created}")

        self.stdout.write(self.style.SUCCESS(f"done. stores={count_store}, total_created={total_created}, ym={year}-{month:02d}"))
