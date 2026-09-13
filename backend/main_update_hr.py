with open("backend/main.py", "a") as f:
    f.write("\nfrom routers import hr_management\n")
    f.write("app.include_router(hr_management.router, prefix='/api/hr', tags=['HR & Shift Management'])\n")
