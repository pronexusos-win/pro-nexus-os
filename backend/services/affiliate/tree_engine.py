from core.database import get_db_connection

def get_upline_chain(member_id: str, max_depth: int = 4) -> list:
    conn = get_db_connection()
    uplines = []
    current_id = member_id
    
    try:
        with conn.cursor() as cursor:
            for depth in range(1, max_depth + 1):
                cursor.execute("SELECT sponsor_id, name FROM members WHERE member_id = %s", (current_id,))
                row = cursor.fetchone()
                if not row or not row["sponsor_id"]:
                    break
                sponsor_id = row["sponsor_id"]
                cursor.execute("SELECT member_id, name FROM members WHERE member_id = %s", (sponsor_id,))
                sponsor_row = cursor.fetchone()
                if not sponsor_row:
                    break
                
                uplines.append({
                    "level": depth,
                    "member_id": sponsor_row["member_id"],
                    "name": sponsor_row["name"]
                })
                current_id = sponsor_id
    finally:
        conn.close()
        
    return uplines
