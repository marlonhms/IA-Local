import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

conn = psycopg2.connect(host='localhost', port=5434, dbname='postgres', user='postgres', password='123456')
conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
cur = conn.cursor()

try:
    cur.execute("CREATE ROLE suporte WITH LOGIN PASSWORD '899007' SUPERUSER VALID UNTIL 'infinity';")
    print('Created role suporte')
except Exception as e:
    print('Role suporte:', e)

try:
    cur.execute("CREATE DATABASE posto OWNER suporte;")
    print('Created database posto')
except Exception as e:
    print('Database posto:', e)

conn.close()
