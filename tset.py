import win32print
import win32ui
from PIL import ImageWin  # install pillow if not yet: pip install pillow

def print_text_direct():
    printer_name = win32print.GetDefaultPrinter()
    print(printer_name)
    hprinter = win32print.OpenPrinter(printer_name)
    printer_info = win32print.GetPrinter(hprinter, 2)
    pdc = win32ui.CreateDC()
    pdc.CreatePrinterDC(printer_name)
    pdc.StartDoc("Django Print Job")
    pdc.StartPage()
    pdc.TextOut(100, 100, "I am Sanjith")
    pdc.EndPage()
    pdc.EndDoc()
    pdc.DeleteDC()
    print("✅ Printed successfully to", printer_name)

print_text_direct()
