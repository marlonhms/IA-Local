import psycopg2

conn = psycopg2.connect(host='localhost', port=5435, dbname='posto', user='postgres')
cur = conn.cursor()

cur.execute("ALTER ROLE suporte WITH PASSWORD '899007' VALID UNTIL 'infinity';")
cur.execute("ALTER ROLE postgres WITH PASSWORD '123456' VALID UNTIL 'infinity';")
conn.commit()
print('Roles updated successfully with VALID UNTIL infinity!')

for t in ['tanques', 'abastecimentos', 'produtos', 'fechabomba', 'fechacaixa']:
    cur.execute(f'SELECT count(*) FROM {t};')
    print(f'{t}: {cur.fetchone()[0]} rows')

conn.close()
