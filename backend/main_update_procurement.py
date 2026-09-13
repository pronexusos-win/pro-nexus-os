with open("backend/main.py", "a") as f:
    f.write("\nfrom routers import procurement\n")
    f.write("app.include_router(procurement.router, prefix='/api/procurement', tags=['Procurement (PO & GR)'])\n")
