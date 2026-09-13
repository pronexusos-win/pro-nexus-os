with open("backend/main.py", "a") as f:
    f.write("\nfrom routers import auto_po_forecast\n")
    f.write("app.include_router(auto_po_forecast.router, prefix='/api/procurement', tags=['Auto-PO & Forecast'])\n")
