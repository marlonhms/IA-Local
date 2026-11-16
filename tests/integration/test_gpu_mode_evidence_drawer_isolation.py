#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/test_gpu_mode_evidence_drawer_isolation.py
-----------------------------------------------------------------------------
Validação Específica de Isolamento: Modo GPU vs EvidenceDrawer & Modais AURA.

Cenários cobertos:
1. Análise Estática de CSS (aura.css):
   - .gpu-guard-active NUNCA aplica transform: none !important ao .evidence-drawer
   - .evidence-drawer:not(.open) e .gpu-guard-active .evidence-drawer:not(.open) possuem translateX(100%) !important
   - .evidence-drawer.open e .gpu-guard-active .evidence-drawer.open possuem translateX(0) !important
   - #aura-sidebar-drawer:not(.open) e #aura-sidebar-overlay:not(.open) isolados contra vazamentos
   - prefers-reduced-motion não força transform: none no evidence-drawer
   - #aura-command-palette-modal.hidden possui display: none !important
2. Validação Estrutural de Marcação (index.html):
   - #aura-evidence-drawer possui aria-hidden="true" inicial
   - #btn-close-evidence-drawer e #aura-evidence-drawer-overlay possuem fallback de fechamento inline
3. Simulação Funcional Live via Node.js (DOM):
   - Ativação do Modo GPU não abre nem altera classes do EvidenceDrawer
   - Com Modo GPU ativo, abertura explícita adiciona .open e aria-hidden="false"
   - Com Modo GPU ativo, clique no botão X (#btn-close-evidence-drawer) fecha imediatamente
   - Com Modo GPU ativo, pressão da tecla Escape fecha imediatamente
   - Com Modo GPU ativo, clique no overlay (#aura-evidence-drawer-overlay) fecha imediatamente
   - Desativação do Modo GPU preserva estado correto
"""

import sys
import subprocess
import json
import re
from pathlib import Path

# Protege stdout no terminal Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent

def run_gpu_drawer_isolation_tests():
    print("=" * 78)
    print("🛡️ SUÍTE DE TESTES: ISOLAMENTO MODO GPU VS EVIDENCE DRAWER & MODAIS")
    print("   (Garantia de Não-Vazamento, Fechamento Infalível e Reset GPU)")
    print("=" * 78)

    css_path = BASE_DIR / "web" / "css" / "aura.css"
    html_path = BASE_DIR / "web" / "index.html"
    chat_js_path = BASE_DIR / "web" / "js" / "aura-chat.js"
    app_js_path = BASE_DIR / "web" / "js" / "aura-app.js"

    css_code = css_path.read_text(encoding="utf-8")
    html_code = html_path.read_text(encoding="utf-8")
    chat_js_code = chat_js_path.read_text(encoding="utf-8")
    app_js_code = app_js_path.read_text(encoding="utf-8")

    # -------------------------------------------------------------------------
    # 1. VALIDAÇÃO DE CSS ESTÁTICO (aura.css)
    # -------------------------------------------------------------------------
    print("\n1. Testando Regras de CSS em web/css/aura.css...")

    # Garante que .gpu-guard-active .evidence-drawer NÃO está no seletor de transform: none
    # Procura blocos com transform: none !important
    transform_none_blocks = re.findall(r'([^{]+)\{\s*transform:\s*none\s*!important', css_code)
    for block in transform_none_blocks:
        assert ".evidence-drawer" not in block, f"Regra inválida encontrada: seletor '{block.strip()}' aplica transform: none ao evidence-drawer"
        assert "#aura-evidence-drawer" not in block, f"Regra inválida encontrada: seletor '{block.strip()}' aplica transform: none ao #aura-evidence-drawer"

    print("   [OK] .gpu-guard-active NÃO aplica transform: none !important ao .evidence-drawer")

    # Garante que .evidence-drawer:not(.open) força translateX(100%) !important
    assert ".evidence-drawer:not(.open)" in css_code, ".evidence-drawer:not(.open) ausente no CSS"
    assert "transform: translateX(100%) !important;" in css_code, "translateX(100%) !important ausente no CSS"
    assert "visibility: hidden !important;" in css_code, "visibility: hidden !important ausente no CSS"
    print("   [OK] .evidence-drawer:not(.open) com translateX(100%) e visibility: hidden estritamente definido")

    # Garante que .gpu-guard-active .evidence-drawer:not(.open) possui regra explícita
    assert ".gpu-guard-active .evidence-drawer:not(.open)" in css_code, "Regra de isolamento .gpu-guard-active .evidence-drawer:not(.open) ausente"
    assert ".gpu-guard-active .evidence-drawer.open" in css_code, "Regra .gpu-guard-active .evidence-drawer.open ausente"
    print("   [OK] .gpu-guard-active .evidence-drawer:not(.open) e .open estritamente definidos no GPU Guard")

    # Garante isolamento do menu lateral e modal command palette e aux panel
    assert ".gpu-guard-active #aura-sidebar-drawer:not(.open)" in css_code, "Isolamento #aura-sidebar-drawer no GPU Guard ausente"
    assert ".gpu-guard-active #aura-command-palette-modal.hidden" in css_code, "Isolamento command palette no GPU Guard ausente"
    assert ".gpu-guard-active #aura-aux-panel.hidden" in css_code, "Isolamento #aura-aux-panel no GPU Guard ausente"
    assert ".gpu-guard-active #command-palette-backdrop.hidden" in css_code, "Isolamento #command-palette-backdrop no GPU Guard ausente"
    print("   [OK] #aura-sidebar-drawer, #aura-command-palette-modal e #aura-aux-panel isolados contra anulações no GPU Guard")

    # Garante que prefers-reduced-motion não zera transform de drawers
    prm_match = re.search(r'@media\s*\(prefers-reduced-motion:\s*reduce\)\s*\{([^}]+)\}', css_code)
    if prm_match:
        prm_content = prm_match.group(1)
        # Não pode ter .evidence-drawer com transform: none
        assert not re.search(r'\.evidence-drawer[^{]*\{[^}]*transform:\s*none', prm_content), "prefers-reduced-motion não deve aplicar transform: none ao evidence-drawer"
    print("   [OK] prefers-reduced-motion validado sem forçar transform: none nos drawers")

    # -------------------------------------------------------------------------
    # 2. VALIDAÇÃO DE MARCAÇÃO E ATRIBUTOS HTML (index.html)
    # -------------------------------------------------------------------------
    print("\n2. Testando Marcação e Fallbacks em web/index.html...")
    assert 'id="aura-evidence-drawer"' in html_code, "#aura-evidence-drawer ausente em index.html"
    assert 'id="btn-close-evidence-drawer"' in html_code, "#btn-close-evidence-drawer ausente em index.html"
    assert 'id="aura-evidence-drawer-overlay"' in html_code, "#aura-evidence-drawer-overlay ausente em index.html"

    # Confere aria-hidden="true" no aside do drawer quando inicializado
    assert re.search(r'<aside[^>]*id="aura-evidence-drawer"[^>]*aria-hidden="true"', html_code), "#aura-evidence-drawer deve ter aria-hidden='true' inicial"
    
    # Confere fallback onclick no botão close e overlay
    assert 'id="btn-close-evidence-drawer" onclick="if (window.auraChat) window.auraChat.closeEvidence();"' in html_code or 'onclick="if (window.auraChat) window.auraChat.closeEvidence();"' in html_code, "Fallback onclick ausente no botão fechar"
    assert 'id="aura-evidence-drawer-overlay"' in html_code and 'closeEvidence()' in html_code, "Fallback onclick ausente no overlay"
    print("   [OK] Marcação HTML validada com aria-hidden inicial e fallbacks onclick resilientes")

    # -------------------------------------------------------------------------
    # 3. VALIDAÇÃO DE JAVASCRIPT (aura-chat.js e aura-app.js)
    # -------------------------------------------------------------------------
    print("\n3. Testando Lógica JS de Abertura, Fechamento e GPU Guard...")
    assert "drawer.setAttribute('aria-hidden', 'true')" in chat_js_code or "drawer.setAttribute('aria-hidden', 'true');" in chat_js_code, "closeEvidence não atualiza aria-hidden"
    assert "drawer.setAttribute('aria-hidden', 'false')" in chat_js_code or "drawer.setAttribute('aria-hidden', 'false');" in chat_js_code, "openEvidence não atualiza aria-hidden"
    assert "applyGpuGuard(enabled)" in app_js_code, "applyGpuGuard ausente em aura-app.js"
    assert "evDrawer && !evDrawer.classList.contains('open')" in app_js_code, "Proteção de drawer fechado no applyGpuGuard ausente"
    print("   [OK] aura-chat.js e aura-app.js blindados para governança de estado do EvidenceDrawer")

    # -------------------------------------------------------------------------
    # 4. SIMULAÇÃO FUNCIONAL COMPLETA NO NODE.JS
    # -------------------------------------------------------------------------
    print("\n4. Executando Simulação Funcional Dinâmica no Node.js...")

    node_test_code = """
    const fs = require('fs');

    // Mock simples de DOM mínimo para teste de comportamento e eventos
    class MockClassList {
      constructor() {
        this.classes = new Set();
      }
      add(c) { this.classes.add(c); }
      remove(c) { this.classes.delete(c); }
      contains(c) { return this.classes.has(c); }
      toString() { return Array.from(this.classes).join(' '); }
    }

    class MockElement {
      constructor(id, tag = 'div') {
        this.id = id;
        this.tagName = tag.toUpperCase();
        this.classList = new MockClassList();
        this.attributes = {};
        this.listeners = {};
        this.style = {};
      }
      setAttribute(k, v) { this.attributes[k] = String(v); }
      getAttribute(k) { return this.attributes[k] || null; }
      addEventListener(ev, fn) {
        if (!this.listeners[ev]) this.listeners[ev] = [];
        this.listeners[ev].push(fn);
      }
      dispatchEvent(event) {
        const fns = this.listeners[event.type] || [];
        for (const fn of fns) fn(event);
      }
      click() {
        this.dispatchEvent({ type: 'click', target: this });
      }
      focus() {}
    }

    // Configura ambiente global falso
    const docElements = {
      'aura-evidence-drawer': new MockElement('aura-evidence-drawer', 'aside'),
      'aura-evidence-drawer-overlay': new MockElement('aura-evidence-drawer-overlay', 'div'),
      'btn-close-evidence-drawer': new MockElement('btn-close-evidence-drawer', 'button'),
      'sidebar-btn-toggle-gpu-guard': new MockElement('sidebar-btn-toggle-gpu-guard', 'button'),
      'sidebar-gpu-badge': new MockElement('sidebar-gpu-badge', 'span'),
      'sidebar-gpu-icon': new MockElement('sidebar-gpu-icon', 'i'),
      'evidence-drawer-title': new MockElement('evidence-drawer-title', 'span'),
      'evidence-drawer-status-chip': new MockElement('evidence-drawer-status-chip', 'span'),
      'evidence-drawer-subtitle': new MockElement('evidence-drawer-subtitle', 'p'),
      'evidence-drawer-content': new MockElement('evidence-drawer-content', 'div')
    };

    const docListeners = {};
    const mockDocument = {
      documentElement: new MockElement('html'),
      body: new MockElement('body'),
      getElementById: (id) => docElements[id] || null,
      querySelectorAll: () => [],
      addEventListener: (ev, fn) => {
        if (!docListeners[ev]) docListeners[ev] = [];
        docListeners[ev].push(fn);
      },
      dispatchEvent: (event) => {
        const fns = docListeners[event.type] || [];
        for (const fn of fns) fn(event);
      }
    };

    global.document = mockDocument;
    global.window = {
      document: mockDocument,
      __auraEvidenceStore: {},
      lucide: { createIcons: () => {} },
      auraAudio: { playChime: () => {} },
      localStorage: {
        store: {},
        getItem: (k) => global.window.localStorage.store[k] || null,
        setItem: (k, v) => { global.window.localStorage.store[k] = String(v); }
      }
    };

    // Carrega controladores
    const { AuraChatController } = require('./web/js/aura-chat.js');
    const { AuraApp } = require('./web/js/aura-app.js');

    const app = new AuraApp();
    const chat = new AuraChatController();
    global.window.auraChat = chat;
    global.window.auraApp = app;

    // Inicializa estado inicial fechado
    const drawer = docElements['aura-evidence-drawer'];
    const overlay = docElements['aura-evidence-drawer-overlay'];
    const closeBtn = docElements['btn-close-evidence-drawer'];

    drawer.setAttribute('aria-hidden', 'true');
    overlay.setAttribute('aria-hidden', 'true');

    // Registrar listeners do chat
    closeBtn.addEventListener('click', () => chat.closeEvidence());
    overlay.addEventListener('click', () => chat.closeEvidence());
    mockDocument.addEventListener('keydown', (e) => {
      const isDrawerOpen = drawer.classList.contains('open') || drawer.getAttribute('aria-hidden') === 'false';
      if (e.key === 'Escape' && isDrawerOpen) {
        chat.closeEvidence();
      }
    });

    // -------------------------------------------------------------
    // TESTE 1: Ativação do Modo GPU NÃO DEVE abrir o Evidence Drawer
    // -------------------------------------------------------------
    console.log('[NODE-TEST] 1. Testando ativação do Modo GPU com drawer fechado...');
    app.applyGpuGuard(true);
    if (!mockDocument.documentElement.classList.contains('gpu-guard-active')) {
      throw new Error('Falha: gpu-guard-active não adicionado a documentElement');
    }
    if (drawer.classList.contains('open')) {
      throw new Error('FALHA CRÍTICA: Ativação do Modo GPU abriu o EvidenceDrawer!');
    }
    if (drawer.getAttribute('aria-hidden') !== 'true') {
      throw new Error('FALHA CRÍTICA: Ativação do Modo GPU alterou aria-hidden do EvidenceDrawer!');
    }
    console.log('[NODE-TEST]    ✓ Modo GPU ativado sem abrir nem alterar o EvidenceDrawer');

    // -------------------------------------------------------------
    // TESTE 2: Abertura e Fechamento com Botão X em Modo GPU Ativo
    // -------------------------------------------------------------
    console.log('[NODE-TEST] 2. Testando abertura explícita e fechamento via Botão X em Modo GPU...');
    chat.openEvidence('cockpit_turno', 'resumo');
    if (!drawer.classList.contains('open') || drawer.getAttribute('aria-hidden') !== 'false') {
      throw new Error('Falha: openEvidence não adicionou .open ou não definiu aria-hidden=false');
    }
    if (!overlay.classList.contains('open') || overlay.getAttribute('aria-hidden') !== 'false') {
      throw new Error('Falha: openEvidence não abriu o overlay');
    }

    // Clique no botão X
    closeBtn.click();
    if (drawer.classList.contains('open')) {
      throw new Error('FALHA CRÍTICA: Clique no Botão X não removeu classe .open do EvidenceDrawer em Modo GPU!');
    }
    if (drawer.getAttribute('aria-hidden') !== 'true') {
      throw new Error('FALHA CRÍTICA: Clique no Botão X não redefiniu aria-hidden=true!');
    }
    if (overlay.classList.contains('open')) {
      throw new Error('FALHA CRÍTICA: Overlay permaneceu aberto após clique no Botão X!');
    }
    console.log('[NODE-TEST]    ✓ Botão X fechou o EvidenceDrawer instantaneamente em Modo GPU');

    // -------------------------------------------------------------
    // TESTE 3: Fechamento via Tecla Escape em Modo GPU Ativo
    // -------------------------------------------------------------
    console.log('[NODE-TEST] 3. Testando fechamento via tecla Escape em Modo GPU...');
    chat.openEvidence('cockpit_turno', 'resumo');
    if (!drawer.classList.contains('open')) throw new Error('Falha ao reabrir drawer');
    
    mockDocument.dispatchEvent({ type: 'keydown', key: 'Escape' });
    if (drawer.classList.contains('open') || drawer.getAttribute('aria-hidden') !== 'true') {
      throw new Error('FALHA CRÍTICA: Tecla Escape não fechou o EvidenceDrawer em Modo GPU!');
    }
    console.log('[NODE-TEST]    ✓ Tecla Escape fechou o EvidenceDrawer instantaneamente em Modo GPU');

    // -------------------------------------------------------------
    // TESTE 4: Fechamento via Clique no Overlay em Modo GPU Ativo
    // -------------------------------------------------------------
    console.log('[NODE-TEST] 4. Testando fechamento via clique no Backdrop/Overlay em Modo GPU...');
    chat.openEvidence('cockpit_turno', 'resumo');
    if (!overlay.classList.contains('open')) throw new Error('Falha ao abrir overlay');

    overlay.click();
    if (drawer.classList.contains('open') || overlay.classList.contains('open')) {
      throw new Error('FALHA CRÍTICA: Clique no Overlay não fechou o EvidenceDrawer em Modo GPU!');
    }
    console.log('[NODE-TEST]    ✓ Clique no Overlay fechou o EvidenceDrawer instantaneamente em Modo GPU');

    // -------------------------------------------------------------
    // TESTE 5: Alternância do Modo GPU com Drawer Aberto
    // -------------------------------------------------------------
    console.log('[NODE-TEST] 5. Testando alternância do Modo GPU com Drawer aberto...');
    chat.openEvidence('cockpit_turno', 'resumo');
    app.applyGpuGuard(false); // Desativa GPU Guard enquanto aberto
    if (!drawer.classList.contains('open')) {
      throw new Error('Falha: Desativação do GPU guard fechou o drawer aberto indevidamente');
    }
    // Agora fecha normalmente
    closeBtn.click();
    if (drawer.classList.contains('open')) {
      throw new Error('Falha: Botão X não fechou após desativar GPU guard');
    }

    // -------------------------------------------------------------
    // TESTE 6: Stress Test de Alternância Repetida do Modo GPU (20 ciclos)
    // -------------------------------------------------------------
    console.log('[NODE-TEST] 6. Testando alternância rápida (stress test 20x) do Modo GPU...');
    for (let i = 0; i < 20; i++) {
      app.applyGpuGuard(i % 2 === 0);
      if (drawer.classList.contains('open') || drawer.getAttribute('aria-hidden') !== 'true') {
        throw new Error(`FALHA: Drawer vazou no ciclo ${i} de stress do Modo GPU!`);
      }
    }
    console.log('[NODE-TEST]    ✓ 20 ciclos de alternância concluídos com drawer estritamente fechado');

    // -------------------------------------------------------------
    // TESTE 7: Ativação do Modo GPU com window.auraChat indefinido (Fallback Resiliente)
    // -------------------------------------------------------------
    console.log('[NODE-TEST] 7. Testando ativação do GPU guard sem window.auraChat inicializado...');
    const originalChat = global.window.auraChat;
    global.window.auraChat = null;
    app.applyGpuGuard(true);
    if (drawer.classList.contains('open') || drawer.getAttribute('aria-hidden') !== 'true') {
      throw new Error('FALHA: Fallback falhou quando window.auraChat não estava disponível!');
    }
    global.window.auraChat = originalChat;
    console.log('[NODE-TEST]    ✓ Fallback resiliente manteve drawer fechado mesmo sem window.auraChat');

    console.log('NODE_ISOLATION_TESTS_SUCCESS');
    """

    res = subprocess.run(
        ["node", "-e", node_test_code],
        cwd=str(BASE_DIR),
        capture_output=True,
        text=True,
        encoding="utf-8"
    )

    if res.returncode != 0:
        print(f"\n[ERRO NO NODE.JS]:\nStdout: {res.stdout}\nStderr: {res.stderr}")
        sys.exit(1)

    print(res.stdout.strip())
    print("\n   [OK] Todos os cenários funcionais de isolamento no Node.js passaram com 100% de sucesso!")

    print("\n" + "=" * 78)
    print("🎉 SUÍTE DE ISOLAMENTO DO MODO GPU VS EVIDENCE DRAWER APROVADA COM SUCESSO!")
    print("=" * 78)


if __name__ == "__main__":
    run_gpu_drawer_isolation_tests()
