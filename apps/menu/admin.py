from django.contrib import admin

from .models import MenuCategory, MenuItem


@admin.register(MenuCategory)
class MenuCategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'restaurant', 'name', 'display_order')
    list_filter = ('restaurant',)
    search_fields = ('name',)


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'restaurant', 'name', 'category', 'price', 'available')
    list_filter = ('restaurant', 'category', 'available')
    search_fields = ('name', 'description')
