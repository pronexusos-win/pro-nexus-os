with open("backend/main.py", "a") as f:
    f.write("\nfrom routers import warehouse_barcode\n")
    f.write("app.include_router(warehouse_barcode.router, prefix='/api/warehouse', tags=['Warehouse & SKU Barcode'])\n")
