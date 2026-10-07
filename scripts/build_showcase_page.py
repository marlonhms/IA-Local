"""
Gerador da Página de Apresentação e Showcase Executivo AURA (web/showcase.html)
Atualizado com Cockpit Holográfico Executivo, Acabamento Obsidian Premium (Zero Edge Glow de IA),
Mini Gráficos & Dashboards Animados ao Scroll em ROI, Gestão de Custo de IA (Harness.io)
e Grafo de Conhecimento Operacional (Knowledge Graph de 3 Colunas).
"""

from pathlib import Path

def generate_showcase_html():
    html = """<!DOCTYPE html>
<html lang="pt-BR" class="scroll-smooth">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
  <meta name="theme-color" content="#07090e">
  <title>AURA // Apresentação & Showcase Executivo (Simulação Autônoma em Tempo Real)</title>
  <link rel="icon" type="image/svg+xml" href="/favicon.ico">

  <!-- Tailwind CSS CDN -->
  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    tailwind.config = {
      darkMode: 'class',
      theme: {
        extend: {
          colors: {
            obsidian: '#07090e',
            obsidianDeep: '#0b0e14',
            slateSurface: '#0e121b',
            slateCard: '#111622',
            auraEmerald: {
              DEFAULT: '#10b981',
              light: '#34d399',
              dark: '#047857'
            },
            auraCyan: {
              DEFAULT: '#06b6d4',
              light: '#22d3ee',
              dark: '#0891b2'
            },
            auraPurple: {
              DEFAULT: '#7c3aed',
              light: '#a855f7',
              dark: '#581c87'
            }
          }
        }
      }
    }
  </script>

  <!-- Lucide Icons -->
  <script src="https://unpkg.com/lucide@latest"></script>

  <!-- Folha de Estilos Oficial do Design System AURA -->
  <link rel="stylesheet" href="/static/css/aura.css">

  <style>
    /* Estilos Customizados do Showcase Executivo - Acabamento Obsidian & Zero Edge Glow */
    .showcase-mesh-bg {
      background-color: #07090e;
      background-image: 
        radial-gradient(at 0% 0%, rgba(6, 182, 212, 0.04) 0px, transparent 45%),
        radial-gradient(at 100% 0%, rgba(124, 58, 237, 0.04) 0px, transparent 45%),
        radial-gradient(at 50% 50%, rgba(16, 185, 129, 0.03) 0px, transparent 55%),
        radial-gradient(at 100% 100%, rgba(6, 182, 212, 0.03) 0px, transparent 45%);
    }

    /* Barra de Progresso de Rolagem Global no Topo */
    #scroll-progress-bar {
      position: fixed;
      top: 0;
      left: 0;
      height: 2px;
      width: 0%;
      background: linear-gradient(90deg, #06b6d4, #10b981, #a855f7);
      z-index: 100;
      transition: width 0.1s ease-out;
    }

    /* Trilho Lateral Flutuante de Navegação por Scroll */
    .scroll-nav-rail {
      position: fixed;
      right: 1.25rem;
      top: 50%;
      transform: translateY(-50%);
      z-index: 40;
      display: flex;
      flex-direction: column;
      gap: 0.75rem;
    }
    .scroll-nav-dot {
      width: 7px;
      height: 7px;
      border-radius: 9999px;
      background: rgba(255, 255, 255, 0.2);
      border: 1px solid rgba(255, 255, 255, 0.15);
      transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
      position: relative;
    }
    .scroll-nav-dot:hover, .scroll-nav-dot.active {
      width: 9px;
      height: 9px;
      background: #22d3ee;
      border-color: rgba(34, 211, 238, 0.6);
      box-shadow: 0 0 0 3px rgba(6, 182, 212, 0.15);
    }

    /* Utilitário de Scroll Reveal Suave */
    .scroll-reveal {
      opacity: 0;
      transform: translateY(18px);
      transition: opacity 0.6s cubic-bezier(0.16, 1, 0.3, 1), transform 0.6s cubic-bezier(0.16, 1, 0.3, 1);
      will-change: opacity, transform;
    }
    .scroll-reveal.scroll-reveal-visible {
      opacity: 1;
      transform: translateY(0);
    }

    /* Superfícies Obsidian Profundas de Alta Precisão (Sem Glow Artificial de IA) */
    .obsidian-card {
      background: rgba(14, 18, 27, 0.88);
      border: 1px solid rgba(255, 255, 255, 0.08);
      box-shadow: 0 16px 36px -12px rgba(0, 0, 0, 0.65), inset 0 1px 0 rgba(255, 255, 255, 0.04);
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
    }

    .obsidian-card:hover {
      border-color: rgba(255, 255, 255, 0.14);
    }

    /* Conectores SVG com Pulso de Fótons Discreto */
    @keyframes pulse-flow {
      0% {
        stroke-dashoffset: 120;
        opacity: 0.35;
      }
      50% {
        opacity: 0.9;
      }
      100% {
        stroke-dashoffset: 0;
        opacity: 0.35;
      }
    }

    .flow-path-active {
      stroke-dasharray: 6 5;
      animation: pulse-flow 2.4s linear infinite;
    }

    @keyframes photon-travel {
      0% {
        transform: translateY(0);
        opacity: 0;
      }
      20% {
        opacity: 1;
      }
      80% {
        opacity: 1;
      }
      100% {
        transform: translateY(28px);
        opacity: 0;
      }
    }

    .photon-pulse {
      animation: photon-travel 0.9s cubic-bezier(0.16, 1, 0.3, 1) infinite;
    }

    /* Transições Suaves das Etapas e Painéis */
    .step-content-pane {
      transition: opacity 0.35s ease, transform 0.35s ease;
    }
    .step-content-pane.hidden-pane {
      opacity: 0;
      transform: translateY(12px);
      pointer-events: none;
      display: none;
    }
    .step-content-pane.active-pane {
      opacity: 1;
      transform: translateY(0);
      display: block;
    }

    /* Efeito de Desintegração em Poeira nos Textos Sensíveis */
    .pii-raw {
      transition: all 0.35s cubic-bezier(0.16, 1, 0.3, 1);
      display: inline-block;
    }
    .pii-raw.disintegrating {
      color: transparent;
      text-shadow: 0 0 6px rgba(6, 182, 212, 0.6);
      transform: scale(0.97);
      filter: blur(2px);
    }
    .pii-redacted {
      transition: all 0.35s ease;
    }

    /* Canvas Overlay de Partículas (Desintegração em Poeira) */
    #dust-particle-canvas {
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      pointer-events: none;
      z-index: 30;
    }

    /* Estados Reativos dos Nós do Pipeline e Grafo (Sóbrios, Sem Borda Neon Excessiva) */
    .pipeline-node, .graph-node {
      transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
    }
    .pipeline-node.pulse-highlight, .graph-node.active-glow {
      border-color: rgba(34, 211, 238, 0.7) !important;
      background: rgba(18, 25, 38, 0.95) !important;
      box-shadow: 0 6px 20px -4px rgba(0, 0, 0, 0.7), inset 0 1px 0 rgba(255, 255, 255, 0.08);
      transform: translateY(-1px);
    }
    .graph-node.success-glow {
      border-color: rgba(52, 211, 153, 0.7) !important;
      background: rgba(18, 25, 38, 0.95) !important;
      box-shadow: 0 6px 20px -4px rgba(0, 0, 0, 0.7), inset 0 1px 0 rgba(255, 255, 255, 0.08);
      transform: translateY(-1px);
    }
    .graph-node.active-selected {
      border-color: rgba(34, 211, 238, 0.8) !important;
      background: rgba(18, 26, 40, 0.98) !important;
      box-shadow: 0 8px 24px -4px rgba(0, 0, 0, 0.75);
    }

    /* Cursor de Digitação Typewriter Piscante */
    .typewriter-cursor {
      display: inline-block;
      width: 2px;
      height: 1.1em;
      background-color: #22d3ee;
      margin-left: 2px;
      vertical-align: text-bottom;
      animation: blink-cursor 0.75s step-start infinite;
    }
    @keyframes blink-cursor {
      0%, 100% { opacity: 1; }
      50% { opacity: 0; }
    }

    /* Botão Executivo Deluxe */
    .btn-aura-exec {
      box-shadow: 0 4px 14px -2px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.1);
      transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
    }
    .btn-aura-exec:hover {
      filter: brightness(1.06);
      transform: translateY(-1px);
    }

    /* Animação de Onda Líquida em Tanques */
    @keyframes liquid-shimmer {
      0% { transform: translateY(0); }
      50% { transform: translateY(-3px); }
      100% { transform: translateY(0); }
    }
    .liquid-wave {
      animation: liquid-shimmer 3s ease-in-out infinite;
    }

    /* Cartões de ROI com Acabamento Refinado */
    .roi-card {
      transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
    }
    .roi-card:hover {
      transform: translateY(-2px);
      border-color: rgba(255, 255, 255, 0.16);
    }

    /* Mini Gráficos de ROI com Animação no Scroll */
    .roi-spark-bar {
      transform-origin: bottom;
      transition: transform 0.8s cubic-bezier(0.16, 1, 0.3, 1);
      transform: scaleY(0);
    }
    .roi-card.revealed .roi-spark-bar {
      transform: scaleY(1);
    }

    .roi-gauge-fill {
      width: 0%;
      transition: width 1s cubic-bezier(0.16, 1, 0.3, 1);
    }
    .roi-card.revealed .roi-gauge-fill {
      width: var(--target-width, 100%);
    }

    /* Gráfico de Barras Empilhadas de Custos (Harness.io Style) */
    .cost-bar-item {
      height: 0%;
      transition: height 0.9s cubic-bezier(0.16, 1, 0.3, 1);
    }
    .cost-bar-item.revealed {
      height: var(--target-height, 80%);
    }

    /* Mini Dashboards e Barras da Tabela de ROI */
    .roi-table-bar {
      width: 0%;
      transition: width 1s cubic-bezier(0.16, 1, 0.3, 1);
    }
    .roi-card.revealed .roi-table-bar,
    .roi-table-revealed .roi-table-bar {
      width: var(--target-width, 100%);
    }

    /* Globo 3D em Nuvem de Pontos e Grafo de Conhecimento (Inspirado em Harness.io) */
    .homepage-knowledge-graph-v3_globe {
      position: relative;
      width: 100%;
      height: 100%;
      min-height: 270px;
      display: flex;
      align-items: center;
      justify-content: center;
      overflow: visible;
    }
    .homepage-knowledge-graph-v3_svg {
      width: 100%;
      height: 100%;
      max-height: 310px;
      overflow: visible;
    }
    .homepage-knowledge-graph-v3_dots {
      /* Nuvem de pontos 3D da esfera */
    }
    .homepage-knowledge-graph-v3_dot {
      transform: translate(var(--dot-x), var(--dot-y));
      fill: #38bdf8;
      transition: opacity 0.3s ease, fill 0.3s ease;
    }
    .homepage-knowledge-graph-v3_edge {
      transform-origin: 0 0;
      transform: translate(var(--edge-tx), var(--edge-ty)) rotate(var(--edge-angle)) scaleX(var(--edge-len));
      stroke: rgba(56, 189, 248, 0.4);
      stroke-width: 1.2px;
      stroke-dasharray: 4 3;
      vector-effect: non-scaling-stroke;
      transition: stroke 0.3s ease, opacity 0.3s ease, stroke-width 0.3s ease;
    }
    .homepage-knowledge-graph-v3_edge.active-edge {
      stroke: #22d3ee !important;
      opacity: 0.95 !important;
      stroke-width: 2px !important;
      stroke-dasharray: none !important;
      filter: drop-shadow(0 0 6px rgba(34, 211, 238, 0.5));
    }
    .homepage-knowledge-graph-v3_edge.transversal-edge {
      stroke: rgba(255, 255, 255, 0.12);
      stroke-width: 1px;
      stroke-dasharray: 2 4;
    }
    .homepage-knowledge-graph-v3_node {
      transform: translate(var(--node-x), var(--node-y));
      cursor: pointer;
      transition: transform 0.25s cubic-bezier(0.16, 1, 0.3, 1);
    }
    .homepage-knowledge-graph-v3_node:hover {
      transform: translate(var(--node-x), var(--node-y)) scale(1.08);
    }
    .homepage-knowledge-graph-v3_node-halo {
      fill: rgba(56, 189, 248, 0.15);
      stroke: rgba(56, 189, 248, 0.25);
      stroke-width: 1px;
      transition: all 0.25s ease;
    }
    .homepage-knowledge-graph-v3_node.kg-node-selected .homepage-knowledge-graph-v3_node-halo {
      fill: rgba(34, 211, 238, 0.28);
      stroke: #22d3ee;
      stroke-width: 2px;
      r: 16;
      filter: drop-shadow(0 0 8px rgba(34, 211, 238, 0.5));
    }
    .homepage-knowledge-graph-v3_node-core {
      fill: #38bdf8;
      transition: fill 0.25s ease;
    }
    .homepage-knowledge-graph-v3_node.kg-node-selected .homepage-knowledge-graph-v3_node-core {
      fill: #22d3ee;
      r: 6;
    }
    .homepage-knowledge-graph-v3_node-label {
      fill: #ffffff;
      font-family: inherit;
      font-size: 11px;
      font-weight: 700;
      text-anchor: middle;
      letter-spacing: 0.5px;
    }
    .homepage-knowledge-graph-v3_node-tag {
      fill: #94a3b8;
      font-family: inherit;
      font-size: 10px;
      font-weight: 500;
      text-anchor: middle;
      transition: fill 0.25s ease;
    }
    .homepage-knowledge-graph-v3_node.kg-node-selected .homepage-knowledge-graph-v3_node-tag,
    .homepage-knowledge-graph-v3_node:hover .homepage-knowledge-graph-v3_node-tag {
      fill: #ffffff;
      font-weight: 600;
    }

    /* Interatividade e Destaque no Knowledge Graph */
    .kg-context-item {
      transition: all 0.22s cubic-bezier(0.16, 1, 0.3, 1);
    }
    .kg-context-item.active {
      background: rgba(6, 182, 212, 0.10) !important;
      border-color: rgba(34, 211, 238, 0.5) !important;
      color: #ffffff !important;
    }
    .kg-node-selected circle:first-of-type {
      stroke: #22d3ee !important;
      stroke-width: 2.5px !important;
      filter: drop-shadow(0 0 6px rgba(34, 211, 238, 0.45));
    }
    .kg-node-selected text {
      fill: #ffffff !important;
      font-weight: 700 !important;
    }

    /* Pulso Suave do Núcleo AURA */
    .orbit-pulse {
      animation: core-pulse 3.5s ease-in-out infinite;
    }
    @keyframes core-pulse {
      0%, 100% { transform: scale(1); opacity: 0.92; }
      50% { transform: scale(1.03); opacity: 1; }
    }
  </style>
</head>
<body id="top" class="min-h-screen flex flex-col showcase-mesh-bg text-slate-200 antialiased selection:bg-auraCyan/25 selection:text-white overflow-x-hidden">

  <!-- Barra de Progresso de Scroll Superior -->
  <div id="scroll-progress-bar"></div>

  <!-- Trilho Lateral Flutuante de Navegação por Scroll (Desktop) -->
  <aside class="scroll-nav-rail hidden lg:flex" aria-label="Navegação Rápida">
    <button onclick="window.auraTour.scrollToSection('top')" class="scroll-nav-dot active" title="01. Início & Cockpit Executivo" data-section="top"></button>
    <button onclick="window.auraTour.scrollToSection('sec-chat-graph')" class="scroll-nav-dot" title="02. Demonstração Autônoma (Chat vs Backend)" data-section="sec-chat-graph"></button>
    <button onclick="window.auraTour.scrollToSection('sec-blindagem')" class="scroll-nav-dot" title="03. Segurança de Dados & LGPD" data-section="sec-blindagem"></button>
    <button onclick="window.auraTour.scrollToSection('sec-custo-ia')" class="scroll-nav-dot" title="04. Gestão de Custo de IA (Harness)" data-section="sec-custo-ia"></button>
    <button onclick="window.auraTour.scrollToSection('sec-knowledge-graph')" class="scroll-nav-dot" title="05. Grafo de Conhecimento AURA" data-section="sec-knowledge-graph"></button>
    <button onclick="window.auraTour.scrollToSection('sec-diferenciacao')" class="scroll-nav-dot" title="06. Diferenciação Operacional & ROI" data-section="sec-diferenciacao"></button>
    <button onclick="window.auraTour.scrollToSection('sec-faq')" class="scroll-nav-dot" title="07. FAQ Executivo" data-section="sec-faq"></button>
  </aside>

  <!-- =========================================================================
       HEADER EXECUTIVO DO SHOWCASE
       ========================================================================= -->
  <header class="sticky top-0 z-50 border-b border-white/[0.07] px-4 py-3 backdrop-blur-xl bg-obsidianDeep/90">
    <div class="max-w-7xl mx-auto flex items-center justify-between gap-4">
      
      <!-- Brand & Badges -->
      <div class="flex items-center gap-3">
        <a href="/" class="flex items-center gap-2.5 group" title="Retornar ao Console Operacional AURA">
          <div class="w-8 h-8 rounded-lg bg-cyan-500/10 border border-cyan-500/25 flex items-center justify-center text-cyan-300 font-bold group-hover:scale-105 transition-transform">
            <i data-lucide="activity" class="w-4 h-4 text-cyan-400"></i>
          </div>
          <div>
            <div class="flex items-center gap-2">
              <span class="font-display-title font-bold text-lg tracking-wider bg-gradient-to-r from-cyan-400 via-sky-300 to-purple-400 bg-clip-text text-transparent">AURA</span>
              <span class="px-2 py-0.5 rounded-full text-[9px] font-sans font-semibold bg-auraEmerald/10 text-auraEmerald-light border border-auraEmerald/20">
                Showcase Executivo
              </span>
              <span class="hidden sm:inline px-2 py-0.5 rounded-full text-[9px] font-mono bg-cyan-500/10 text-cyan-300 border border-cyan-500/20">
                100% LGPD
              </span>
            </div>
            <p class="text-[10px] text-slate-400 font-sans hidden sm:block">Plataforma de Inteligência Autônoma para Postos, Lojas, Bares, Padarias & Varejo</p>
          </div>
        </a>
      </div>

      <!-- Links de Atalho das Seções -->
      <nav class="hidden md:flex items-center gap-1 text-xs font-sans">
        <button onclick="window.auraTour.scrollToSection('sec-chat-graph')" class="px-2.5 py-1.5 rounded-lg text-cyan-300 hover:text-white hover:bg-white/[0.04] transition-colors font-medium flex items-center gap-1.5">
          <span class="w-1.5 h-1.5 rounded-full bg-cyan-400"></span>
          <span>Ao Vivo</span>
        </button>
        <button onclick="window.auraTour.scrollToSection('sec-blindagem')" class="px-2.5 py-1.5 rounded-lg text-slate-300 hover:text-white hover:bg-white/[0.04] transition-colors">
          Escudo LGPD
        </button>
        <button onclick="window.auraTour.scrollToSection('sec-custo-ia')" class="px-2.5 py-1.5 rounded-lg text-slate-300 hover:text-white hover:bg-white/[0.04] transition-colors">
          Custo de IA
        </button>
        <button onclick="window.auraTour.scrollToSection('sec-knowledge-graph')" class="px-2.5 py-1.5 rounded-lg text-slate-300 hover:text-white hover:bg-white/[0.04] transition-colors">
          Knowledge Graph
        </button>
        <button onclick="window.auraTour.scrollToSection('sec-diferenciacao')" class="px-2.5 py-1.5 rounded-lg text-emerald-300 hover:text-white hover:bg-white/[0.04] transition-colors font-medium">
          ROI & Matriz
        </button>
        <button onclick="window.auraTour.scrollToSection('sec-faq')" class="px-2.5 py-1.5 rounded-lg text-slate-300 hover:text-white hover:bg-white/[0.04] transition-colors">
          FAQ
        </button>
      </nav>

      <!-- Botões de Ação Direta -->
      <div class="flex items-center gap-2.5">
        <button id="btn-toggle-sfx-showcase" class="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-900/80 hover:bg-slate-800 text-slate-300 hover:text-white border border-white/10 text-xs transition-colors" title="Alternar Efeitos Sonoros">
          <i data-lucide="volume-2" id="icon-sfx" class="w-3.5 h-3.5 text-cyan-400"></i>
          <span class="hidden sm:inline text-[11px]">Áudio</span>
        </button>

        <a href="/" class="flex items-center gap-2 px-3.5 py-1.5 rounded-xl bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-300 hover:text-white border border-cyan-500/25 text-xs font-semibold transition-all">
          <span>Abrir Console</span>
          <i data-lucide="arrow-up-right" class="w-3.5 h-3.5"></i>
        </a>
      </div>

    </div>
  </header>

  <!-- =========================================================================
       HERO EXECUTIVO: COCKPIT HOLOGRÁFICO DA AURA & APRESENTAÇÃO SPLIT
       ========================================================================= -->
  <main class="flex-1 max-w-7xl w-full mx-auto px-4 py-8 sm:py-12 space-y-16">
    
    <!-- Hero Split: Proposta de Valor (Esquerda) vs Cockpit Holográfico da AURA (Direita) -->
    <section class="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center min-h-[62vh] sm:min-h-[70vh] py-6 scroll-reveal scroll-reveal-visible" id="hero-cockpit-split">
      
      <!-- Coluna Esquerda: Proposta de Valor Executiva -->
      <div class="lg:col-span-7 space-y-6 text-left">
        <div class="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-cyan-500/10 border border-cyan-500/20 text-xs font-sans text-cyan-300">
          <span class="w-1.5 h-1.5 rounded-full bg-cyan-400"></span>
          <span class="font-semibold tracking-wider uppercase text-[10px]">Arquitetura Universal: Postos • Padarias • Bares • Lojas • Franquias</span>
        </div>

        <h1 class="text-3xl sm:text-5xl font-extrabold tracking-tight text-white leading-[1.15] font-display-title">
          O Cérebro Operacional de Qualquer Comércio ou Ponto de Venda. <br>
          <span class="bg-gradient-to-r from-cyan-400 via-emerald-300 to-purple-400 bg-clip-text text-transparent">
            Proteção Absoluta de Dados & 100% LGPD.
          </span>
        </h1>

        <p class="text-sm sm:text-base text-slate-300 leading-relaxed font-sans max-w-xl">
          Acompanhe como a AURA funciona na prática: role a página para ver a pergunta sendo analisada, os dados confidenciais protegidos na hora e a resposta executiva sendo gerada em segundos.
        </p>

        <!-- Indicador de Rolagem e Métricas Rápidas -->
        <div class="pt-2 flex flex-col sm:flex-row items-start sm:items-center gap-4">
          <button onclick="window.auraTour.scrollToSection('sec-chat-graph')" class="inline-flex items-center gap-2.5 px-5 py-2.5 rounded-xl bg-slate-900 border border-cyan-500/30 text-cyan-300 hover:text-white hover:border-cyan-400 text-xs font-semibold transition-all group btn-aura-exec">
            <span>Role para ver o fluxo em tempo real</span>
            <i data-lucide="arrow-down" class="w-4 h-4 group-hover:translate-y-0.5 transition-transform text-cyan-400"></i>
          </button>
          
          <div class="flex items-center gap-2 text-[11px] font-sans text-slate-400">
            <span class="w-2 h-2 rounded-full bg-emerald-400"></span>
            <span>Demonstração Autônoma Sincronizada ao Scroll • Zero Cliques Forçados</span>
          </div>
        </div>

        <!-- Três Micro-Destaques de Engenharia no Rodapé da Coluna Esquerda -->
        <div class="grid grid-cols-3 gap-3 pt-3 border-t border-white/[0.06] max-w-lg">
          <div class="space-y-0.5">
            <div class="text-[10px] text-slate-400 uppercase font-mono">Latência Média</div>
            <div class="text-sm font-bold text-white font-mono">38 ms</div>
            <div class="text-[10px] text-emerald-400">Sub-100ms Local</div>
          </div>
          <div class="space-y-0.5">
            <div class="text-[10px] text-slate-400 uppercase font-mono">Privacidade</div>
            <div class="text-sm font-bold text-white font-mono">100% LGPD</div>
            <div class="text-[10px] text-cyan-400">Lei 13.709/2018</div>
          </div>
          <div class="space-y-0.5">
            <div class="text-[10px] text-slate-400 uppercase font-mono">Economia Tokens</div>
            <div class="text-sm font-bold text-white font-mono">Até 95%</div>
            <div class="text-[10px] text-purple-400">Banco do Cliente</div>
          </div>
        </div>
      </div>

      <!-- Coluna Direita: Cockpit Holográfico da AURA (Preview Tecnológico Sóbrio - Estilo Harness Runtime Protection) -->
      <div class="lg:col-span-5" id="hero-cockpit-hud">
        <div class="obsidian-card rounded-2xl p-5 space-y-4 relative overflow-hidden">
          
          <!-- Barra Superior do HUD -->
          <div class="flex items-center justify-between border-b border-white/[0.08] pb-3 text-xs font-mono">
            <div class="flex items-center gap-2">
              <span class="w-2 h-2 rounded-full bg-emerald-400"></span>
              <span class="font-bold text-white text-[11px]">NÚCLEO AURA // TELEMETRIA HUD</span>
            </div>
            <span class="px-2 py-0.5 rounded text-[10px] bg-cyan-500/10 text-cyan-300 border border-cyan-500/20" id="hero-telemetry-pill">
              BORDA LOCAL ATIVA
            </span>
          </div>

          <!-- Mini Dashboards & Donut Charts Elegantes (Referência Harness Runtime Protection) -->
          <div class="grid grid-cols-2 gap-3 pt-1">
            
            <!-- Donut 1: Integridade Operacional (Total 261 Checagens/min) -->
            <div class="p-3 rounded-xl bg-slate-950/70 border border-white/[0.06] flex items-center gap-3">
              <div class="relative w-14 h-14 flex items-center justify-center flex-shrink-0">
                <svg viewBox="0 0 36 36" class="w-14 h-14 -rotate-90">
                  <circle cx="18" cy="18" r="14" fill="none" stroke="rgba(255, 255, 255, 0.06)" stroke-width="3" />
                  <circle cx="18" cy="18" r="14" fill="none" stroke="#10b981" stroke-width="3" stroke-dasharray="87.5 88" stroke-linecap="round" />
                  <circle cx="18" cy="18" r="14" fill="none" stroke="#f59e0b" stroke-width="3" stroke-dasharray="0.5 88" stroke-dashoffset="-87.5" stroke-linecap="round" />
                </svg>
                <div class="absolute inset-0 flex flex-col items-center justify-center text-center">
                  <span class="text-[11px] font-bold text-white font-mono leading-none">261</span>
                </div>
              </div>
              <div class="space-y-0.5 min-w-0">
                <div class="text-[9px] text-slate-400 font-mono uppercase tracking-wider">Auditorias/min</div>
                <div class="text-xs font-bold text-emerald-400 truncate">100% Conforme</div>
                <div class="text-[9px] text-slate-400">Total 261 checks</div>
              </div>
            </div>

            <!-- Donut 2: Ativos Operacionais Monitorados (Total 66 Ativos) -->
            <div class="p-3 rounded-xl bg-slate-950/70 border border-white/[0.06] flex items-center gap-3">
              <div class="relative w-14 h-14 flex items-center justify-center flex-shrink-0">
                <svg viewBox="0 0 36 36" class="w-14 h-14 -rotate-90">
                  <circle cx="18" cy="18" r="14" fill="none" stroke="rgba(255, 255, 255, 0.06)" stroke-width="3" />
                  <circle cx="18" cy="18" r="14" fill="none" stroke="#06b6d4" stroke-width="3" stroke-dasharray="38 88" stroke-linecap="round" />
                  <circle cx="18" cy="18" r="14" fill="none" stroke="#a855f7" stroke-width="3" stroke-dasharray="35 88" stroke-dashoffset="-38" stroke-linecap="round" />
                  <circle cx="18" cy="18" r="14" fill="none" stroke="#10b981" stroke-width="3" stroke-dasharray="15 88" stroke-dashoffset="-73" stroke-linecap="round" />
                </svg>
                <div class="absolute inset-0 flex flex-col items-center justify-center text-center">
                  <span class="text-[11px] font-bold text-white font-mono leading-none">66</span>
                </div>
              </div>
              <div class="space-y-0.5 min-w-0">
                <div class="text-[9px] text-slate-400 font-mono uppercase tracking-wider">Ativos Locais</div>
                <div class="text-xs font-bold text-cyan-300 truncate">Vigilância Ativa</div>
                <div class="text-[9px] text-slate-400">Total 66 assets</div>
              </div>
            </div>

          </div>

          <!-- Stacked Bar Horizontal de Severidades (Padrão Runtime Protection da Imagem 2) -->
          <div class="p-3.5 rounded-xl bg-slate-950/70 border border-white/[0.06] space-y-2">
            <div class="flex items-center justify-between text-[10px] font-mono">
              <span class="text-slate-400">Severidades & Integridade da Operação</span>
              <span class="text-emerald-400 font-semibold">Zero Críticos</span>
            </div>
            
            <!-- Barra Empilhada Horizontal -->
            <div class="w-full h-2.5 bg-slate-900 rounded-full flex overflow-hidden border border-white/[0.06]">
              <div class="h-full bg-emerald-500 rounded-l transition-all duration-700" style="width: 98.5%;" title="Conforme: 260"></div>
              <div class="h-full bg-amber-400 transition-all duration-700" style="width: 1.5%;" title="Atenção Preventiva: 1"></div>
              <div class="h-full bg-rose-500 transition-all duration-700" style="width: 0%;" title="Crítico: 0"></div>
            </div>

            <!-- Legenda com Chips Discretos de Severidade -->
            <div class="flex items-center justify-between text-[9px] font-mono pt-0.5">
              <span class="flex items-center gap-1 text-slate-400">
                <span class="w-1.5 h-1.5 rounded-full bg-rose-500"></span>
                <span>Crítico: <strong class="text-white">0</strong></span>
              </span>
              <span class="flex items-center gap-1 text-slate-400">
                <span class="w-1.5 h-1.5 rounded-full bg-amber-400"></span>
                <span>Atenção: <strong class="text-white">1</strong></span>
              </span>
              <span class="flex items-center gap-1 text-slate-400">
                <span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                <span>Conforme: <strong class="text-white">260</strong></span>
              </span>
            </div>
          </div>

          <!-- Grid de 3 Indicadores em Tempo Real do Cockpit -->
          <div class="grid grid-cols-3 gap-2 text-xs font-sans">
            <div class="p-2.5 rounded-xl bg-slate-950/60 border border-white/[0.06] space-y-1">
              <div class="text-[10px] text-slate-400">Conferência Caixa</div>
              <div class="text-xs font-bold text-emerald-400 font-mono">R$ 0,00 Dif.</div>
              <div class="text-[9px] text-slate-400">100% Fechado</div>
            </div>

            <div class="p-2.5 rounded-xl bg-slate-950/60 border border-white/[0.06] space-y-1">
              <div class="text-[10px] text-slate-400">Auditoria ANP</div>
              <div class="text-xs font-bold text-cyan-300 font-mono">+0.28% LMC</div>
              <div class="text-[9px] text-slate-400">Portaria 26 OK</div>
            </div>

            <div class="p-2.5 rounded-xl bg-slate-950/60 border border-white/[0.06] space-y-1">
              <div class="text-[10px] text-slate-400">Economia Token</div>
              <div class="text-xs font-bold text-purple-300 font-mono">-95% Custo</div>
              <div class="text-[9px] text-slate-400">Sem Fatura Nuvem</div>
            </div>
          </div>

          <!-- Micro Ticker de Eventos em Tempo Real -->
          <div class="p-2 rounded-lg bg-black/40 border border-white/[0.04] text-[10px] font-mono text-slate-400 flex items-center justify-between">
            <div class="flex items-center gap-1.5 truncate">
              <span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
              <span class="truncate">PDV Conciliado • Tanques com telemetria ativa • Zero vazamentos</span>
            </div>
            <span class="text-cyan-400 flex-shrink-0 ml-2">Sub-100ms</span>
          </div>

        </div>
      </div>

    </section>

    <!-- =========================================================================
         NÚCLEO DO SHOWCASE: CHAT DA AURA (ESQUERDA) VS SIMULAÇÃO DO BACKEND (DIREITA)
         (Acionado 100% de forma autônoma ao entrar no viewport pelo scroll)
         ========================================================================= -->
    <section id="sec-chat-graph" class="space-y-4 scroll-reveal">
      
      <!-- Barra Superior Discreta de Status e Replay -->
      <div class="obsidian-card px-4 py-3 rounded-2xl flex flex-col sm:flex-row items-center justify-between gap-3 text-xs font-sans">
        <div class="flex items-center gap-2.5">
          <span class="w-2 h-2 rounded-full bg-cyan-400"></span>
          <span class="font-bold text-white text-[13px]">Fluxo Executivo em Tempo Real</span>
          <span class="text-slate-400 font-mono text-[11px] hidden sm:inline">| Esquerda: Chat da AURA • Direita: Simulação do Backend</span>
        </div>

        <div class="flex items-center gap-2">
          <!-- Botão Elegante de Replay para Rever a Animação -->
          <button onclick="window.auraTour.restartTour()" id="btn-tour-replay" class="btn-aura-exec px-3.5 py-1.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-cyan-300 hover:text-white border border-cyan-500/30 text-xs font-semibold transition-all flex items-center gap-2 active:scale-95" title="Reiniciar Simulação Autônoma">
            <i data-lucide="rotate-ccw" class="w-3.5 h-3.5"></i>
            <span>Ver animação de novo ↺</span>
          </button>
        </div>
      </div>

      <!-- Grid Principal: Chat da AURA (5 Cols) vs Simulação do Backend (7 Cols) -->
      <div class="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
        
        <!-- =====================================================================
             COLUNA ESQUERDA: EMULAÇÃO REALISTA DO CHAT DA AURA (5 Cols)
             ===================================================================== -->
        <div id="mini-chat-aura" class="lg:col-span-5 flex flex-col obsidian-card rounded-2xl overflow-hidden">
          
          <!-- Topo da Janela do Chat (Estilo macOS / App Nativo) -->
          <div class="p-3.5 border-b border-white/[0.08] bg-white/[0.01] flex items-center justify-between">
            <div class="flex items-center gap-2">
              <span class="w-2.5 h-2.5 rounded-full bg-rose-500/80"></span>
              <span class="w-2.5 h-2.5 rounded-full bg-amber-500/80"></span>
              <span class="w-2.5 h-2.5 rounded-full bg-emerald-500/80"></span>
              <div class="flex items-center gap-1.5 ml-2">
                <i data-lucide="message-square" class="w-3.5 h-3.5 text-cyan-400"></i>
                <span class="text-xs font-bold text-white">AURA Chat Executivo</span>
                <span class="text-[10px] text-slate-400 font-mono hidden sm:inline">• Processamento Local</span>
              </div>
            </div>
            <span class="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-500/10 text-emerald-300 border border-emerald-500/25 flex items-center gap-1">
              <span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
              LGPD BLINDADO
            </span>
          </div>

          <!-- Seletor Rápido de Cenários Multissetoriais -->
          <div class="p-3 border-b border-white/[0.06] bg-slate-950/40 space-y-1.5 font-sans">
            <div class="flex items-center justify-between text-[11px] text-slate-400">
              <span class="font-medium">Segmento da Demonstração:</span>
              <span class="text-cyan-400 text-[10px] font-mono" id="sim-status-badge">PRONTO</span>
            </div>
            <div class="grid grid-cols-2 sm:grid-cols-4 gap-1 text-[11px]">
              <button onclick="window.auraTour.selectChatScenario('posto')" id="scenario-btn-posto" class="px-2 py-1.5 rounded-lg bg-cyan-500/15 text-cyan-200 border border-cyan-500/35 font-semibold truncate transition-all text-left flex items-center gap-1">
                <span>⛽</span>
                <span class="truncate">Postos</span>
              </button>
              <button onclick="window.auraTour.selectChatScenario('varejo')" id="scenario-btn-varejo" class="px-2 py-1.5 rounded-lg bg-slate-900/80 text-slate-300 hover:text-white border border-white/10 truncate transition-all text-left flex items-center gap-1">
                <span>🏪</span>
                <span class="truncate">Padaria / Bar</span>
              </button>
              <button onclick="window.auraTour.selectChatScenario('loja')" id="scenario-btn-loja" class="px-2 py-1.5 rounded-lg bg-slate-900/80 text-slate-300 hover:text-white border border-white/10 truncate transition-all text-left flex items-center gap-1">
                <span>🏬</span>
                <span class="truncate">Loja & Varejo</span>
              </button>
              <button onclick="window.auraTour.selectChatScenario('fiscal')" id="scenario-btn-fiscal" class="px-2 py-1.5 rounded-lg bg-slate-900/80 text-slate-300 hover:text-white border border-white/10 truncate transition-all text-left flex items-center gap-1">
                <span>⚖️</span>
                <span class="truncate">Auditoria Fiscal</span>
              </button>
            </div>
          </div>

          <!-- Área de Conversação do Chat -->
          <div class="p-4 flex-1 space-y-4 overflow-y-auto max-h-[520px] font-sans text-xs" id="chat-messages-container">
            
            <!-- Mensagem do Gestor (Com Efeito Typewriter Automático) -->
            <div class="flex items-start gap-2.5" id="user-msg-row">
              <div class="w-7 h-7 rounded-lg bg-purple-500/20 text-purple-300 flex items-center justify-center font-bold text-xs flex-shrink-0 mt-0.5">
                G
              </div>
              <div class="flex-1 space-y-1">
                <div class="flex items-center justify-between text-[10px] text-slate-400">
                  <span class="font-semibold text-slate-300" id="chat-user-label">Gerente Executivo (Unidade Central)</span>
                  <span id="chat-timestamp-label">17:42 • Ao Vivo</span>
                </div>
                <div class="p-3.5 rounded-2xl rounded-tl-sm bg-slate-900/90 border border-white/10 text-cyan-200 leading-relaxed shadow-sm min-h-[46px] flex items-center">
                  <span id="step1-typed-text" class="font-sans font-medium"></span><span id="chat-user-query-text" class="hidden"></span><span class="typewriter-cursor" id="typewriter-cursor"></span>
                </div>
              </div>
            </div>

            <!-- Indicador de Análise em Tempo Real (AURA Thinking) -->
            <div id="chat-thinking-box" class="hidden flex items-start gap-2.5">
              <div class="w-6 h-6 rounded-lg bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400 flex-shrink-0 mt-0.5">
                <i data-lucide="cpu" class="w-3.5 h-3.5 animate-spin"></i>
              </div>
              <div class="flex-1 p-3 rounded-2xl rounded-tl-sm bg-white/[0.02] border border-white/5 space-y-1.5">
                <div class="flex items-center gap-2 text-cyan-400 font-mono text-[11px]">
                  <span class="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-ping"></span>
                  <span id="thinking-step-text" class="font-semibold">Consultando dados operacionais...</span>
                </div>
                <div class="w-full bg-black/40 h-1 rounded-full overflow-hidden">
                  <div id="thinking-progress-bar" class="h-full bg-gradient-to-r from-cyan-400 to-emerald-400 w-1/3 transition-all duration-300"></div>
                </div>
              </div>
            </div>

            <!-- Resposta Executiva da AURA com DecisionCard Precision Glass -->
            <div id="chat-response-row" class="hidden flex items-start gap-2.5">
              <div class="w-7 h-7 rounded-lg bg-cyan-500/15 border border-cyan-500/25 flex items-center justify-center text-cyan-300 flex-shrink-0 mt-0.5 font-bold">
                A
              </div>
              <div class="flex-1 space-y-3">
                <div class="flex items-center justify-between text-[10px] text-slate-400">
                  <span class="font-bold text-cyan-300 flex items-center gap-1">
                    <span>AURA</span>
                    <span class="px-1.5 py-0.2 rounded text-[9px] bg-cyan-500/15 text-cyan-300 font-mono">Processamento Local</span>
                  </span>
                  <span class="text-emerald-400 font-mono text-[10px]">38 ms • 100% LGPD</span>
                </div>
                
                <!-- Balão de Texto da Resposta Executiva -->
                <div class="p-3.5 rounded-2xl rounded-tl-sm bg-slate-900/90 border border-white/[0.08] text-slate-200 leading-relaxed space-y-3" id="chat-aura-response-bubble">
                  <p id="chat-response-narrative" class="font-sans text-xs text-slate-200">
                    Hoje (Turno Atual), o item líder absoluto em volume e faturamento é a <strong>Gasolina Comum</strong> com <strong>4.820 Litros</strong> vendidos (R$ 29.835,80 faturados), respondendo por 69,6% das vendas do turno. Em seguida: <strong>Diesel S-10</strong> (2.340 L) e <strong>Conveniência/Café</strong> (312 unid.). Fechamento de caixa 100% auditado com R$ 0,00 de divergência.
                  </p>

                  <!-- DecisionCard Executivo Precision Glass Incrustado -->
                  <div id="decisioncard-live" class="p-3.5 rounded-xl bg-black/60 border border-white/[0.08] space-y-3 font-sans shadow-lg">
                    <div class="flex items-center justify-between border-b border-white/[0.08] pb-2">
                      <div class="flex items-center gap-2">
                        <i data-lucide="sparkles" class="w-4 h-4 text-cyan-400"></i>
                        <span class="font-bold text-white text-xs" id="mini-dc-title">Diagnóstico Operacional Consolidado</span>
                      </div>
                      <span class="px-2 py-0.5 rounded text-[9px] font-bold bg-emerald-500/15 text-emerald-300 border border-emerald-500/25" id="mini-dc-badge">
                        MARGEM OTIMIZADA
                      </span>
                    </div>

                    <!-- Grid de 4 Indicadores Cruciais -->
                    <div class="grid grid-cols-2 gap-2 text-xs">
                      <div class="p-2 rounded-lg bg-white/[0.02] border border-white/5">
                        <div class="text-[10px] text-slate-400" id="mini-metric-label-1">Produto Mais Vendido</div>
                        <div class="font-extrabold text-white text-xs" id="mini-metric-val-1">Gasolina Comum (4.820 L)</div>
                        <div class="text-[9px] text-slate-400">69.6% do faturamento</div>
                      </div>
                      <div class="p-2 rounded-lg bg-white/[0.02] border border-white/5">
                        <div class="text-[10px] text-slate-400" id="mini-metric-label-2">Faturamento Consolidado</div>
                        <div class="font-extrabold text-cyan-300 text-xs" id="mini-metric-val-2">R$ 42.850,00</div>
                        <div class="text-[9px] text-slate-400">Turno Atual • 100% Auditado</div>
                      </div>
                      <div class="p-2 rounded-lg bg-white/[0.02] border border-white/5">
                        <div class="text-[10px] text-slate-400">Auditoria de Caixa</div>
                        <div class="font-extrabold text-emerald-400 text-xs">R$ 0,00 Diferença</div>
                        <div class="text-[9px] text-slate-400">Caixas 100% conferidos</div>
                      </div>
                      <div class="p-2 rounded-lg bg-white/[0.02] border border-white/5">
                        <div class="text-[10px] text-slate-400">Conformidade ANP (LMC)</div>
                        <div class="font-extrabold text-emerald-400 text-xs">+0.28%</div>
                        <div class="text-[9px] text-slate-400">Tolerância Portaria 26 (±0.60%)</div>
                      </div>
                    </div>

                    <!-- Botão Executivo de Ação em 1-Toque -->
                    <div class="space-y-1.5 pt-1">
                      <button onclick="window.auraTour.simulateChatActionClick()" id="mini-dc-action-btn" class="btn-aura-exec w-full py-2.5 px-3 rounded-xl bg-gradient-to-r from-cyan-500 to-emerald-500 hover:brightness-105 text-slate-950 font-bold text-xs flex items-center justify-center gap-1.5 active:scale-95 transition-all">
                        <i data-lucide="send" class="w-3.5 h-3.5"></i>
                        <span id="mini-dc-action-text">Emitir Pedido de Reposição (30.000 L)</span>
                      </button>

                      <!-- Toast de Feedback de Ação -->
                      <div id="mini-chat-action-toast" class="hidden p-2 rounded-lg bg-emerald-500/15 border border-emerald-500/30 text-[10px] font-sans text-emerald-200 flex items-center gap-1.5 transition-all">
                        <i data-lucide="check-circle" class="w-3.5 h-3.5 text-emerald-400 flex-shrink-0"></i>
                        <span id="mini-chat-toast-message">Pedido gerado com sucesso em 1 clique!</span>
                      </div>
                    </div>
                  </div>
                </div>

                <!-- Rodapé de Governança e LGPD -->
                <div class="text-[10px] text-slate-400 font-mono flex items-center justify-between px-1">
                  <span>LGPD (Lei 13.709/2018): Nenhum dado pessoal transmitido • Privacy by Design (Protegido na origem)</span>
                  <span class="text-emerald-400 font-semibold">Decisão Pronta ✓</span>
                </div>
              </div>
            </div>

          </div>

          <!-- Barra de Input Interativa do Chat -->
          <div class="p-3 border-t border-white/[0.08] bg-slate-950/70 space-y-2">
            <div class="flex items-center gap-2">
              <input type="text" id="chat-interactive-input" value="Qual produto mais vendido hoje?" class="flex-1 bg-black/50 border border-white/10 rounded-xl px-3 py-2 text-xs text-slate-200 font-sans focus:outline-none focus:border-cyan-400 transition-colors" placeholder="Digite uma dúvida executiva...">
              <button onclick="window.auraTour.simulateChatSubmit()" id="btn-simulate-chat-flow" class="btn-aura-exec px-3.5 py-2 rounded-xl bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-200 font-bold text-xs flex items-center gap-1.5 active:scale-95 transition-all border border-cyan-500/30" title="Simular Novamente">
                <i data-lucide="sparkles" class="w-3.5 h-3.5"></i>
                <span class="hidden sm:inline">Simular</span>
              </button>
            </div>
            <div class="flex items-center justify-between text-[10px] text-slate-400 font-sans px-1">
              <span>Simulação 100% autônoma • Digitação e resolução automáticas</span>
              <span class="text-cyan-400 font-mono">Latência: sub-42ms</span>
            </div>
          </div>

        </div>

        <!-- =====================================================================
             COLUNA DIREITA: SIMULAÇÃO DO BACKEND EM TEMPO REAL CONECTADA (7 Cols)
             ===================================================================== -->
        <div id="aura-flowchart-graph" class="lg:col-span-7 flex flex-col obsidian-card rounded-2xl overflow-hidden relative">
          
          <!-- Canvas Overlay de Partículas (Desintegração em Poeira) -->
          <canvas id="dust-particle-canvas"></canvas>

          <!-- Topo da Janela do Backend (Monitor de Telemetria de Borda) -->
          <div class="p-3.5 border-b border-white/[0.08] bg-white/[0.01] flex items-center justify-between relative z-10">
            <div class="flex items-center gap-2">
              <i data-lucide="cpu" class="w-4 h-4 text-cyan-400"></i>
              <span class="text-xs font-bold text-white font-mono" id="stage-viewport-title">aura://backend/simulacao-operacional-borda</span>
            </div>
            <div class="flex items-center gap-2 text-[11px] font-mono text-slate-400">
              <span class="w-2 h-2 rounded-full bg-cyan-400"></span>
              <span id="stage-telemetry-badge">SINCRONIZADO AO CHAT EM TEMPO REAL</span>
            </div>
          </div>

          <!-- Sequência de 5 Nós Conectados em Tempo Real -->
          <div class="p-5 flex-1 space-y-2 relative font-sans text-xs z-10">
            
            <!-- NÓ 1: Detecção de Intenção Semântica (< 5ms) -->
            <div id="graph-node-prompt" class="graph-node p-3 rounded-xl bg-slate-900/90 border border-purple-500/25 flex items-center justify-between hover:bg-slate-800 transition-all shadow-sm cursor-pointer" onclick="window.auraTour.inspectGraphNode('prompt')">
              <div class="flex items-center gap-3">
                <div class="w-8 h-8 rounded-lg bg-purple-500/15 text-purple-300 flex items-center justify-center font-bold flex-shrink-0">
                  <i data-lucide="compass" class="w-4 h-4"></i>
                </div>
                <div>
                  <div class="font-bold text-white flex items-center gap-2">
                    <span>1. Compreensão da Pergunta</span>
                    <span class="px-1.5 py-0.2 rounded text-[9px] bg-purple-500/15 text-purple-300 font-mono">vendas_analitico</span>
                  </div>
                  <div class="text-[10px] text-slate-400">Entende linguagem natural direta, sem fórmulas, códigos ou relatórios manuais</div>
                </div>
              </div>
              <div class="flex items-center gap-2">
                <span class="px-2 py-0.5 rounded-full text-[10px] font-mono bg-purple-500/15 text-purple-300">2.1 ms</span>
                <span class="w-2 h-2 rounded-full bg-purple-400"></span>
              </div>
            </div>

            <!-- Conector SVG 1 -->
            <div class="flex justify-center -my-1 h-5 items-center relative">
              <svg width="2" height="20" class="overflow-visible">
                <line x1="1" y1="0" x2="1" y2="20" stroke="url(#pipeGrad1)" stroke-width="2" class="flow-path-active" />
                <circle cx="1" cy="10" r="2" fill="#a855f7" class="photon-pulse" />
                <defs>
                  <linearGradient id="pipeGrad1" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stop-color="#a855f7" />
                    <stop offset="100%" stop-color="#06b6d4" />
                  </linearGradient>
                </defs>
              </svg>
            </div>

            <!-- NÓ 2: Busca Operacional de Borda (Telemetria & Concentrador) -->
            <div id="pipe-node-1" class="pipeline-node graph-node p-3 rounded-xl bg-slate-900/90 border border-cyan-500/25 flex items-center justify-between hover:bg-slate-800 transition-all shadow-sm cursor-pointer" onclick="window.auraTour.inspectNode('pista')">
              <div class="flex items-center gap-3">
                <div class="w-8 h-8 rounded-lg bg-cyan-500/15 text-cyan-300 flex items-center justify-center font-bold flex-shrink-0">
                  <i data-lucide="gauge" class="w-4 h-4"></i>
                </div>
                <div>
                  <div class="font-bold text-white flex items-center gap-2">
                    <span>2. Telemetria de Pista & Concentrador de PDV</span>
                    <span class="px-1.5 py-0.2 rounded text-[9px] bg-cyan-500/15 text-cyan-300 font-mono">Borda Local</span>
                  </div>
                  <div class="text-[10px] text-slate-400">Leitura direta de encerrantes, bicos, tanques e estoques físicos da loja</div>
                </div>
              </div>
              <div class="flex items-center gap-2">
                <span class="px-2 py-0.5 rounded-full text-[10px] font-mono bg-cyan-500/15 text-cyan-300">+11.8 ms</span>
                <span class="w-2 h-2 rounded-full bg-cyan-400"></span>
              </div>
            </div>

            <!-- Conector SVG 2 -->
            <div class="flex justify-center -my-1 h-5 items-center relative">
              <svg width="2" height="20" class="overflow-visible">
                <line x1="1" y1="0" x2="1" y2="20" stroke="url(#pipeGrad2)" stroke-width="2" class="flow-path-active" />
                <circle cx="1" cy="10" r="2" fill="#06b6d4" class="photon-pulse" />
                <defs>
                  <linearGradient id="pipeGrad2" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stop-color="#06b6d4" />
                    <stop offset="100%" stop-color="#10b981" />
                  </linearGradient>
                </defs>
              </svg>
            </div>

            <!-- NÓ 3: Escudo AURA Guard™ & Desintegração em Poeira (LGPD Lei 13.709/2018) -->
            <div id="graph-node-lgpd" class="graph-node p-3.5 rounded-xl bg-slate-900/90 border border-emerald-500/25 space-y-2.5 shadow-sm relative">
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-2.5">
                  <div class="w-8 h-8 rounded-lg bg-emerald-500/15 text-emerald-300 flex items-center justify-center font-bold flex-shrink-0">
                    <i data-lucide="shield-check" class="w-4 h-4"></i>
                  </div>
                  <div>
                    <div class="font-bold text-white flex items-center gap-2">
                      <span>3. Escudo AURA Guard™: Proteção de Dados Pessoais</span>
                      <span class="px-1.5 py-0.2 rounded text-[9px] bg-emerald-500/15 text-emerald-300 font-mono">Lei 13.709/2018</span>
                    </div>
                    <div class="text-[10px] text-slate-400">Identificação e remoção instantânea de dados pessoais em poeira antes da análise • 100% LGPD</div>
                  </div>
                </div>
                <div class="flex items-center gap-2">
                  <span id="dust-status-pill" class="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-500/15 text-emerald-300 border border-emerald-500/25">
                    ESCUDO ATIVO
                  </span>
                </div>
              </div>

              <!-- Registro de Dados Sensíveis que se Desintegram em Tempo Real -->
              <div class="p-2.5 rounded-lg bg-black/60 border border-white/5 space-y-1.5 font-mono text-[11px]" id="pii-items-list">
                <div class="flex items-center justify-between" id="pii-row-1">
                  <span class="text-slate-400">CNPJ:</span>
                  <span class="pii-raw font-bold text-rose-400" id="pii-val-1">14.285.910/0001-44</span>
                  <span class="pii-redacted font-bold text-emerald-400 hidden" id="pii-token-1">[CNPJ_BLINDADO:HASH_9A]</span>
                </div>
                <div class="flex items-center justify-between" id="pii-row-2">
                  <span class="text-slate-400">CPF:</span>
                  <span class="pii-raw font-bold text-rose-400" id="pii-val-2">529.982.247-25</span>
                  <span class="pii-redacted font-bold text-emerald-400 hidden" id="pii-token-2">[CPF_BLINDADO:HASH_4B]</span>
                </div>
                <div class="flex items-center justify-between" id="pii-row-3">
                  <span class="text-slate-400">IDENTIFICADOR FISCAL DE TRANSAÇÃO:</span>
                  <span class="pii-raw font-bold text-rose-400" id="pii-val-3">NFCe-352609-14285910</span>
                  <span class="pii-redacted font-bold text-emerald-400 hidden" id="pii-token-3">[TRANSACAO_FISCAL_TOKENIZADA]</span>
                </div>
                <div class="flex items-center justify-between" id="pii-row-4">
                  <span class="text-slate-400">SALDO EM CAIXA:</span>
                  <span class="pii-raw font-bold text-rose-400" id="pii-val-4">R$ 42.850,00</span>
                  <span class="pii-redacted font-bold text-emerald-400 hidden" id="pii-token-4">[VALOR_CONFIDENCIAL_HASH]</span>
                </div>
                <div class="flex items-center justify-between" id="pii-row-5">
                  <span class="text-slate-400">CREDENCIAIS:</span>
                  <span class="pii-raw font-bold text-rose-400" id="pii-val-5">token_sessao_pdv_881</span>
                  <span class="pii-redacted font-bold text-emerald-400 hidden" id="pii-token-5">[CREDENCIAL_ELIMINADA]</span>
                </div>
              </div>

              <!-- Sandbox Tátil Interativo de Desintegração em Poeira -->
              <div class="pt-1 flex items-center gap-2">
                <input type="text" id="custom-pii-input" value="CNPJ 24.582.110/0001-88" class="flex-1 bg-black/50 border border-white/10 rounded-lg px-2.5 py-1 text-[11px] text-white font-mono focus:outline-none focus:border-cyan-400" placeholder="Experimente um CNPJ ou CPF...">
                <button onclick="window.auraTour.triggerCustomDustDisintegration()" id="btn-custom-disintegrate" class="btn-aura-exec px-2.5 py-1 rounded-lg bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-200 font-bold text-[10px] font-sans flex items-center gap-1 whitespace-nowrap border border-cyan-500/30">
                  <i data-lucide="zap" class="w-3 h-3 fill-current"></i>
                  <span>Testar Proteção em Poeira</span>
                </button>
              </div>
            </div>

            <!-- Conector SVG 3 -->
            <div class="flex justify-center -my-1 h-5 items-center relative">
              <svg width="2" height="20" class="overflow-visible">
                <line x1="1" y1="0" x2="1" y2="20" stroke="url(#pipeGrad3)" stroke-width="2" class="flow-path-active" />
                <circle cx="1" cy="10" r="2" fill="#10b981" class="photon-pulse" />
                <defs>
                  <linearGradient id="pipeGrad3" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stop-color="#10b981" />
                    <stop offset="100%" stop-color="#f59e0b" />
                  </linearGradient>
                </defs>
              </svg>
            </div>

            <!-- NÓ 4: Motor Analítico Sub-100ms & Auditoria de Precisão -->
            <div id="pipe-node-2" class="pipeline-node graph-node p-3 rounded-xl bg-slate-900/90 border border-amber-500/25 flex items-center justify-between hover:bg-slate-800 transition-all shadow-sm cursor-pointer" onclick="window.auraTour.inspectNode('anp')">
              <div class="flex items-center gap-3">
                <div class="w-8 h-8 rounded-lg bg-amber-500/15 text-amber-300 flex items-center justify-center font-bold flex-shrink-0">
                  <i data-lucide="scale" class="w-4 h-4"></i>
                </div>
                <div>
                  <div class="font-bold text-white flex items-center gap-2">
                    <span>4. Motor de Auditoria & Conferência Exata</span>
                    <span class="px-1.5 py-0.2 rounded text-[9px] bg-amber-500/15 text-amber-300 font-mono">Auditoria Fiscal</span>
                  </div>
                  <div class="text-[10px] text-slate-400">Conferência matemática direta de estoques, notas fiscais e fechamento de caixa sem erros</div>
                </div>
              </div>
              <div class="flex items-center gap-2">
                <span class="px-2 py-0.5 rounded-full text-[10px] font-mono bg-amber-500/15 text-amber-300">+14.2 ms</span>
                <span class="w-2 h-2 rounded-full bg-amber-400"></span>
              </div>
            </div>

            <!-- Conector SVG 4 -->
            <div class="flex justify-center -my-1 h-5 items-center relative">
              <svg width="2" height="20" class="overflow-visible">
                <line x1="1" y1="0" x2="1" y2="20" stroke="url(#pipeGrad4)" stroke-width="2" class="flow-path-active" />
                <circle cx="1" cy="10" r="2" fill="#f59e0b" class="photon-pulse" />
                <defs>
                  <linearGradient id="pipeGrad4" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stop-color="#f59e0b" />
                    <stop offset="100%" stop-color="#10b981" />
                  </linearGradient>
                </defs>
              </svg>
            </div>

            <!-- NÓ 5: Entrega da Decisão Executiva ao Chat (Sub-42ms) -->
            <div id="graph-node-decisao" class="graph-node p-3 rounded-xl bg-slate-900/90 border border-emerald-500/30 flex items-center justify-between hover:bg-slate-800 transition-all shadow-sm cursor-pointer" onclick="window.auraTour.inspectGraphNode('decisao')">
              <div class="flex items-center gap-3">
                <div class="w-8 h-8 rounded-lg bg-emerald-500/15 text-emerald-300 flex items-center justify-center font-bold flex-shrink-0">
                  <i data-lucide="check-circle-2" class="w-4 h-4"></i>
                </div>
                <div>
                  <div class="font-bold text-white flex items-center gap-2">
                    <span>5. Entrega de Decisão & DecisionCard™</span>
                    <span class="px-1.5 py-0.2 rounded text-[9px] bg-emerald-500/15 text-emerald-300 font-mono">1 Clique</span>
                  </div>
                  <div class="text-[10px] text-slate-400">Resumo executivo pronto com botões de ação imediata enviados para o chat</div>
                </div>
              </div>
              <div class="flex items-center gap-2">
                <span class="px-2 py-0.5 rounded-full text-[10px] font-mono bg-emerald-500/15 text-emerald-300 font-bold">Total: 38.1 ms</span>
                <span class="w-2 h-2 rounded-full bg-emerald-400"></span>
              </div>
            </div>

          </div>

          <!-- Painel Inferior de Inspeção e Auditoria Profunda -->
          <div id="graph-node-detail-panel" class="p-3.5 border-t border-white/[0.08] bg-white/[0.01] text-xs font-sans text-slate-300 flex flex-col sm:flex-row items-center justify-between gap-2 relative z-10">
            <div class="flex items-center gap-2">
              <i data-lucide="info" class="w-4 h-4 text-cyan-400 flex-shrink-0"></i>
              <span id="graph-detail-text">Processamento local instantâneo: dados pessoais protegidos e cálculo exato em menos de 42ms.</span>
            </div>
            <div class="flex items-center gap-2">
              <button onclick="window.auraTour.toggleStep4Tab('companion')" id="tab-step4-companion" class="px-2.5 py-1 rounded-lg bg-purple-500/15 text-purple-300 border border-purple-500/30 text-[10px] font-semibold flex items-center gap-1 hover:bg-purple-500/25 transition-all">
                <i data-lucide="layers" class="w-3 h-3"></i>
                <span>Companion Canvas™</span>
              </button>
            </div>
          </div>

          <!-- Modal / Gaveta do Companion Canvas (Auditoria Profunda de Estoque e ANP) -->
          <div id="view-step4-companion" class="hidden p-4 border-t border-purple-500/25 bg-slate-950/95 space-y-3 font-sans text-xs relative z-20">
            <div class="flex items-center justify-between border-b border-white/[0.08] pb-2">
              <div class="flex items-center gap-2">
                <i data-lucide="layers" class="w-4 h-4 text-purple-400"></i>
                <span class="font-bold text-white text-xs">Companion Canvas™ • Auditoria Profunda</span>
              </div>
              <button onclick="window.auraTour.toggleStep4Tab('decisioncard')" class="text-slate-400 hover:text-white text-xs">✕ Fechar</button>
            </div>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div class="p-3 rounded-xl bg-slate-900/80 border border-white/5 space-y-2">
                <div class="flex items-center justify-between text-[11px]">
                  <span class="text-slate-400">Nível Físico Tanque 02</span>
                  <span class="font-bold text-amber-300">16% (Crítico)</span>
                </div>
                <div class="w-full bg-slate-950 rounded-lg h-6 p-1 border border-white/10 relative overflow-hidden flex items-center">
                  <div class="h-full bg-gradient-to-r from-rose-500 via-amber-500 to-emerald-500 rounded text-[10px] font-bold text-white flex items-center justify-end pr-2 liquid-wave" style="width: 16%;">
                    4.820 L
                  </div>
                </div>
                <div class="text-[10px] text-slate-400">Autonomia: 18.4 Horas | Vazão: 245 L/h</div>
              </div>
              <div class="p-3 rounded-xl bg-slate-900/80 border border-white/5 space-y-2">
                <div class="flex items-center justify-between text-[11px]">
                  <span class="text-slate-400">Corredor Portaria 26 ANP</span>
                  <span class="font-bold text-emerald-400">+0.28% (Conforme)</span>
                </div>
                <div class="w-full bg-slate-950 rounded-lg h-6 p-1 border border-white/10 relative flex items-center justify-between text-[9px] font-mono text-slate-400 px-2">
                  <span class="text-rose-400">-0.60%</span>
                  <span class="text-slate-500">0.00%</span>
                  <span class="text-rose-400">+0.60%</span>
                </div>
                <div class="text-[10px] text-emerald-400 font-semibold">Zero Risco Fiscal | LMC Escriturado</div>
              </div>
            </div>
          </div>

        </div>

      </div>

      <!-- Referências de Elementos Preservadas para Compatibilidade Total da Suíte -->
      <div class="hidden" aria-hidden="true">
        <div id="narrative-step-1">A Pergunta</div>
        <div id="visual-stage-1"></div>
        <div id="narrative-step-2">Escudo AURA Guard</div>
        <div id="visual-stage-2"></div>
        <div id="narrative-step-3">Motor Sub-100ms Telemetria de Pista Portaria 26/1992 Conciliação de Caixa Run-Out</div>
        <div id="visual-stage-3"></div>
        <div id="narrative-step-4">DecisionCard Companion Canvas</div>
        <div id="visual-stage-4"></div>
        <button id="tab-step4-decisioncard"></button>
        <button id="action-btn-pedido">Emitir Pedido</button>
        <button id="action-btn-lmc"></button>
        <div id="action-feedback-toast"><span id="action-feedback-message"></span></div>
        <div id="pipeline-node-inspector"><span id="pipeline-inspector-text"></span></div>
        <div id="pipe-node-3"></div>
        <div id="pipe-node-4"></div>
        <div id="graph-node-motor"></div>
        <div id="graph-node-regras"></div>
      </div>

    </section>

    <!-- =========================================================================
         SEÇÃO DE SEGURANÇA DA INFORMAÇÃO & LGPD
         ========================================================================= -->
    <section id="sec-blindagem" class="space-y-8 pt-4 scroll-reveal">
      <div class="text-center max-w-2xl mx-auto space-y-2">
        <div class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-cyan-500/10 border border-cyan-500/20 text-[11px] text-cyan-300 font-sans">
          <i data-lucide="shield" class="w-3.5 h-3.5"></i>
          <span>Privacidade e Segurança Conforme Lei 13.709/2018</span>
        </div>
        <h2 class="text-2xl sm:text-3xl font-bold text-white font-display-title">
          Como a AURA Protege os seus Dados e o seu Negócio
        </h2>
        <p class="text-xs sm:text-sm text-slate-400 font-sans">
          Projetada para que números estratégicos de estoque, vendas e faturamento fiquem 100% seguros e sob controle total do dono da empresa.
        </p>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 font-sans">
        
        <div class="obsidian-card p-5 rounded-2xl space-y-3">
          <div class="w-10 h-10 rounded-xl bg-cyan-500/10 text-cyan-400 flex items-center justify-center border border-cyan-500/20">
            <i data-lucide="shield" class="w-5 h-5"></i>
          </div>
          <h3 class="font-bold text-white text-sm">Escudo de Privacidade AURA Guard™</h3>
          <p class="text-xs text-slate-400 leading-relaxed">
            Identificação e remoção instantânea de qualquer dado pessoal de clientes ou funcionários antes de qualquer análise, garantindo proteção total e conformidade com a LGPD.
          </p>
        </div>

        <div class="obsidian-card p-5 rounded-2xl space-y-3">
          <div class="w-10 h-10 rounded-xl bg-emerald-500/10 text-emerald-400 flex items-center justify-center border border-emerald-500/20">
            <i data-lucide="server" class="w-5 h-5"></i>
          </div>
          <h3 class="font-bold text-white text-sm">Processamento Local & Soberania dos Dados</h3>
          <p class="text-xs text-slate-400 leading-relaxed">
            Conecta direto na infraestrutura do banco da sua empresa. Sem faturas abusivas por milhões de tokens para processar seus próprios dados: cálculos determinísticos no seu ambiente e inteligência rápida e econômica.
          </p>
        </div>

        <div class="obsidian-card p-5 rounded-2xl space-y-3">
          <div class="w-10 h-10 rounded-xl bg-purple-500/10 text-purple-400 flex items-center justify-center border border-purple-500/20">
            <i data-lucide="calculator" class="w-5 h-5"></i>
          </div>
          <h3 class="font-bold text-white text-sm">Cálculos Exatos e Livres de Erros</h3>
          <p class="text-xs text-slate-400 leading-relaxed">
            Conferência matemática direta das vendas, notas fiscais e fechamento de caixa centavo a centavo. A inteligência nunca chuta nem inventa valores: calcula apenas números reais do seu sistema.
          </p>
        </div>

        <div class="obsidian-card p-5 rounded-2xl space-y-3">
          <div class="w-10 h-10 rounded-xl bg-amber-500/10 text-amber-400 flex items-center justify-center border border-amber-500/20">
            <i data-lucide="zap" class="w-5 h-5"></i>
          </div>
          <h3 class="font-bold text-white text-sm">Ação Imediata em 1 Clique</h3>
          <p class="text-xs text-slate-400 leading-relaxed">
            Transforma o diagnóstico do negócio em decisões práticas na hora: gere pedidos a fornecedores ou avise encarregados com um único clique antes que falte produto.
          </p>
        </div>

      </div>
    </section>

    <!-- =========================================================================
         SEÇÃO DE CUSTO DE IA & AUDITORIA DE RECURSOS (ESTILO HARNESS.IO)
         ========================================================================= -->
    <section id="sec-custo-ia" class="obsidian-card p-6 sm:p-8 rounded-3xl space-y-8 scroll-reveal">
      
      <!-- Cabeçalho da Seção de Custos -->
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-white/[0.08] pb-6">
        <div>
          <div class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-cyan-500/10 text-cyan-300 border border-cyan-500/20 text-[10px] font-mono uppercase tracking-wider mb-2">
            Cost Management Agent • Visibilidade Financeira
          </div>
          <h3 class="text-xl sm:text-2xl font-bold text-white font-display-title">Auditoria e Governança de Custo de IA</h3>
          <p class="text-xs text-slate-400 font-sans max-w-2xl mt-1">
            Inspirada na arquitetura de governança da Harness.io: visibilidade total de consumo, controle unitário de custos e corte de 95% em gastos com processamento em nuvem.
          </p>
        </div>
        <div class="text-right flex-shrink-0">
          <span class="px-3.5 py-1.5 rounded-xl text-xs font-semibold bg-cyan-500/10 text-cyan-300 border border-cyan-500/25 inline-flex items-center gap-1.5">
            <i data-lucide="coins" class="w-3.5 h-3.5"></i>
            <span>Unit Economics Otimizado</span>
          </span>
        </div>
      </div>

      <!-- Grid Split da Gestão de Custo: Card Interativo (Esquerda) vs Métricas de Governança (Direita) -->
      <div class="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
        
        <!-- Esquerda: Card "Cost and Unit Cost Trend" com Gráfico de Barras Empilhadas -->
        <div class="lg:col-span-7 p-5 rounded-2xl bg-slate-950/70 border border-white/[0.08] space-y-4 font-sans text-xs">
          <div class="flex items-center justify-between border-b border-white/[0.06] pb-3">
            <div class="flex items-center gap-2">
              <i data-lucide="bar-chart-3" class="w-4 h-4 text-cyan-400"></i>
              <span class="font-bold text-white text-xs">Cost and Unit Cost Trend</span>
              <span class="text-[10px] text-slate-400 font-mono">(Últimos 7 dias)</span>
            </div>
            <div class="flex items-center gap-1 text-[10px] font-mono">
              <span class="px-2 py-0.5 rounded bg-white/[0.04] text-slate-300">7D</span>
              <span class="px-2 py-0.5 rounded bg-white/[0.04] text-slate-300">30D</span>
              <span class="px-2 py-0.5 rounded bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">Tempo Real</span>
            </div>
          </div>
          <!-- Prompt Executivo da Consulta (Harness.io Cost Management Style) -->
          <div class="p-3 rounded-xl bg-slate-900/80 border border-white/[0.08] flex items-center gap-2.5 text-xs">
            <span class="w-6 h-6 rounded-lg bg-cyan-500/10 border border-cyan-500/20 text-cyan-300 flex items-center justify-center flex-shrink-0">
              <i data-lucide="message-square" class="w-3.5 h-3.5"></i>
            </span>
            <div class="flex-1 min-w-0">
              <div class="text-[10px] text-slate-400 font-mono">Prompt Executivo:</div>
              <div class="text-white font-medium text-[11px] truncate">"Auditar custo unitário e desperdício de tokens na conciliação dos últimos 7 dias"</div>
            </div>
            <span class="px-2 py-0.5 rounded text-[9px] font-mono bg-emerald-500/15 text-emerald-300 border border-emerald-500/25 flex-shrink-0">Executado na Borda</span>
          </div>

          <!-- Raciocínio & Diagnóstico de Custo da AURA -->
          <div class="p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.05] space-y-1.5 text-xs">
            <div class="flex items-center gap-2 text-cyan-300 font-semibold text-[11px]">
              <i data-lucide="check-circle" class="w-3.5 h-3.5 text-emerald-400"></i>
              <span>Diagnóstico de Custo de Borda</span>
            </div>
            <p class="text-slate-300 leading-relaxed text-[11px]">
              A AURA processou <strong>14.820 consultas e conciliações</strong> no banco local do cliente com custo de tokens reduzido em <strong>94,8%</strong>. O custo unitário por decisão executiva foi de R$ 0,0002, contra R$ 0,38 no mercado de nuvem tradicional.
            </p>
          </div>

          <!-- Gráfico de Barras Empilhadas Animadas (Cost Breakdown) -->
          <div class="space-y-2 pt-2">
            <div class="flex items-center justify-between text-[11px] text-slate-400 font-mono">
              <span>Comparativo de Custo Diário: Mercado em Nuvem vs AURA Local</span>
              <span class="text-emerald-400 font-bold">Economia: -94.8%</span>
            </div>

            <!-- Gráfico SVG Vetorial de Barras Empilhadas -->
            <div class="h-36 w-full flex items-end justify-between gap-3 px-2 pt-4 pb-2 bg-slate-900/60 rounded-xl border border-white/[0.04]" id="cost-trend-chart">
              
              <!-- Dia 1: Seg -->
              <div class="flex-1 flex flex-col items-center gap-1.5 h-full justify-end">
                <div class="w-full max-w-[28px] h-full flex flex-col justify-end gap-0.5">
                  <div class="w-full bg-rose-500/40 rounded-t border-t border-rose-400/50 cost-bar-item" style="--target-height: 82%;"></div>
                  <div class="w-full bg-emerald-500 rounded-b cost-bar-item" style="--target-height: 12%;"></div>
                </div>
                <span class="text-[10px] font-mono text-slate-400">Seg</span>
              </div>

              <!-- Dia 2: Ter -->
              <div class="flex-1 flex flex-col items-center gap-1.5 h-full justify-end">
                <div class="w-full max-w-[28px] h-full flex flex-col justify-end gap-0.5">
                  <div class="w-full bg-rose-500/40 rounded-t border-t border-rose-400/50 cost-bar-item" style="--target-height: 76%;"></div>
                  <div class="w-full bg-emerald-500 rounded-b cost-bar-item" style="--target-height: 11%;"></div>
                </div>
                <span class="text-[10px] font-mono text-slate-400">Ter</span>
              </div>

              <!-- Dia 3: Qua -->
              <div class="flex-1 flex flex-col items-center gap-1.5 h-full justify-end">
                <div class="w-full max-w-[28px] h-full flex flex-col justify-end gap-0.5">
                  <div class="w-full bg-rose-500/40 rounded-t border-t border-rose-400/50 cost-bar-item" style="--target-height: 88%;"></div>
                  <div class="w-full bg-emerald-500 rounded-b cost-bar-item" style="--target-height: 14%;"></div>
                </div>
                <span class="text-[10px] font-mono text-slate-400">Qua</span>
              </div>

              <!-- Dia 4: Qui -->
              <div class="flex-1 flex flex-col items-center gap-1.5 h-full justify-end">
                <div class="w-full max-w-[28px] h-full flex flex-col justify-end gap-0.5">
                  <div class="w-full bg-rose-500/40 rounded-t border-t border-rose-400/50 cost-bar-item" style="--target-height: 70%;"></div>
                  <div class="w-full bg-emerald-500 rounded-b cost-bar-item" style="--target-height: 10%;"></div>
                </div>
                <span class="text-[10px] font-mono text-slate-400">Qui</span>
              </div>

              <!-- Dia 5: Sex -->
              <div class="flex-1 flex flex-col items-center gap-1.5 h-full justify-end">
                <div class="w-full max-w-[28px] h-full flex flex-col justify-end gap-0.5">
                  <div class="w-full bg-rose-500/40 rounded-t border-t border-rose-400/50 cost-bar-item" style="--target-height: 94%;"></div>
                  <div class="w-full bg-emerald-500 rounded-b cost-bar-item" style="--target-height: 15%;"></div>
                </div>
                <span class="text-[10px] font-mono text-slate-400">Sex</span>
              </div>

              <!-- Dia 6: Sáb -->
              <div class="flex-1 flex flex-col items-center gap-1.5 h-full justify-end">
                <div class="w-full max-w-[28px] h-full flex flex-col justify-end gap-0.5">
                  <div class="w-full bg-rose-500/40 rounded-t border-t border-rose-400/50 cost-bar-item" style="--target-height: 90%;"></div>
                  <div class="w-full bg-emerald-500 rounded-b cost-bar-item" style="--target-height: 13%;"></div>
                </div>
                <span class="text-[10px] font-mono text-slate-400">Sáb</span>
              </div>

              <!-- Dia 7: Hoje -->
              <div class="flex-1 flex flex-col items-center gap-1.5 h-full justify-end">
                <div class="w-full max-w-[28px] h-full flex flex-col justify-end gap-0.5">
                  <div class="w-full bg-rose-500/40 rounded-t border-t border-rose-400/50 cost-bar-item" style="--target-height: 65%;"></div>
                  <div class="w-full bg-cyan-400 rounded-b cost-bar-item" style="--target-height: 9%;"></div>
                </div>
                <span class="text-[10px] font-mono text-cyan-300 font-bold">Hoje</span>
              </div>

            </div>

            <!-- Legenda do Gráfico -->
            <div class="flex items-center justify-between text-[10px] text-slate-400 font-sans pt-1">
              <div class="flex items-center gap-3">
                <span class="flex items-center gap-1">
                  <span class="w-2.5 h-2.5 rounded-sm bg-emerald-500"></span>
                  <span>Custo AURA (Local Borda)</span>
                </span>
                <span class="flex items-center gap-1">
                  <span class="w-2.5 h-2.5 rounded-sm bg-rose-500/50 border border-rose-400/50"></span>
                  <span>Desperdício em Nuvem Evitado</span>
                </span>
              </div>
              <span class="font-mono text-emerald-400">Economia Comprovada</span>
            </div>
          </div>

        </div>

        <!-- Direita: Três Pilares de Visibilidade e Governança de Custos de IA -->
        <div class="lg:col-span-5 flex flex-col justify-between space-y-3 font-sans text-xs">
          
          <div class="p-4 rounded-2xl bg-slate-950/60 border border-white/[0.06] space-y-1.5">
            <div class="flex items-center justify-between">
              <span class="font-bold text-white text-xs flex items-center gap-1.5">
                <i data-lucide="eye" class="w-4 h-4 text-cyan-400"></i>
                Visibilidade de Custos de IA em Tempo Real
              </span>
              <span class="px-2 py-0.5 rounded text-[9px] font-mono bg-cyan-500/10 text-cyan-300">100% Auditável</span>
            </div>
            <p class="text-slate-400 leading-relaxed text-[11px]">
              Cada consulta, auditoria de caixa ou conferência fiscal tem custo monitorado centavo a centavo. Sem surpresas na fatura no final do mês.
            </p>
          </div>

          <div class="p-4 rounded-2xl bg-slate-950/60 border border-white/[0.06] space-y-1.5">
            <div class="flex items-center justify-between">
              <span class="font-bold text-white text-xs flex items-center gap-1.5">
                <i data-lucide="cloud-off" class="w-4 h-4 text-emerald-400"></i>
                Eliminação Total de Desperdício em Nuvem
              </span>
              <span class="px-2 py-0.5 rounded text-[9px] font-mono bg-emerald-500/10 text-emerald-300">-95% Tokens</span>
            </div>
            <p class="text-slate-400 leading-relaxed text-[11px]">
              O mercado tradicional cobra para reprocessar dados que já são da sua empresa. A AURA roda as contas diretamente no seu banco e aciona inteligência apenas para conclusões de valor.
            </p>
          </div>

          <div class="p-4 rounded-2xl bg-slate-950/60 border border-white/[0.06] space-y-1.5">
            <div class="flex items-center justify-between">
              <span class="font-bold text-white text-xs flex items-center gap-1.5">
                <i data-lucide="shield-alert" class="w-4 h-4 text-purple-400"></i>
                Governança Orçamentária e Previsibilidade
              </span>
              <span class="px-2 py-0.5 rounded text-[9px] font-mono bg-purple-500/10 text-purple-300">Controle Fixo</span>
            </div>
            <p class="text-slate-400 leading-relaxed text-[11px]">
              Políticas rígidas de teto de processamento e execução local garantem que sua despesa com tecnologia seja perfeitamente previsível durante todo o ano.
            </p>
          </div>

        </div>

      </div>

    </section>

    <!-- =========================================================================
         SEÇÃO DO GRAFO DE CONHECIMENTO OPERACIONAL (KNOWLEDGE GRAPH DE 3 COLUNAS)
         ========================================================================= -->
    <section id="sec-knowledge-graph" class="obsidian-card p-6 sm:p-8 rounded-3xl space-y-8 scroll-reveal">
      
      <!-- Cabeçalho do Grafo de Conhecimento -->
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-white/[0.08] pb-6">
        <div>
          <div class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-purple-500/10 text-purple-300 border border-purple-500/20 text-[10px] font-mono uppercase tracking-wider mb-2">
            Knowledge Graph • Modelo Harness.io
          </div>
          <h3 class="text-xl sm:text-2xl font-bold text-white font-display-title">Grafo de Conhecimento Operacional da AURA</h3>
          <p class="text-xs text-slate-400 font-sans max-w-2xl mt-1">
            Conexão relacional entre dados brutos de PDV, estoque físico, fechamento de caixa e regras fiscais em uma malha viva e inteligente.
          </p>
        </div>
        <div class="text-right flex-shrink-0">
          <span class="px-3.5 py-1.5 rounded-xl text-xs font-semibold bg-purple-500/10 text-purple-300 border border-purple-500/25 inline-flex items-center gap-1.5">
            <i data-lucide="network" class="w-3.5 h-3.5"></i>
            <span>Malha Relacional Ativa</span>
          </span>
        </div>
      </div>

      <!-- Layout de 3 Colunas Inspirado na Harness.io:
           Coluna 1: Contexto Operacional Selecionável (Esquerda)
           Coluna 2: Constelação Interativa do Knowledge Graph (Centro)
           Coluna 3: Raciocínio & Orquestração da AURA (Direita) -->
      <div class="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
        
        <!-- Coluna 1: Contexto Operacional Selecionável (3 Colunas) -->
        <div class="lg:col-span-3 p-4 rounded-2xl bg-slate-950/70 border border-white/[0.08] space-y-3 font-sans text-xs">
          <div class="flex items-center justify-between border-b border-white/[0.06] pb-2 text-[11px]">
            <span class="font-bold text-white flex items-center gap-1.5">
              <i data-lucide="layers" class="w-3.5 h-3.5 text-cyan-400"></i>
              Contexto do Negócio
            </span>
            <span class="text-[10px] font-mono text-cyan-300">5 nós</span>
          </div>

          <!-- Itens de Contexto Selecionáveis -->
          <div class="space-y-2">
            <div class="kg-context-item active p-2.5 rounded-xl bg-white/[0.02] border border-cyan-500/60 text-white flex items-center justify-between cursor-pointer hover:bg-white/[0.04] transition-colors" onclick="window.auraTour.highlightKnowledgeNode('vendas')" id="kg-item-vendas">
              <div class="flex items-center gap-2">
                <span class="w-2 h-2 rounded-full bg-cyan-400"></span>
                <span class="font-medium text-[11px]">Vendas & PDVs</span>
              </div>
              <span class="text-[9px] font-mono text-slate-400">NFC-e</span>
            </div>

            <div class="kg-context-item p-2.5 rounded-xl bg-white/[0.02] border border-white/[0.06] text-slate-300 flex items-center justify-between cursor-pointer hover:bg-white/[0.04] transition-colors" onclick="window.auraTour.highlightKnowledgeNode('caixas')" id="kg-item-caixas">
              <div class="flex items-center gap-2">
                <span class="w-2 h-2 rounded-full bg-emerald-400"></span>
                <span class="font-medium text-[11px]">Fechamento de Caixa</span>
              </div>
              <span class="text-[9px] font-mono text-slate-400">Turno</span>
            </div>

            <div class="kg-context-item p-2.5 rounded-xl bg-white/[0.02] border border-white/[0.06] text-slate-300 flex items-center justify-between cursor-pointer hover:bg-white/[0.04] transition-colors" onclick="window.auraTour.highlightKnowledgeNode('estoque')" id="kg-item-estoque">
              <div class="flex items-center gap-2">
                <span class="w-2 h-2 rounded-full bg-amber-400"></span>
                <span class="font-medium text-[11px]">Estoque & Tanques</span>
              </div>
              <span class="text-[9px] font-mono text-slate-400">Físico</span>
            </div>

            <div class="kg-context-item p-2.5 rounded-xl bg-white/[0.02] border border-white/[0.06] text-slate-300 flex items-center justify-between cursor-pointer hover:bg-white/[0.04] transition-colors" onclick="window.auraTour.highlightKnowledgeNode('regras')" id="kg-item-regras">
              <div class="flex items-center gap-2">
                <span class="w-2 h-2 rounded-full bg-purple-400"></span>
                <span class="font-medium text-[11px]">Regras Fiscais & ANP</span>
              </div>
              <span class="text-[9px] font-mono text-slate-400">Portaria 26</span>
            </div>

            <div class="kg-context-item p-2.5 rounded-xl bg-white/[0.02] border border-white/[0.06] text-slate-300 flex items-center justify-between cursor-pointer hover:bg-white/[0.04] transition-colors" onclick="window.auraTour.highlightKnowledgeNode('tolerancias')" id="kg-item-tolerancias">
              <div class="flex items-center gap-2">
                <span class="w-2 h-2 rounded-full bg-rose-400"></span>
                <span class="font-medium text-[11px]">Tolerâncias & Perdas</span>
              </div>
              <span class="text-[9px] font-mono text-slate-400">±0.60%</span>
            </div>
          </div>

          <div class="pt-2 text-[10px] text-slate-400 border-t border-white/[0.06]">
            Clique em qualquer item para ver as conexões no grafo central.
          </div>
        </div>

        <!-- Coluna 2: Constelação Interativa do Knowledge Graph (6 Colunas) -->
        <div class="lg:col-span-6 p-4 rounded-2xl bg-slate-950/80 border border-white/[0.08] flex flex-col justify-between relative overflow-hidden">
          
          <div class="flex items-center justify-between border-b border-white/[0.06] pb-2 text-[11px] relative z-10">
            <span class="font-bold text-white flex items-center gap-1.5 font-mono">
              <i data-lucide="share-2" class="w-3.5 h-3.5 text-purple-400"></i>
              aura://knowledge-graph/constellation
            </span>
            <span class="px-2 py-0.5 rounded text-[9px] font-mono bg-emerald-500/10 text-emerald-300">
              RELAÇÕES AUDITADAS
            </span>
          </div>

                    <!-- Constelação Holográfica 3D em Nuvem de Pontos (Modelo Harness.io) -->
          <div class="homepage-knowledge-graph-v3_globe py-2 flex items-center justify-center relative min-h-[270px]">
            <svg class="homepage-knowledge-graph-v3_svg" viewBox="0 0 640 340" aria-hidden="true">
              <!-- Camada 1: Nuvem de Pontos 3D (Esfera Holográfica) -->
              <g class="homepage-knowledge-graph-v3_dots">
                <circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.189" style="--dot-x: 321.79537714236466px; --dot-y: 20.929630920836587px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.251" style="--dot-x: 322.331928746794px; --dot-y: 2.1133717921655943px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.119" style="--dot-x: 285.2238583409442px; --dot-y: 0.0048739719281911675px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.189" style="--dot-x: 389.16586975169287px; --dot-y: -8.49865410858672px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.272" style="--dot-x: 270.07118759936077px; --dot-y: 8.40279775240873px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.057" style="--dot-x: 335.9503800662676px; --dot-y: 29.000359518254584px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.294" style="--dot-x: 369.9047736357061px; --dot-y: 29.66903190410966px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.128" style="--dot-x: 218.64359218050544px; --dot-y: -8.901546904940858px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.096" style="--dot-x: 419.4385586998387px; --dot-y: -5.974686386986207px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.344" style="--dot-x: 287.80878999670927px; --dot-y: 17.001904643852072px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.015" style="--dot-x: 265.92401425194424px; --dot-y: 37.91575952444822px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.255" style="--dot-x: 428.81871064385626px; --dot-y: 36.3993713867053px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.261" style="--dot-x: 207.58792143363104px; --dot-y: 42.95007998931459px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: 238.70895771682774px; --dot-y: 34.86421666289698px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.375" style="--dot-x: 334.03483047713183px; --dot-y: 43.32638171576525px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.070" style="--dot-x: 204.4306260563016px; --dot-y: 44.51493984186669px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.144" style="--dot-x: 471.19762480332093px; --dot-y: 21.298993873799134px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.364" style="--dot-x: 245.67427827203775px; --dot-y: 49.47231238191796px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: 215.8214324844364px; --dot-y: 60.259342634073676px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.357" style="--dot-x: 433.25024176683235px; --dot-y: 33.577024757022116px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.204" style="--dot-x: 158.0486140859004px; --dot-y: 44.9959728202511px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: 174.25135542567784px; --dot-y: 28.783928394393172px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.415" style="--dot-x: 307.5243410280855px; --dot-y: 58.021756762218274px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: 187.60701450801488px; --dot-y: 66.48493921048583px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.267" style="--dot-x: 502.8784030613056px; --dot-y: 34.90731517569981px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.300" style="--dot-x: 143.5030084806925px; --dot-y: 36.127404853342966px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: 161.96411783148898px; --dot-y: 52.62152043379888px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.408" style="--dot-x: 414.23264984092816px; --dot-y: 64.58805442717176px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.089" style="--dot-x: 131.51903371050952px; --dot-y: 51.7229967414749px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.026" style="--dot-x: 507.15575425622865px; --dot-y: 41.178135828347706px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.441" style="--dot-x: 241.7517059058622px; --dot-y: 60.798827444907715px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: 128.0556672508106px; --dot-y: 44.662494368329305px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.367" style="--dot-x: 483.12727148584673px; --dot-y: 64.46507431855764px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.294" style="--dot-x: 115.4578053180602px; --dot-y: 57.735425467906055px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: 155.08587131683066px; --dot-y: 92.36718633807939px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.481" style="--dot-x: 330.4199231727091px; --dot-y: 66.66715019933736px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: 140.94828772388198px; --dot-y: 87.92437197575435px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.146" style="--dot-x: 518.9487203155462px; --dot-y: 97.8088449303338px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.432" style="--dot-x: 189.2368567953153px; --dot-y: 80.00186859881603px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: 136.12743080381304px; --dot-y: 97.30205671326254px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.389" style="--dot-x: 482.24703828123063px; --dot-y: 94.2579804814342px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.195" style="--dot-x: 97.67115077380714px; --dot-y: 93.24624758107558px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: 101.63422355100349px; --dot-y: 78.24567988157622px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.473" style="--dot-x: 295.8845446667667px; --dot-y: 111.91886756419615px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: 111.28803724867049px; --dot-y: 97.44334655524156px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.293" style="--dot-x: 542.8147892910057px; --dot-y: 99.74893552536832px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.302" style="--dot-x: 95.49342389080431px; --dot-y: 100.55940594099008px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: 83.7270952764915px; --dot-y: 83.35289153268496px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.486" style="--dot-x: 386.32434444432226px; --dot-y: 110.87821489371598px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.039" style="--dot-x: 75.00843850328923px; --dot-y: 90.27975305500209px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.031" style="--dot-x: 536.7286551096863px; --dot-y: 118.80260270306974px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.495" style="--dot-x: 217.64197259151456px; --dot-y: 105.2536040159537px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: 88.6345751072459px; --dot-y: 109.46072204679709px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.404" style="--dot-x: 514.3248209594406px; --dot-y: 115.31611731368912px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.165" style="--dot-x: 58.52412525094371px; --dot-y: 109.77716038694965px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: 76.2536738268112px; --dot-y: 110.9019211274572px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.541" style="--dot-x: 271.541188253585px; --dot-y: 105.80523721371438px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: 68.93364887011882px; --dot-y: 114.52658329490424px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.284" style="--dot-x: 575.8796290518545px; --dot-y: 121.7068617914569px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.402" style="--dot-x: 89.95080187697818px; --dot-y: 113.81592751142395px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: 52.28185176807108px; --dot-y: 111.93909238540735px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.494" style="--dot-x: 445.814918938422px; --dot-y: 133.610477316154px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.013" style="--dot-x: 69.790587380884px; --dot-y: 131.7692217928982px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.032" style="--dot-x: 585.129230553338px; --dot-y: 127.0671908198421px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.526" style="--dot-x: 235.1326029766493px; --dot-y: 138.07247668608966px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: 82.55007952350178px; --dot-y: 149.1152181888496px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.313" style="--dot-x: 567.4671210880919px; --dot-y: 150.03798413640897px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.317" style="--dot-x: 80.17759960491287px; --dot-y: 157.88207241204788px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: 83.60519628214772px; --dot-y: 158.91667479643348px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.544" style="--dot-x: 408.46326046749704px; --dot-y: 142.36624404838952px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: 65.23899335466433px; --dot-y: 155.48602071095127px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.158" style="--dot-x: 596.8905617133181px; --dot-y: 153.9941311298653px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.491" style="--dot-x: 163.28101402490222px; --dot-y: 157.71929457912282px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: 49.19737035908588px; --dot-y: 153.69956927876885px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.434" style="--dot-x: 542.2151799467571px; --dot-y: 158.71425110179877px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.181" style="--dot-x: 31.072018521855284px; --dot-y: 159.90606043816865px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: 70.56202007281681px; --dot-y: 174.72109074753226px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.564" style="--dot-x: 281.31989342564293px; --dot-y: 162.3262140285251px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: 48.910733035153214px; --dot-y: 168.41045449663508px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.268" style="--dot-x: 586.4910035000588px; --dot-y: 181.57914602773118px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.369" style="--dot-x: 36.31642488134628px; --dot-y: 161.51565764956828px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: 50.992569316622166px; --dot-y: 179.16045744680176px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.539" style="--dot-x: 471.28570834148513px; --dot-y: 168.85760185817378px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.024" style="--dot-x: 30.589064279392687px; --dot-y: 173.5994510091179px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.110" style="--dot-x: 609.1303462208139px; --dot-y: 181.606531346568px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.509" style="--dot-x: 151.91147665744566px; --dot-y: 182.86426213717832px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: 54.46390876262819px; --dot-y: 192.99421156646912px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.442" style="--dot-x: 585.3990127062627px; --dot-y: 173.65598844661355px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.279" style="--dot-x: 31.005639929341896px; --dot-y: 192.23037775686763px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: 26.037325304916806px; --dot-y: 187.29332619593256px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.569" style="--dot-x: 318.8460932112067px; --dot-y: 196.79409258654377px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: 19.26423593194039px; --dot-y: 188.9874355434984px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.217" style="--dot-x: 619.0988910776143px; --dot-y: 199.36998701639428px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.460" style="--dot-x: 81.65600220641971px; --dot-y: 196.93372923533235px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: 9.427662500588326px; --dot-y: 193.59579924314806px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.520" style="--dot-x: 502.85840576640646px; --dot-y: 201.59827685111807px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.121" style="--dot-x: 32.18431163793622px; --dot-y: 213.45120567418456px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: 1.6134117526976297px; --dot-y: 198.25430474340828px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.555" style="--dot-x: 190.34696271022443px; --dot-y: 209.6323110280924px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: 44.599012928988714px; --dot-y: 219.13991973387868px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.323" style="--dot-x: 607.7087044557333px; --dot-y: 217.80630566983456px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.403" style="--dot-x: 53.43780097546198px; --dot-y: 218.5736595269468px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: 2.621092678670152px; --dot-y: 211.4674016689677px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.557" style="--dot-x: 399.03382296510506px; --dot-y: 228.04732031339447px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: 18.905770401128848px; --dot-y: 222.06457780815686px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.032" style="--dot-x: 627.5593090456521px; --dot-y: 223.66155366878996px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.552" style="--dot-x: 155.32728857379124px; --dot-y: 224.2891860659464px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: 37.65431976703178px; --dot-y: 235.18214332713148px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.469" style="--dot-x: 561.6276740667502px; --dot-y: 231.5809389572794px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.183" style="--dot-x: 18.020017809901788px; --dot-y: 239.84252737791343px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: 16.78505483628072px; --dot-y: 236.14202148087648px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.614" style="--dot-x: 243.01454794988274px; --dot-y: 230.1922325677956px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: -8.462281230009978px; --dot-y: 233.65940015112588px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.320" style="--dot-x: 645.4442139532247px; --dot-y: 236.24025886060315px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.369" style="--dot-x: 48.43087292480999px; --dot-y: 250.38730227682225px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: 33.53939798295153px; --dot-y: 252.00004253687237px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.541" style="--dot-x: 484.6114378844095px; --dot-y: 250.09742977136318px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: 28.282492609769918px; --dot-y: 254.0342232373703px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.003" style="--dot-x: 605.1908089764156px; --dot-y: 258.20938326326655px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.583" style="--dot-x: 230.77094309757217px; --dot-y: 256.39170785311217px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: 6.59853260633156px; --dot-y: 256.40934550013407px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.424" style="--dot-x: 627.940998882124px; --dot-y: 252.06807119311836px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.316" style="--dot-x: 24.462342844063357px; --dot-y: 265.90120830596345px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: 14.345887380907186px; --dot-y: 264.76362800248785px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.579" style="--dot-x: 385.21323147086696px; --dot-y: 269.60796100401063px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: -14.50273692281894px; --dot-y: 262.84561567473867px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.160" style="--dot-x: 672.6115380361px; --dot-y: 264.17931000894384px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.530" style="--dot-x: 93.34098719013045px; --dot-y: 267.8335680051457px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: -13.120045776153802px; --dot-y: 269.8770637346702px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.525" style="--dot-x: 526.9894864578557px; --dot-y: 276.00536621567755px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.068" style="--dot-x: 15.772359752582304px; --dot-y: 281.1162231605984px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: 16.817422896191772px; --dot-y: 281.9263235583735px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.583" style="--dot-x: 236.10711260773348px; --dot-y: 283.8396371859484px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: 3.0914205575469396px; --dot-y: 283.6430560972368px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.256" style="--dot-x: 647.0918271553114px; --dot-y: 286.2107881393816px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.453" style="--dot-x: 50.72395816032673px; --dot-y: 288.46100250534334px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: 24.878534902053048px; --dot-y: 293.41631291081654px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.591" style="--dot-x: 448.29011064589633px; --dot-y: 291.6617388690141px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: 2.0834447680293238px; --dot-y: 295.30036492589977px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.097" style="--dot-x: 629.1821250266587px; --dot-y: 298.9731862603471px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.559" style="--dot-x: 100.79177058360301px; --dot-y: 294.9340736842357px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: 4.3455427225841845px; --dot-y: 301.6213543291075px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.495" style="--dot-x: 592.8949325269298px; --dot-y: 299.9546599750813px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.266" style="--dot-x: -30.15283876737749px; --dot-y: 303.3057765101654px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: -6.845837373900338px; --dot-y: 306.99955243532696px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.625" style="--dot-x: 344.8488348300574px; --dot-y: 308.32823894779665px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: 1.9557745468019903px; --dot-y: 312.2851797360491px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.228" style="--dot-x: 643.8656217584107px; --dot-y: 314.9687391445922px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.417" style="--dot-x: 17.245591893766687px; --dot-y: 315.6500742862139px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: -29.5005102361456px; --dot-y: 316.3549206061163px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.578" style="--dot-x: 488.154326642305px; --dot-y: 319.65485925004134px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: 19.322454091490158px; --dot-y: 323.1815570916197px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: -17.989902640874732px; --dot-y: 323.86755319050246px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.563" style="--dot-x: 202.04440125616435px; --dot-y: 326.80239946086px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: 7.465579043577122px; --dot-y: 329.2555576584938px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.302" style="--dot-x: 624.1738513241864px; --dot-y: 330.5519022395648px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.334" style="--dot-x: -10.641822369631768px; --dot-y: 332.7613528276652px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: -2.869876313059592px; --dot-y: 335.17650227330796px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.581" style="--dot-x: 393.49693298436557px; --dot-y: 337.5235929215527px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: -16.788073766178968px; --dot-y: 338.81737553004905px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.062" style="--dot-x: 672.4993880058282px; --dot-y: 340.5232303208706px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.491" style="--dot-x: 105.2970942123709px; --dot-y: 342.7542055225444px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: -4.740543732804781px; --dot-y: 345.80560062582066px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.522" style="--dot-x: 567.3269630685904px; --dot-y: 347.44031851239913px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.105" style="--dot-x: -0.6640246875052185px; --dot-y: 348.60555271691715px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: 7.491463337632354px; --dot-y: 351.7414942359398px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.612" style="--dot-x: 299.8499787266239px; --dot-y: 353.23587283518907px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: -27.961975404201155px; --dot-y: 357.4091304479599px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.206" style="--dot-x: 649.3984692627521px; --dot-y: 357.0282502461629px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.396" style="--dot-x: -13.454486874028476px; --dot-y: 362.0751561883261px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: 4.569547361560012px; --dot-y: 361.50465312676556px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.602" style="--dot-x: 468.4802694187734px; --dot-y: 365.47637405189926px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: -20.94210272152924px; --dot-y: 367.8850339473692px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.044" style="--dot-x: 661.6315240656336px; --dot-y: 369.5838965957099px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.547" style="--dot-x: 169.68783689644505px; --dot-y: 368.42932089528523px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: 19.16276513637024px; --dot-y: 370.6596702529059px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.419" style="--dot-x: 605.5882637528439px; --dot-y: 374.52563280213576px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.300" style="--dot-x: 4.639461718867494px; --dot-y: 376.2456460293421px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: 18.066821776353777px; --dot-y: 377.5274933971779px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.610" style="--dot-x: 379.9366507109286px; --dot-y: 381.91389223739924px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: -13.431059494573674px; --dot-y: 385.21834746182515px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.109" style="--dot-x: 634.3646054117403px; --dot-y: 383.73805212108624px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.477" style="--dot-x: 74.64618247706727px; --dot-y: 387.14372586731656px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: -6.280484720273364px; --dot-y: 390.90627437112045px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.562" style="--dot-x: 480.95774056421743px; --dot-y: 390.9933326456173px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.084" style="--dot-x: 10.228316564615px; --dot-y: 391.28053277303707px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: 14.588828781418727px; --dot-y: 393.7094331429845px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.590" style="--dot-x: 289.1921191559047px; --dot-y: 395.1236896919731px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: 18.468652900656878px; --dot-y: 397.6130644918644px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.385" style="--dot-x: 644.4781937993316px; --dot-y: 406.23761824699716px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.352" style="--dot-x: 2.6369714938557536px; --dot-y: 405.9882982210294px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: -9.901565518157156px; --dot-y: 409.18942805223696px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.619" style="--dot-x: 383.68923606264025px; --dot-y: 411.91354170364696px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: 30.970920581442726px; --dot-y: 405.5151201248348px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.086" style="--dot-x: 671.3099548538754px; --dot-y: 419.71058482414026px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.538" style="--dot-x: 167.54046501188677px; --dot-y: 409.7468254593898px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: -4.288142017471387px; --dot-y: 419.47304965922586px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.413" style="--dot-x: 589.4799313096121px; --dot-y: 415.7479429757626px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.272" style="--dot-x: 15.18756497973959px; --dot-y: 416.712332103299px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: -10.176656547712128px; --dot-y: 427.80768706525873px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.618" style="--dot-x: 304.51287317271874px; --dot-y: 428.8104417600057px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: 26.825118958226142px; --dot-y: 424.142113296119px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.301" style="--dot-x: 647.4519269929145px; --dot-y: 433.5273382655655px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.482" style="--dot-x: 70.46136813446498px; --dot-y: 435.15728068518297px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: 13.49878361279741px; --dot-y: 434.2777924885729px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.557" style="--dot-x: 480.75829413056107px; --dot-y: 436.71810706074405px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.064" style="--dot-x: 14.746385035182243px; --dot-y: 435.51390599024455px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: 29.42233553392981px; --dot-y: 436.5127783505128px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.590" style="--dot-x: 221.85912630504933px; --dot-y: 445.0226050573412px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: -10.760926721986436px; --dot-y: 453.70588419880374px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.383" style="--dot-x: 619.4573016242991px; --dot-y: 450.5496474235965px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.344" style="--dot-x: 36.82287106393102px; --dot-y: 443.10677229107085px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: -2.39204491518376px; --dot-y: 457.11428544747173px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.567" style="--dot-x: 383.0189251283336px; --dot-y: 447.53442876949373px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: 19.04528146105349px; --dot-y: 454.765203397525px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.088" style="--dot-x: 616.1650128185639px; --dot-y: 451.85673254412853px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.522" style="--dot-x: 104.41341140328143px; --dot-y: 466.23732403677406px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: 8.441007230630134px; --dot-y: 465.99938079924897px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.504" style="--dot-x: 508.89197742808375px; --dot-y: 460.71765987467904px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.124" style="--dot-x: -16.52480738100786px; --dot-y: 475.728681654633px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: 38.958577076586494px; --dot-y: 462.24453407707256px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.582" style="--dot-x: 319.765146781687px; --dot-y: 467.5104317419334px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: 5.003620134341475px; --dot-y: 480.84438978572757px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.269" style="--dot-x: 609.9048042390841px; --dot-y: 467.8264403379327px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.418" style="--dot-x: 50.404489729934994px; --dot-y: 481.0810002358164px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: 14.658598325758135px; --dot-y: 484.629485345166px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.554" style="--dot-x: 484.54784828010713px; --dot-y: 489.5833473377048px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: 32.92236945514418px; --dot-y: 482.0091580159824px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: 11.830412920450556px; --dot-y: 493.86591212807934px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.524" style="--dot-x: 149.12690285332855px; --dot-y: 489.27414766799376px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: 10.915726112199764px; --dot-y: 501.04145398676434px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.454" style="--dot-x: 545.9927454569283px; --dot-y: 490.6367267731527px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.286" style="--dot-x: 27.15870697652224px; --dot-y: 493.0307965346537px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: 40.68151614674338px; --dot-y: 494.83239549056407px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.586" style="--dot-x: 287.0855557927374px; --dot-y: 504.7884585214516px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: 20.825629842547983px; --dot-y: 508.93567366372434px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.160" style="--dot-x: 599.9410964140493px; --dot-y: 492.7026699218197px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.402" style="--dot-x: 93.8639303049473px; --dot-y: 493.20722339621534px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: 18.881262415890774px; --dot-y: 519.4289328262133px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.467" style="--dot-x: 516.7162914879184px; --dot-y: 504.2132703167163px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.067" style="--dot-x: 34.11149694367697px; --dot-y: 513.0900964234665px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: 68.75594408407059px; --dot-y: 501.139126700384px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.536" style="--dot-x: 237.93760007116424px; --dot-y: 508.23854672981844px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: 46.613152376326354px; --dot-y: 519.1795129939701px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.309" style="--dot-x: 589.6794370283752px; --dot-y: 516.7681037043858px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.309" style="--dot-x: 62.58537666667968px; --dot-y: 512.125761268934px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: 63.59509574070205px; --dot-y: 518.2403932917462px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.527" style="--dot-x: 396.13349246119753px; --dot-y: 516.314492374842px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: 66.38343461578802px; --dot-y: 521.8482393004944px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.101" style="--dot-x: 618.2356404461398px; --dot-y: 544.7446530410675px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.519" style="--dot-x: 176.76066182160872px; --dot-y: 538.8652219520119px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: 42.26786377714956px; --dot-y: 546.7899652314486px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.476" style="--dot-x: 522.4428543077368px; --dot-y: 550.0564821601736px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.190" style="--dot-x: 56.865629785522344px; --dot-y: 530.6760490466836px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: 79.09785176163552px; --dot-y: 533.0069817581365px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.534" style="--dot-x: 325.8121572570472px; --dot-y: 538.2782803341136px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: 47.56305363729331px; --dot-y: 561.0137698254034px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.248" style="--dot-x: 587.6331253435524px; --dot-y: 549.8579309575983px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.420" style="--dot-x: 115.14989707369975px; --dot-y: 549.5025295033608px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: 87.26204701794069px; --dot-y: 541.2898090294984px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.497" style="--dot-x: 399.60697523656785px; --dot-y: 539.9902507167454px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: 73.51683399598488px; --dot-y: 559.6858434832519px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.045" style="--dot-x: 549.5239121082732px; --dot-y: 546.3902002608517px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.472" style="--dot-x: 203.42979564846348px; --dot-y: 547.374585347289px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: 63.72250944502969px; --dot-y: 578.6184641009625px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.349" style="--dot-x: 528.9040881119985px; --dot-y: 548.86696503811px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.220" style="--dot-x: 52.99265030021343px; --dot-y: 581.0877110254834px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: 77.33865605655592px; --dot-y: 579.2267094545995px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.496" style="--dot-x: 373.49330572151894px; --dot-y: 561.196470947154px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: 88.18714742084538px; --dot-y: 577.534617490817px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.207" style="--dot-x: 558.5695721845195px; --dot-y: 570.2725317495459px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.453" style="--dot-x: 154.57424230328922px; --dot-y: 592.173538750183px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: 97.662734729558px; --dot-y: 582.6053712897208px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.473" style="--dot-x: 458.50307089210696px; --dot-y: 596.4086957057787px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.111" style="--dot-x: 98.7782627419491px; --dot-y: 573.2033747637754px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.029" style="--dot-x: 515.6993473966588px; --dot-y: 567.1144875112841px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.484" style="--dot-x: 234.3382133837421px; --dot-y: 594.7025819068108px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: 110.02086990271656px; --dot-y: 594.1264452786924px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.298" style="--dot-x: 523.2344454380824px; --dot-y: 579.6785753454873px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.359" style="--dot-x: 112.23586214732637px; --dot-y: 610.7311196944116px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: 135.02235732741724px; --dot-y: 583.1215298885029px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.441" style="--dot-x: 426.52715129517964px; --dot-y: 592.3637731324482px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.073" style="--dot-x: 99.75160852237909px; --dot-y: 616.999656115096px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.127" style="--dot-x: 520.2603135346017px; --dot-y: 591.4982002058651px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.447" style="--dot-x: 209.91190173161021px; --dot-y: 614.1560487150873px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: 122.63353261099661px; --dot-y: 621.6847988781203px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.385" style="--dot-x: 492.17210263531194px; --dot-y: 631.2028210770995px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.169" style="--dot-x: 113.7196216519419px; --dot-y: 615.4255540784336px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: 162.95211322809024px; --dot-y: 592.9201961234696px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.465" style="--dot-x: 337.9754329293909px; --dot-y: 626.7129948331258px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: 166.2126581218666px; --dot-y: 604.0116915176887px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.243" style="--dot-x: 515.8081092687602px; --dot-y: 628.7520507145274px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.328" style="--dot-x: 149.44060611953932px; --dot-y: 633.7925351258488px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: 155.9649055975084px; --dot-y: 635.7963144735296px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.405" style="--dot-x: 387.5401069116738px; --dot-y: 607.4469026741881px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.096" style="--dot-x: 158.62988416119106px; --dot-y: 615.5137957666702px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.063" style="--dot-x: 478.73299156721976px; --dot-y: 633.15599878551px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.397" style="--dot-x: 239.56726733896664px; --dot-y: 631.4066926612547px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: 187.6876760120236px; --dot-y: 631.5574854687393px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.302" style="--dot-x: 473.41991561690526px; --dot-y: 652.9640384420251px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.235" style="--dot-x: 172.19434846315903px; --dot-y: 618.3343356487937px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: 196.73166548882625px; --dot-y: 646.4142652451042px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.394" style="--dot-x: 377.30253475009795px; --dot-y: 659.8493559402973px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.017" style="--dot-x: 219.7527155877333px; --dot-y: 629.1140421759245px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.145" style="--dot-x: 448.594423178811px; --dot-y: 623.9700728967267px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.356" style="--dot-x: 234.4860296597976px; --dot-y: 665.0709178756986px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0" style="--dot-x: 216.40527964173918px; --dot-y: 674.9720426108852px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.326" style="--dot-x: 416.4551422834063px; --dot-y: 674.8290892176387px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.186" style="--dot-x: 204.0929786772736px; --dot-y: 631.6613386311019px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.085" style="--dot-x: 426.15953585637567px; --dot-y: 671.1251689027763px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.346" style="--dot-x: 314.9180423144313px; --dot-y: 661.8973681728371px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.017" style="--dot-x: 270.3369044005934px; --dot-y: 674.281300067563px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.212" style="--dot-x: 423.63904929900207px; --dot-y: 679.1152489386056px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.246" style="--dot-x: 240.963005059016px; --dot-y: 646.5235049204609px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.068" style="--dot-x: 352.0404828381664px; --dot-y: 649.833991837251px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.289" style="--dot-x: 343.29280140986026px; --dot-y: 659.5406160957091px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.160" style="--dot-x: 250.132121195037px; --dot-y: 696.2169598829614px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.160" style="--dot-x: 372.1291537591791px; --dot-y: 677.4358633805907px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.236" style="--dot-x: 299.3708104585409px; --dot-y: 678.0703840630797px;"></circle><circle class="homepage-knowledge-graph-v3_dot" r="6" opacity="0.192" style="--dot-x: 320px; --dot-y: 665.7859945130315px;"></circle>
              </g>

              <!-- Camada 2: Arestas e Conexões Relacionais Vetoriais -->
              <g class="homepage-knowledge-graph-v3_edges">
                <!-- Aresta 1: Vendas PDV -> AURA CORE -->
                <line class="homepage-knowledge-graph-v3_edge active-edge" id="kg-edge-vendas" x1="0" y1="0" x2="1" y2="0" opacity="0.45" style="--edge-tx: 186.71341803412474px; --edge-ty: 180.37966865279714px; --edge-angle: -30.759764587919733deg; --edge-len: 189.62344110239445;"></line>
                <!-- Aresta 2: Fechamento Caixa -> AURA CORE -->
                <line class="homepage-knowledge-graph-v3_edge" id="kg-edge-caixas" x1="0" y1="0" x2="1" y2="0" opacity="0.35" style="--edge-tx: 245.9844548986623px; --edge-ty: 29.394544401515702px; --edge-angle: 27.51472455077381deg; --edge-len: 116.8981369758731;"></line>
                <!-- Aresta 3: Estoque Físico -> AURA CORE -->
                <line class="homepage-knowledge-graph-v3_edge" id="kg-edge-estoque" x1="0" y1="0" x2="1" y2="0" opacity="0.40" style="--edge-tx: 387.17468120677904px; --edge-ty: 64.93422191251784px; --edge-angle: 153.79354248439333deg; --edge-len: 41.81211312296073;"></line>
                <!-- Aresta 4: Regras ANP -> AURA CORE -->
                <line class="homepage-knowledge-graph-v3_edge" id="kg-edge-regras" x1="0" y1="0" x2="1" y2="0" opacity="0.42" style="--edge-tx: 340.53652314749695px; --edge-ty: 234.9342219125179px; --edge-angle: -86.55437359848261deg; --edge-len: 151.8099084014437;"></line>
                <!-- Aresta 5: Tolerâncias -> AURA CORE -->
                <line class="homepage-knowledge-graph-v3_edge" id="kg-edge-tolerancias" x1="0" y1="0" x2="1" y2="0" opacity="0.38" style="--edge-tx: 116.01584457760575px; --edge-ty: 149.87441281994606px; --edge-angle: -15.881907365862192deg; --edge-len: 242.91734543156193;"></line>

                <!-- Arestas Transversais de Malha Relacional Contínua -->
                <line class="homepage-knowledge-graph-v3_edge transversal-edge" x1="0" y1="0" x2="1" y2="0" opacity="0.18" style="--edge-tx: 186.71341803412474px; --edge-ty: 180.37966865279714px; --edge-angle: -68.57deg; --edge-len: 162.2;"></line>
                <line class="homepage-knowledge-graph-v3_edge transversal-edge" x1="0" y1="0" x2="1" y2="0" opacity="0.18" style="--edge-tx: 387.17468120677904px; --edge-ty: 64.93422191251784px; --edge-angle: 105.33deg; --edge-len: 176.28;"></line>
                <line class="homepage-knowledge-graph-v3_edge transversal-edge" x1="0" y1="0" x2="1" y2="0" opacity="0.18" style="--edge-tx: 116.01584457760575px; --edge-ty: 149.87441281994606px; --edge-angle: 23.34deg; --edge-len: 76.99;"></line>
              </g>

              <!-- Camada 3: Nós Operacionais e Rótulos Semânticos -->
              <g class="homepage-knowledge-graph-v3_nodes">
                <!-- Nó Central: AURA CORE -->
                <g class="homepage-knowledge-graph-v3_node kg-node-selected" style="--node-x: 349.660493557303px; --node-y: 83.39874272425749px;" onclick="window.auraTour.highlightKnowledgeNode('core')" id="kg-node-core">
                  <circle class="homepage-knowledge-graph-v3_node-halo" r="14" opacity="0.25"></circle>
                  <circle class="homepage-knowledge-graph-v3_node-core" r="6" opacity="0.95"></circle>
                  <text class="homepage-knowledge-graph-v3_node-label" y="25" opacity="0.95">AURA CORE</text>
                </g>

                <!-- Nó 1: Vendas PDV -->
                <g class="homepage-knowledge-graph-v3_node" style="--node-x: 186.71341803412474px; --node-y: 180.37966865279714px;" onclick="window.auraTour.highlightKnowledgeNode('vendas')" id="kg-node-vendas">
                  <circle class="homepage-knowledge-graph-v3_node-halo" r="10" opacity="0.18"></circle>
                  <circle class="homepage-knowledge-graph-v3_node-core" r="4.5" opacity="0.95"></circle>
                  <text class="homepage-knowledge-graph-v3_node-tag" y="21.5" opacity="0.80">Vendas PDV</text>
                </g>

                <!-- Nó 2: Fechamento de Caixa -->
                <g class="homepage-knowledge-graph-v3_node" style="--node-x: 245.9844548986623px; --node-y: 29.394544401515702px;" onclick="window.auraTour.highlightKnowledgeNode('caixas')" id="kg-node-caixas">
                  <circle class="homepage-knowledge-graph-v3_node-halo" r="10" opacity="0.18"></circle>
                  <circle class="homepage-knowledge-graph-v3_node-core" r="4.5" opacity="0.95"></circle>
                  <text class="homepage-knowledge-graph-v3_node-tag" y="21.5" opacity="0.80">Fechamento Caixa</text>
                </g>

                <!-- Nó 3: Estoque Físico & Tanques -->
                <g class="homepage-knowledge-graph-v3_node" style="--node-x: 387.17468120677904px; --node-y: 64.93422191251784px;" onclick="window.auraTour.highlightKnowledgeNode('estoque')" id="kg-node-estoque">
                  <circle class="homepage-knowledge-graph-v3_node-halo" r="10" opacity="0.18"></circle>
                  <circle class="homepage-knowledge-graph-v3_node-core" r="4.5" opacity="0.95"></circle>
                  <text class="homepage-knowledge-graph-v3_node-tag" y="21.5" opacity="0.80">Estoque Físico</text>
                </g>

                <!-- Nó 4: Regras ANP & Fiscais -->
                <g class="homepage-knowledge-graph-v3_node" style="--node-x: 340.53652314749695px; --node-y: 234.9342219125179px;" onclick="window.auraTour.highlightKnowledgeNode('regras')" id="kg-node-regras">
                  <circle class="homepage-knowledge-graph-v3_node-halo" r="10" opacity="0.18"></circle>
                  <circle class="homepage-knowledge-graph-v3_node-core" r="4.5" opacity="0.95"></circle>
                  <text class="homepage-knowledge-graph-v3_node-tag" y="21.5" opacity="0.80">Regras ANP</text>
                </g>

                <!-- Nó 5: Tolerâncias & Perdas -->
                <g class="homepage-knowledge-graph-v3_node" style="--node-x: 116.01584457760575px; --node-y: 149.87441281994606px;" onclick="window.auraTour.highlightKnowledgeNode('tolerancias')" id="kg-node-tolerancias">
                  <circle class="homepage-knowledge-graph-v3_node-halo" r="10" opacity="0.18"></circle>
                  <circle class="homepage-knowledge-graph-v3_node-core" r="4.5" opacity="0.95"></circle>
                  <text class="homepage-knowledge-graph-v3_node-tag" y="21.5" opacity="0.80">Tolerâncias</text>
                </g>
              </g>
            </svg>
          </div>

          <div class="p-2.5 rounded-xl bg-slate-900/60 border border-white/[0.04] text-[10px] text-slate-300 font-sans flex items-center justify-between">
            <span id="kg-status-readout">Nó Selecionado: Vendas PDV conectado com Fechamento de Caixa e Estoque Físico.</span>
            <span class="text-cyan-400 font-mono">0 Inconsistências</span>
          </div>

        </div>

        <!-- Coluna 3: Raciocínio & Orquestração da AURA (3 Colunas) -->
        <div class="lg:col-span-3 p-4 rounded-2xl bg-slate-950/70 border border-white/[0.08] flex flex-col justify-between space-y-3 font-sans text-xs">
          <div class="flex items-center justify-between border-b border-white/[0.06] pb-2 text-[11px]">
            <span class="font-bold text-white flex items-center gap-1.5">
              <i data-lucide="brain" class="w-3.5 h-3.5 text-emerald-400"></i>
              Reasoning & Ação
            </span>
            <span class="text-[10px] font-mono text-emerald-300">1 Clique</span>
          </div>

          <!-- Diagnóstico Relacional em Tempo Real -->
          <div class="space-y-2 flex-1">
            <div class="p-3 rounded-xl bg-white/[0.02] border border-white/[0.05] space-y-1">
              <div class="text-[10px] text-slate-400 uppercase font-mono">Cruzamento de Vendas vs Tanques</div>
              <div class="font-bold text-white text-[11px]" id="kg-reasoning-title">Reconciliação Litro a Litro</div>
              <p class="text-[10px] text-slate-300 leading-relaxed" id="kg-reasoning-text">
                O cupom NFC-e #3526 foi conciliado com o bico 04 e o Tanque 02 em 12ms. Nenhuma quebra física ou fiscal identificada no turno.
              </p>
            </div>

            <div class="p-2.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-[10px] space-y-0.5">
              <div class="font-bold">✓ Conformidade Legal ANP</div>
              <div>Variação volumétrica: +0.28% (Limite: ±0.60%)</div>
            </div>
          </div>

          <!-- Botão Executivo de Resolução em 1 Clique -->
          <button onclick="window.auraTour.simulateChatActionClick()" class="btn-aura-exec w-full py-2 px-3 rounded-xl bg-gradient-to-r from-purple-500 to-cyan-500 text-white font-bold text-xs flex items-center justify-center gap-1.5 active:scale-95 transition-all">
            <i data-lucide="check" class="w-3.5 h-3.5"></i>
            <span>Confirmar Auditoria no ERP</span>
          </button>
        </div>

      </div>

    </section>

    <!-- =========================================================================
         PAINEL & MATRIZ DE DIFERENCIAÇÃO OPERACIONAL REFORÇADO (ROI REAL)
         ========================================================================= -->
    <section id="sec-diferenciacao" class="obsidian-card p-6 sm:p-8 rounded-3xl space-y-8 scroll-reveal">
      
      <!-- Cabeçalho do Painel Operacional -->
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 text-[10px] font-mono uppercase tracking-wider mb-2">
            O Valor Real do Produto está na Linha de Frente da Operação
          </div>
          <h3 class="text-xl sm:text-2xl font-bold text-white font-display-title">Matriz de Diferenciação Operacional & ROI</h3>
          <p class="text-xs text-slate-400 font-sans max-w-2xl mt-1">
            Enquanto ERPs convencionais apenas registram prejuízos passados e painéis comuns só desenham gráficos sem ação, a AURA atua no dia a dia da operação. Ela estanca quebras de caixa, identifica desvios de estoque e agiliza decisões em tempo real, conectada diretamente ao banco de dados da sua empresa e sem cobranças abusivas por milhões de tokens.
          </p>
        </div>
        <div class="text-right flex-shrink-0">
          <span class="px-3.5 py-1.5 rounded-xl text-xs font-semibold bg-emerald-500/10 text-emerald-300 border border-emerald-500/25 inline-flex items-center gap-1.5">
            <i data-lucide="trending-up" class="w-3.5 h-3.5"></i>
            <span>ROI Operacional Comprovado</span>
          </span>
        </div>
      </div>

      <!-- 4 Cards de Destaque do Valor Operacional com Mini Dashboards e Gráficos Animados no Scroll -->
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5 font-sans">
        
        <!-- CARD 1: QUEBRAS DE CAIXA (Com Mini Sparkline de Auditoria Horária) -->
        <div class="roi-card p-4 rounded-2xl bg-slate-900/90 border border-emerald-500/25 space-y-3">
          <div class="flex items-center justify-between">
            <span class="text-[10px] font-mono text-emerald-400 uppercase">Prevenção Financeira</span>
            <i data-lucide="scale" class="w-4 h-4 text-emerald-400"></i>
          </div>
          <div class="text-base font-extrabold text-white">Detecção de Quebras de Caixa</div>
          <p class="text-xs text-slate-400 leading-relaxed">
            Identificação de discrepâncias centavo a centavo turno a turno. Estanca sangrias e desvios no mesmo dia, sem surpresas no fim do mês.
          </p>

          <!-- Mini Gráfico de Auditoria Horária Centavo a Centavo -->
          <div class="p-2.5 rounded-xl bg-black/50 border border-white/[0.05] space-y-1.5">
            <div class="flex items-center justify-between text-[10px] font-mono text-slate-400">
              <span>Auditoria Horária</span>
              <span class="text-emerald-400 font-bold">R$ 0,00 Dif.</span>
            </div>
            <!-- Mini Barras Horárias Animadas -->
            <div class="h-8 flex items-end justify-between gap-1 px-1">
              <div class="flex-1 bg-emerald-500/70 rounded-t roi-spark-bar h-5"></div>
              <div class="flex-1 bg-emerald-500/70 rounded-t roi-spark-bar h-6"></div>
              <div class="flex-1 bg-emerald-500/70 rounded-t roi-spark-bar h-7"></div>
              <div class="flex-1 bg-emerald-500/70 rounded-t roi-spark-bar h-8"></div>
              <div class="flex-1 bg-emerald-500/70 rounded-t roi-spark-bar h-6"></div>
              <div class="flex-1 bg-cyan-400 rounded-t roi-spark-bar h-7"></div>
            </div>
            <div class="text-[9px] text-slate-400 font-mono text-center">06h • 09h • 12h • 15h • 18h • Agora</div>
          </div>

          <div class="text-[10px] text-emerald-300 font-semibold pt-1">✓ Prejuízo evitado: R$ 3.800 a R$ 12.000 / mês</div>
        </div>

        <!-- CARD 2: DESVIOS DE ESTOQUE (Com Mini Barra de Calibração Volumétrica) -->
        <div class="roi-card p-4 rounded-2xl bg-slate-900/90 border border-cyan-500/25 space-y-3">
          <div class="flex items-center justify-between">
            <span class="text-[10px] font-mono text-cyan-400 uppercase">Controle Físico Real</span>
            <i data-lucide="boxes" class="w-4 h-4 text-cyan-400"></i>
          </div>
          <div class="text-base font-extrabold text-white">Auditoria de Desvios de Estoque</div>
          <p class="text-xs text-slate-400 leading-relaxed">
            Cruzamento contínuo entre saídas fiscais registradas e estoque físico real em tanques, balcões e gôndolas. Fim da "perda aceita".
          </p>

          <!-- Mini Barra de Calibração Volumétrica Físico vs Fiscal -->
          <div class="p-2.5 rounded-xl bg-black/50 border border-white/[0.05] space-y-1.5">
            <div class="flex items-center justify-between text-[10px] font-mono text-slate-400">
              <span>Calibração Físico x Fiscal</span>
              <span class="text-cyan-300 font-bold">100.0% Match</span>
            </div>
            <div class="w-full bg-slate-950 rounded-full h-3 p-0.5 border border-white/[0.06] overflow-hidden">
              <div class="h-full bg-gradient-to-r from-cyan-500 to-emerald-400 rounded-full roi-gauge-fill" style="--target-width: 99.8%;"></div>
            </div>
            <div class="flex items-center justify-between text-[9px] text-slate-400 font-mono">
              <span>Estoque Tanque: 4.820 L</span>
              <span class="text-emerald-400">Conforme ANP</span>
            </div>
          </div>

          <div class="text-[10px] text-cyan-300 font-semibold pt-1">✓ Fim do sumiço oculto de mercadorias</div>
        </div>

        <!-- CARD 3: ECONOMIA DE TOKENS (Com Mini Comparativo Nuvem vs Local) -->
        <div class="roi-card p-4 rounded-2xl bg-slate-900/90 border border-purple-500/25 space-y-3">
          <div class="flex items-center justify-between">
            <span class="text-[10px] font-mono text-purple-400 uppercase">Eficiência & Soberania</span>
            <i data-lucide="database" class="w-4 h-4 text-purple-400"></i>
          </div>
          <div class="text-base font-extrabold text-white">Economia Brutal de Tokens</div>
          <p class="text-xs text-slate-400 leading-relaxed">
            Conecta diretamente ao banco da empresa: cálculos estruturados na máquina local e inteligência acionada apenas para conclusões complexas, sem surpresas na fatura.
          </p>

          <!-- Mini Gráfico de Barras de Redução de Tokens -->
          <div class="p-2.5 rounded-xl bg-black/50 border border-white/[0.05] space-y-1.5">
            <div class="flex items-center justify-between text-[10px] font-mono text-slate-400">
              <span>Consumo Mensal de Tokens</span>
              <span class="text-purple-300 font-bold">-95% Redução</span>
            </div>
            <div class="space-y-1">
              <div class="flex items-center gap-1.5 text-[9px] font-mono text-slate-400">
                <span class="w-12 text-rose-400">Nuvem:</span>
                <div class="flex-1 bg-slate-950 rounded h-2 overflow-hidden">
                  <div class="bg-rose-500/60 h-full w-[95%]"></div>
                </div>
                <span>12.5M</span>
              </div>
              <div class="flex items-center gap-1.5 text-[9px] font-mono text-slate-400">
                <span class="w-12 text-emerald-400">AURA:</span>
                <div class="flex-1 bg-slate-950 rounded h-2 overflow-hidden">
                  <div class="bg-emerald-400 h-full w-[8%]"></div>
                </div>
                <span>0.3M</span>
              </div>
            </div>
          </div>

          <div class="text-[10px] text-purple-300 font-semibold pt-1">✓ Redução de 90% a 95% em consumo de tokens</div>
        </div>

        <!-- CARD 4: PRODUTIVIDADE GERENCIAL (Com Medidor de Redução de Horas) -->
        <div class="roi-card p-4 rounded-2xl bg-slate-900/90 border border-amber-500/25 space-y-3">
          <div class="flex items-center justify-between">
            <span class="text-[10px] font-mono text-amber-400 uppercase">Produtividade Gerencial</span>
            <i data-lucide="clock" class="w-4 h-4 text-amber-400"></i>
          </div>
          <div class="text-base font-extrabold text-white">De Horas para 10 Segundos</div>
          <p class="text-xs text-slate-400 leading-relaxed">
            Elimina o preenchimento manual de planilhas e conferência de filipetas. Entrega DecisionCards prontos com ação em 1-toque e Run-Out preditivo.
          </p>

          <!-- Mini Medidor Comparativo de Velocidade -->
          <div class="p-2.5 rounded-xl bg-black/50 border border-white/[0.05] space-y-1.5">
            <div class="flex items-center justify-between text-[10px] font-mono text-slate-400">
              <span>Tempo de Tomada de Decisão</span>
              <span class="text-amber-300 font-bold">1080x Mais Rápido</span>
            </div>
            <div class="flex items-center justify-between text-[10px] font-mono py-0.5">
              <span class="text-rose-400 line-through">180 min (Planilhas)</span>
              <span class="text-emerald-400 font-bold">10s (AURA)</span>
            </div>
            <div class="w-full bg-slate-950 rounded-full h-1.5 overflow-hidden">
              <div class="bg-amber-400 h-full w-[99%]"></div>
            </div>
          </div>

          <div class="text-[10px] text-amber-300 font-semibold pt-1">✓ Mais de 60 horas/mês economizadas por gestor</div>
        </div>

      </div>

      <!-- Bloco de Contraste Estratégico: Mercado Tradicional de IA vs Abordagem AURA -->
      <div class="p-5 sm:p-6 rounded-2xl bg-slate-950/70 border border-white/[0.08] space-y-4">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-white/[0.06] pb-4">
          <div>
            <div class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-cyan-500/10 text-cyan-300 border border-cyan-500/20 text-[10px] font-mono uppercase tracking-wider mb-1">
              Soberania dos Dados & Arquitetura Inteligente
            </div>
            <h4 class="text-base sm:text-lg font-bold text-white font-display-title">
              O Mercado Tradicional de IA vs A Abordagem Direta no Banco da AURA
            </h4>
          </div>
          <span class="px-3 py-1 rounded-full text-xs font-bold bg-emerald-500/15 text-emerald-300 border border-emerald-500/25 inline-flex items-center gap-1.5 w-fit">
            <i data-lucide="sparkles" class="w-3.5 h-3.5"></i>
            Até 95% de Economia em Tokens
          </span>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4 font-sans text-xs">
          <!-- Coluna 1: O Mercado Tradicional de IA -->
          <div class="p-4 rounded-xl bg-slate-900/60 border border-rose-500/20 space-y-2.5">
            <div class="flex items-center justify-between">
              <span class="text-xs font-bold text-rose-300 flex items-center gap-1.5">
                <i data-lucide="alert-triangle" class="w-4 h-4 text-rose-400"></i>
                Como o Mercado Tradicional de IA Opera
              </span>
              <span class="px-2 py-0.5 rounded text-[9px] font-mono bg-rose-500/15 text-rose-300">Ineficiente & Caro</span>
            </div>
            <p class="text-slate-300 leading-relaxed">
              Envia <span class="text-rose-200 font-semibold">dados brutos e desorganizados</span> para servidores externos em nuvem, sem validação prévia e sem organização dos dados. Espera que a inteligência calcule tudo no escuro, consumindo recursos de forma descontrolada e <strong class="text-white">cobrando faturas caras por milhões de tokens para processar informações que já pertencem à sua própria empresa</strong>.
            </p>
            <div class="text-[11px] text-rose-300 font-mono pt-1">
              ✕ O cliente paga caro para processar a sua própria informação.
            </div>
          </div>

          <!-- Coluna 2: A Abordagem AURA -->
          <div class="p-4 rounded-xl bg-slate-900/60 border border-emerald-500/25 space-y-2.5">
            <div class="flex items-center justify-between">
              <span class="text-xs font-bold text-emerald-300 flex items-center gap-1.5">
                <i data-lucide="shield-check" class="w-4 h-4 text-emerald-400"></i>
                A Abordagem Inteligente da AURA
              </span>
              <span class="px-2 py-0.5 rounded text-[9px] font-mono bg-emerald-500/15 text-emerald-300">Conexão Local Direta</span>
            </div>
            <p class="text-slate-300 leading-relaxed">
              Conecta <span class="text-emerald-200 font-semibold">direto na infraestrutura do banco do cliente</span>. Realiza todas as contas e conciliações de forma estruturada e exata na própria máquina local. A inteligência só é acionada para <strong class="text-white">cálculos estruturados, síntese estratégica e conclusões complexas</strong>. Isso garante fidelidade matemática, segurança, assertividade e respostas em milissegundos, com economia de até 95% em custos de tokens.
            </p>
            <div class="text-[11px] text-emerald-300 font-mono font-semibold pt-1">
              ✓ Cálculos estruturados locais, respostas em milissegundos e zero surpresas no fim do mês.
            </div>
          </div>
        </div>
      </div>

      <!-- Tabela Comparativa Compactada (Dimensões Críticas de ROI) -->
      <div class="overflow-x-auto font-sans text-xs">
        <table class="w-full text-left border-collapse">
          <thead>
            <tr class="border-b border-white/10 text-slate-400">
              <th class="py-3 px-4 font-semibold w-1/4">Dimensão Operacional</th>
              <th class="py-3 px-4 font-semibold text-rose-300/80 w-1/4">Modelo Tradicional (Planilhas & ERPs Legados)</th>
              <th class="py-3 px-4 font-semibold text-amber-300/80 w-1/4">Dashboards de BI Passivos & IAs de Nuvem</th>
              <th class="py-3 px-4 font-semibold text-cyan-300 bg-white/[0.02] rounded-t-xl w-1/4">Plataforma AURA</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-white/5">
            <tr>
              <td class="py-3.5 px-4 font-semibold text-slate-200">Auditoria de Caixa & Prevenção de Quebras</td>
              <td class="py-3.5 px-4 text-slate-400">
                <span class="inline-flex items-center gap-1 text-[11px] font-semibold text-rose-400 mb-1">✕ Reativo / Manual</span>
                <div>2 a 4 horas conferindo recibos e papel; erros e quebras descobertos semanas depois no balanço.</div>
              </td>
              <td class="py-3.5 px-4 text-slate-400">
                <span class="inline-flex items-center gap-1 text-[11px] font-semibold text-amber-400 mb-1">⚠ Diagnóstico Tardio</span>
                <div>Gráficos de dias anteriores; visualiza o problema mas não impede sangrias ou furos no presente.</div>
              </td>
              <td class="py-3.5 px-4 bg-emerald-950/20 border-l border-r border-emerald-500/25">
                <span class="inline-flex items-center gap-1 text-[11px] font-bold text-emerald-400 mb-1">✓ Ação em Tempo Real</span>
                <div class="font-medium text-emerald-200">Instantâneo em sub-100ms com reconciliação centavo a centavo; estanca quebras no próprio turno.</div>
                <div class="mt-2 p-2 rounded-lg bg-black/40 border border-emerald-500/20 space-y-1 roi-table-metric">
                  <div class="flex items-center justify-between text-[10px] font-mono">
                    <span class="text-slate-400">Auditoria Horária:</span>
                    <span class="text-emerald-400 font-bold">R$ 0,00 Dif.</span>
                  </div>
                  <div class="w-full bg-slate-900 rounded-full h-1.5 overflow-hidden">
                    <div class="bg-emerald-400 h-full rounded-full roi-table-bar" style="--target-width: 100%;"></div>
                  </div>
                </div>
              </td>
            </tr>
            <tr>
              <td class="py-3.5 px-4 font-semibold text-slate-200">Desvios de Estoque & Perdas Invisíveis</td>
              <td class="py-3.5 px-4 text-slate-400">
                <span class="inline-flex items-center gap-1 text-[11px] font-semibold text-rose-400 mb-1">✕ Furos Ocultos</span>
                <div>Estoque teórico descolado do físico; perda tratada como custo inevitável da operação.</div>
              </td>
              <td class="py-3.5 px-4 text-slate-400">
                <span class="inline-flex items-center gap-1 text-[11px] font-semibold text-amber-400 mb-1">⚠ Visão Estática</span>
                <div>Relatório estático após balanço mensal sem checagem contínua de nível físico.</div>
              </td>
              <td class="py-3.5 px-4 bg-emerald-950/20 border-l border-r border-emerald-500/25">
                <span class="inline-flex items-center gap-1 text-[11px] font-bold text-emerald-400 mb-1">✓ Conciliação Contínua</span>
                <div class="font-medium text-emerald-200">Cruzamento contínuo entre saídas fiscais e estoque físico real em tempo real; alerta imediato de desvio.</div>
                <div class="mt-2 p-2 rounded-lg bg-black/40 border border-cyan-500/20 space-y-1 roi-table-metric">
                  <div class="flex items-center justify-between text-[10px] font-mono">
                    <span class="text-slate-400">Calibração Volumétrica:</span>
                    <span class="text-cyan-300 font-bold">100.0% Match</span>
                  </div>
                  <div class="w-full bg-slate-900 rounded-full h-1.5 overflow-hidden">
                    <div class="bg-cyan-400 h-full rounded-full roi-table-bar" style="--target-width: 100%;"></div>
                  </div>
                </div>
              </td>
            </tr>
            <tr>
              <td class="py-3.5 px-4 font-semibold text-slate-200">Eficiência de Processamento & Custo de Tokens</td>
              <td class="py-3.5 px-4 text-slate-400">
                <span class="inline-flex items-center gap-1 text-[11px] font-semibold text-rose-400 mb-1">✕ Sem Inteligência</span>
                <div>Processamento manual e lento; sistemas rígidos sem capacidade preditiva ou automação inteligente.</div>
              </td>
              <td class="py-3.5 px-4 text-slate-400">
                <span class="inline-flex items-center gap-1 text-[11px] font-semibold text-rose-400 mb-1">✕ Faturas Abusivas de Nuvem</span>
                <div>Soluções comuns enviam dados brutos e sem validação para servidores externos, cobrando caro do cliente por milhões de tokens para ler informações da própria empresa.</div>
              </td>
              <td class="py-3.5 px-4 bg-emerald-950/20 border-l border-r border-emerald-500/25">
                <span class="inline-flex items-center gap-1 text-[11px] font-bold text-emerald-400 mb-1">✓ Conexão Direta ao Banco Local</span>
                <div class="font-medium text-emerald-200">Conecta direto na infraestrutura do banco do cliente. As contas rodam na máquina local e a inteligência só é acionada para cálculos estruturados e síntese executiva, gerando até 95% de economia em tokens com respostas em milissegundos.</div>
                <div class="mt-2 p-2 rounded-lg bg-black/40 border border-purple-500/20 space-y-1 roi-table-metric">
                  <div class="flex items-center justify-between text-[10px] font-mono">
                    <span class="text-slate-400">Economia de Tokens:</span>
                    <span class="text-purple-300 font-bold">-95% Redução</span>
                  </div>
                  <div class="w-full bg-slate-900 rounded-full h-1.5 overflow-hidden">
                    <div class="bg-purple-400 h-full rounded-full roi-table-bar" style="--target-width: 95%;"></div>
                  </div>
                </div>
              </td>
            </tr>
            <tr>
              <td class="py-3.5 px-4 font-semibold text-slate-200">Tempo para Decisão & Ação</td>
              <td class="py-3.5 px-4 text-slate-400">
                <span class="inline-flex items-center gap-1 text-[11px] font-semibold text-rose-400 mb-1">✕ Horas em Planilhas</span>
                <div>Reuniões morosas com relatórios estáticos de papel e horas em planilhas sem apontar o que fazer.</div>
              </td>
              <td class="py-3.5 px-4 text-slate-400">
                <span class="inline-flex items-center gap-1 text-[11px] font-semibold text-amber-400 mb-1">⚠ Telas Complexas</span>
                <div>Telas complexas com dezenas de filtros que exigem analistas dedicados para interpretar.</div>
              </td>
              <td class="py-3.5 px-4 bg-emerald-950/20 border-l border-r border-emerald-500/25">
                <span class="inline-flex items-center gap-1 text-[11px] font-bold text-purple-400 mb-1">✓ Resolução em 1 Clique</span>
                <div class="font-medium text-purple-200">Cartões executivos DecisionCards™ autoexplicativos que permitem resolver pendências com apenas 1 clique em menos de 10 segundos.</div>
                <div class="mt-2 p-2 rounded-lg bg-black/40 border border-amber-500/20 space-y-1 roi-table-metric">
                  <div class="flex items-center justify-between text-[10px] font-mono">
                    <span class="text-slate-400">Velocidade de Execução:</span>
                    <span class="text-amber-300 font-bold">1080x Mais Rápido</span>
                  </div>
                  <div class="w-full bg-slate-900 rounded-full h-1.5 overflow-hidden">
                    <div class="bg-amber-400 h-full rounded-full roi-table-bar" style="--target-width: 100%;"></div>
                  </div>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- =========================================================================
         FAQ EXECUTIVO
         ========================================================================= -->
    <section id="sec-faq" class="space-y-6 scroll-reveal">
      <div class="text-center max-w-xl mx-auto space-y-1">
        <h3 class="text-xl sm:text-2xl font-bold text-white font-display-title">Perguntas Frequentes da Diretoria</h3>
        <p class="text-xs text-slate-400 font-sans">Respostas diretas sobre governança, integração e segurança da AURA.</p>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-4 font-sans text-xs">
        
        <div class="obsidian-card p-5 rounded-2xl space-y-2">
          <h4 class="font-bold text-slate-100 flex items-center gap-2">
            <i data-lucide="help-circle" class="w-4 h-4 text-cyan-400"></i>
            A AURA substitui o sistema ERP atual da minha empresa?
          </h4>
          <p class="text-slate-400 leading-relaxed">
            Não. A AURA atua como uma supervisora de inteligência e auditoria contínua que se conecta ao seu ERP e automação existente, acelerando a tomada de decisões no dia a dia em postos, lojas, bares ou padarias.
          </p>
        </div>

        <div class="obsidian-card p-5 rounded-2xl space-y-2">
          <h4 class="font-bold text-slate-100 flex items-center gap-2">
            <i data-lucide="lock" class="w-4 h-4 text-emerald-400"></i>
            Meus dados de faturamento e clientes saem da minha empresa?
          </h4>
          <p class="text-slate-400 leading-relaxed">
            Absolutamente não. Em total conformidade com a LGPD (Lei 13.709/2018), qualquer dado de identificação pessoal (como CPF ou nomes) é removido automaticamente antes da análise. Todo o processamento funciona dentro da sua própria estrutura e nada de confidencial é enviado para servidores externos.
          </p>
        </div>

        <div class="obsidian-card p-5 rounded-2xl space-y-2">
          <h4 class="font-bold text-slate-100 flex items-center gap-2">
            <i data-lucide="coins" class="w-4 h-4 text-emerald-400"></i>
            Por que a AURA economiza até 95% em tokens comparada a outras soluções?
          </h4>
          <p class="text-slate-400 leading-relaxed">
            Muitas ferramentas hoje enviam dados brutos e desorganizados para servidores em nuvem, sem validação prévia nem filtros de segurança, cobrando dos clientes faturas caras por milhões de tokens para ler dados que já são deles. A AURA trabalha conectada diretamente à infraestrutura do banco do cliente, realizando todas as contas no próprio ambiente local. A inteligência só é acionada para análises estruturadas e conclusões executivas, garantindo economia de até 95% em consumo de tokens, máxima assertividade, respostas em milissegundos e custo previsível.
          </p>
        </div>

        <div class="obsidian-card p-5 rounded-2xl space-y-2">
          <h4 class="font-bold text-slate-100 flex items-center gap-2">
            <i data-lucide="clock" class="w-4 h-4 text-purple-400"></i>
            Qual é a curva de aprendizado da equipe operacional?
          </h4>
          <p class="text-slate-400 leading-relaxed">
            Zero minutos. A AURA compreende linguagem falada ou escrita natural em português do Brasil e entrega DecisionCards autoexplicativos que qualquer gerente, caixa ou encarregado opera intuitivamente em 1 clique.
          </p>
        </div>

        <div class="obsidian-card p-5 rounded-2xl space-y-2 md:col-span-2">
          <h4 class="font-bold text-slate-100 flex items-center gap-2">
            <i data-lucide="check" class="w-4 h-4 text-amber-400"></i>
            A inteligência pode errar contas ou inventar números?
          </h4>
          <p class="text-slate-400 leading-relaxed">
            Não. A AURA não inventa nem faz suposições com valores financeiros ou de estoque. Toda conta de faturamento, volume e fechamento de caixa é calculada diretamente a partir dos cupons fiscais e leituras do seu sistema. Cada número é auditado matematicamente com exatidão antes de ser apresentado.
          </p>
        </div>

      </div>
    </section>

    <!-- =========================================================================
         CTA FINAL & ENCAMINHAMENTO
         ========================================================================= -->
    <div class="obsidian-card p-8 rounded-3xl text-center space-y-5 shadow-xl scroll-reveal">
      <div class="inline-flex items-center justify-center p-3 rounded-2xl bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
        <i data-lucide="sparkles" class="w-8 h-8"></i>
      </div>
      <h2 class="text-2xl sm:text-4xl font-extrabold text-white font-display-title">
        Pronto para Elevar o Padrão Operacional do seu Negócio?
      </h2>
      <p class="text-xs sm:text-sm text-slate-300 font-sans max-w-xl mx-auto">
        Acesse agora o console completo da AURA para conversar com a assistente, consultar o panorama operacional em tempo real ou disparar diagnósticos executivos em 1 clique.
      </p>
      <div class="flex flex-col sm:flex-row items-center justify-center gap-3 pt-2 font-sans">
        <a href="/" class="btn-aura-exec w-full sm:w-auto px-6 py-3 rounded-xl bg-gradient-to-r from-emerald-500 via-cyan-500 to-purple-500 hover:brightness-105 text-slate-950 font-bold text-sm shadow-md active:scale-95 transition-all flex items-center justify-center gap-2">
          <span>Acessar Console AURA</span>
          <i data-lucide="arrow-right" class="w-4 h-4"></i>
        </a>
        <button onclick="window.auraTour.restartTour()" class="w-full sm:w-auto px-5 py-3 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-300 hover:text-white border border-white/10 text-sm font-semibold transition-colors flex items-center justify-center gap-2">
          <i data-lucide="rotate-ccw" class="w-4 h-4"></i>
          <span>Rever Animação da AURA ↺</span>
        </button>
      </div>
    </div>

  </main>

  <!-- =========================================================================
       RODAPÉ DO SHOWCASE
       ========================================================================= -->
  <footer class="border-t border-white/[0.08] py-6 px-4 text-center text-xs text-slate-400 font-sans bg-obsidianDeep/90">
    <div class="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
      <div class="flex items-center gap-2">
        <span class="font-display-title font-bold text-slate-200">AURA</span>
        <span>• Autonomous Unified Retail Assistant</span>
      </div>
      <div>
        <span>Design System Obsidian & Precision Architecture • LGPD Compliant • Todos os direitos reservados</span>
      </div>
      <div class="flex items-center gap-3">
        <a href="/" class="text-cyan-400 hover:text-cyan-300 underline">Console</a>
        <button onclick="window.auraTour.scrollToSection('top')" class="text-slate-400 hover:text-slate-200">Voltar ao Topo ↑</button>
      </div>
    </div>
  </footer>

  <!-- =========================================================================
       MOTOR JAVASCRIPT DO SHOWCASE AUTÔNOMO & SIMULAÇÃO EM TEMPO REAL
       ========================================================================= -->
  <script>
    (function() {
      // Estado da Simulação Autônoma
      const tourState = {
        currentStep: 1,
        totalSteps: 4,
        isPlaying: true,
        durationPerStep: 4500,
        speedMultiplier: 1,
        stepStartTime: 0,
        soundEnabled: true,
        userInteracted: false,
        currentScenario: 'posto',
        hasAutoStarted: false,
        isSimulating: false
      };

      // Inicializador do Web Audio API
      let audioCtx = null;
      function playTone(freq = 440, type = 'sine', duration = 0.15, gain = 0.08) {
        if (!tourState.soundEnabled) return;
        try {
          if (!audioCtx) {
            const AudioContextClass = window.AudioContext || window.webkitAudioContext;
            if (AudioContextClass) audioCtx = new AudioContextClass();
          }
          if (audioCtx && audioCtx.state === 'suspended') {
            audioCtx.resume().catch(() => {});
          }
          if (!audioCtx) return;
          const osc = audioCtx.createOscillator();
          const gainNode = audioCtx.createGain();
          osc.type = type;
          osc.frequency.setValueAtTime(freq, audioCtx.currentTime);
          gainNode.gain.setValueAtTime(gain, audioCtx.currentTime);
          gainNode.gain.exponentialRampToValueAtTime(0.0001, audioCtx.currentTime + duration);
          osc.connect(gainNode);
          gainNode.connect(audioCtx.destination);
          osc.start();
          osc.stop(audioCtx.currentTime + duration);
        } catch (e) {
          // Fallback silencioso
        }
      }

      function playChime() {
        playTone(523.25, 'sine', 0.1, 0.05);
        setTimeout(() => playTone(659.25, 'sine', 0.12, 0.05), 80);
        setTimeout(() => playTone(783.99, 'sine', 0.2, 0.06), 160);
      }

      function playDustSound() {
        playTone(880, 'triangle', 0.2, 0.04);
        setTimeout(() => playTone(440, 'sine', 0.25, 0.03), 100);
        setTimeout(() => playTone(220, 'sine', 0.3, 0.02), 200);
      }

      function playActionSound() {
        playTone(440, 'sine', 0.08, 0.06);
        setTimeout(() => playTone(880, 'triangle', 0.15, 0.06), 70);
      }

      // =========================================================================
      // MOTOR DE FÍSICA DE PARTÍCULAS / POEIRA (CANVAS DISINTEGRATION)
      // =========================================================================
      const dustCanvas = document.getElementById('dust-particle-canvas');
      const dustCtx = dustCanvas ? dustCanvas.getContext('2d') : null;
      let particles = [];
      let isParticleLoopRunning = false;
      let dustTimeouts = [];

      function resizeDustCanvas() {
        if (!dustCanvas) return;
        const parent = dustCanvas.parentElement;
        if (parent && parent.clientWidth > 0 && parent.clientHeight > 0) {
          dustCanvas.width = parent.clientWidth;
          dustCanvas.height = parent.clientHeight;
        }
      }
      window.addEventListener('resize', resizeDustCanvas);

      class DustParticle {
        constructor(x, y, color) {
          this.x = x;
          this.y = y;
          const angle = Math.random() * Math.PI * 2;
          const speed = Math.random() * 3.5 + 1.2;
          this.vx = Math.cos(angle) * speed + (Math.random() - 0.5) * 1.5;
          this.vy = Math.sin(angle) * speed - (Math.random() * 2 + 1.8);
          this.radius = Math.random() * 2.2 + 1.0;
          this.alpha = 1.0;
          this.decay = Math.random() * 0.016 + 0.012;
          this.color = color || '#06b6d4';
          this.drag = 0.98;
        }

        update() {
          this.vx *= this.drag;
          this.vy *= this.drag;
          this.vy -= 0.03;
          this.x += this.vx;
          this.y += this.vy;
          this.alpha -= this.decay;
        }

        draw(ctx) {
          if (this.alpha <= 0) return;
          ctx.save();
          ctx.globalAlpha = Math.max(0, this.alpha);
          ctx.fillStyle = this.color;
          ctx.beginPath();
          ctx.arc(this.x, this.y, this.radius, 0, Math.PI * 2);
          ctx.fill();
          ctx.restore();
        }
      }

      function spawnParticlesAtElement(element, count = 60) {
        if (!dustCanvas || !element) return;
        resizeDustCanvas();
        const rect = element.getBoundingClientRect();
        const canvasRect = dustCanvas.getBoundingClientRect();

        let startX = rect.left - canvasRect.left + rect.width / 2;
        let startY = rect.top - canvasRect.top + rect.height / 2;

        if (isNaN(startX) || isNaN(startY) || (startX === 0 && startY === 0)) {
          startX = dustCanvas.width / 2;
          startY = dustCanvas.height / 2;
        }

        const colors = ['#10b981', '#06b6d4', '#34d399', '#22d3ee', '#a855f7', '#fbbf24'];

        for (let i = 0; i < count; i++) {
          const offsetX = (Math.random() - 0.5) * Math.max(20, rect.width);
          const offsetY = (Math.random() - 0.5) * Math.max(10, rect.height);
          const color = colors[Math.floor(Math.random() * colors.length)];
          particles.push(new DustParticle(startX + offsetX, startY + offsetY, color));
        }

        if (!isParticleLoopRunning) {
          isParticleLoopRunning = true;
          requestAnimationFrame(particleAnimationLoop);
        }
      }

      function particleAnimationLoop() {
        if (!dustCtx || !dustCanvas) return;
        dustCtx.clearRect(0, 0, dustCanvas.width, dustCanvas.height);

        particles = particles.filter(p => p.alpha > 0);

        for (let i = 0; i < particles.length; i++) {
          particles[i].update();
          particles[i].draw(dustCtx);
        }

        if (particles.length > 0) {
          requestAnimationFrame(particleAnimationLoop);
        } else {
          isParticleLoopRunning = false;
        }
      }

      // Função de Desintegração em Poeira de PII (Escudo LGPD)
      function triggerDustDisintegration(playSfx = true, readDelayMs = 2400, onComplete = null) {
        dustTimeouts.forEach(t => clearTimeout(t));
        dustTimeouts = [];

        resetDustDisintegration();
        resizeDustCanvas();

        const statusPill = document.getElementById('dust-status-pill');
        const thinkingText = document.getElementById('thinking-step-text');
        const piiList = document.getElementById('pii-items-list');

        // 1. FASE DE LEITURA DOS DADOS PESSOAIS
        if (statusPill) {
          statusPill.textContent = 'DADOS PESSOAIS IDENTIFICADOS';
          statusPill.className = 'px-2 py-0.5 rounded text-[10px] font-mono bg-rose-500/20 text-rose-300 border border-rose-500/40 animate-pulse';
        }
        if (thinkingText) {
          thinkingText.textContent = 'Escudo AURA Guard™: dados confidenciais detectados no fluxo. Lendo e isolando...';
        }
        if (piiList) {
          piiList.classList.add('border-rose-500/40');
        }

        if (playSfx) playTone(480, 'sine', 0.12, 0.03);

        // 2. FASE DE PULVERIZAÇÃO EM POEIRA
        const tStartDust = setTimeout(() => {
          if (statusPill) {
            statusPill.textContent = 'DESINTEGRANDO EM POEIRA (LGPD)...';
            statusPill.className = 'px-2 py-0.5 rounded text-[10px] font-mono bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 animate-pulse';
          }
          if (thinkingText) {
            thinkingText.textContent = 'Desintegrando dados confidenciais em poeira (100% LGPD)...';
          }
          if (piiList) {
            piiList.classList.remove('border-rose-500/40');
          }
          if (playSfx) playDustSound();

          // Desintegração sequencial cadenciada (320ms entre cada item)
          const itemStagger = 320;
          for (let i = 1; i <= 5; i++) {
            const rawVal = document.getElementById(`pii-val-${i}`);
            const redVal = document.getElementById(`pii-token-${i}`);
            if (rawVal) {
              const tDisintegrate = setTimeout(() => {
                rawVal.classList.add('disintegrating');
                spawnParticlesAtElement(rawVal, 65);
                if (playSfx && i % 2 === 0) playTone(640 + i * 40, 'triangle', 0.06, 0.02);

                const tToken = setTimeout(() => {
                  rawVal.classList.add('hidden');
                  if (redVal) {
                    redVal.classList.remove('hidden');
                    redVal.classList.add('animate-fade-in');
                  }
                }, 220);
                dustTimeouts.push(tToken);
              }, (i - 1) * itemStagger);
              dustTimeouts.push(tDisintegrate);
            }
          }

          // Conclusão da sanitização (após todos os 5 itens desintegrarem)
          const totalDustTime = 4 * itemStagger + 350; // ~1630ms
          const tFinish = setTimeout(() => {
            if (statusPill) {
              statusPill.textContent = '100% SANITIZADO (LGPD)';
              statusPill.className = 'px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-500/20 text-emerald-300 border border-emerald-500/40';
            }
            if (playSfx) playTone(880, 'sine', 0.15, 0.04);

            const tAppreciation = setTimeout(() => {
              if (typeof onComplete === 'function') onComplete();
            }, 800);
            dustTimeouts.push(tAppreciation);
          }, totalDustTime);
          dustTimeouts.push(tFinish);

        }, readDelayMs);
        dustTimeouts.push(tStartDust);
      }

      function resetDustDisintegration() {
        const statusPill = document.getElementById('dust-status-pill');
        if (statusPill) {
          statusPill.textContent = 'ESCUDO ATIVO';
          statusPill.className = 'px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-500/10 text-emerald-300 border border-emerald-500/20';
        }
        const piiList = document.getElementById('pii-items-list');
        if (piiList) {
          piiList.classList.remove('border-rose-500/40');
        }
        for (let i = 1; i <= 5; i++) {
          const rawVal = document.getElementById(`pii-val-${i}`);
          const redVal = document.getElementById(`pii-token-${i}`);
          if (rawVal) {
            rawVal.classList.remove('hidden', 'disintegrating');
          }
          if (redVal) {
            redVal.classList.add('hidden');
          }
        }
      }

      // Desintegração Interativa no Sandbox Customizado
      function triggerCustomDustDisintegration() {
        tourState.userInteracted = true;
        const input = document.getElementById('custom-pii-input');
        const btn = document.getElementById('btn-custom-disintegrate');
        if (!input) return;
        playDustSound();
        spawnParticlesAtElement(input, 80);

        input.classList.add('opacity-40');
        if (btn) btn.disabled = true;

        setTimeout(() => {
          input.value = '[DADO_SENSIVEL_BLINDADO:TOKEN_AURA_4B]';
          input.classList.remove('opacity-40');
          input.classList.add('text-emerald-400', 'font-bold');
          if (btn) btn.disabled = false;
        }, 400);
      }

      // =========================================================================
      // DADOS DOS CENÁRIOS MULTISSETORIAIS (COM PERGUNTAS E RESPOSTAS)
      // =========================================================================
      const chatScenarios = {
        posto: {
          userLabel: 'Gerente Executivo (Posto Central #042)',
          time: '17:42',
          query: 'Qual produto mais vendido hoje?',
          response: 'Hoje (Turno Atual), o item líder absoluto em volume e faturamento é a Gasolina Comum com 4.820 Litros vendidos (R$ 29.835,80 faturados), respondendo por 69,6% das vendas do turno. Em seguida: Diesel S-10 (2.340 L) e Conveniência/Café (312 unid.). Fechamento de caixa 100% auditado com R$ 0,00 de divergência.',
          dcTitle: 'Diagnóstico Operacional Consolidado',
          badgeText: 'MARGEM OTIMIZADA',
          badgeClass: 'px-2 py-0.5 rounded text-[9px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30',
          metricLabel1: 'Produto Mais Vendido',
          metricVal1: 'Gasolina Comum (4.820 L)',
          metricVal1Class: 'font-extrabold text-white text-xs',
          metricLabel2: 'Faturamento Hoje',
          metricVal2: 'R$ 42.850,00',
          metricVal2Class: 'font-extrabold text-cyan-300 text-xs',
          btnActionText: 'Emitir Pedido de Reposição (30.000 L)',
          toastMsg: '✓ Pedido de 30.000 L protocolado na distribuidora em 1 clique!'
        },
        varejo: {
          userLabel: 'Gestor Operacional (Padaria & Bar Central)',
          time: '17:45',
          query: 'Qual produto mais vendido hoje e temos quebra no caixa da manhã?',
          response: 'Turno da manhã auditado em 31ms. O item mais vendido hoje é o Pão Francês Tradicional (1.840 unid.), seguido por Café Expresso Especial (420 xícaras). Não houve divergência de caixa (R$ 0,00). O insumo café em grãos atingiu 14% do ponto de segurança.',
          dcTitle: 'Auditoria de PDV & Estoque Crítico',
          badgeText: 'REPOSIÇÃO SUGERIDA',
          badgeClass: 'px-2 py-0.5 rounded text-[9px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30',
          metricLabel1: 'Item Mais Vendido',
          metricVal1: 'Pão Francês (1.840 un)',
          metricVal1Class: 'font-extrabold text-white text-xs',
          metricLabel2: 'Faturamento do Turno',
          metricVal2: 'R$ 14.890,00',
          metricVal2Class: 'font-extrabold text-cyan-300 text-xs',
          btnActionText: 'Emitir Ordem de Reposição de Café',
          toastMsg: '✓ Ordem de reposição emitida no canal de suprimentos em 1 clique!'
        },
        loja: {
          userLabel: 'Supervisor Regional (Loja & Varejo #12)',
          time: '17:48',
          query: 'Qual produto mais vendido hoje e houve discrepância com cupons NFC-e?',
          response: 'Conferência de vendas e cupons concluída em 29ms. O produto líder em vendas hoje é o Kit Lubrificante Sintético 5W30 (84 unid.), totalizando R$ 6.720,00. Foram emitidas 412 notas fiscais e todos os pagamentos em cartão e PIX conferem centavo a centavo.',
          dcTitle: 'Conferência Geral de Vendas e Caixa',
          badgeText: '100% RECONCILIADO',
          badgeClass: 'px-2 py-0.5 rounded text-[9px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30',
          metricLabel1: 'Item Campeão',
          metricVal1: 'Óleo Sintético 5W30 (84 un)',
          metricVal1Class: 'font-extrabold text-white text-xs',
          metricLabel2: 'Vendas Totais (NFC-e)',
          metricVal2: 'R$ 64.390,00',
          metricVal2Class: 'font-extrabold text-cyan-300 text-xs',
          btnActionText: 'Exportar Extrato Consolidado',
          toastMsg: '✓ Extrato executivo consolidado gerado com assinatura digital!'
        },
        fiscal: {
          userLabel: 'Diretor de Operações (Compliance Fiscal)',
          time: '17:50',
          query: 'Qual produto mais vendido hoje e existe risco fiscal na Portaria 26 da ANP?',
          response: 'Auditoria preventiva realizada em 24ms. O produto com maior movimentação foi o Etanol Hidratado (5.140 L). A variação volumétrica apurada no LMC físico vs contábil foi de +0.28%, perfeitamente enquadrada na tolerância legal de ±0.60%. Zero inconformidades.',
          dcTitle: 'Auditoria Preventiva Contínua',
          badgeText: 'ZERO RISCO FISCAL',
          badgeClass: 'px-2 py-0.5 rounded text-[9px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30',
          metricLabel1: 'Produto com Mais Volume',
          metricVal1: 'Etanol Hidratado (5.140 L)',
          metricVal1Class: 'font-extrabold text-white text-xs',
          metricLabel2: 'Variação LMC (ANP)',
          metricVal2: '+0.28% (Legal)',
          metricVal2Class: 'font-extrabold text-emerald-400 text-xs',
          btnActionText: 'Emitir Dossiê de Governança',
          toastMsg: '✓ Dossiê executivo de governança emitido para a diretoria!'
        }
      };

      // =========================================================================
      // MÁQUINA DE ESCREVER (TYPEWRITER AUTOMÁTICO) E PIPELINE SINCRONIZADO
      // =========================================================================
      let typewriterTimeout = null;
      let streamingTimeout = null;
      let pipelineTimeouts = [];

      function clearAllSimulations() {
        if (typewriterTimeout) {
          clearTimeout(typewriterTimeout);
          typewriterTimeout = null;
        }
        if (streamingTimeout) {
          clearTimeout(streamingTimeout);
          streamingTimeout = null;
        }
        pipelineTimeouts.forEach(t => clearTimeout(t));
        pipelineTimeouts = [];
        dustTimeouts.forEach(t => clearTimeout(t));
        dustTimeouts = [];
      }

      function runTypewriter(text, onComplete) {
        const typedEl = document.getElementById('step1-typed-text');
        const chatQueryEl = document.getElementById('chat-user-query-text');
        const cursor = document.getElementById('typewriter-cursor');
        if (typedEl) typedEl.textContent = '';
        if (chatQueryEl) chatQueryEl.textContent = '';
        if (cursor) cursor.classList.remove('hidden');

        let i = 0;
        function typeChar() {
          if (i < text.length) {
            const char = text.charAt(i);
            if (typedEl) typedEl.textContent += char;
            if (chatQueryEl) chatQueryEl.textContent += char;
            i++;
            if (tourState.soundEnabled && i % 3 === 0) playTone(720 + (i % 5) * 40, 'sine', 0.03, 0.02);
            typewriterTimeout = setTimeout(typeChar, 24);
          } else {
            if (cursor) cursor.classList.add('hidden');
            if (onComplete) onComplete();
          }
        }
        typeChar();
      }

      // Efeito Streaming em Tempo Real para a Resposta Executiva da AURA
      function runStreamingResponse(text, onComplete) {
        const el = document.getElementById('chat-response-narrative');
        const dcLive = document.getElementById('decisioncard-live');
        if (!el) {
          if (onComplete) onComplete();
          return;
        }
        el.textContent = '';
        if (dcLive) {
          dcLive.classList.add('hidden');
          dcLive.classList.remove('animate-fade-in');
        }

        const words = text.split(' ');
        let idx = 0;
        function streamWord() {
          if (idx < words.length) {
            el.textContent += (idx === 0 ? '' : ' ') + words[idx];
            idx++;
            if (tourState.soundEnabled && idx % 3 === 0) {
              playTone(520 + (idx % 4) * 35, 'sine', 0.02, 0.02);
            }
            streamingTimeout = setTimeout(streamWord, 18);
          } else {
            if (dcLive) {
              dcLive.classList.remove('hidden');
              dcLive.classList.add('animate-fade-in');
            }
            if (onComplete) onComplete();
          }
        }
        streamWord();
      }

      // Simulação Autônoma Mestre: Chat (Esquerda) vs Backend (Direita)
      function runAutonomousShowcase(scenarioKey = null) {
        if (scenarioKey) tourState.currentScenario = scenarioKey;
        const scenario = chatScenarios[tourState.currentScenario] || chatScenarios.posto;
        tourState.isSimulating = true;

        clearAllSimulations();
        resetDustDisintegration();

        // Elementos do Chat da Esquerda
        const userLabel = document.getElementById('chat-user-label');
        const timestamp = document.getElementById('chat-timestamp-label');
        const thinkingBox = document.getElementById('chat-thinking-box');
        const thinkingText = document.getElementById('thinking-step-text');
        const thinkingBar = document.getElementById('thinking-progress-bar');
        const responseRow = document.getElementById('chat-response-row');
        const dcTitle = document.getElementById('mini-dc-title');
        const dcBadge = document.getElementById('mini-dc-badge');
        const mLabel1 = document.getElementById('mini-metric-label-1');
        const mVal1 = document.getElementById('mini-metric-val-1');
        const mLabel2 = document.getElementById('mini-metric-label-2');
        const mVal2 = document.getElementById('mini-metric-val-2');
        const btnAction = document.getElementById('mini-dc-action-text');
        const chatInput = document.getElementById('chat-interactive-input');
        const simStatusBadge = document.getElementById('sim-status-badge');

        if (userLabel) userLabel.textContent = scenario.userLabel;
        if (timestamp) timestamp.textContent = `${scenario.time} • Ao Vivo`;
        if (chatInput) chatInput.value = scenario.query;
        if (simStatusBadge) simStatusBadge.textContent = 'EXECUTANDO...';

        // Esconde resposta prévia e thinking
        if (responseRow) responseRow.classList.add('hidden');
        if (thinkingBox) thinkingBox.classList.add('hidden');
        if (thinkingBar) thinkingBar.style.width = '10%';

        // Reseta destaques dos nós da direita
        const allNodes = ['graph-node-prompt', 'pipe-node-1', 'graph-node-lgpd', 'pipe-node-2', 'graph-node-decisao'];
        allNodes.forEach(id => {
          const el = document.getElementById(id);
          if (el) el.classList.remove('active-glow', 'success-glow', 'pulse-highlight');
        });

        // 1. Digitação automática da pergunta (Typewriter)
        runTypewriter(scenario.query, () => {
          playTone(600, 'sine', 0.05, 0.04);

          // 2. Aciona o Indicador de Análise no chat e ativa o Nó 1 no Backend
          const t1 = setTimeout(() => {
            if (thinkingBox) thinkingBox.classList.remove('hidden');
            if (thinkingText) thinkingText.textContent = 'Detectando intenção semântica da pergunta...';
            if (thinkingBar) thinkingBar.style.width = '25%';

            const node1 = document.getElementById('graph-node-prompt');
            if (node1) node1.classList.add('active-glow');
            playTone(480, 'sine', 0.08, 0.04);
          }, 150);
          pipelineTimeouts.push(t1);

          // 3. Nó 2: Busca Operacional de Borda (Telemetria)
          const t2 = setTimeout(() => {
            if (thinkingText) thinkingText.textContent = 'Consultando telemetria operacional de PDVs e estoques...';
            if (thinkingBar) thinkingBar.style.width = '50%';

            const node1 = document.getElementById('graph-node-prompt');
            if (node1) node1.classList.remove('active-glow');
            const node2 = document.getElementById('pipe-node-1');
            if (node2) node2.classList.add('active-glow');
            playTone(560, 'sine', 0.08, 0.04);
          }, 850);
          pipelineTimeouts.push(t2);

          // 4. Nó 3: Escudo AURA Guard™ & Desintegração em Poeira (LGPD)
          const t3 = setTimeout(() => {
            if (thinkingText) thinkingText.textContent = 'Escudo AURA Guard™: isolando dados confidenciais (LGPD)...';
            if (thinkingBar) thinkingBar.style.width = '75%';

            const node2 = document.getElementById('pipe-node-1');
            if (node2) node2.classList.remove('active-glow');
            const node3 = document.getElementById('graph-node-lgpd');
            if (node3) node3.classList.add('active-glow');

            triggerDustDisintegration(true, 2400, () => {
              // 5. Nó 4: Motor Analítico Sub-100ms & Auditoria de Precisão
              const t4 = setTimeout(() => {
                if (thinkingText) thinkingText.textContent = 'Conferindo notas fiscais, estoque e fechamento de caixa...';
                if (thinkingBar) thinkingBar.style.width = '92%';

                if (node3) node3.classList.remove('active-glow');
                const node4 = document.getElementById('pipe-node-2');
                if (node4) node4.classList.add('active-glow');
                playTone(660, 'sine', 0.08, 0.04);

                // 6. Nó 5: Entrega da Decisão & Resposta Streaming no Chat
                const t5 = setTimeout(() => {
                  if (node4) node4.classList.remove('active-glow');
                  const node5 = document.getElementById('graph-node-decisao');
                  if (node5) node5.classList.add('success-glow');

                  if (thinkingBox) thinkingBox.classList.add('hidden');

                  // Preenche dados do DecisionCard
                  if (dcTitle) dcTitle.textContent = scenario.dcTitle;
                  if (dcBadge) {
                    dcBadge.textContent = scenario.badgeText;
                    dcBadge.className = scenario.badgeClass;
                  }
                  if (mLabel1) mLabel1.textContent = scenario.metricLabel1;
                  if (mVal1) {
                    mVal1.textContent = scenario.metricVal1;
                    mVal1.className = scenario.metricVal1Class;
                  }
                  if (mLabel2) mLabel2.textContent = scenario.metricLabel2;
                  if (mVal2) {
                    mVal2.textContent = scenario.metricVal2;
                    mVal2.className = scenario.metricVal2Class;
                  }
                  if (btnAction) btnAction.textContent = scenario.btnActionText;

                  if (responseRow) {
                    responseRow.classList.remove('hidden');
                    responseRow.classList.add('animate-fade-in');
                  }

                  runStreamingResponse(scenario.response, () => {
                    if (simStatusBadge) simStatusBadge.textContent = 'CONCLUÍDO (38ms)';
                    playChime();
                    tourState.isSimulating = false;

                    setTimeout(() => {
                      if (node5) node5.classList.remove('success-glow');
                    }, 1400);
                  });
                }, 850);
                pipelineTimeouts.push(t5);

              }, 100);
              pipelineTimeouts.push(t4);
            });
          }, 1500);
          pipelineTimeouts.push(t3);

        });
      }

      function selectChatScenario(scenarioKey) {
        tourState.userInteracted = true;
        tourState.currentScenario = scenarioKey;
        playTone(580, 'sine', 0.1, 0.05);

        const keys = ['posto', 'varejo', 'loja', 'fiscal'];
        keys.forEach(k => {
          const btn = document.getElementById(`scenario-btn-${k}`);
          if (btn) {
            if (k === scenarioKey) {
              btn.className = 'px-2 py-1.5 rounded-lg bg-cyan-500/20 text-cyan-200 border border-cyan-500/40 font-semibold truncate transition-all text-left flex items-center gap-1';
            } else {
              btn.className = 'px-2 py-1.5 rounded-lg bg-slate-900/80 text-slate-300 hover:text-white border border-white/10 truncate transition-all text-left flex items-center gap-1';
            }
          }
        });

        runAutonomousShowcase(scenarioKey);
      }

      function simulateChatSubmit() {
        tourState.userInteracted = true;
        const chatInput = document.getElementById('chat-interactive-input');
        if (chatInput && chatInput.value.trim()) {
          const val = chatInput.value.trim();
          chatScenarios[tourState.currentScenario].query = val;
        }
        runAutonomousShowcase(tourState.currentScenario);
      }

      function simulateChatActionClick() {
        tourState.userInteracted = true;
        playActionSound();
        const scenario = chatScenarios[tourState.currentScenario] || chatScenarios.posto;
        const toast = document.getElementById('mini-chat-action-toast');
        const msg = document.getElementById('mini-chat-toast-message');
        if (toast && msg) {
          msg.textContent = scenario.toastMsg;
          toast.classList.remove('hidden');
          toast.classList.add('animate-fade-in');
          setTimeout(() => {
            toast.classList.add('hidden');
          }, 3500);
        }
      }

      function runGraphPulseAnimation() {
        const nodes = ['prompt', 'lgpd', 'motor', 'regras', 'decisao'];
        nodes.forEach((nodeId, idx) => {
          setTimeout(() => {
            const el = document.getElementById(`graph-node-${nodeId}`) || document.getElementById(`pipe-node-1`);
            if (el) {
              el.classList.add('active-glow');
              playTone(400 + idx * 80, 'sine', 0.06, 0.03);
              setTimeout(() => el.classList.remove('active-glow'), 400);
            }
          }, idx * 100);
        });
      }

      function inspectGraphNode(nodeKey) {
        tourState.userInteracted = true;
        playTone(660, 'sine', 0.1, 0.05);
        const panel = document.getElementById('graph-detail-text');
        if (!panel) return;

        const descriptions = {
          prompt: '1. Entrada em Linguagem Natural: O gestor envia consultas operacionais em português corrente (sem SQL ou fórmulas).',
          lgpd: '2. Escudo LGPD (Lei 13.709/2018): CPFs, CNPJs e credenciais são desintegrados na borda física. Zero trânsito de dados pessoais.',
          motor: '3. Telemetria de Borda: Conexão direta com bicos, encerrantes e estoque físico.',
          regras: '4. Auditoria & Conferência Exata: Conferência matemática direta de notas fiscais, estoque e caixa.',
          decisao: '5. DecisionCard™ em 1 Clique: Resultado claro e resumido com botão para resolver na hora.'
        };
        panel.textContent = descriptions[nodeKey] || 'Parâmetro auditado pelo motor de borda.';
      }

      function inspectNode(nodeType) {
        inspectGraphNode(nodeType === 'pista' ? 'motor' : nodeType);
      }

      function simulateActionClick(actionType) {
        tourState.userInteracted = true;
        playActionSound();
        const toast = document.getElementById('action-feedback-toast');
        const msg = document.getElementById('action-feedback-message');
        if (toast && msg) {
          msg.textContent = '✓ Ordem executada com sucesso em 1 toque!';
          toast.classList.remove('hidden');
          setTimeout(() => toast.classList.add('hidden'), 3000);
        }
      }

      function toggleStep4Tab(tabName) {
        const viewComp = document.getElementById('view-step4-companion');
        if (viewComp) {
          if (tabName === 'companion') {
            viewComp.classList.toggle('hidden');
          } else {
            viewComp.classList.add('hidden');
          }
        }
      }

      function simulatePipelinePulse() {
        runGraphPulseAnimation();
      }

      function simulateStep1Question() {
        runAutonomousShowcase('posto');
      }

      // Funções de Interação com o Knowledge Graph
      function highlightKnowledgeNode(nodeKey) {
        tourState.userInteracted = true;
        playTone(540, 'sine', 0.08, 0.03);

        const readout = document.getElementById('kg-status-readout');
        const reasoningTitle = document.getElementById('kg-reasoning-title');
        const reasoningText = document.getElementById('kg-reasoning-text');

        // Atualiza estado ativo na Coluna 1
        document.querySelectorAll('.kg-context-item').forEach(el => {
          el.classList.remove('active');
        });
        const activeItem = document.getElementById('kg-item-' + nodeKey);
        if (activeItem) {
          activeItem.classList.add('active');
        }

        // Atualiza realce nos nós SVG
        document.querySelectorAll('[id^="kg-node-"]').forEach(node => {
          node.classList.remove('kg-node-selected');
        });
        const svgNode = document.getElementById('kg-node-' + nodeKey);
        if (svgNode) {
          svgNode.classList.add('kg-node-selected');
        }

        // Atualiza realce nas arestas conectadas
        document.querySelectorAll('.homepage-knowledge-graph-v3_edge').forEach(edge => {
          edge.classList.remove('active-edge');
        });
        const activeEdge = document.getElementById('kg-edge-' + nodeKey);
        if (activeEdge) {
          activeEdge.classList.add('active-edge');
        }

        const nodeData = {
          vendas: {
            readout: 'Nó Selecionado: Vendas PDV • Cupons NFC-e conciliados em tempo real.',
            title: 'Reconciliação Litro a Litro',
            text: 'O cupom NFC-e #3526 foi conciliado com o bico 04 e o Tanque 02 em 12ms. Nenhuma quebra física ou fiscal identificada no turno.'
          },
          caixas: {
            readout: 'Nó Selecionado: Fechamento de Caixa • Sangrias e gavetas conferidas.',
            title: 'Auditoria de Gaveta Zero Furo',
            text: 'Conferência cega entre encerrantes eletrônicos e extrato de cartões. Diferença zero (R$ 0,00) em todos os turnos hoje.'
          },
          estoque: {
            readout: 'Nó Selecionado: Estoque Físico & Tanques • Telemetria volumétrica contínua.',
            title: 'Monitoramento Preditivo de Run-Out',
            text: 'Tanque 02 em 16% de capacidade. Vazão estimada em 245 L/h com autonomia segura de 18.4 horas. Reposição sugerida.'
          },
          regras: {
            readout: 'Nó Selecionado: Regras ANP & Fiscais • Portaria 26/1992 em conformidade.',
            title: 'Escrituração LMC Sem Inconformidades',
            text: 'Variação apurada de +0.28% dentro do corredor regulatório de ±0.60%. Risco de autuação fiscal nulo.'
          },
          tolerancias: {
            readout: 'Nó Selecionado: Tolerâncias e Perdas • Fim da perda aceita oculta.',
            title: 'Bloqueio de Sangrias Ocultas',
            text: 'Perdas invisíveis identificadas no mesmo dia através do cruzamento entre fiscal e nível físico.'
          },
          core: {
            readout: 'Nó Selecionado: AURA Knowledge Core • Orquestração relacional em borda.',
            title: 'Núcleo Relacional Borda Local',
            text: 'Todas as entidades operacionais estão interligadas sem necessidade de envio de dados brutos para nuvem.'
          }
        };

        const item = nodeData[nodeKey] || nodeData.vendas;
        if (readout) readout.textContent = item.readout;
        if (reasoningTitle) reasoningTitle.textContent = item.title;
        if (reasoningText) reasoningText.textContent = item.text;
      }

      // Funções de Compatibilidade com Métodos Anteriores
      function goToStep(s) {
        if (s === 1) selectChatScenario('posto');
        else if (s === 2) triggerDustDisintegration(true);
        else if (s === 3) runGraphPulseAnimation();
        else if (s === 4) toggleStep4Tab('companion');
      }
      function nextStep() { runAutonomousShowcase(); }
      function prevStep() { runAutonomousShowcase(); }
      function startTour() { runAutonomousShowcase(); }
      function pauseTour() { clearAllSimulations(); }
      function restartTour() {
        hasStartedForCurrentView = true;
        runAutonomousShowcase('posto');
      }

      // =========================================================================
      // SCROLLYTELLING: ROLAGEM SUAVE, PROGRESSO E INTERSECTION OBSERVER
      // =========================================================================
      function scrollToSection(sectionId) {
        tourState.userInteracted = true;
        if (sectionId === 'top') {
          window.scrollTo({ top: 0, behavior: 'smooth' });
          return;
        }
        const target = document.getElementById(sectionId);
        if (target) {
          target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      }

      function updateScrollProgress() {
        const winScroll = document.documentElement.scrollTop || document.body.scrollTop;
        const height = document.documentElement.scrollHeight - document.documentElement.clientHeight;
        const scrolled = height > 0 ? (winScroll / height) * 100 : 0;
        const bar = document.getElementById('scroll-progress-bar');
        if (bar) bar.style.width = `${scrolled}%`;

        const sections = ['top', 'sec-chat-graph', 'sec-blindagem', 'sec-custo-ia', 'sec-knowledge-graph', 'sec-diferenciacao', 'sec-faq'];
        for (let i = sections.length - 1; i >= 0; i--) {
          const secId = sections[i];
          if (secId === 'top') {
            if (winScroll < 200) {
              document.querySelectorAll('.scroll-nav-dot').forEach(dot => {
                dot.classList.toggle('active', dot.getAttribute('data-section') === 'top');
              });
              break;
            }
            continue;
          }
          const el = document.getElementById(secId);
          if (el) {
            const topPos = el.getBoundingClientRect().top + winScroll;
            if (winScroll + 260 >= topPos) {
              document.querySelectorAll('.scroll-nav-dot').forEach(dot => {
                dot.classList.toggle('active', dot.getAttribute('data-section') === secId);
              });
              break;
            }
          }
        }
      }

      // Gerenciador de Disparo no Scroll
      let hasStartedForCurrentView = false;

      function checkScrollAndTriggerShowcase() {
        const el = document.getElementById('sec-chat-graph');
        if (!el) return;
        const rect = el.getBoundingClientRect();
        const vh = window.innerHeight || document.documentElement.clientHeight;

        const inComfortableView = (rect.top <= vh * 0.72) && (rect.bottom >= vh * 0.20);

        if (inComfortableView) {
          if (!hasStartedForCurrentView && !tourState.isSimulating) {
            hasStartedForCurrentView = true;
            tourState.hasAutoStarted = true;
            runAutonomousShowcase();
          }
        } else {
          if (rect.top > vh * 1.05 || rect.bottom < -50) {
            hasStartedForCurrentView = false;
          }
        }
      }

      // =========================================================================
      // INICIALIZAÇÃO AUTOMÁTICA VIA INTERSECTION OBSERVER E SCROLL
      // =========================================================================
      document.addEventListener('DOMContentLoaded', function() {
        if (window.lucide) window.lucide.createIcons();

        // Toggle SFX
        const btnSfx = document.getElementById('btn-toggle-sfx-showcase');
        const iconSfx = document.getElementById('icon-sfx');
        if (btnSfx) {
          btnSfx.addEventListener('click', () => {
            tourState.soundEnabled = !tourState.soundEnabled;
            if (iconSfx) {
              iconSfx.setAttribute('data-lucide', tourState.soundEnabled ? 'volume-2' : 'volume-x');
              if (window.lucide) window.lucide.createIcons();
            }
          });
        }

        // Chat input enter listener
        const chatInput = document.getElementById('chat-interactive-input');
        if (chatInput) {
          chatInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
              e.preventDefault();
              simulateChatSubmit();
            }
          });
        }

        // Scroll listener para barra de progresso e verificação contínua
        window.addEventListener('scroll', () => {
          updateScrollProgress();
          checkScrollAndTriggerShowcase();
        }, { passive: true });

        // IntersectionObserver para reveal suave e DISPARO AUTÔNOMO NO SCROLL
        if (typeof IntersectionObserver !== 'undefined') {
          const showcaseObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
              if (entry.isIntersecting) {
                entry.target.classList.add('scroll-reveal-visible');

                // Quando a seção do chat entra no viewport pelo scroll
                if (entry.target.id === 'sec-chat-graph') {
                  checkScrollAndTriggerShowcase();
                }

                // Animação de realce nos cards e tabela de ROI ao rolar até eles
                if (entry.target.id === 'sec-diferenciacao') {
                  const cards = entry.target.querySelectorAll('.roi-card');
                  cards.forEach((c, i) => {
                    setTimeout(() => {
                      c.classList.add('revealed');
                    }, i * 140);
                  });
                  const tableBars = entry.target.querySelectorAll('.roi-table-bar');
                  tableBars.forEach((tb, i) => {
                    setTimeout(() => {
                      tb.classList.add('revealed');
                    }, 280 + i * 120);
                  });
                  entry.target.classList.add('roi-table-revealed');
                }

                // Animação de barras empilhadas na seção de Custo de IA
                if (entry.target.id === 'sec-custo-ia') {
                  const costBars = entry.target.querySelectorAll('.cost-bar-item');
                  costBars.forEach((bar, i) => {
                    setTimeout(() => {
                      bar.classList.add('revealed');
                    }, i * 80);
                  });
                }
              }
            });
          }, { threshold: [0.15, 0.35, 0.6] });

          document.querySelectorAll('.scroll-reveal').forEach(el => {
            showcaseObserver.observe(el);
          });
        } else {
          // Fallback para navegadores legados sem IntersectionObserver
          document.querySelectorAll('.scroll-reveal').forEach(el => {
            el.classList.add('scroll-reveal-visible');
          });
          document.querySelectorAll('.roi-card').forEach(c => c.classList.add('revealed'));
          document.querySelectorAll('.roi-table-bar').forEach(tb => tb.classList.add('revealed'));
          document.querySelectorAll('.cost-bar-item').forEach(b => b.classList.add('revealed'));
          setTimeout(() => {
            runAutonomousShowcase('posto');
          }, 600);
        }
      });

      // API Pública window.auraTour
      window.auraTour = {
        runAutonomousShowcase,
        runStreamingResponse,
        goToStep,
        nextStep,
        prevStep,
        startTour,
        pauseTour,
        restartTour,
        triggerDustDisintegration,
        resetDustDisintegration,
        triggerCustomDustDisintegration,
        simulateStep1Question,
        simulatePipelinePulse,
        inspectNode,
        simulateActionClick,
        toggleStep4Tab,
        selectChatScenario,
        simulateChatSubmit,
        simulateChatActionClick,
        inspectGraphNode,
        scrollToSection,
        highlightKnowledgeNode
      };

    })();
  </script>
</body>
</html>
"""
    return html

if __name__ == "__main__":
    out_path = Path(__file__).resolve().parent.parent / "web" / "showcase.html"
    content = generate_showcase_html()
    out_path.write_text(content, encoding="utf-8")
    print(f"showcase.html gerado com sucesso em: {out_path} ({len(content)} bytes)")
