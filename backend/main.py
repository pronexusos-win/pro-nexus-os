from fastapi import FastAPI, Request, HTTPException

app = FastAPI(title="Pro Nexus OS")

ALLOWED_TENANTS = ["tp_extra", "pro_nexus", "luck_kio", "peak_icon"]

@app.get("/")
def read_root():
    return {"message": "Welcome to Pro Nexus OS API"}

@app.post("/api/v1/{tenant}/webhook")
async def webhook_handler(tenant: str, request: Request):
    if tenant not in ALLOWED_TENANTS:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    try:
        payload = await request.json()
        print(f"[{tenant.upper()}] Webhook Payload: {payload}")
    except Exception as e:
        print(f"Error reading payload: {e}")
    
    return {"status": "success", "tenant": tenant}
