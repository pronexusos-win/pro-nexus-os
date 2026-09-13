from fastapi import APIRouter, HTTPException
from services.affiliate.tree_engine import get_upline_chain

router = APIRouter()

@router.get("/tree/{member_id}")
def get_member_affiliate_tree(member_id: str):
    try:
        uplines = get_upline_chain(member_id, max_depth=4)
        return {
            "status": "success",
            "member_id": member_id,
            "unilevel_uplines": uplines
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
