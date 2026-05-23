import sqlalchemy
from sqlalchemy import create_engine

urls = [
    'postgresql://postgres:pandapanding%40123@db.maoyowmvptlsgggqzero.supabase.co:5432/postgres',
    'postgresql://postgres.maoyowmvptlsgggqzero:pandapanding%40123@aws-0-ap-south-1.pooler.supabase.com:6543/postgres',
    'postgresql://postgres.maoyowmvptlsgggqzero:pandapanding%40123@aws-0-ap-south-1.pooler.supabase.com:6543/postgres?sslmode=require',
    'postgresql://postgres:pandapanding%40123@db.maoyowmvptlsgggqzero.supabase.co:5432/postgres?sslmode=require'
]

for url in urls:
    print(f'Testing: {url.split("@")[1]}')
    try:
        engine = create_engine(url, connect_args={'connect_timeout': 5})
        conn = engine.connect()
        print('SUCCESS!')
        conn.close()
    except Exception as e:
        print(f'FAILED: {type(e).__name__} - {str(e)[:100]}')
