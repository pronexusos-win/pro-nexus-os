CREATE TABLE tenants (
    tenant_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    status ENUM('active', 'suspended') DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE members (
    member_id VARCHAR(50) PRIMARY KEY,
    tenant_id VARCHAR(50) NOT NULL,
    sponsor_id VARCHAR(50),
    name VARCHAR(150),
    line_user_id VARCHAR(100) UNIQUE,
    pin_hash VARCHAR(255),
    role ENUM('super_admin', 'company_admin', 'franchise', 'member') DEFAULT 'member',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id)
);

CREATE TABLE commissions (
    transaction_id VARCHAR(50) PRIMARY KEY,
    member_id VARCHAR(50) NOT NULL,
    gross_amount DECIMAL(10,2) NOT NULL,
    tax_amount DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    net_amount DECIMAL(10,2) NOT NULL,
    type ENUM('unilevel', 'affiliate', 'watch_to_earn'),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
