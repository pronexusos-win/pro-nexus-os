with open("backend/main.py", "a") as f:
    f.write("\nfrom routers import fulfillment_pack\n")
    f.write("app.include_router(fulfillment_pack.router, prefix='/api/fulfillment', tags=['Scan-to-Pack'])\n")
