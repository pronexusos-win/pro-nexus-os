with open("backend/main.py", "a") as f:
    f.write("\nfrom routers import inventory_bom\n")
    f.write("app.include_router(inventory_bom.router, prefix='/api/inventory', tags=['BOM & Recipe'])\n")
