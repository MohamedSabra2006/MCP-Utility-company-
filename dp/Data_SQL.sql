USE [Utility_Company]; -- Replace with your actual database name!
GO

-- 1. Insert Customers
INSERT INTO customers (national_id, full_name, phone_number) VALUES
(N'29901011234567', N'Ahmed Hassan', N'+201012345678'),
(N'29505121234568', N'Sara Mohamed', N'+201123456789'),
(N'28803201234569', N'El-Galaa Hospital', N'+201234567890'),
(N'29207151234570', N'Central Water Utility', N'+201098765432');

-- 2. Insert Meters (Matching format ^NC-MTR-[0-9]{5}$)
INSERT INTO meters (meter_id, customer_id, district_name, meter_type, status, is_protected) VALUES
('NC-MTR-20045', 1, N'Maadi', 'Residential', 'Active', 0),            -- Standard residential meter
('NC-MTR-30012', 2, N'Heliopolis', 'Residential', 'Active', 1),       -- Protected (Medical Exemption)
('NC-MTR-40088', 3, N'Downtown', 'Commercial', 'Active', 1),         -- Protected (Hospital)
('NC-MTR-50099', 4, N'Shoubra', 'Industrial', 'Active', 1);          -- Protected (Water Station)

-- 3. Insert Overdue Unpaid Bills
INSERT INTO bills (meter_id, billing_period, amount_egp, due_date, is_paid) VALUES
('NC-MTR-20045', '2026-04-01', 1250.50, '2026-05-01', 0),
('NC-MTR-20045', '2026-05-01', 1400.00, '2026-06-01', 0),
('NC-MTR-20045', '2026-06-01', 1350.25, '2026-07-01', 0), -- 3 unpaid bills for NC-MTR-20045
('NC-MTR-30012', '2026-05-01', 850.00, '2026-06-01', 0),  -- Unpaid, but protected!
('NC-MTR-40088', '2026-05-01', 15000.00, '2026-06-01', 0); -- Unpaid hospital, but protected!

-- 4. Insert Medical Exemption (Protects NC-MTR-30012)
INSERT INTO medical_exemptions (meter_id, medical_condition, hospital_approval_ref, expiry_date, is_active) VALUES
('NC-MTR-30012', N'Home Oxygen Concentrator Dependent', N'HOSP-REF-99201', '2027-12-31', 1);

-- 5. Insert Critical Facility (Protects NC-MTR-40088 & NC-MTR-50099)
INSERT INTO critical_facilities (meter_id, facility_name, facility_type) VALUES
('NC-MTR-40088', N'El-Galaa Emergency Wing', 'Hospital'),
('NC-MTR-50099', N'Main Nile Pumping Station #3', 'Water_Pumping_Station');