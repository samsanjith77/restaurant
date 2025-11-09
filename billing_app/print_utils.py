import win32print
import win32ui
from datetime import datetime

def print_order_bill(order):
    """
    Prints a formatted thermal bill for Appatha Restaurant.
    Optimized for WeP CN811-UEB (80mm paper width).
    Fixed alignment and separator lines.
    """

    now = datetime.now().strftime("%d-%m-%Y %I:%M %p")

    # 🖨️ Printer setup
    printer_name = win32print.GetDefaultPrinter()
    pdc = win32ui.CreateDC()
    pdc.CreatePrinterDC(printer_name)
    pdc.StartDoc("Appatha Restaurant Bill")
    pdc.StartPage()

    # 🧱 Font definitions
    # Small font for bill date and type only
    small_font = win32ui.CreateFont({
        "name": "Latha",
        "height": 22,
        "weight": 400,
    })
    
    # Medium font for header, separators, footer
    medium_font = win32ui.CreateFont({
        "name": "Courier New",
        "height": 26,
        "weight": 600,
    })
    
    # Large font for item names (Tamil support)
    large_font = win32ui.CreateFont({
        "name": "Latha",
        "height": 32,
        "weight": 700,
    })
    
    # Medium monospace for quantities and prices
    mono_font = win32ui.CreateFont({
        "name": "Courier New",
        "height": 32,
        "weight": 700,
    })

    # 📄 Print coordinates
    x = 20
    y = 40
    small_line_height = 28
    medium_line_height = 32
    large_line_height = 38

    # Full width separator for 80mm paper
    full_separator = "=" * 48
    half_separator = "-" * 48

    # === HEADER SECTION (Medium font) ===
    pdc.SelectObject(medium_font)
    
    pdc.TextOut(x, y, full_separator)
    y += medium_line_height
    
    pdc.TextOut(x, y, "        APPATHA RESTAURANT 🍽️")
    y += medium_line_height
    
    pdc.TextOut(x, y, "             Mannargudi")
    y += medium_line_height
    
    pdc.TextOut(x, y, full_separator)
    y += medium_line_height
    
    pdc.TextOut(x, y, f"Bill No : {order.id}")
    y += medium_line_height

    # === BILL INFO (Small font) ===
    pdc.SelectObject(small_font)
    
    pdc.TextOut(x, y, f"Date    : {now}")
    y += small_line_height
    
    pdc.TextOut(x, y, f"Type    : {order.get_order_type_display()}")
    y += small_line_height

    # === COLUMN HEADER (Medium font) ===
    pdc.SelectObject(medium_font)
    
    pdc.TextOut(x, y, half_separator)
    y += medium_line_height
    
    pdc.TextOut(x, y, "Item Name              Qty     Price")
    y += medium_line_height
    
    pdc.TextOut(x, y, half_separator)
    y += medium_line_height

    # === ITEMS SECTION ===
    for item in order.items.all():
        display_name = item.dish.secondary_name if item.dish.secondary_name else item.dish.name
        
        # Item name in large font (Tamil)
        pdc.SelectObject(large_font)
        pdc.TextOut(x, y, display_name[:22])
        
        # Quantity and Price in monospace (aligned)
        pdc.SelectObject(mono_font)
        
        # Calculate positions for alignment
        qty_x = x + 320  # Position for quantity
        price_x = x + 420  # Position for price
        
        qty_text = str(item.quantity)
        price_text = f"Rs.{item.price:.2f}"
        
        pdc.TextOut(qty_x, y, qty_text)
        pdc.TextOut(price_x, y, price_text)
        
        y += large_line_height

    # === FOOTER SECTION (Medium font) ===
    pdc.SelectObject(large_font)
    
    pdc.TextOut(x, y, half_separator)
    y += 38
    
    # Total line with proper alignment
    total_label = "TOTAL :"
    total_value = f"Rs.{order.total_amount:.2f}"
    
    pdc.TextOut(x, y, total_label)
    pdc.TextOut(x + 420, y, total_value)
    y += medium_line_height
    
    pdc.TextOut(x, y, full_separator)
    y += medium_line_height

    pdc.EndPage()
    pdc.EndDoc()
    pdc.DeleteDC()

    print(f"✅ Bill printed successfully to {printer_name}")