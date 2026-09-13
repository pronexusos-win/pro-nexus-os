with open("backend/main.py", "a") as f:
    f.write("\nfrom routers import community_market\n")
    f.write("app.include_router(community_market.router, prefix='/api/community', tags=['Hyper-Local Community'])\n")
