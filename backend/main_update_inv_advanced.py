with open("backend/main.py", "a") as f:
    f.write("\nfrom routers import inventory_advanced\n")
    f.write("app.include_router(inventory_advanced.router, prefix='/api/inventory', tags=['Advanced Inventory (Lot & Tax)'])\n")
