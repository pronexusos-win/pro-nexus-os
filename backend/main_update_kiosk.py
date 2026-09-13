with open("backend/main.py", "a") as f:
    f.write("\nfrom routers import iot_kiosk\n")
    f.write("app.include_router(iot_kiosk.router, prefix='/api/iot', tags=['IoT Kiosk & Vending'])\n")
