with open("backend/main.py", "a") as f:
    f.write("\nfrom routers import finance_expenses\n")
    f.write("app.include_router(finance_expenses.router, prefix='/api/finance', tags=['Expenses & Taxes'])\n")
