from django.db import models
from django.db.models import Sum
from django.utils import timezone
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from decimal import Decimal


# ====================== 1. HÀNG HÓA ======================
class HangHoa(models.Model):
    LOAI_CHOICES = [
        ('nuoc_uong', 'Nước uống'),
        ('do_an', 'Đồ ăn'),
        ('khac', 'Khác'),
    ]

    ten = models.CharField("Tên hàng hóa", max_length=200, unique=True)
    loai = models.CharField("Phân loại", max_length=20, choices=LOAI_CHOICES, default='nuoc_uong')
    don_vi_quay_bar = models.CharField("Đơn vị quầy bar (ml, g, kg…)", max_length=50)
    don_vi_le_tan = models.CharField("Đơn vị lễ tân (chai, lon…)", max_length=50, blank=True, null=True)
    ty_le_quy_doi = models.DecimalField(
        "1 đơn vị lễ tân = bao nhiêu quầy bar?",
        max_digits=12, decimal_places=4, default=1.0000,
        help_text="Ví dụ: 1 chai Coca = 1500ml → nhập 1500.0000"
    )

    def __str__(self):
        return f"[{self.get_loai_display()}] {self.ten}"

    class Meta:
        verbose_name_plural = "1. Hàng hóa"
        ordering = ['loai', 'ten']


# ====================== 2. CÔNG THỨC MÓN ======================
class CongThuc(models.Model):
    mon = models.CharField("Tên món", max_length=200, unique=True)

    def __str__(self):
        return self.mon

    class Meta:
        verbose_name_plural = "2. Công thức món"


class ChiTietCongThuc(models.Model):
    cong_thuc = models.ForeignKey(CongThuc, on_delete=models.CASCADE, related_name='chi_tiet')
    hang_hoa = models.ForeignKey(HangHoa, on_delete=models.CASCADE)
    dinh_luong = models.DecimalField("Định lượng cho 1 món", max_digits=12, decimal_places=4)

    class Meta:
        unique_together = ('cong_thuc', 'hang_hoa')
        verbose_name_plural = "   Chi tiết công thức"

    def __str__(self):
        return f"{self.cong_thuc} → {self.hang_hoa} ({self.dinh_luong})"


# ====================== 3. TỒN KHO QUẦY BAR ======================
class TonKhoQuayBar(models.Model):
    hang_hoa = models.ForeignKey(HangHoa, on_delete=models.CASCADE, related_name='ton_quay_bar')
    ngay = models.DateField("Ngày")
    ton_dau = models.DecimalField("Tồn đầu ngày (tự động)", max_digits=14, decimal_places=4, default=0, editable=False)
    nhap = models.DecimalField("Nhập trong ngày", max_digits=14, decimal_places=4, default=0)
    ton_cuoi = models.DecimalField("Tồn cuối ngày (nhân viên nhập)", max_digits=14, decimal_places=4)
    luong_dung = models.DecimalField("Lượng dùng trong ngày (tự động)", max_digits=14, decimal_places=4, default=0, editable=False)

    class Meta:
        unique_together = ('hang_hoa', 'ngay')
        verbose_name_plural = "3. Tồn kho quầy bar"

    def clean(self):
        if self.ton_cuoi < 0:
            raise ValidationError("Tồn cuối ngày không được âm")

    def save(self, *args, **kwargs):
        # Tính tồn đầu ngày = tồn cuối hôm trước + nhập hôm nay
        ngay_truoc = self.ngay - timezone.timedelta(days=1)
        ton_truoc = TonKhoQuayBar.objects.filter(hang_hoa=self.hang_hoa, ngay=ngay_truoc).first()
        self.ton_dau = (ton_truoc.ton_cuoi if ton_truoc else Decimal('0')) + self.nhap

        # Tính lượng dùng
        self.luong_dung = self.ton_dau - self.ton_cuoi
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.hang_hoa} - {self.ngay} | Dùng: {self.luong_dung}"


