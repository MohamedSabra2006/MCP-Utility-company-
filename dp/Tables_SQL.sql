USE [Utility_Company]; -- Change this to your database name!
GO

-- 1. Create Customers Table
CREATE TABLE customers (
    customer_id INT IDENTITY(1,1) PRIMARY KEY,
    national_id NVARCHAR(14) NOT NULL UNIQUE,
    full_name NVARCHAR(100) NOT NULL,
    phone_number NVARCHAR(15),
    created_at DATETIME2 DEFAULT GETDATE()
);

-- 2. Create Meters Table
CREATE TABLE meters (
    meter_id NVARCHAR(20) PRIMARY KEY,
    customer_id INT FOREIGN KEY REFERENCES customers(customer_id),
    district_name NVARCHAR(50) NOT NULL,
    meter_type NVARCHAR(20) CHECK (meter_type IN ('Residential', 'Commercial', 'Industrial')),
    status NVARCHAR(20) DEFAULT 'Active' CHECK (status IN ('Active', 'Disconnected', 'Pending_Cut')),
    is_protected BIT DEFAULT 0
);

-- 3. Create Bills Table
CREATE TABLE bills (
    bill_id INT IDENTITY(1,1) PRIMARY KEY,
    meter_id NVARCHAR(20) FOREIGN KEY REFERENCES meters(meter_id),
    billing_period DATE NOT NULL,
    amount_egp DECIMAL(10,2) NOT NULL,
    due_date DATE NOT NULL,
    is_paid BIT DEFAULT 0
);

-- 4. Create Medical Exemptions Table
CREATE TABLE medical_exemptions (
    exemption_id INT IDENTITY(1,1) PRIMARY KEY,
    meter_id NVARCHAR(20) UNIQUE FOREIGN KEY REFERENCES meters(meter_id),
    medical_condition NVARCHAR(200) NOT NULL,
    hospital_approval_ref NVARCHAR(50) NOT NULL,
    expiry_date DATE NOT NULL,
    is_active BIT DEFAULT 1
);

-- 5. Create Critical Facilities Table
CREATE TABLE critical_facilities (
    facility_id INT IDENTITY(1,1) PRIMARY KEY,
    meter_id NVARCHAR(20) UNIQUE FOREIGN KEY REFERENCES meters(meter_id),
    facility_name NVARCHAR(100) NOT NULL,
    facility_type NVARCHAR(50) CHECK (facility_type IN ('Hospital', 'Water_Pumping_Station', 'Emergency_Services'))
);

-- 6. Create Disconnection Tickets Table
CREATE TABLE disconnection_tickets (
    ticket_id INT IDENTITY(1,1) PRIMARY KEY,
    meter_id NVARCHAR(20) FOREIGN KEY REFERENCES meters(meter_id),
    requested_by NVARCHAR(50) NOT NULL,
    status NVARCHAR(20) DEFAULT 'Pending_Approval',
    requires_elicitation BIT DEFAULT 0,
    supervisor_override_code NVARCHAR(50) NULL,
    created_at DATETIME2 DEFAULT GETDATE()
);