import sys
import os

# เพิ่ม Root path เพื่อให้อิมพอร์ต backend ได้
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.app.core.database import get_db_connection

DDL_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        line_user_id VARCHAR(64) NOT NULL,
        company_slug ENUM('pro_nexus', 'tp_extra', 'luck_kio', 'peak_icon') NOT NULL,
        display_name VARCHAR(255) NOT NULL,
        picture_url TEXT NULL,
        role ENUM('superadmin', 'admin', 'staff', 'member') DEFAULT 'member',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE KEY uk_company_line (company_slug, line_user_id),
        INDEX idx_company_role (company_slug, role)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """,
    """
    CREATE TABLE IF NOT EXISTS slips (
        id INT AUTO_INCREMENT PRIMARY KEY,
        company_slug ENUM('pro_nexus', 'tp_extra', 'luck_kio', 'peak_icon') NOT NULL,
        line_user_id VARCHAR(64) NOT NULL,
        image_url TEXT NOT NULL,
        trans_amount DECIMAL(10, 2) NULL,
        trans_date VARCHAR(20) NULL,
        trans_time VARCHAR(20) NULL,
        sender_bank VARCHAR(50) NULL,
        receiver_bank VARCHAR(50) NULL,
        receiver_account VARCHAR(50) NULL,
        raw_ocr_data JSON NULL,
        verification_status ENUM('pending', 'verified', 'rejected') DEFAULT 'pending',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_company_status (company_slug, verification_status),
        INDEX idx_line_user (line_user_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """,
    """
    CREATE TABLE IF NOT EXISTS orders (
        id INT AUTO_INCREMENT PRIMARY KEY,
        order_no VARCHAR(64) NOT NULL UNIQUE,
        company_slug ENUM('pro_nexus', 'tp_extra', 'luck_kio', 'peak_icon') NOT NULL DEFAULT 'tp_extra',
        line_user_id VARCHAR(64) NOT NULL,
        total_amount DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
        status ENUM('pending_payment', 'paid', 'shipping', 'completed', 'cancelled') DEFAULT 'pending_payment',
        slip_id INT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        CONSTRAINT fk_orders_slip FOREIGN KEY (slip_id) REFERENCES slips (id) ON DELETE SET NULL,
        INDEX idx_company_status (company_slug, status),
        INDEX idx_line_user (line_user_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """
]

def run_migrations():
    print("🚀 เริ่มต้นรัน Migration ตารางฐานข้อมูล...")
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                for statement in DDL_STATEMENTS:
                    cursor.execute(statement)
            conn.commit()
        print("✅ สร้างตาราง users, slips, และ orders สำเร็จเรียบร้อยแล้ว!")
    except Exception as e:
        print(f"❌ Migration ล้มเหลว: {e}")

if __name__ == "__main__":
    run_migrations()