# ====================== 9. TỔNG LƯỢNG DÙNG QUẦY BAR THEO KHOẢNG NGÀY ======================
class TongLuongDungQuayBar(models.Model):
    hang_hoa = models.ForeignKey(HangHoa, on_delete=models.CASCADE)
    ngay_bat_dau = models.DateField("Từ ngày")
    ngay_ket_thuc = models.DateField("Đến ngày")
    tong_luong_dung = models.DecimalField(
        "TỔNG LƯỢNG DÙNG (thực tế quầy bar)", 
        max_digits=16, decimal_places=4, 
        default=0, editable=False
    )
    so_ngay = models.PositiveIntegerField("Số ngày", default=0, editable=False)

    class Meta:
        unique_together = ('hang_hoa', 'ngay_bat_dau', 'ngay_ket_thuc')
        verbose_name_plural = "9. Tổng lượng dùng quầy bar theo khoảng ngày"
        indexes = [models.Index(fields=['ngay_bat_dau', 'ngay_ket_thuc'])]

    def save(self, *args, **kwargs):
        # Tự động tính tổng lượng dùng từ bảng TonKhoQuayBar
        qs = TonKhoQuayBar.objects.filter(
            hang_hoa=self.hang_hoa,
            ngay__range=[self.ngay_bat_dau, self.ngay_ket_thuc]
        ).aggregate(
            tong=Sum('luong_dung')
        )
        self.tong_luong_dung = qs['tong'] or Decimal('0')
        self.so_ngay = (self.ngay_ket_thuc - self.ngay_bat_dau).days + 1
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.hang_hoa} | {self.ngay_bat_dau} → {self.ngay_ket_thuc} | Tổng dùng: {self.tong_luong_dung} {self.hang_hoa.don_vi_quay_bar}"

# ====================== 4. TỒN KHO LỄ TÂN ======================
class TonKhoLeTan(models.Model):
    hang_hoa = models.ForeignKey(HangHoa, on_delete=models.CASCADE, related_name='ton_le_tan')
    ngay = models.DateField("Ngày")
    ton_cuoi = models.DecimalField("Tồn cuối ngày (nhân viên nhập)", max_digits=14, decimal_places=4)

    class Meta:
        unique_together = ('hang_hoa', 'ngay')
        verbose_name_plural = "4. Tồn kho lễ tân"

    def __str__(self):
        return f"{self.hang_hoa} - {self.ngay}: {self.ton_cuoi} {self.hang_hoa.don_vi_le_tan or ''}"


# ====================== 5. TỔNG TỒN KHO (TỰ ĐỘNG) ======================
class TongTonKho(models.Model):
    hang_hoa = models.ForeignKey(HangHoa, on_delete=models.CASCADE)
    ngay = models.DateField("Ngày")
    ton_quay_bar = models.DecimalField("Tồn quầy bar", max_digits=14, decimal_places=4, default=0, editable=False)
    ton_le_tan = models.DecimalField("Tồn lễ tân", max_digits=14, decimal_places=4, default=0, editable=False)
    tong_quy_doi = models.DecimalField("TỔNG TỒN (quy đổi về quầy bar)", max_digits=14, decimal_places=4, default=0, editable=False)

    class Meta:
        unique_together = ('hang_hoa', 'ngay')
        verbose_name_plural = "5. Tổng tồn kho (tự động)"

    def save(self, *args, **kwargs):
        bar = TonKhoQuayBar.objects.filter(hang_hoa=self.hang_hoa, ngay=self.ngay).first()
        le = TonKhoLeTan.objects.filter(hang_hoa=self.hang_hoa, ngay=self.ngay).first()

        self.ton_quay_bar = bar.ton_cuoi if bar else Decimal('0')
        self.ton_le_tan = le.ton_cuoi if le else Decimal('0')
        self.tong_quy_doi = self.ton_quay_bar + (self.ton_le_tan * self.hang_hoa.ty_le_quy_doi)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.hang_hoa} - {self.ngay}: {self.tong_quy_doi} {self.hang_hoa.don_vi_quay_bar}"


