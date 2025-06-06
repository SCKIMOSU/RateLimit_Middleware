from django.contrib import admin
from .models import AllowedIP

@admin.register(AllowedIP)
class AllowedIPAdmin(admin.ModelAdmin):
    list_display = ('ip_address', 'description')
    search_fields = ('ip_address',)
