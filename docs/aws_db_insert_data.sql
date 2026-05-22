USE `physician_portal`;

-- 1. Insert ICD9 Codes
INSERT INTO `icd9_codes` (`icd9_code`, `description`) VALUES
('250.00', 'Diabetes mellitus without mention of complication, type II or unspecified type, not stated as uncontrolled'),
('401.9', 'Unspecified essential hypertension'),
('493.90', 'Asthma, unspecified type, unspecified'),
('272.4', 'Other and unspecified hyperlipidemia'),
('V70.0', 'Routine general medical examination at a health care facility');

-- 2. Insert Patients
INSERT INTO `patients` (`patient_id`, `member_number`, `first_name`, `last_name`, `dob`, `gender`, `phone`, `email`) VALUES
(1, 'MEM-0001', 'John', 'Doe', '1980-05-15', 'Male', '555-0101', 'john.doe@example.com'),
(2, 'MEM-0002', 'Jane', 'Smith', '1975-08-22', 'Female', '555-0102', 'jane.smith@example.com'),
(3, 'MEM-0003', 'Robert', 'Johnson', '1962-11-03', 'Male', '555-0103', 'robert.j@example.com'),
(4, 'MEM-0004', 'Emily', 'Davis', '1990-02-14', 'Female', '555-0104', 'emily.davis@example.com'),
(5, 'MEM-0005', 'Michael', 'Wilson', '1985-09-30', 'Male', '555-0105', 'm.wilson@example.com');

-- 3. Insert Physicians
INSERT INTO `physicians` (`physician_id`, `npi`, `first_name`, `last_name`, `specialty`, `phone`) VALUES
(1, 'NPI-1001', 'Sarah', 'Connor', 'Internal Medicine', '555-0201'),
(2, 'NPI-1002', 'Gregory', 'House', 'Diagnostic Medicine', '555-0202'),
(3, 'NPI-1003', 'Miranda', 'Bailey', 'General Surgery', '555-0203');

-- 4. Insert Allergies (References patients)
INSERT INTO `allergies` (`allergy_id`, `patient_id`, `allergen_name`, `reaction`, `severity`, `status`, `recorded_date`) VALUES
(1, 1, 'Penicillin', 'Hives', 'Moderate', 'ACTIVE', '2023-01-10'),
(2, 2, 'Peanuts', 'Anaphylaxis', 'Severe', 'ACTIVE', '2023-02-15'),
(3, 3, 'Latex', 'Skin Rash', 'Mild', 'ACTIVE', '2023-03-20'),
(4, 1, 'Dust Mites', 'Sneezing', 'Mild', 'ACTIVE', '2023-04-05');

-- 5. Insert Caremaps (References patients, icd9_codes)
INSERT INTO `caremaps` (`caremap_id`, `patient_id`, `primary_icd9_code`, `title`, `status`, `start_date`, `end_date`, `steps_json`) VALUES
(1, 1, '250.00', 'Type II Diabetes Management', 'ACTIVE', '2023-10-01', '2024-10-01', '{"goal": "Maintain A1C below 7.0"}'),
(2, 3, '401.9', 'Hypertension Control Protocol', 'ACTIVE', '2023-11-15', '2024-11-15', '{"goal": "Maintain BP below 130/80"}'),
(3, 4, '493.90', 'Asthma Action Plan', 'COMPLETED', '2023-01-01', '2023-12-31', '{"goal": "Zero emergency visits"}');

-- 6. Insert Caremap Steps (References caremaps)
INSERT INTO `caremap_steps` (`caremap_step_id`, `caremap_id`, `step_number`, `step_name`, `due_date`, `completed_date`, `status`, `notes`) VALUES
(1, 1, 1, 'Initial A1C Lab Test', '2023-10-15', '2023-10-12', 'COMPLETED', 'A1C was 7.8'),
(2, 1, 2, 'Dietary Consultation', '2023-11-15', NULL, 'PENDING', 'Scheduled for next week'),
(3, 1, 3, 'Follow-up A1C Lab Test', '2024-01-15', NULL, 'PENDING', NULL),
(4, 2, 1, 'Baseline Blood Pressure Check', '2023-11-20', '2023-11-20', 'COMPLETED', 'BP was 145/90'),
(5, 2, 2, 'Start Lisinopril 10mg', '2023-11-21', '2023-11-21', 'COMPLETED', 'Prescription filled'),
(6, 2, 3, 'Two-week BP Recheck', '2023-12-05', NULL, 'PENDING', NULL);

-- 7. Insert Appointments (References patients, physicians)
INSERT INTO `appointments` (`appointment_id`, `patient_id`, `physician_id`, `appointment_datetime`, `status`, `reason`) VALUES
(1, 1, 1, '2023-10-10 09:00:00', 'COMPLETED', 'Annual Physical'),
(2, 1, 1, '2023-11-15 10:30:00', 'SCHEDULED', 'Diabetes Follow-up'),
(3, 2, 2, '2023-10-20 14:00:00', 'COMPLETED', 'Diagnostic Consult'),
(4, 3, 1, '2023-11-20 11:00:00', 'COMPLETED', 'Hypertension Follow-up'),
(5, 4, 3, '2023-12-01 15:30:00', 'SCHEDULED', 'Surgical Consult'),
(6, 5, 1, '2023-12-10 09:30:00', 'CANCELED', 'Routine Checkup');
