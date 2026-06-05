"""
Views cho Supabase schema (đã refactor từ old Django models).

⚠️ Old views (dùng HangHoa/TonKhoQuayBar/CongThuc...) đã được remove vì schema thay đổi.
Hiện tại UI chính là Django Admin tại /admin/.

TODO (future):
- Trang home: dashboard hiển thị cost của tất cả món
- Trang nhập tồn kho hàng ngày
- Trang clone bảng giá + sửa giá
"""
from django.shortcuts import render, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.db import connection
from .models import Recipe, Product, PriceList


def home(request):
    """Home: redirect tạm sang /admin/. Sau này build dashboard custom."""
    return redirect('/admin/')


@staff_member_required
def recipe_costs(request):
    """Trang xem cost của tất cả recipe (truy vấn view recipe_costs_active)."""
    with connection.cursor() as cur:
        cur.execute("""
            SELECT recipe_id, recipe_name, recipe_type,
                   output_qty, output_unit, total_cost, unit_cost
            FROM public.recipe_costs_active
            ORDER BY recipe_type, recipe_name
        """)
        rows = [
            dict(zip(['id', 'name', 'type', 'output_qty', 'output_unit', 'total_cost', 'unit_cost'], r))
            for r in cur.fetchall()
        ]
    return render(request, 'recipe_costs.html', {'recipes': rows})
