import win32print
import win32ui
from datetime import datetime

def print_order_bill(order):
    """
    Prints a formatted thermal bill for Appatha Restaurant.
    Optimized for WeP CN811-UEB (80mm paper width).
    """

    now = datetime.now().strftime("%d-%m-%Y %I:%M %p")

    # 🧾 Prepare bill lines
    lines = []
    lines.append("======================================")  # 38 chars wide
    lines.append("        APPATHA RESTAURANT 🍽️")
    lines.append("             Mannargudi")
    lines.append("======================================")
    lines.append(f"Bill No : {order.id}")
    lines.append(f"Date    : {now}")
    lines.append(f"Type    : {order.get_order_type_display()}")
    lines.append("--------------------------------------")
    lines.append("Item               Qty      Price")
    lines.append("--------------------------------------")

    # Fit items cleanly within 38 chars
    for item in order.items.all():
        name = item.dish.name[:14].ljust(14)
        qty = str(item.quantity).rjust(5)
        price = f"{item.price:.2f}".rjust(9)
        lines.append(f"{name}{qty}{price}")

    lines.append("--------------------------------------")

    # ✅ Keep TOTAL within 38-char width
    total_text = f"TOTAL : ₹{order.total_amount:.2f}"
    lines.append(total_text.rjust(38))

    lines.append("======================================")
    lines.append("   Thank you for dining with us!")
    lines.append("        Visit Again 🙏")
    lines.append("======================================")

    # 🖨️ Printer setup
    printer_name = win32print.GetDefaultPrinter()
    pdc = win32ui.CreateDC()
    pdc.CreatePrinterDC(printer_name)
    pdc.StartDoc("Appatha Restaurant Bill")
    pdc.StartPage()

    # 🧱 Font setup
    font = win32ui.CreateFont({
        "name": "Consolas",   # Monospace font
        "height": 28,         # Bigger and bolder text
        "weight": 600,
    })
    pdc.SelectObject(font)

    # 📄 Coordinates
    x = 30         # small left margin
    y = 50         # top margin
    line_height = 34

    for line in lines:
        pdc.TextOut(x, y, line)
        y += line_height

    # ✅ Finish print
    pdc.EndPage()
    pdc.EndDoc()
    pdc.DeleteDC()

    print(f"✅ Bill printed successfully to {printer_name}")
