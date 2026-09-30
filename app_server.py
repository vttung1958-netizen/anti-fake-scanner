# 2. Tạo tệp PDF "2_TrangInThu_MauA4.pdf" chuẩn khổ A4 ngang (Landscape)
        pdf_path = "static/TrangInThu_MauA4.pdf"
        pdf = FPDF(orientation='L', unit='mm', format='A4')
        pdf.add_page()
        pdf.set_font("helvetica", "B", 13)
        pdf.cell(0, 8, "TRANG IN THU MAU (TEST TEM QR) - LOU HANG", align="C", new_x="LMARGIN", new_y="NEXT")
        
        pdf.set_font("helvetica", "I", 9)
        pdf.cell(0, 6, "Doanh nghiep in file PDF nay ra giay A4 ngang de kiem tra kich thuoc va quet thu ma QR truoc khi in hang loat.", align="C", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(5)
        
        # Bố trí lưới 4 cột x 3 hàng (tổng 12 tem trải đều trên khổ ngang A4)
        col_width = 65
        row_height = 45
        start_x = 18
        start_y = pdf.get_y()
        
        for idx, (s_code, s_path) in enumerate(sample_qr_data):
            c = idx % 4
            r = idx // 4
            x = start_x + c * col_width
            y = start_y + r * row_height
            
            # Vẽ khung viền tem
            pdf.rect(x, y, col_width - 6, row_height - 4)
            
            # Ghi mã code
            pdf.set_xy(x, y + 3)
            pdf.set_font("helvetica", "B", 10)
            pdf.cell(col_width - 6, 6, s_code, align="C", new_x="LMARGIN", new_y="NEXT")
            
            # Chèn hình ảnh QR
            try:
                pdf.image(s_path, x=x + 17, y=y + 10, w=30, h=30)
            except Exception:
                pass
                
        pdf.output(pdf_path)
