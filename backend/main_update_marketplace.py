with open("backend/main.py", "a") as f:
    f.write("\nfrom routers import marketplace_cellpage\n")
    f.write("app.include_router(marketplace_cellpage.router, prefix='/api/marketplace', tags=['Cell Page & Marketplace'])\n")
