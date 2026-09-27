from flask import Flask, render_template, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Kích hoạt CORS cho toàn bộ ứng dụng

# Cơ sở dữ liệu mẫu về sản phẩm chống hàng giả
PRODUCT_DB = {
    "SP001": {
        "name": "Đông trùng hạ thảo chính hãng",
        "status": "Hàng thật",
        "maker": "Công ty cổ phần dược liệu",
        "date": "2026-01-15"
    },
    "SP002": {
        "name": "Sâm ngọc linh nguyên chất",
        "status": "Hàng thật",
        "maker": "Tập đoàn dược phẩm VN",
        "date": "2026-02-10"
    }
}

@app.route('/', methods=['GET', 'POST'])
def home():
    result = None
    if request.method == 'POST':
        code = request.form.get('code', '').strip().upper()
        if code in PRODUCT_DB:
            result = PRODUCT_DB[code]
        else:
            result = {
                "name": "Không xác định",
                "status": "Không tìm thấy",
                "maker": "Không rõ nguồn gốc hoặc mã sai",
                "date": "N/A"
            }
    return render_template('index.html', result=result)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
