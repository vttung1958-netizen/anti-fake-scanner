@app.route('/buy', methods=['GET', 'POST'])
def buy():
    if request.method == 'POST':
        prod_name = request.form.get('prod_name')
        manufacturer = request.form.get('manufacturer')
        tax_code = request.form.get('tax_code', 'Chưa cung cấp')
        quantity = int(request.form.get('quantity', 1000))
        print_type = request.form.get('print_type', 'black_white')
        
        company_hw_id = f"HW-CORP-{uuid.uuid4().hex[:10].upper()}"
        
        # Áp dụng biểu giá bậc thang thông minh
        total_price = calculate_tem_price(quantity)
            
        order_id = f"DH{uuid.uuid4().hex[:6].upper()}"
        
        orders_db[order_id] = {
            "prod_name": prod_name,
            "manufacturer": manufacturer,
            "tax_code": tax_code,
            "hardware_id": company_hw_id,
            "quantity": quantity,
            "print_type": print_type,
            "total_price": total_price,
            "status": "pending",
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        return redirect(url_for('checkout', order_id=order_id))
        
    return render_template('buy.html')
