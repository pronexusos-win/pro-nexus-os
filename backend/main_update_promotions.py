with open("backend/main.py", "a") as f:
    f.write("\nfrom routers import promotions\n")
    f.write("app.include_router(promotions.router, prefix='/api/sales', tags=['Promotions & Discounts'])\n")
