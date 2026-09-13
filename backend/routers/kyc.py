from fastapi import APIRouter
router = APIRouter()

@router.get("/status")
def check_kyc_status():
    return {"kyc_status": "verified"}
