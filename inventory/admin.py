from django.contrib import admin
from .models import (
    HangHoa, CongThuc, ChiTietCongThuc,
    TonKhoQuayBar, TonKhoLeTan, TongTonKho,
    XuatMonFabi, XuatNguyenLieuFabi, SoSanhFabiVsThucTe,
    TongLuongDungQuayBar
)

# Đăng ký để xem trong admin (nếu bạn muốn)
admin.site.register(HangHoa)
admin.site.register(CongThuc)
admin.site.register(ChiTietCongThuc)
admin.site.register(TonKhoQuayBar)
admin.site.register(TonKhoLeTan)
admin.site.register(TongTonKho)
admin.site.register(XuatMonFabi)
admin.site.register(XuatNguyenLieuFabi)
admin.site.register(SoSanhFabiVsThucTe)
admin.site.register(TongLuongDungQuayBar)