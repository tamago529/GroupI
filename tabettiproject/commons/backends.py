from django.core.mail.backends.smtp import EmailBackend
import ssl

class FixedEmailBackend(EmailBackend):
    """
    Python 3.12 で SMTP.starttls() から keyfile と certfile 引数が削除されたことに伴い、
    Django 4.0 の標準 EmailBackend で発生する TypeError を回避するためのカスタムバックエンド。
    """
    def open(self):
        if self.connection:
            return False
        connection_params = {}
        if self.timeout is not None:
            connection_params['timeout'] = self.timeout
        try:
            self.connection = self.connection_class(self.host, self.port, **connection_params)
            if self.use_tls:
                # Python 3.12 互換の呼び出し: keyfile, certfile を渡さない
                # 代わりに ssl_context を使用するのが推奨されるが、Gmail 等では引数なしでも動作する
                self.connection.starttls()
            if self.username and self.password:
                self.connection.login(self.username, self.password)
            return True
        except OSError:
            if not self.fail_silently:
                raise
            return False
