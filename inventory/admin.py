"""
Django Admin cho Supabase schema.
Truy cập qua /admin/ — đây là UI chính cho user quản lý hệ thống.
"""
from django.contrib import admin
from django.utils.html import format_html
from django.db import connection
from .models import (
    Product, Supplier, PriceList, PriceListItem,
    CostOverhead, Recipe, InventoryDaily,
)


# ===== 1. PRODUCT =====
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'unit', 'package_size', 'package_unit', 'is_intermediate', 'in_letan')
    list_filter = ('category', 'is_intermediate', 'in_letan')
    search_fields = ('name',)
    ordering = ('category', 'name')
    list_per_page = 100


# ===== 2. SUPPLIER =====
@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'address')
    search_fields = ('name', 'phone')


# ===== 3. PRICE LIST =====
class PriceListItemInline(admin.TabularInline):
    model = PriceListItem
    extra = 0
    autocomplete_fields = ('product', 'supplier')
    fields = ('product', 'supplier', 'price', 'unit', 'note')


@admin.register(PriceList)
class PriceListAdmin(admin.ModelAdmin):
    list_display = ('name', 'effective_from', 'is_active', 'item_count')
    list_filter = ('is_active',)
    inlines = [PriceListItemInline]
    ordering = ('-effective_from',)
    actions = ['clone_price_list']

    def item_count(self, obj):
        return obj.items.count()
    item_count.short_description = 'Số items'

    @admin.action(description="Clone bảng giá (tạo version mới)")
    def clone_price_list(self, request, queryset):
        from datetime import date
        for pl in queryset:
            new_pl = PriceList.objects.create(
                name=f"{pl.name} (copy)",
                effective_from=date.today(),
                is_active=False,
                note=f"Cloned từ {pl.name}",
            )
            for item in pl.items.all():
                PriceListItem.objects.create(
                    price_list=new_pl,
                    product=item.product,
                    supplier=item.supplier,
                    price=item.price,
                    unit=item.unit,
                    note=item.note,
                )
            self.message_user(request, f"Đã clone '{pl.name}' → '{new_pl.name}' với {pl.items.count()} items")


@admin.register(PriceListItem)
class PriceListItemAdmin(admin.ModelAdmin):
    list_display = ('product', 'price_list', 'supplier', 'price', 'unit')
    list_filter = ('price_list', 'supplier')
    search_fields = ('product__name',)
    autocomplete_fields = ('product', 'supplier', 'price_list')


# ===== 4. COST OVERHEAD =====
@admin.register(CostOverhead)
class CostOverheadAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'cost', 'unit', 'note')
    search_fields = ('name', 'code')


# ===== 5. RECIPE — UI quan trọng nhất =====
@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ('name', 'recipe_type', 'output_display', 'cost_display', 'unit_cost_display')
    list_filter = ('recipe_type',)
    search_fields = ('name',)
    autocomplete_fields = ('output_product',)
    fields = ('name', 'recipe_type', 'ingredients', 'output_product', 'output_qty', 'output_unit')
    ordering = ('recipe_type', 'name')

    def output_display(self, obj):
        if obj.output_product:
            return f"{obj.output_qty} {obj.output_unit} {obj.output_product.name}"
        return "—"
    output_display.short_description = "Output"

    def cost_display(self, obj):
        try:
            cost = obj.compute_cost_active()
            return format_html('<b>{:,.0f}đ</b>', float(cost or 0))
        except Exception as e:
            return format_html('<span style="color:red">Lỗi: {}</span>', str(e))
    cost_display.short_description = "Tổng cost"

    def unit_cost_display(self, obj):
        if obj.recipe_type != 'sub' or not obj.output_qty:
            return "—"
        try:
            cost = obj.compute_cost_active()
            return f"{float(cost or 0) / float(obj.output_qty):,.2f}đ/{obj.output_unit}"
        except Exception:
            return "—"
    unit_cost_display.short_description = "Đơn giá"


# ===== 6. INVENTORY =====
@admin.register(InventoryDaily)
class InventoryDailyAdmin(admin.ModelAdmin):
    list_display = ('date', 'warehouse', 'product', 'opening_stock', 'received', 'closing_stock', 'actual_used')
    list_filter = ('warehouse', 'date')
    search_fields = ('product__name',)
    autocomplete_fields = ('product',)
    date_hierarchy = 'date'
    ordering = ('-date', 'warehouse', 'product__name')
    list_per_page = 50
    readonly_fields = ('actual_used',)
