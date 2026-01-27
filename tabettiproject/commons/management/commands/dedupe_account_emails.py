from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count

from commons.models import (
    Account, CustomerAccount, StoreAccount, CompanyAccount,
    Review, Follow, Store, Reservator, StoreAccountRequest,
    TempRequestMailLog, StoreInfoReport,
    ReviewReport, PasswordResetLog,
)

class Command(BaseCommand):
    help = "Deduplicate Account.email and merge related objects. Use --apply to execute."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="Actually apply changes (default: dry-run).")

    def handle(self, *args, **options):
        apply = options["apply"]

        dup_emails = (
            Account.objects.exclude(email="")
            .values("email")
            .annotate(c=Count("id"))
            .filter(c__gt=1)
            .values_list("email", flat=True)
        )

        if not dup_emails:
            self.stdout.write(self.style.SUCCESS("No duplicate emails found."))
            return

        self.stdout.write(f"Duplicate emails: {len(list(dup_emails))}")
        self.stdout.write("----")

        for email in dup_emails:
            qs = Account.objects.filter(email__iexact=email).select_related("account_type").order_by("pk")
            accounts = list(qs)
            ids = [a.pk for a in accounts]

            # どの型が混じっているか（multi-table継承の判定）
            customer_ids = set(CustomerAccount.objects.filter(pk__in=ids).values_list("pk", flat=True))
            store_ids = set(StoreAccount.objects.filter(pk__in=ids).values_list("pk", flat=True))
            company_ids = set(CompanyAccount.objects.filter(pk__in=ids).values_list("pk", flat=True))

            def role_rank(a):
                # 顧客を優先して残す（パスワードリセット運用上）
                if a.pk in customer_ids: return 0
                if a.pk in store_ids: return 1
                if a.pk in company_ids: return 2
                return 3

            # master（残す）を決める：顧客＞店舗＞企業＞その他、同ランクなら pk が小さい方
            master = sorted(accounts, key=lambda a: (role_rank(a), a.pk))[0]
            losers = [a for a in accounts if a.pk != master.pk]

            def role_str(a):
                if a.pk in customer_ids: return "CustomerAccount"
                if a.pk in store_ids: return "StoreAccount"
                if a.pk in company_ids: return "CompanyAccount"
                return "Account"

            self.stdout.write(f"[{email}]")
            self.stdout.write(f"  master: id={master.pk}, username={master.username}, type={master.account_type}, role={role_str(master)}")
            for a in losers:
                self.stdout.write(f"  delete: id={a.pk}, username={a.username}, type={a.account_type}, role={role_str(a)}")

            if not apply:
                self.stdout.write("  (dry-run)\n")
                continue

            with transaction.atomic():
                # --- Account を参照しているFKを付け替え ---
                ReviewReport.objects.filter(reporter__in=losers).update(reporter=master)
                PasswordResetLog.objects.filter(account__in=losers).update(account=master)

                # --- CustomerAccount を参照しているFKを付け替え（masterがCustomerの場合のみ） ---
                if master.pk in customer_ids:
                    master_c = CustomerAccount.objects.get(pk=master.pk)

                    for a in losers:
                        if a.pk in customer_ids:
                            loser_c = CustomerAccount.objects.get(pk=a.pk)

                            Review.objects.filter(reviewer=loser_c).update(reviewer=master_c)
                            Follow.objects.filter(follower=loser_c).update(follower=master_c)
                            Follow.objects.filter(followee=loser_c).update(followee=master_c)
                            Store.objects.filter(creator=loser_c).update(creator=master_c)
                            Reservator.objects.filter(customer_account=loser_c).update(customer_account=master_c)
                            StoreAccountRequest.objects.filter(requester=loser_c).update(requester=master_c)
                            TempRequestMailLog.objects.filter(requester=loser_c).update(requester=master_c)
                            StoreInfoReport.objects.filter(reporter=loser_c).update(reporter=master_c)

                # --- いよいよ削除（multi-table継承なので子テーブルも一緒に消える） ---
                for a in losers:
                    a.delete()

            self.stdout.write(self.style.SUCCESS("  applied.\n"))

        self.stdout.write(self.style.SUCCESS("Done."))
