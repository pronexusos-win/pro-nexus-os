with open("backend/main.py", "a") as f:
    f.write("\nfrom routers import offline_sync\n")
    f.write("app.include_router(offline_sync.router, prefix='/api/sales', tags=['Offline POS Sync'])\n")
