with open("backend/main.py", "a") as f:
    f.write("\nfrom routers import transit_stock\n")
    f.write("app.include_router(transit_stock.router, prefix='/api/procurement', tags=['Transit Stock'])\n")
