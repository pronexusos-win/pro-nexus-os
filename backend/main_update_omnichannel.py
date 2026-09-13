with open("backend/main.py", "a") as f:
    f.write("\nfrom routers import omnichannel_pos\n")
    f.write("app.include_router(omnichannel_pos.router, prefix='/api/sales', tags=['Multi-channel POS & Wholesale'])\n")
