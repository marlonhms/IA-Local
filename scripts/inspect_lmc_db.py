import psycopg2
from psycopg2.extras import RealDictCursor

conn = psycopg2.connect(host='localhost', port=5435, dbname='posto', user='suporte', password='899007')
cur = conn.cursor(cursor_factory=RealDictCursor)

for table in ['tanques', 'abastecimentos', 'produtos', 'tanque_medida_manual', 'fechabomba']:
    cur.execute(f"""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = '{table}'
        ORDER BY ordinal_position;
    """)
    cols = [f"{r['column_name']} ({r['data_type']})" for r in cur.fetchall()]
    print(f'=== {table} ===')
    print(', '.join(cols[:20]))
    print(', '.join(cols[20:40]))
    if len(cols) > 40:
        print(', '.join(cols[40:]))

print('\n=== Sample tanques ===')
cur.execute("SELECT * FROM tanques LIMIT 3;")
for r in cur.fetchall():
    print(dict(r))

print('\n=== Sample abastecimentos ===')
cur.execute("SELECT a.controle, a.data, a.hora, a.bomba, a.tanque, a.codpro, a.litros, a.total FROM abastecimentos a LIMIT 3;")
for r in cur.fetchall():
    print(dict(r))

print('\n=== Sample tanque_medida_manual (if any) ===')
try:
    cur.execute("SELECT * FROM tanque_medida_manual LIMIT 3;")
    print(cur.fetchall())
except Exception as e:
    print('tanque_medida_manual error:', e)

conn.close()
