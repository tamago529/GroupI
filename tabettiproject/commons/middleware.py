# commons/middleware.py
import time
from django.conf import settings
from django.contrib.sessions.middleware import SessionMiddleware
from django.utils.cache import patch_vary_headers
from django.utils.http import http_date
from django.utils import timezone


class AdminSeparateSessionMiddleware(SessionMiddleware):
    """
    /admin/ 配下だけ別のセッションCookieを使うミドルウェア。
    同一ブラウザで「adminログイン」と「顧客ログイン」を共存させられる。
    """

    def _cookie_name(self, request) -> str:
        admin_name = getattr(settings, "ADMIN_SESSION_COOKIE_NAME", "admin_sessionid")
        site_name = getattr(settings, "SESSION_COOKIE_NAME", "sessionid")

        # /admin/ 配下のみ admin_cookie
        if request.path.startswith("/admin/"):
            return admin_name
        return site_name

    def process_request(self, request):
        cookie_name = self._cookie_name(request)
        session_key = request.COOKIES.get(cookie_name)
        request.session = self.SessionStore(session_key)

        # 後で process_response で使う
        request._session_cookie_name = cookie_name

    def process_response(self, request, response):
        try:
            session = request.session
        except AttributeError:
            return response

        cookie_name = getattr(request, "_session_cookie_name", getattr(settings, "SESSION_COOKIE_NAME", "sessionid"))

        accessed = session.accessed
        modified = session.modified
        empty = session.is_empty()

        if accessed:
            patch_vary_headers(response, ("Cookie",))

        # 保存対象か？
        if modified or settings.SESSION_SAVE_EVERY_REQUEST:
            if empty:
                # セッションが空ならCookie消す
                if cookie_name in request.COOKIES:
                    response.delete_cookie(
                        cookie_name,
                        path=settings.SESSION_COOKIE_PATH,
                        domain=settings.SESSION_COOKIE_DOMAIN,
                        samesite=getattr(settings, "SESSION_COOKIE_SAMESITE", "Lax"),
                    )
            else:
                # セッション保存＆Cookie更新
                session.save()

                # 期限計算
                expires = None
                max_age = None
                try:
                    if not session.get_expire_at_browser_close():
                        expiry_date = session.get_expiry_date()
                        # expiry_date は aware 想定
                        max_age = int((expiry_date - timezone.now()).total_seconds())
                        if max_age < 0:
                            max_age = 0
                        expires = http_date(expiry_date.timestamp())
                except Exception:
                    # 何かあっても cookie は最低限セットする
                    expires = None
                    max_age = None

                response.set_cookie(
                    cookie_name,
                    session.session_key,
                    max_age=max_age,
                    expires=expires,
                    domain=settings.SESSION_COOKIE_DOMAIN,
                    path=settings.SESSION_COOKIE_PATH,
                    secure=settings.SESSION_COOKIE_SECURE,
                    httponly=settings.SESSION_COOKIE_HTTPONLY,
                    samesite=getattr(settings, "SESSION_COOKIE_SAMESITE", "Lax"),
                )

        return response
