with open("backend/main.py", "a") as f:
    f.write("\nfrom routers import finance_accounting\n")
    f.write("app.include_router(finance_accounting.router, prefix='/api/finance', tags=['Finance & Accounting (AP/AR)'])\n")
