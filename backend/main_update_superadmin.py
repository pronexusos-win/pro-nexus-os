with open("backend/main.py", "a") as f:
    f.write("\nfrom routers import super_admin_core\n")
    f.write("app.include_router(super_admin_core.router, prefix='/api/admin', tags=['Super Admin (God Mode)'])\n")
