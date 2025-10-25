import win32print
import win32ui
from datetime import datetime

def print_order_bill(order):
    """
    Prints a formatted thermal bill for Appatha Restaurant.
    Works on any USB-connected thermal printer installed in Windows.
    """

    # 🕒 Date & Time
    now = datetime.now().strftime("%d-%m-%Y %I:%M %p")

    # 🧾 Prepare bill lines (for 58mm printer)
    lines = []
    lines.append("================================")
    lines.append("     APPATHA RESTAURANT 🍽️")
    lines.append("          Mannargudi")
    lines.append("        Ph: +91-XXXXXXXXXX")  # optional
    lines.append("================================")
    lines.append(f"Bill No : {order.id}")
    lines.append(f"Date    : {now}")
    lines.append(f"Type    : {order.get_order_type_display()}")
    lines.append("--------------------------------")
    lines.append("Item               Qty   Price")
    lines.append("--------------------------------")

    for item in order.items.all():
        name = item.dish.name[:13].ljust(13)
        qty = str(item.quantity).rjust(3)
        price = f"{item.price:.2f}".rjust(7)
        lines.append(f"{name} {qty} {price}")

    lines.append("--------------------------------")
    lines.append(f"TOTAL : ₹{order.total_amount:.2f}".rjust(32))
    lines.append("================================")
    lines.append("     Thank you for dining with us!")
    lines.append("         Visit Again 🙏")
    lines.append("================================")

    # 🖨️ Printer initialization
    printer_name = win32print.GetDefaultPrinter()
    pdc = win32ui.CreateDC()
    pdc.CreatePrinterDC(printer_name)
    pdc.StartDoc("Appatha Restaurant Bill")
    pdc.StartPage()

    # 🧱 Font setup (good for 58mm printers)
    font = win32ui.CreateFont({
        "name": "Consolas",
        "height": 18,   # adjust for printer paper width
        "weight": 400,
    })
    pdc.SelectObject(font)

    # 📄 Starting coordinates
    x = 60  # margin from left
    y = 50
    line_height = 24

    # 🖨️ Print each line
    for line in lines:
        pdc.TextOut(x, y, line)
        y += line_height

    # ✅ Finish print
    pdc.EndPage()
    pdc.EndDoc()
    pdc.DeleteDC()

    print(f"✅ Bill printed successfully to {printer_name}")
