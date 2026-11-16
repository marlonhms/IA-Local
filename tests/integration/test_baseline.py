import os
import sys
sys.path.insert(0, os.path.abspath('.'))
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from core.tools import get_erp_connection, PostoTools

sys.stdout.reconfigure(encoding='utf-8')

tools = PostoTools()
res = tools.consultar_analise_vendas_erp()
print("Teste baseline erp:", type(res))
