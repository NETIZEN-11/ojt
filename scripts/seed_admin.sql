-- Insert admin user
INSERT INTO users (id, email, username, hashed_password, full_name, is_active, is_superuser, created_at, updated_at)
VALUES (
  'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11'::uuid,
  'admin@redteam.local',
  'admin',
  '$2b$12$RIoIKqyY/1vlm5918JUQNuAhVMLnT3oyWxJ7qLni1ROlzaVjfEPgG',
  'Admin User',
  true,
  true,
  NOW(),
  NOW()
) ON CONFLICT (email) DO NOTHING;

SELECT 'Admin user created successfully' as message;
