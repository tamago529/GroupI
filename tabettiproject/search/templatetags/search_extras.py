from django import template

register = template.Library()

@register.simple_tag(takes_context=True)
def url_replace(context, **kwargs):
    """
    現在のGETパラメータを維持しつつ、kwargsで指定されたパラメータを更新・追加する。
    例: {% url_replace page=page_obj.next_page_number %}
    """
    query = context['request'].GET.copy()
    for key, value in kwargs.items():
        query[key] = value
    return query.urlencode()
