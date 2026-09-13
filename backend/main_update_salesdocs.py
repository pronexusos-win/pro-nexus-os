with open("backend/main.py", "a") as f:
    f.write("\nfrom routers import sales_documents\n")
    f.write("app.include_router(sales_documents.router, prefix='/api/sales', tags=['Sales Documents & Tax'])\n")
