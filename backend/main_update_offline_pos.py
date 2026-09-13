with open("backend/main.py", "a") as f:
    f.write("\nfrom routers import offline_pos_restaurant\n")
    f.write("app.include_router(offline_pos_restaurant.router, prefix='/api/pos-restaurant', tags=['Offline POS & Restaurant 4-Screen'])\n")
