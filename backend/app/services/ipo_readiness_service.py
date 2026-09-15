from datetime import datetime
from backend.app.core.database import get_db_connection

def calculate_ipo_readiness_index(company_slug: str = "tp_extra"):
    """
    วิเคราะห์ความพร้อมสู่การเข้าจดทะเบียนในตลาดหลักทรัพย์ 6 เสาหลัก:
    1. Financial Integrity (ความสมบูรณ์โปร่งใสทางการเงิน)
    2. Tax & Statutory Compliance (ความถูกต้องทางภาษีและงานราชการ)
    3. Corporate Governance (บรรษัทภิบาลและมติกรรมการ บอจ.5)
    4. Internal Control & Anti-Fraud (ระบบการควบคุมภายใน COSO)
    5. Human Capital & Labor Rights (สิทธิแรงงานและการป้องกันพนักงานผี)
    6. Supply Chain & Quality Standards (ห่วงโซ่อุปทานและมาตรฐาน อย./สคบ.)
    """
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT pillar_category, COUNT(id) as total_checks,
                       SUM(CASE WHEN is_compliant = TRUE THEN 1 ELSE 0 END) as passed_checks
                FROM ipo_readiness_checkpoints
                GROUP BY pillar_category;
            """)
            pillar_stats = cursor.fetchall()

            cursor.execute("""
                SELECT checkpoint_code, checkpoint_name, pillar_category, regulatory_body,
                       target_metric, is_compliant, verification_module
                FROM ipo_readiness_checkpoints
                ORDER BY pillar_category, checkpoint_code ASC;
            """)
            all_checkpoints = cursor.fetchall()

    pillars_summary = {}
    total_score_acc = 0.0
    total_categories = len(pillar_stats)

    for p in pillar_stats:
        cat = p["pillar_category"]
        total = p["total_checks"]
        passed = p["passed_checks"]
        score = round((passed / total) * 100.0, 1) if total > 0 else 100.0
        pillars_summary[cat] = {
            "category_name": cat,
            "passed_checks": passed,
            "total_checks": total,
            "readiness_score": score,
            "status": "READY" if score >= 90.0 else "IN_PROGRESS"
        }
        total_score_acc += score

    overall_ipo_score = round(total_score_acc / total_categories, 1) if total_categories > 0 else 100.0

    return {
        "status": "success",
        "company_slug": company_slug,
        "evaluated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "overall_ipo_readiness_score": overall_ipo_score,
        "listing_eligibility": "READY_FOR_FILING_PREPARATION" if overall_ipo_score >= 85.0 else "CONDITIONAL",
        "pillars": pillars_summary,
        "checkpoints": all_checkpoints
    }
