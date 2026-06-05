"""
Models cho Supabase schema (managed = False — Django không migrate).
Schema được build trực tiếp trên Supabase qua SQL.
"""
import uuid
from decimal import Decimal
from django.db import models


# ====================== 1. PRODUCT ======================
class Product(models.Model):
    CATEGORY_CHOICES = [
        ('Bếp', 'Bếp'),
        ('Quầy', 'Quầy'),
        ('Lễ tân', 'Lễ tân'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    name = models.TextField("Tên sản phẩm")
    category = models.TextField("Danh mục", choices=CATEGORY_CHOICES)
    unit = models.TextField("Đơn vị base (g, ml, lon, cái...)")
    package_size = models.DecimalField("Số base unit / package", max_digits=14, decimal_places=4, default=0)
    package_unit = models.TextField("Đơn vị package (kg, chai, kiện...)", blank=True, null=True)
    in_letan = models.BooleanField("Có ở lễ tân?", default=False)
    is_intermediate = models.BooleanField("Là intermediate (cốt)?", default=False)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        managed = False
        db_table = 'products'
        verbose_name = 'Sản phẩm'
        verbose_name_plural = '1. Sản phẩm'
        ordering = ['category', 'name']

    def __str__(self):
        flag = " [INTERMEDIATE]" if self.is_intermediate else ""
        return f"[{self.category}] {self.name}{flag}"


# ====================== 2. SUPPLIER ======================
class Supplier(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    name = models.TextField("Tên nhà cung cấp", unique=True)
    phone = models.TextField("Điện thoại", blank=True, null=True)
    address = models.TextField("Địa chỉ", blank=True, null=True)
    note = models.TextField("Ghi chú", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)

    class Meta:
        managed = False
        db_table = 'suppliers'
        verbose_name = 'Nhà cung cấp'
        verbose_name_plural = '2. Nhà cung cấp'
        ordering = ['name']

    def __str__(self):
        return self.name


# ====================== 3. PRICE LIST (versioned) ======================
class PriceList(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    name = models.TextField("Tên bảng giá (vd: Bảng giá 5/2026)")
    effective_from = models.DateField("Áp dụng từ")
    is_active = models.BooleanField("Đang dùng?", default=False, help_text="Chỉ 1 bảng được active tại 1 thời điểm")
    note = models.TextField("Ghi chú", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)

    class Meta:
        managed = False
        db_table = 'price_lists'
        verbose_name = 'Bảng giá'
        verbose_name_plural = '3. Bảng giá (versions)'
        ordering = ['-effective_from']

    def __str__(self):
        flag = " ★" if self.is_active else ""
        return f"{self.name}{flag}"


class PriceListItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    price_list = models.ForeignKey(PriceList, on_delete=models.CASCADE, db_column='price_list_id', related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, db_column='product_id', related_name='prices')
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True, db_column='supplier_id')
    price = models.DecimalField("Giá / base unit", max_digits=14, decimal_places=4)
    unit = models.TextField("Đơn vị base")
    note = models.TextField("Ghi chú (vd: Mua 127000đ / 2000 gam)", blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'price_list_items'
        verbose_name = 'Giá / bảng / NCC'
        verbose_name_plural = '   Giá theo bảng'
        unique_together = (('price_list', 'product', 'supplier'),)

    def __str__(self):
        return f"{self.product.name} @ {self.price}đ/{self.unit}"


# ====================== 4. COST OVERHEAD ======================
class CostOverhead(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    code = models.TextField("Mã (vd da_vien, gas_cn)", unique=True)
    name = models.TextField("Tên định mức")
    unit = models.TextField("Đơn vị (suất, lần, bộ)")
    cost = models.DecimalField("Cost / đơn vị", max_digits=14, decimal_places=4)
    note = models.TextField("Ghi chú", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)

    class Meta:
        managed = False
        db_table = 'cost_overhead'
        verbose_name = 'Chi phí định mức'
        verbose_name_plural = '4. Chi phí định mức'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.cost}đ/{self.unit})"


# ====================== 5. RECIPE ======================
class Recipe(models.Model):
    RECIPE_TYPE_CHOICES = [
        ('final', 'Món bán'),
        ('sub', 'Sub-recipe (ủ cốt)'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    name = models.TextField("Tên món / công thức", unique=True)
    ingredients = models.JSONField(
        "Nguyên liệu (jsonb array)",
        default=list,
        help_text='Format: [{"type":"product","product_id":"uuid","qty":30,"unit":"g"},{"type":"overhead","overhead_id":"uuid","qty":1,"unit":"lần"}]'
    )
    recipe_type = models.TextField("Loại", choices=RECIPE_TYPE_CHOICES, default='final')
    output_product = models.ForeignKey(
        Product, on_delete=models.SET_NULL,
        null=True, blank=True, db_column='output_product_id',
        related_name='produced_by',
        help_text="Chỉ dùng cho sub-recipe — recipe này tạo ra product nào"
    )
    output_qty = models.DecimalField("Output qty", max_digits=14, decimal_places=4, null=True, blank=True)
    output_unit = models.TextField("Output unit", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        managed = False
        db_table = 'recipes'
        verbose_name = 'Công thức'
        verbose_name_plural = '5. Công thức món'
        ordering = ['recipe_type', 'name']

    def __str__(self):
        prefix = "🍵 " if self.recipe_type == 'sub' else "🍽 "
        return f"{prefix}{self.name}"

    def compute_cost_active(self):
        """Gọi function PostgreSQL compute_recipe_cost_active(id)."""
        from django.db import connection
        with connection.cursor() as cur:
            cur.execute("SELECT public.compute_recipe_cost_active(%s)", [str(self.id)])
            return cur.fetchone()[0]


# ====================== 6. INVENTORY DAILY ======================
class InventoryDaily(models.Model):
    WAREHOUSE_CHOICES = [
        ('Bếp', 'Bếp'),
        ('Quầy', 'Quầy'),
        ('Lễ tân', 'Lễ tân'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, db_column='product_id')
    date = models.DateField("Ngày")
    warehouse = models.TextField("Kho", choices=WAREHOUSE_CHOICES)
    opening_stock = models.DecimalField("Tồn đầu", max_digits=14, decimal_places=4, default=0)
    received = models.DecimalField("Nhập", max_digits=14, decimal_places=4, default=0)
    closing_stock = models.DecimalField("Tồn cuối", max_digits=14, decimal_places=4, default=0)
    actual_used = models.DecimalField(
        "Lượng dùng (tự tính)",
        max_digits=14, decimal_places=4,
        null=True, blank=True, editable=False,
        help_text="= opening + received - closing (Postgres generated column)"
    )
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_by = models.UUIDField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'inventory_daily'
        verbose_name = 'Tồn kho ngày'
        verbose_name_plural = '6. Tồn kho theo ngày'
        unique_together = (('product', 'date', 'warehouse'),)
        ordering = ['-date', 'warehouse', 'product__name']

    def __str__(self):
        return f"{self.product.name} - {self.date} - {self.warehouse}"
