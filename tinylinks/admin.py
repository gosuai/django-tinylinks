"""Admin sites for the ``django-tinylinks`` app."""
from django.core.paginator import Paginator
from django.contrib import admin
from django.db import connection
from django.db.models import Q
from django.template.defaultfilters import truncatechars
from django.utils.translation import ugettext_lazy as _

from tinylinks.forms import TinylinkAdminForm
from tinylinks.models import Tinylink


class ShortUrlFilter(admin.SimpleListFilter):
    template = 'admin/input_filter.html'

    parameter_name = 'short_url'
    title = _('short_url starts with')

    def lookups(self, request, model_admin):
        # Dummy, required to show the filter.
        return ((),)

    def choices(self, changelist):
        yield next(super().choices(changelist))

    def queryset(self, request, queryset):
        if self.value() is not None:
            short_url = self.value()

            return queryset.filter(
                Q(short_url__istartswith=short_url)
            )


class LargeTablePaginator(Paginator):
    """
    Warning: Postgresql only hack
    Overrides the count method of QuerySet objects to get an estimate instead of actual count when not filtered.
    However, this estimate can be stale and hence not fit for situations where the count of objects actually matter.

    Originally posted here:
        https://medium.com/squad-engineering/estimated-counts-for-faster-django-admin-change-list-963cbf43683e
    """
    def _get_count(self):
        if getattr(self, '_count', None) is not None:
            return self._count

        query = self.object_list.query
        if not query.where:
            try:
                cursor = connection.cursor()
                cursor.execute("SELECT reltuples FROM pg_class WHERE relname = %s",
                               [query.model._meta.db_table])
                self._count = int(cursor.fetchone()[0])
            except:
                self._count = super(LargeTablePaginator, self).count
        else:
            self._count = super(LargeTablePaginator, self).count

        return self._count

    count = property(_get_count)


class TinylinkAdmin(admin.ModelAdmin):
    list_display = ('short_url', 'url_truncated', 'amount_of_views', 'user',
                    'last_checked', 'status', 'validation_error')
    search_fields = ['short_url']
    list_filter = (ShortUrlFilter,)

    form = TinylinkAdminForm
    show_full_result_count = False
    paginator = LargeTablePaginator

    def url_truncated(self, obj):
        return truncatechars(obj.long_url, 60)
    url_truncated.short_description = _('Long URL')

    def status(self, obj):
        if not obj.is_broken:
            return _('OK')
        return _('Link broken')

    status.short_description = _('Status')


admin.site.register(Tinylink, TinylinkAdmin)
