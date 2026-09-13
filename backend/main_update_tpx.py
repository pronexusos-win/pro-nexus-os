with open("backend/main.py", "a") as f:
    f.write("\nfrom routers import tpx_commission_engine\n")
    f.write("app.include_router(tpx_commission_engine.router, prefix='/api/tpx', tags=['TP Extra Engine'])\n")
