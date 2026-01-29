import os
import random
import shutil
from uuid import uuid4

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from commons.models import StoreImage


def _list_files(abs_dir: str):
    if not os.path.isdir(abs_dir):
        return []
    files = []
    for f in os.listdir(abs_dir):
        p = os.path.join(abs_dir, f)
        if os.path.isfile(p):
            files.append(p)
    return files


class Command(BaseCommand):
    """
    image_file が指す実ファイルが存在しない StoreImage だけを対象に、
    status(料理/メニュー表/内装など)に応じたプール画像で image_file を差し替える。

    - 既存レコードは削除しない
    - 壊れていないレコードは触らない
    - image_status は保持
    """

    def add_arguments(self, parser):
        parser.add_argument("--food_pool", type=str, default="media/_pool/store/food")
        parser.add_argument("--menu_table_pool", type=str, default="media/_pool/store/menu_table")
        parser.add_argument("--dryrun", action="store_true")
        parser.add_argument("--limit", type=int, default=0, help="0=無制限 / 例:100 のように指定すると先頭から100件だけ修復")

    def handle(self, *args, **opt):
        if not settings.MEDIA_ROOT:
            raise CommandError("MEDIA_ROOT が設定されていません")

        base_dir = settings.BASE_DIR

        food_pool_dir = os.path.join(base_dir, opt["food_pool"])
        menu_pool_dir = os.path.join(base_dir, opt["menu_table_pool"])

        food_pool = _list_files(food_pool_dir)
        menu_pool = _list_files(menu_pool_dir)

        if not food_pool:
            raise CommandError(f"料理プールが空です: {food_pool_dir}")
        if not menu_pool:
            raise CommandError(f"メニュー表プールが空です: {menu_pool_dir}")

        # 破損（ファイル無し）抽出
        broken = []
        qs = StoreImage.objects.exclude(image_file="").only("id", "image_file", "image_status__status")
        for si in qs.iterator():
            name = si.image_file.name
            p = os.path.join(settings.MEDIA_ROOT, name)
            if not os.path.exists(p):
                broken.append((si.id, si.image_status.status, name))

        self.stdout.write(f"破損件数: {len(broken)}")
        if broken:
            self.stdout.write("例: " + str(broken[:5]))

        if opt["dryrun"]:
            self.stdout.write("dryrun のため変更しません")
            return

        dst_dir = os.path.join(settings.MEDIA_ROOT, "store", "images")
        os.makedirs(dst_dir, exist_ok=True)

        fixed = 0
        limit = int(opt["limit"] or 0)

        with transaction.atomic():
            for i, (sid, status, old_name) in enumerate(broken):
                if limit and fixed >= limit:
                    break

                si = StoreImage.objects.select_related("image_status").get(id=sid)

                # status判定（外装は今回は触らないならここでcontinueも可能）
                if status.startswith("料理"):
                    src = random.choice(food_pool)
                elif status.startswith("メニュー表"):
                    src = random.choice(menu_pool)
                else:
                    # 今回は料理/メニュー表以外はスキップ
                    continue

                ext = os.path.splitext(src)[1].lower() or ".png"
                new_filename = f"repair_{sid}_{uuid4().hex}{ext}"
                rel_name = f"store/images/{new_filename}"
                abs_path = os.path.join(settings.MEDIA_ROOT, "store", "images", new_filename)

                shutil.copy2(src, abs_path)

                si.image_file.name = rel_name
                si.save(update_fields=["image_file"])
                fixed += 1

        self.stdout.write(self.style.SUCCESS(f"修復完了: {fixed} 件"))
