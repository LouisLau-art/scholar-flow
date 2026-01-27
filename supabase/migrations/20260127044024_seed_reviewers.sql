-- 插入 Mock 审稿人数据
-- 注意：在生产环境这些数据应由 Auth 系统生成
INSERT INTO auth.users (id, email, raw_user_meta_data) VALUES 
(gen_random_uuid(), 'reviewer1@example.com', '{"domains": ["AI", "NLP"]}'::jsonb),
(gen_random_uuid(), 'reviewer2@example.com', '{"domains": ["Machine Learning", "Computer Vision"]}'::jsonb),
(gen_random_uuid(), 'reviewer3@example.com', '{"domains": ["Blockchain", "Security"]}'::jsonb)
ON CONFLICT DO NOTHING;

