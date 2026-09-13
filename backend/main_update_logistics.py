with open("backend/main.py", "a") as f:
    f.write("\nfrom routers import logistics_delivery\n")
    f.write("app.include_router(logistics_delivery.router, prefix='/api/logistics', tags=['Delivery & Logistics'])\n")
