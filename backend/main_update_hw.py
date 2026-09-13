with open("backend/main.py", "a") as f:
    f.write("\nfrom routers import hardware_devices\n")
    f.write("app.include_router(hardware_devices.router, prefix='/api/hardware', tags=['Hardware Integration'])\n")
