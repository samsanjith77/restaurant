import win32print
import win32ui

def print_order_bill(order):
    """
    Prints an order bill to the default printer with proper spacing and font.
    """
    # Prepare bill lines
    lines = []
    lines.append("====================================")
    lines.append("           🧾 ORDER RECEIPT")
    lines.append("====================================")
    lines.append(f"Order ID   : {order.id}")
    lines.append(f"Order Type : {order.get_order_type_display()}")
    lines.append("------------------------------------")
    lines.append("Item                  Qty    Price")
    lines.append("------------------------------------")

    for item in order.items.all():
        name = item.dish.name[:15].ljust(15)
        qty = str(item.quantity).rjust(3)
        price = f"{item.price:.2f}".rjust(8)
        lines.append(f"{name} {qty} {price}")

    lines.append("------------------------------------")
    lines.append(f"TOTAL AMOUNT : ₹{order.total_amount:.2f}")
    lines.append("====================================")
    lines.append("     Thank you! Visit again 🙏")
    lines.append("====================================")

    # 🖨️ Printer setup
    printer_name = win32print.GetDefaultPrinter()
    pdc = win32ui.CreateDC()
    pdc.CreatePrinterDC(printer_name)
    pdc.StartDoc("Django Order Bill")
    pdc.StartPage()

    # 🧾 Font setup (monospaced for perfect alignment)
    font = win32ui.CreateFont({
        "name": "Courier New",
        "height": 25,     # font size
        "weight": 700,    # 400 = normal, 700 = bold
    })
    pdc.SelectObject(font)

    # Starting coordinates
    x = 100
    y = 100
    line_height = 28  # Adjust spacing based on font height

    # ✅ Print each line separately
    for line in lines:
        pdc.TextOut(x, y, line)
        y += line_height

    pdc.EndPage()
    pdc.EndDoc()
    pdc.DeleteDC()

    print(f"✅ Bill printed successfully to {printer_name}")
