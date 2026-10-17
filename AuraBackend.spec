# -*- mode: python ; coding: utf-8 -*-
"""
AuraBackend.spec - Especificacao PyInstaller para Distribuicao Standalone da AURA (Fase 8).
Empacota a AURA em modo --onedir para inicializacao instantanea (< 1s) como servico nativo
do Windows SCM (AuraBackendService) ou executavel de console, sem dependencia de Python no posto.
Regra inegociavel: ZERO travessoes em todo o arquivo.
"""

import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

BASE_DIR = os.path.abspath(SPECPATH if 'SPECPATH' in globals() else '.')

hiddenimports = [
    # Windows SCM & Win32 native APIs
    'win32service',
    'win32serviceutil',
    'win32event',
    'servicemanager',
    'win32con',

    # ASGI & Uvicorn runtime
    'uvicorn',
    'uvicorn.logging',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.websockets',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.lifespan',
    'uvicorn.lifespan.on',

    # Web Framework & Data Validation
    'fastapi',
    'fastapi.responses',
    'fastapi.staticfiles',
    'fastapi.middleware.cors',
    'starlette',
    'starlette.responses',
    'starlette.staticfiles',
    'pydantic',
    'pydantic_core',
    'dotenv',

    # Database Drivers & Tools
    'psycopg2',
    'psycopg2.extensions',
    'psycopg2.extras',
    'sqlite3',
    'sqlglot',
    'sqlglot.dialects',
    'sqlglot.dialects.postgres',

    # LLM & AI
    'google.generativeai',

    # Core Architecture Modules
    'core.service',
    'core.identity_vault',
    'core.resource_watchdog',
    'core.desktop_notifier',
    'core.outbox',
    'core.command_journal',
    'core.aura_api',
    'core.aura_engine',
    'core.semantic_router',
    'core.rag_engine',
    'core.tools',
    'core.db_pool',
    'core.tenancy',
    'core.backup_manager',
    'core.compliance_manager',
    'core.watchdog',
    'core.proactive_daemon',
    'core.migrations',
    'core.cdc_listener',
    'core.webhook_dispatcher',
    'core.webhooks',
    'core.telemetry',
    'core.logger',
    'core.sanitizer',
    'core.installer_wizard',
    'core.schemas',
    'core.schemas.genui',
    'core.schemas.compliance',
    'core.domain',
    'core.domain.sales',
    'core.domain.tanks',
    'core.domain.pumps',
    'core.domain.cashier',
    'core.adapters',
    'core.adapters.erp',
    'core.adapters.erp.base',
    'core.adapters.erp.mock_adapter',
    'core.adapters.erp.postgres_local_adapter',
    'core.adapters.erp.yaml_data_mapper',
    'config.settings',
]

# Coleta submodulos essenciais
hiddenimports += collect_submodules('core')
hiddenimports += collect_submodules('sqlglot')

# Assets estaticos e configuracoes para distribuicao
datas = [
    ('web', 'web'),
    ('config/erp_mappings', 'config/erp_mappings'),
]

if os.path.exists('alembic'):
    datas.append(('alembic', 'alembic'))
if os.path.exists('.env.example'):
    datas.append(('.env.example', '.'))

# Deduplica lista de modulos ocultos
hiddenimports = sorted(list(set(hiddenimports)))

a = Analysis(
    ['server.py'],
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'scipy', 'IPython', 'pytest', 'unittest'],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='AuraBackend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AuraBackend',
)
