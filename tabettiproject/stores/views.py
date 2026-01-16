from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin , UserPassesTestMixin
from django.views.generic.base import TemplateView
from commons.models import StoreAccount, Store
from django.urls import reverse # 追記
from django.db.models import Q # 追記
import urllib.parse # 追記



class customer_mapView(TemplateView):
    template_name = "stores/customer_map.html"


class customer_menu_courseView(TemplateView):
    template_name = "stores/customer_menu_course.html"


class customer_store_basic_editView(TemplateView):
    template_name = "stores/customer_store_basic_edit.html"


class store_basic_editView(TemplateView):
    template_name = "stores/store_basic_edit.html"


class company_store_infoView(TemplateView):
    template_name = "stores/company_store_info.html"
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # URLから渡されたID(pk)を使って、特定の店舗1件を取得
        context['store'] = get_object_or_404(Store, pk=self.kwargs['pk'])
        return context

class customer_store_infoView(TemplateView):
    template_name = "stores/customer_store_info.html"


class customer_store_new_registerView(TemplateView):
    template_name = "stores/customer_store_new_register.html"


class customer_store_new_register_confirmView(TemplateView):
    template_name = "stores/customer_store_new_register_confirm.html"

def is_store_user(user) -> bool:
    if not user or not user.is_authenticated:
        return False
    try:
        _ = user.storeaccount
        return True
    except StoreAccount.DoesNotExist:
        return False
    except Exception:
        return False

class store_topView(LoginRequiredMixin,UserPassesTestMixin,TemplateView):
    template_name = "stores/store_top.html"
    login_url = 'accounts:store_login'

    def test_func(self):
        return is_store_user(self.request.user)

class store_logoutView(TemplateView):
    template_name = "accounts/store_logout.html"    

class company_store_managementView(TemplateView):
    template_name = "stores/company_store_management.html"
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # 検索キーワードを取得
        query = self.request.GET.get('q', '')
        
        if query:
            # 店舗名にキーワードを含むものを検索
            stores = Store.objects.filter(Q(store_name__icontains=query)).order_by('store_name')
        else:
            # キーワードがなければ全件
            stores = Store.objects.all().order_by('store_name')
            
        context['stores'] = stores
        context['query'] = query
        return context
def store_delete_execute(request, pk):
    # 削除対象の店舗を取得
    store = get_object_or_404(Store, pk=pk)
    name = store.store_name
    store.delete() # 削除実行
    
    # 完了画面へメッセージ付きでリダイレクト
    msg = f"店舗「{name}」の削除"
    encoded_msg = urllib.parse.quote(msg)
    return redirect(reverse('commons:company_common_complete') + f"?message={encoded_msg}")