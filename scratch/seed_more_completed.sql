DO $$
DECLARE
    v_cust_id uuid := '10730c16-21cb-422d-ab72-6175ca66b381';
    v_tech_id uuid := '5833de36-6c7c-4c1d-8d8f-64b061e07cb8';
    v_dev1_id uuid := 'bf3adc74-c512-4eaa-ae63-49fff6149f48';
    v_dev2_id uuid := '5df701bc-5283-43f2-8210-0e68c5dd83ab';
    v_svc1_id uuid := '76839d2a-a4e6-4827-b5a7-17d294e129ef';
    v_svc2_id uuid := '9d17136c-1458-4697-b8f6-f7f42fc5edab';
    v_appt3_id uuid := gen_random_uuid();
    v_appt4_id uuid := gen_random_uuid();
BEGIN
    INSERT INTO appointment (id, appointment_number, appointment_date, status, customer_id, technician_id, device_id, total_amount, created_at)
    VALUES (v_appt3_id, 'APPT-20261103-C303', '2026-11-03 10:00:00+00', 'COMPLETED', v_cust_id, v_tech_id, v_dev1_id, 450000, '2026-11-03 09:00:00+00')
    ON CONFLICT (appointment_number) DO NOTHING;

    INSERT INTO appointment_service (id, appointment_id, service_id, price_at_booking, quantity)
    VALUES (gen_random_uuid(), v_appt3_id, v_svc1_id, 450000, 1)
    ON CONFLICT DO NOTHING;

    INSERT INTO appointment (id, appointment_number, appointment_date, status, customer_id, technician_id, device_id, total_amount, created_at)
    VALUES (v_appt4_id, 'APPT-20261029-D404', '2026-10-29 15:30:00+00', 'COMPLETED', v_cust_id, v_tech_id, v_dev2_id, 650000, '2026-10-29 14:00:00+00')
    ON CONFLICT (appointment_number) DO NOTHING;

    INSERT INTO appointment_service (id, appointment_id, service_id, price_at_booking, quantity)
    VALUES (gen_random_uuid(), v_appt4_id, v_svc2_id, 650000, 1)
    ON CONFLICT DO NOTHING;
END $$;

