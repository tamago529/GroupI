from django.test import TestCase
from django.urls import reverse
from commons.models import Store, Area, Scene
from datetime import time

class SearchTimeFilterTest(TestCase):
    def setUp(self):
        # マスタデータ作成
        self.area = Area.objects.create(area_name="テストエリア")
        self.scene = Scene.objects.create(scene_name="テストシーン")
        
        # 店舗A: 通常営業 (11:00 - 20:00)
        self.store_normal = Store.objects.create(
            store_name="通常営業店",
            area=self.area,
            scene=self.scene,
            email="test1@example.com",
            open_time_1=time(11, 0),
            close_time_1=time(20, 0),
            seats=10,
            budget=1000
        )
        
        # 店舗B: 深夜営業 (23:00 - 05:00) - 日跨ぎ
        self.store_midnight = Store.objects.create(
            store_name="深夜営業店",
            area=self.area,
            scene=self.scene,
            email="test2@example.com",
            open_time_1=time(23, 0),
            close_time_1=time(5, 0),
            seats=10,
            budget=1000
        )

    def test_search_normal_open(self):
        """通常営業店が営業時間内にヒットするか"""
        response = self.client.get(reverse('search:customer_search_list'), {'time': '12:00'})
        self.assertContains(response, self.store_normal.store_name)
        self.assertNotContains(response, self.store_midnight.store_name)

    def test_search_normal_closed(self):
        """通常営業店が営業時間外にヒットしないか"""
        response = self.client.get(reverse('search:customer_search_list'), {'time': '21:00'})
        self.assertNotContains(response, self.store_normal.store_name)
        self.assertNotContains(response, self.store_midnight.store_name)

    def test_search_midnight_open_before_midnight(self):
        """深夜営業店が日付変わり前(23:30)にヒットするか"""
        response = self.client.get(reverse('search:customer_search_list'), {'time': '23:30'})
        self.assertNotContains(response, self.store_normal.store_name)
        self.assertContains(response, self.store_midnight.store_name)

    def test_search_midnight_open_after_midnight(self):
        """深夜営業店が日付変わり後(02:00)にヒットするか"""
        response = self.client.get(reverse('search:customer_search_list'), {'time': '02:00'})
        self.assertNotContains(response, self.store_normal.store_name)
        self.assertContains(response, self.store_midnight.store_name)
    
    def test_search_midnight_closed(self):
        """深夜営業店が営業時間外(06:00)にヒットしないか"""
        response = self.client.get(reverse('search:customer_search_list'), {'time': '06:00'})
        self.assertNotContains(response, self.store_normal.store_name)
        self.assertNotContains(response, self.store_midnight.store_name)
