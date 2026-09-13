import os
with open("backend/main.py", "a") as f:
    f.write("\nfrom routers import social_commerce\n")
    f.write("app.include_router(social_commerce.router, prefix='/api/social', tags=['Social Commerce'])\n")