# ====================== 6. XUẤT MÓN THEO FABI (từ Excel) ======================
class XuatMonFabi(models.Model):
    ngay_xuat = models.DateField("Ngày xuất")
    cong_thuc = models.ForeignKey(CongThuc, on_delete=models.PROTECT)
    so_luong = models.PositiveIntegerField("Số lượng món")

    class Meta:
        verbose_name_plural = "6. Xuất món theo Fabi (Excel)"

    def __str__(self):
        return f"{self.cong_thuc} × {self.so_luong} - {self.ngay_xuat}"


# ====================== 7. XUẤT NGUYÊN LIỆU THEO FABI (tự động tính) ======================
class XuatNguyenLieuFabi(models.Model):
    ngay_xuat = models.DateField("Ngày xuất")
    hang_hoa = models.ForeignKey(HangHoa, on_delete=models.CASCADE)
    so_luong = models.DecimalField("Số lượng theo Fabi", max_digits=14, decimal_places=4)

    class Meta:
        unique_together = ('ngay_xuat', 'hang_hoa')
        verbose_name_plural = "7. Xuất nguyên liệu theo Fabi (tự động)"

    def __str__(self):
        return f"{self.hang_hoa} - {self.ngay_xuat}: {self.so_luong}"
    
# ====================== 8. SO SÁNH FABI VS THỰC TẾ THEO KỲ (THAY THẾ HOÀN TOÀN BẢNG CŨ) ======================
class SoSanhFabiVsThucTe(models.Model):
    hang_hoa = models.ForeignKey(HangHoa, on_delete=models.CASCADE)
    ngay_bat_dau = models.DateField("Từ ngày")
    ngay_ket_thuc = models.DateField("Đến ngày")
    
    fabi_tong = models.DecimalField("Tổng Fabi (lý thuyết)", max_digits=16, decimal_places=4, default=0, editable=False)
    thuc_te_tong = models.DecimalField("Tổng thực tế (quầy bar)", max_digits=16, decimal_places=4, default=0, editable=False)
    chenh_lech_tong = models.DecimalField("Chênh lệch tổng kỳ", max_digits=16, decimal_places=4, default=0, editable=False)
    ghi_chu = models.CharField("Kết luận", max_length=100, blank=True, editable=False)
    so_ngay = models.PositiveIntegerField("Số ngày", default=0, editable=False)

    class Meta:
        unique_together = ('hang_hoa', 'ngay_bat_dau', 'ngay_ket_thuc')
        verbose_name_plural = "8. SO SÁNH FABI VS THỰC TẾ THEO KỲ (CHÍNH THỨC)"
        indexes = [models.Index(fields=['ngay_bat_dau', 'ngay_ket_thuc'])]

    def save(self, *args, **kwargs):
        # Tổng Fabi trong kỳ
        fabi = XuatNguyenLieuFabi.objects.filter(
            hang_hoa=self.hang_hoa,
            ngay_xuat__range=[self.ngay_bat_dau, self.ngay_ket_thuc]
        ).aggregate(tong=Sum('so_luong'))['tong'] or Decimal('0')
        
        # Tổng thực tế trong kỳ
        thuc_te = TonKhoQuayBar.objects.filter(
            hang_hoa=self.hang_hoa,
            ngay__range=[self.ngay_bat_dau, self.ngay_ket_thuc]
        ).aggregate(tong=Sum('luong_dung'))['tong'] or Decimal('0')
        
        self.fabi_tong = fabi
        self.thuc_te_tong = thuc_te
        self.chenh_lech_tong = thuc_te - fabi
        self.so_ngay = (self.ngay_ket_thuc - self.ngay_bat_dau).days + 1
        
        if abs(self.chenh_lech_tong) < Decimal('0.0001'):
            self.ghi_chu = "ĐÚNG CHUẨN"
        elif self.chenh_lech_tong > 0:
            self.ghi_chu = f"HAO HỤT {self.chenh_lech_tong} {self.hang_hoa.don_vi_quay_bar}"
        else:
            self.ghi_chu = f"THỪA {abs(self.chenh_lech_tong)} {self.hang_hoa.don_vi_quay_bar}"
            
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.hang_hoa} | {self.ngay_bat_dau}→{self.ngay_ket_thuc} | Chênh: {self.chenh_lech_tong}"