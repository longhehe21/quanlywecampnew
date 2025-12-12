from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum
from decimal import Decimal
from datetime import datetime
import pandas as pd
from .models import (
    HangHoa, CongThuc, ChiTietCongThuc,
    TonKhoQuayBar, TonKhoLeTan, TongTonKho,
    TongLuongDungQuayBar, XuatMonFabi, XuatNguyenLieuFabi, SoSanhFabiVsThucTe
)


def calculate_xuat_nguyen_lieu_fabi():
    XuatNguyenLieuFabi.objects.all().delete()
    for xm in XuatMonFabi.objects.select_related('cong_thuc'):
        for ct in xm.cong_thuc.chi_tiet.all():
            obj, created = XuatNguyenLieuFabi.objects.get_or_create(
                ngay_xuat=xm.ngay_xuat,
                hang_hoa=ct.hang_hoa,
                defaults={'so_luong': ct.dinh_luong * xm.so_luong}
            )
            if not created:
                obj.so_luong += ct.dinh_luong * xm.so_luong
                obj.save()


def home(request):
    today = timezone.now().date()

    # === XỬ LÝ POST ===
    if request.method == "POST":
        form_type = request.POST.get("form_type")

        # 1. THÊM HÀNG HÓA
        if form_type == "hanghoa":
            ten = request.POST.get("ten", "").strip()
            loai = request.POST.get("loai", "nuoc_uong")
            if HangHoa.objects.filter(ten__iexact=ten).exists():
                messages.error(request, f"Hàng hóa '{ten}' đã tồn tại!")
            else:
                HangHoa.objects.create(
                    ten=ten,
                    loai=loai,
                    don_vi_quay_bar=request.POST.get("don_vi_quay_bar", ""),
                    don_vi_le_tan=request.POST.get("don_vi_le_tan") or None,
                    ty_le_quy_doi=Decimal(request.POST.get("ty_le_quy_doi", "1"))
                )
                messages.success(request, f"Đã thêm hàng hóa: {ten}")

        # 2. CÔNG THỨC MÓN
        elif form_type == "congthuc_multi":
            ten_mon = request.POST.get("ten_mon", "").strip()
            if not ten_mon:
                messages.error(request, "Chưa nhập tên món!")
            else:
                cong_thuc, _ = CongThuc.objects.get_or_create(mon=ten_mon)
                ChiTietCongThuc.objects.filter(cong_thuc=cong_thuc).delete()
                ids = request.POST.getlist("hang_hoa")
                dls = request.POST.getlist("dinh_luong")
                added = 0
                for id, dl in zip(ids, dls):
                    if id and dl:
                        ChiTietCongThuc.objects.create(
                            cong_thuc=cong_thuc,
                            hang_hoa_id=id,
                            dinh_luong=dl
                        )
                        added += 1
                messages.success(request, f"Đã lưu công thức: {ten_mon} ({added} nguyên liệu)")

        # 3. TỒN KHO QUẦY BAR (chỉ hàng loại nước + khác)
        elif form_type == "tonkho_bar":
            ngay_str = request.POST.get("ngay")
            try:
                ngay = datetime.strptime(ngay_str, "%Y-%m-%d").date()
            except:
                messages.error(request, "Ngày không hợp lệ!")
                return redirect('home')

            for hh in HangHoa.objects.filter(loai__in=['nuoc_uong', 'khac']):
                nhap = Decimal(request.POST.get(f"nhap_{hh.id}", "0") or "0")
                tc = Decimal(request.POST.get(f"toncuoi_{hh.id}", "0") or "0")
                obj, _ = TonKhoQuayBar.objects.get_or_create(
                    hang_hoa=hh, ngay=ngay,
                    defaults={'nhap': nhap, 'ton_cuoi': tc}
                )
                if not _:
                    obj.nhap = nhap
                    obj.ton_cuoi = tc
                    obj.save()
            messages.success(request, f"Lưu tồn quầy bar ngày {ngay.strftime('%d/%m/%Y')}")

        # 4. TỒN KHO BẾP (chỉ hàng loại đồ ăn)
        elif form_type == "tonkho_bep":
            ngay_str = request.POST.get("ngay")
            try:
                ngay = datetime.strptime(ngay_str, "%Y-%m-%d").date()
            except:
                messages.error(request, "Ngày không hợp lệ!")
                return redirect('home')

            for hh in HangHoa.objects.filter(loai='do_an'):
                nhap = Decimal(request.POST.get(f"nhap_{hh.id}", "0") or "0")
                tc = Decimal(request.POST.get(f"toncuoi_{hh.id}", "0") or "0")
                obj, _ = TonKhoQuayBar.objects.get_or_create(
                    hang_hoa=hh, ngay=ngay,
                    defaults={'nhap': nhap, 'ton_cuoi': tc}
                )
                if not _:
                    obj.nhap = nhap
                    obj.ton_cuoi = tc
                    obj.save()
            messages.success(request, f"Lưu tồn bếp ngày {ngay.strftime('%d/%m/%Y')}")

        # 5. TỒN KHO LỄ TÂN
        elif form_type == "tonkho_letan":
            ngay_str = request.POST.get("ngay")
            try:
                ngay = datetime.strptime(ngay_str, "%Y-%m-%d").date()
            except:
                messages.error(request, "Ngày không hợp lệ!")
                return redirect('home')

            for hh in HangHoa.objects.filter(don_vi_le_tan__isnull=False):
                tc = Decimal(request.POST.get(f"toncuoi_{hh.id}", "0") or "0")
                TonKhoLeTan.objects.update_or_create(
                    hang_hoa=hh, ngay=ngay,
                    defaults={'ton_cuoi': tc}
                )
            messages.success(request, f"Lưu tồn lễ tân ngày {ngay.strftime('%d/%m/%Y')}")

        # XÓA TỒN BAR
        elif form_type == "xoa_bar":
            ngay_str = request.POST.get("ngay_xoa")
            try:
                ngay = datetime.strptime(ngay_str, "%Y-%m-%d").date()
                count = TonKhoQuayBar.objects.filter(
                    ngay=ngay,
                    hang_hoa__loai__in=['nuoc_uong', 'khac']
                ).delete()[0]
                messages.success(request, f"Đã xóa {count} bản ghi tồn quầy bar ngày {ngay.strftime('%d/%m/%Y')}")
            except:
                messages.error(request, "Lỗi xóa tồn bar")

        # XÓA TỒN BẾP
        elif form_type == "xoa_bep":
            ngay_str = request.POST.get("ngay_xoa")
            try:
                ngay = datetime.strptime(ngay_str, "%Y-%m-%d").date()
                count = TonKhoQuayBar.objects.filter(
                    ngay=ngay,
                    hang_hoa__loai='do_an'
                ).delete()[0]
                messages.success(request, f"Đã xóa {count} bản ghi tồn bếp ngày {ngay.strftime('%d/%m/%Y')}")
            except:
                messages.error(request, "Lỗi xóa tồn bếp")

        # XÓA TỒN LỄ TÂN
        elif form_type == "xoa_letan":
            ngay_str = request.POST.get("ngay_xoa")
            try:
                ngay = datetime.strptime(ngay_str, "%Y-%m-%d").date()
                count = TonKhoLeTan.objects.filter(ngay=ngay).delete()[0]
                messages.success(request, f"Đã xóa {count} bản ghi tồn lễ tân ngày {ngay.strftime('%d/%m/%Y')}")
            except:
                messages.error(request, "Lỗi xóa tồn lễ tân")

        # TẢI FILE FABI
        elif form_type == "upload_fabi":
            excel_file = request.FILES.get('excel_file')
            if excel_file:
                try:
                    df = pd.read_excel(excel_file)
                    cols = [c.lower().strip() for c in df.columns]
                    if not all(c in cols for c in ['ngày xuất', 'tên món', 'số lượng món']):
                        messages.error(request, "File phải có cột: ngày xuất, tên món, số lượng món")
                    else:
                        added = 0
                        for _, row in df.iterrows():
                            try:
                                ngay = pd.to_datetime(row['ngày xuất']).date()
                                mon = str(row['tên món']).strip()
                                sl = int(row['số lượng món'])
                                cong_thuc = get_object_or_404(CongThuc, mon__iexact=mon)
                                XuatMonFabi.objects.create(ngay_xuat=ngay, cong_thuc=cong_thuc, so_luong=sl)
                                added += 1
                            except:
                                continue
                        calculate_xuat_nguyen_lieu_fabi()
                        messages.success(request, f"Đã tải {added} món Fabi và tính xuất nguyên liệu")
                except Exception as e:
                    messages.error(request, f"Lỗi: {str(e)}")
        # XÓA XUẤT MÓN FABI THEO NGÀY
        elif form_type == "xoa_fabi":
            ngay_str = request.POST.get("ngay_xoa_fabi")
            try:
                ngay = datetime.strptime(ngay_str, "%Y-%m-%d").date()
                # Xóa cả xuất món và xuất nguyên liệu
                count_mon = XuatMonFabi.objects.filter(ngay_xuat=ngay).delete()[0]
                count_nl = XuatNguyenLieuFabi.objects.filter(ngay_xuat=ngay).delete()[0]
                count = count_mon + count_nl
                messages.success(request, f"Đã xóa {count} bản ghi Fabi ngày {ngay.strftime('%d/%m/%Y')}")
            except:
                messages.error(request, "Lỗi xóa Fabi")

        return redirect('home')

    # === LOAD DỮ LIỆU ===
    hang_hoa_list = HangHoa.objects.all().order_by('ten')

    # Phân loại hàng hóa cho nhập tồn
    hang_hoa_bar = HangHoa.objects.filter(loai__in=['nuoc_uong', 'khac']).order_by('ten')
    hang_hoa_bep = HangHoa.objects.filter(loai='do_an').order_by('ten')
    hang_hoa_letan = HangHoa.objects.exclude(don_vi_le_tan__isnull=True).exclude(don_vi_le_tan='')

    cong_thuc_list = ChiTietCongThuc.objects.select_related('cong_thuc', 'hang_hoa').order_by('cong_thuc__mon')

    # Tổng tồn kho theo ngày chọn
    ngay_xem_tong_str = request.GET.get('ngay_xem_tong')
    try:
        ngay_xem_tong = datetime.strptime(ngay_xem_tong_str, "%Y-%m-%d").date() if ngay_xem_tong_str else today
    except:
        ngay_xem_tong = today

    tong_ton_chi_tiet = []
    for hh in hang_hoa_list:
        bar = TonKhoQuayBar.objects.filter(hang_hoa=hh, ngay=ngay_xem_tong).first()
        letan = TonKhoLeTan.objects.filter(hang_hoa=hh, ngay=ngay_xem_tong).first()
        tong_ton_chi_tiet.append({
            'ten': hh.ten,
            'ton_bar': bar.ton_cuoi if bar else Decimal('0'),
            'don_vi_bar': hh.don_vi_quay_bar,
            'ton_letan': letan.ton_cuoi if letan else Decimal('0'),
            'don_vi_letan': hh.don_vi_le_tan or '',
            'tong_quy_doi': (bar.ton_cuoi if bar else Decimal('0')) + (letan.ton_cuoi if letan else Decimal('0')) * hh.ty_le_quy_doi
        })

    # Tổng lượng dùng theo kỳ
    tu_ngay_str = request.GET.get('tu_ngay')
    den_ngay_str = request.GET.get('den_ngay')
    try:
        tu_ngay = datetime.strptime(tu_ngay_str, "%Y-%m-%d").date() if tu_ngay_str else today
        den_ngay = datetime.strptime(den_ngay_str, "%Y-%m-%d").date() if den_ngay_str else today
    except:
        tu_ngay = den_ngay = today

    tong_luong_dung_list = []
    for hh in hang_hoa_list:
        obj, _ = TongLuongDungQuayBar.objects.get_or_create(
            hang_hoa=hh, ngay_bat_dau=tu_ngay, ngay_ket_thuc=den_ngay
        )
        tong_luong_dung_list.append(obj)

    # LỊCH SỬ TỒN KHO BAR (chỉ hàng loại nước uống + khác)
    lich_su_bar = TonKhoQuayBar.objects.filter(
        hang_hoa__loai__in=['nuoc_uong', 'khac']
    ).select_related('hang_hoa').order_by('-ngay', 'hang_hoa__ten')[:200]

    # LỊCH SỬ TỒN KHO BẾP (chỉ hàng loại đồ ăn)
    lich_su_bep = TonKhoQuayBar.objects.filter(
        hang_hoa__loai='do_an'
    ).select_related('hang_hoa').order_by('-ngay', 'hang_hoa__ten')[:200]

    # LỊCH SỬ TỒN LỄ TÂN
    lich_su_letan = TonKhoLeTan.objects.select_related('hang_hoa').order_by('-ngay', 'hang_hoa__ten')[:200]

    # TAB 3: FABI
    xuat_mon_fabi_list = XuatMonFabi.objects.select_related('cong_thuc').order_by('-ngay_xuat', 'cong_thuc__mon')[:200]
    xuat_nguyen_lieu_fabi_list = XuatNguyenLieuFabi.objects.select_related('hang_hoa').order_by('-ngay_xuat', 'hang_hoa__ten')[:200]

    tu_ngay_fabi_str = request.GET.get('tu_ngay_fabi')
    den_ngay_fabi_str = request.GET.get('den_ngay_fabi')
    try:
        tu_ngay_fabi = datetime.strptime(tu_ngay_fabi_str, "%Y-%m-%d").date() if tu_ngay_fabi_str else today
        den_ngay_fabi = datetime.strptime(den_ngay_fabi_str, "%Y-%m-%d").date() if den_ngay_fabi_str else today
    except:
        tu_ngay_fabi = den_ngay_fabi = today

    sosanh_fabi_list = []
    for hh in hang_hoa_list:
        obj, _ = SoSanhFabiVsThucTe.objects.get_or_create(
            hang_hoa=hh,
            ngay_bat_dau=tu_ngay_fabi,
            ngay_ket_thuc=den_ngay_fabi
        )
        sosanh_fabi_list.append(obj)

    context = {
        'hang_hoa_list': hang_hoa_list,
        'hang_hoa_bar': hang_hoa_bar,
        'hang_hoa_bep': hang_hoa_bep,
        'hang_hoa_letan': hang_hoa_letan,
        'cong_thuc_list': cong_thuc_list,
        'tong_ton_chi_tiet': tong_ton_chi_tiet,
        'ngay_xem_tong': ngay_xem_tong,
        'today': today,
        'tong_luong_dung_list': tong_luong_dung_list,
        'tu_ngay': tu_ngay,
        'den_ngay': den_ngay,
        'lich_su_bar': lich_su_bar,
        'lich_su_bep': lich_su_bep,
        'lich_su_letan': lich_su_letan,
        # TAB 3
        'xuat_mon_fabi_list': xuat_mon_fabi_list,
        'xuat_nguyen_lieu_fabi_list': xuat_nguyen_lieu_fabi_list,
        'sosanh_fabi_list': sosanh_fabi_list,
        'tu_ngay_fabi': tu_ngay_fabi,
        'den_ngay_fabi': den_ngay_fabi,
    }

    return render(request, 'base.html', context)


# XÓA HÀNG HÓA
def xoa_hang_hoa(request, pk):
    hh = get_object_or_404(HangHoa, pk=pk)
    ten = hh.ten
    hh.delete()
    messages.success(request, f"Đã xóa hàng hóa: {ten}")
    return redirect('home')

# XÓA CHI TIẾT CÔNG THỨC
def xoa_chi_tiet(request, pk):
    ct = get_object_or_404(ChiTietCongThuc, pk=pk)
    ct.delete()
    messages.success(request, "Đã xóa nguyên liệu khỏi công thức")
    return redirect('home')