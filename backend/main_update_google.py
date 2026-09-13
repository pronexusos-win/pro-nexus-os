with open("backend/main.py", "a") as f:
    f.write("\nfrom routers import google_auth\n")
    f.write("app.include_router(google_auth.router, prefix='/api/auth/google', tags=['Google Authentication'])\n")
