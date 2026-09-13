with open("backend/main.py", "a") as f:
    f.write("\nfrom routers import barcode_scanner\n")
    f.write("app.include_router(barcode_scanner.router, prefix='/api/sales', tags=['Barcode Scanner'])\n")
