"""
Gerador da Página de Apresentação e Showcase Executivo AURA (web/showcase.html)
Atualizado com Arquitetura Autônoma de Simulação em Tempo Real:
1. Eliminação de Player Artificial (sem play/pause ou slides manuais forçados).
2. Simulação Autônoma Conectada Esquerda vs Direita:
   - Lado Esquerdo: Chat da AURA com efeito typewriter automático ("Qual produto mais vendido hoje?"),
     indicador de análise pulsando e streaming do DecisionCard executivo Precision Glass.
   - Lado Direito: Backend de Borda em tempo real com Detecção de Intenção Semântica, Busca Operacional,
     Escudo AURA Guard™ com desintegração em poeira de dados confidenciais (LGPD 13.709/2018), cálculo sub-100ms e entrega.
3. Acionamento 100% Autônomo ao rolar a página (IntersectionObserver) + Botão elegante "Ver animação de novo ↺".
4. Matriz de Diferenciação Operacional com ROI real preservada e integrada.
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
            slateSurface: '#0c121e',
            slateCard: '#0f172a',
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
    /* Estilos Customizados do Showcase Executivo */
    .showcase-mesh-bg {
      background-color: #07090e;
      background-image: 
        radial-gradient(at 0% 0%, rgba(6, 182, 212, 0.10) 0px, transparent 50%),
        radial-gradient(at 100% 0%, rgba(124, 58, 237, 0.10) 0px, transparent 50%),
        radial-gradient(at 50% 50%, rgba(16, 185, 129, 0.07) 0px, transparent 60%),
        radial-gradient(at 100% 100%, rgba(6, 182, 212, 0.07) 0px, transparent 50%);
    }

    /* Barra de Progresso de Rolagem Global no Topo */
    #scroll-progress-bar {
      position: fixed;
      top: 0;
      left: 0;
      height: 3px;
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
      width: 8px;
      height: 8px;
      border-radius: 9999px;
      background: rgba(255, 255, 255, 0.25);
      border: 1px solid rgba(255, 255, 255, 0.35);
      transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
      position: relative;
    }
    .scroll-nav-dot:hover, .scroll-nav-dot.active {
      width: 10px;
      height: 10px;
      background: #06b6d4;
      border-color: #22d3ee;
      box-shadow: 0 0 10px rgba(6, 182, 212, 0.45);
    }

    /* Utilitário de Scroll Reveal Suave */
    .scroll-reveal {
      opacity: 0;
      transform: translateY(22px);
      transition: opacity 0.65s cubic-bezier(0.16, 1, 0.3, 1), transform 0.65s cubic-bezier(0.16, 1, 0.3, 1);
      will-change: opacity, transform;
    }
    .scroll-reveal.scroll-reveal-visible {
      opacity: 1;
      transform: translateY(0);
    }

    /* Cards com Glow Suavizado (Liquid Glass Executivo Sóbrio) */
    .glass-card-glow-cyan {
      background: rgba(12, 18, 30, 0.88);
      border: 1px solid rgba(6, 182, 212, 0.25);
      box-shadow: 0 12px 36px 0 rgba(0, 0, 0, 0.45), 0 0 14px 0 rgba(6, 182, 212, 0.10);
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
    }

    .glass-card-glow-emerald {
      background: rgba(12, 18, 30, 0.88);
      border: 1px solid rgba(16, 185, 129, 0.25);
      box-shadow: 0 12px 36px 0 rgba(0, 0, 0, 0.45), 0 0 14px 0 rgba(16, 185, 129, 0.10);
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
    }

    .glass-card-glow-purple {
      background: rgba(12, 18, 30, 0.88);
      border: 1px solid rgba(124, 58, 237, 0.25);
      box-shadow: 0 12px 36px 0 rgba(0, 0, 0, 0.45), 0 0 14px 0 rgba(124, 58, 237, 0.10);
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
    }

    /* Conectores SVG com Pulso de Fótons em Tempo Real */
    @keyframes pulse-flow {
      0% {
        stroke-dashoffset: 120;
        opacity: 0.4;
      }
      50% {
        opacity: 1;
      }
      100% {
        stroke-dashoffset: 0;
        opacity: 0.4;
      }
    }

    .flow-path-active {
      stroke-dasharray: 8 6;
      animation: pulse-flow 2s linear infinite;
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
      animation: photon-travel 0.85s cubic-bezier(0.4, 0, 0.2, 1) infinite;
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
      transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
      display: inline-block;
    }
    .pii-raw.disintegrating {
      color: transparent;
      text-shadow: 0 0 8px rgba(6, 182, 212, 0.8), 0 0 16px rgba(16, 185, 129, 0.6);
      transform: scale(0.96) skewX(-2deg);
      filter: blur(3px);
    }
    .pii-redacted {
      transition: all 0.4s ease;
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

    /* Estados Reativos dos Nós do Pipeline */
    .pipeline-node, .graph-node {
      transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    .pipeline-node.pulse-highlight, .graph-node.active-glow {
      border-color: #22d3ee !important;
      box-shadow: 0 0 18px rgba(6, 182, 212, 0.35), inset 0 0 10px rgba(6, 182, 212, 0.10);
      transform: scale(1.015);
    }
    .graph-node.success-glow {
      border-color: #34d399 !important;
      box-shadow: 0 0 18px rgba(16, 185, 129, 0.35), inset 0 0 10px rgba(16, 185, 129, 0.10);
      transform: scale(1.015);
    }
    .graph-node.active-selected {
      border-color: #22d3ee !important;
      background: rgba(15, 23, 42, 0.95) !important;
      box-shadow: 0 0 16px rgba(6, 182, 212, 0.35);
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

    /* Suavização de Botões com Glow Moderado e Elegante */
    .btn-aura-glow-soft {
      box-shadow: 0 4px 14px 0 rgba(0, 0, 0, 0.35), 0 0 10px 0 rgba(16, 185, 129, 0.12);
      transition: all 0.25s ease;
    }
    .btn-aura-glow-soft:hover {
      filter: brightness(1.06);
      box-shadow: 0 6px 18px 0 rgba(0, 0, 0, 0.4), 0 0 14px 0 rgba(6, 182, 212, 0.2);
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

    .roi-card {
      transition: all 0.35s ease;
    }
  </style>
</head>
<body id="top" class="min-h-screen flex flex-col showcase-mesh-bg text-slate-200 antialiased selection:bg-auraCyan/30 selection:text-white overflow-x-hidden">

  <!-- Barra de Progresso de Scroll Superior -->
  <div id="scroll-progress-bar"></div>

  <!-- Trilho Lateral Flutuante de Navegação por Scroll (Desktop) -->
  <aside class="scroll-nav-rail hidden lg:flex" aria-label="Navegação Rápida">
    <button onclick="window.auraTour.scrollToSection('top')" class="scroll-nav-dot active" title="01. Início & Visão Executiva" data-section="top"></button>
    <button onclick="window.auraTour.scrollToSection('sec-chat-graph')" class="scroll-nav-dot" title="02. Demonstração Autônoma (Chat vs Backend)" data-section="sec-chat-graph"></button>
    <button onclick="window.auraTour.scrollToSection('sec-blindagem')" class="scroll-nav-dot" title="03. Segurança de Dados & LGPD" data-section="sec-blindagem"></button>
    <button onclick="window.auraTour.scrollToSection('sec-diferenciacao')" class="scroll-nav-dot" title="04. Diferenciação Operacional & ROI" data-section="sec-diferenciacao"></button>
    <button onclick="window.auraTour.scrollToSection('sec-faq')" class="scroll-nav-dot" title="05. FAQ Executivo" data-section="sec-faq"></button>
  </aside>

  <!-- =========================================================================
       HEADER EXECUTIVO DO SHOWCASE
       ========================================================================= -->
  <header class="sticky top-0 z-50 glass-panel border-b border-white/10 px-4 py-3 backdrop-blur-xl bg-obsidian/90">
    <div class="max-w-7xl mx-auto flex items-center justify-between gap-4">
      
      <!-- Brand & Badges -->
      <div class="flex items-center gap-3">
        <a href="/" class="flex items-center gap-2.5 group" title="Retornar ao Console Operacional AURA">
          <div class="neural-core-orb !w-8 !h-8 group-hover:scale-105 transition-transform"></div>
          <div>
            <div class="flex items-center gap-2">
              <span class="font-display-title font-bold text-lg tracking-wider bg-gradient-to-r from-cyan-400 via-sky-300 to-purple-400 bg-clip-text text-transparent">AURA</span>
              <span class="px-2 py-0.5 rounded-full text-[9px] font-sans font-semibold bg-auraEmerald/15 text-auraEmerald-light border border-auraEmerald/30">
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
      <nav class="hidden md:flex items-center gap-1.5 text-xs font-sans">
        <button onclick="window.auraTour.scrollToSection('sec-chat-graph')" class="px-3 py-1.5 rounded-lg text-cyan-300 hover:text-white hover:bg-cyan-500/10 transition-colors font-semibold flex items-center gap-1.5">
          <span class="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-ping"></span>
          <span>Demonstração ao Vivo</span>
        </button>
        <button onclick="window.auraTour.scrollToSection('sec-blindagem')" class="px-3 py-1.5 rounded-lg text-slate-300 hover:text-white hover:bg-white/5 transition-colors">
          Escudo LGPD
        </button>
        <button onclick="window.auraTour.scrollToSection('sec-diferenciacao')" class="px-3 py-1.5 rounded-lg text-emerald-300 hover:text-white hover:bg-emerald-500/10 transition-colors font-medium">
          Diferenciação & ROI
        </button>
        <button onclick="window.auraTour.scrollToSection('sec-faq')" class="px-3 py-1.5 rounded-lg text-slate-300 hover:text-white hover:bg-white/5 transition-colors">
          FAQ
        </button>
      </nav>

      <!-- Botões de Ação Direta -->
      <div class="flex items-center gap-2.5">
        <button id="btn-toggle-sfx-showcase" class="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-slate-900/80 hover:bg-slate-800 text-slate-300 hover:text-white border border-white/10 text-xs transition-colors shadow-sm" title="Alternar Efeitos Sonoros">
          <i data-lucide="volume-2" id="icon-sfx" class="w-3.5 h-3.5 text-cyan-400"></i>
          <span class="hidden sm:inline text-[11px]">Áudio</span>
        </button>

        <a href="/" class="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-gradient-to-r from-cyan-500/20 to-purple-500/20 hover:from-cyan-500/30 hover:to-purple-500/30 text-cyan-300 hover:text-white border border-cyan-500/30 text-xs font-semibold transition-all shadow-sm active:scale-95">
          <span>Abrir Console AURA</span>
          <i data-lucide="arrow-up-right" class="w-3.5 h-3.5"></i>
        </a>
      </div>

    </div>
  </header>

  <!-- =========================================================================
       HERO EXECUTIVO: APRESENTAÇÃO MODERNA E INTUITIVA
       ========================================================================= -->
  <main class="flex-1 max-w-7xl w-full mx-auto px-4 py-8 sm:py-12 space-y-14">
    
    <!-- Hero Header Multissetorial -->
    <div class="text-center max-w-3xl mx-auto space-y-5 min-h-[58vh] sm:min-h-[65vh] flex flex-col justify-center items-center py-10 scroll-reveal scroll-reveal-visible">
      <div class="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-cyan-500/10 border border-cyan-500/25 text-xs font-sans text-cyan-300">
        <span class="w-2 h-2 rounded-full bg-cyan-400 animate-ping"></span>
        <span class="font-semibold tracking-wider uppercase text-[10px]">Arquitetura Universal: Postos • Padarias • Bares • Lojas • Franquias</span>
      </div>
      <h1 class="text-3xl sm:text-5xl font-extrabold tracking-tight text-white leading-tight font-display-title">
        O Cérebro Operacional de Qualquer Comércio ou Ponto de Venda. <br>
        <span class="bg-gradient-to-r from-cyan-400 via-emerald-300 to-purple-400 bg-clip-text text-transparent">
          Proteção Absoluta de Dados & 100% LGPD.
        </span>
      </h1>
      <p class="text-sm sm:text-base text-slate-300 leading-relaxed font-sans max-w-2xl mx-auto">
        Acompanhe como a AURA funciona na prática: role a página para ver a pergunta sendo analisada, os dados confidenciais protegidos na hora e a resposta executiva sendo gerada em segundos.
      </p>

      <!-- Indicador / Botão Convidativo de Rolagem -->
      <div class="pt-4 flex flex-col items-center gap-2.5">
        <button onclick="window.auraTour.scrollToSection('sec-chat-graph')" class="inline-flex items-center gap-2.5 px-5 py-2.5 rounded-full bg-slate-900/90 border border-cyan-500/30 text-cyan-300 hover:text-white hover:border-cyan-400 text-xs font-semibold transition-all shadow-lg hover:shadow-cyan-500/20 group">
          <span>Role para ver o fluxo em tempo real</span>
          <i data-lucide="arrow-down" class="w-4 h-4 group-hover:translate-y-1 transition-transform text-cyan-400"></i>
        </button>
        <div class="flex items-center gap-2 text-[11px] font-sans text-slate-400">
          <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
          <span>Demonstração Autônoma Sincronizada ao Scroll • Zero Cliques Forçados</span>
        </div>
      </div>
    </div>

    <!-- =========================================================================
         NÚCLEO DO SHOWCASE: CHAT DA AURA (ESQUERDA) VS SIMULAÇÃO DO BACKEND (DIREITA)
         (Acionado 100% de forma autônoma ao entrar no viewport pelo scroll)
         ========================================================================= -->
    <section id="sec-chat-graph" class="space-y-4 scroll-reveal">
      
      <!-- Barra Superior Discreta de Status e Replay -->
      <div class="glass-panel px-4 py-3 rounded-2xl border border-white/10 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs font-sans bg-slateSurface/80 shadow-md">
        <div class="flex items-center gap-2.5">
          <span class="w-2.5 h-2.5 rounded-full bg-cyan-400 shadow-[0_0_8px_#22d3ee]"></span>
          <span class="font-bold text-white text-[13px]">Fluxo Executivo em Tempo Real</span>
          <span class="text-slate-400 font-mono text-[11px] hidden sm:inline">| Esquerda: Chat da AURA • Direita: Simulação do Backend</span>
        </div>

        <div class="flex items-center gap-2">
          <!-- Botão Elegante de Replay para Rever a Animação -->
          <button onclick="window.auraTour.restartTour()" id="btn-tour-replay" class="btn-aura-glow-soft px-3.5 py-1.5 rounded-xl bg-slate-900/90 hover:bg-slate-800 text-cyan-300 hover:text-white border border-cyan-500/30 text-xs font-semibold transition-all flex items-center gap-2 active:scale-95" title="Reiniciar Simulação Autônoma">
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
        <div id="mini-chat-aura" class="lg:col-span-5 flex flex-col glass-panel rounded-2xl border border-white/10 shadow-2xl backdrop-blur-xl bg-slateSurface/95 overflow-hidden">
          
          <!-- Topo da Janela do Chat (Estilo macOS / App Nativo) -->
          <div class="p-3.5 border-b border-white/10 bg-white/[0.02] flex items-center justify-between">
            <div class="flex items-center gap-2">
              <span class="w-3 h-3 rounded-full bg-rose-500/80"></span>
              <span class="w-3 h-3 rounded-full bg-amber-500/80"></span>
              <span class="w-3 h-3 rounded-full bg-emerald-500/80"></span>
              <div class="flex items-center gap-1.5 ml-2">
                <div class="neural-core-orb !w-4 !h-4"></div>
                <span class="text-xs font-bold text-white">AURA Chat Executivo</span>
                <span class="text-[10px] text-slate-400 font-mono hidden sm:inline">• Processamento Local</span>
              </div>
            </div>
            <span class="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 flex items-center gap-1">
              <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping"></span>
              LGPD BLINDADO
            </span>
          </div>

          <!-- Seletor Rápido de Cenários Multissetoriais -->
          <div class="p-3 border-b border-white/5 bg-slate-950/50 space-y-1.5 font-sans">
            <div class="flex items-center justify-between text-[11px] text-slate-400">
              <span class="font-medium">Segmento da Demonstração:</span>
              <span class="text-cyan-400 text-[10px] font-mono" id="sim-status-badge">PRONTO</span>
            </div>
            <div class="grid grid-cols-2 sm:grid-cols-4 gap-1 text-[11px]">
              <button onclick="window.auraTour.selectChatScenario('posto')" id="scenario-btn-posto" class="px-2 py-1.5 rounded-lg bg-cyan-500/20 text-cyan-200 border border-cyan-500/40 font-semibold truncate transition-all text-left flex items-center gap-1">
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
              <div class="neural-core-orb !w-6 !h-6 flex-shrink-0 mt-0.5"></div>
              <div class="flex-1 p-3 rounded-2xl rounded-tl-sm bg-white/[0.03] border border-white/5 space-y-1.5">
                <div class="flex items-center gap-2 text-cyan-400 font-mono text-[11px]">
                  <span class="w-2 h-2 rounded-full bg-cyan-400 animate-ping"></span>
                  <span id="thinking-step-text" class="font-semibold">Consultando dados operacionais...</span>
                </div>
                <div class="w-full bg-black/40 h-1 rounded-full overflow-hidden">
                  <div id="thinking-progress-bar" class="h-full bg-gradient-to-r from-cyan-400 to-emerald-400 w-1/3 transition-all duration-300"></div>
                </div>
              </div>
            </div>

            <!-- Resposta Executiva da AURA com DecisionCard Precision Glass -->
            <div id="chat-response-row" class="hidden flex items-start gap-2.5">
              <div class="neural-core-orb !w-7 !h-7 flex-shrink-0 mt-0.5"></div>
              <div class="flex-1 space-y-3">
                <div class="flex items-center justify-between text-[10px] text-slate-400">
                  <span class="font-bold text-cyan-300 flex items-center gap-1">
                    <span>AURA</span>
                    <span class="px-1.5 py-0.2 rounded text-[9px] bg-cyan-500/20 text-cyan-300 font-mono">Processamento Local</span>
                  </span>
                  <span class="text-emerald-400 font-mono text-[10px]">38 ms • 100% LGPD</span>
                </div>
                
                <!-- Balão de Texto da Resposta Executiva -->
                <div class="p-3.5 rounded-2xl rounded-tl-sm bg-cyan-950/25 border border-cyan-500/30 text-slate-200 leading-relaxed space-y-3" id="chat-aura-response-bubble">
                  <p id="chat-response-narrative" class="font-sans text-xs text-slate-200">
                    Hoje (Turno Atual), o item líder absoluto em volume e faturamento é a <strong>Gasolina Comum</strong> com <strong>4.820 Litros</strong> vendidos (R$ 29.835,80 faturados), respondendo por 69,6% das vendas do turno. Em seguida: <strong>Diesel S-10</strong> (2.340 L) e <strong>Conveniência/Café</strong> (312 unid.). Fechamento de caixa 100% auditado com R$ 0,00 de divergência.
                  </p>

                  <!-- DecisionCard Executivo Precision Glass Incrustado -->
                  <div id="decisioncard-live" class="p-3.5 rounded-xl bg-black/70 border border-cyan-500/30 space-y-3 font-sans shadow-xl">
                    <div class="flex items-center justify-between border-b border-white/10 pb-2">
                      <div class="flex items-center gap-2">
                        <i data-lucide="sparkles" class="w-4 h-4 text-cyan-400"></i>
                        <span class="font-bold text-white text-xs" id="mini-dc-title">Diagnóstico Operacional Consolidado</span>
                      </div>
                      <span class="px-2 py-0.5 rounded text-[9px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 animate-pulse" id="mini-dc-badge">
                        MARGEM OTIMIZADA
                      </span>
                    </div>

                    <!-- Grid de 4 Indicadores Cruciais -->
                    <div class="grid grid-cols-2 gap-2 text-xs">
                      <div class="p-2 rounded-lg bg-white/[0.03] border border-white/5">
                        <div class="text-[10px] text-slate-400" id="mini-metric-label-1">Produto Mais Vendido</div>
                        <div class="font-extrabold text-white text-xs" id="mini-metric-val-1">Gasolina Comum (4.820 L)</div>
                        <div class="text-[9px] text-slate-400">69.6% do faturamento</div>
                      </div>
                      <div class="p-2 rounded-lg bg-white/[0.03] border border-white/5">
                        <div class="text-[10px] text-slate-400" id="mini-metric-label-2">Faturamento Consolidado</div>
                        <div class="font-extrabold text-cyan-300 text-xs" id="mini-metric-val-2">R$ 42.850,00</div>
                        <div class="text-[9px] text-slate-400">Turno Atual • 100% Auditado</div>
                      </div>
                      <div class="p-2 rounded-lg bg-white/[0.03] border border-white/5">
                        <div class="text-[10px] text-slate-400">Auditoria de Caixa</div>
                        <div class="font-extrabold text-emerald-400 text-xs">R$ 0,00 Diferença</div>
                        <div class="text-[9px] text-slate-400">Caixas 100% conferidos</div>
                      </div>
                      <div class="p-2 rounded-lg bg-white/[0.03] border border-white/5">
                        <div class="text-[10px] text-slate-400">Conformidade ANP (LMC)</div>
                        <div class="font-extrabold text-emerald-400 text-xs">+0.28%</div>
                        <div class="text-[9px] text-slate-400">Tolerância Portaria 26 (±0.60%)</div>
                      </div>
                    </div>

                    <!-- Botão Executivo de Ação em 1-Toque -->
                    <div class="space-y-1.5 pt-1">
                      <button onclick="window.auraTour.simulateChatActionClick()" id="mini-dc-action-btn" class="btn-aura-glow-soft w-full py-2.5 px-3 rounded-xl bg-gradient-to-r from-cyan-500 to-emerald-500 hover:brightness-105 text-slate-950 font-bold text-xs flex items-center justify-center gap-1.5 active:scale-95 transition-all border border-white/10">
                        <i data-lucide="send" class="w-3.5 h-3.5"></i>
                        <span id="mini-dc-action-text">Emitir Pedido de Reposição (30.000 L)</span>
                      </button>

                      <!-- Toast de Feedback de Ação -->
                      <div id="mini-chat-action-toast" class="hidden p-2 rounded-lg bg-emerald-500/20 border border-emerald-500/40 text-[10px] font-sans text-emerald-200 flex items-center gap-1.5 transition-all">
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

          <!-- Barra de Input Interativa do Chat (Para quem quiser testar manualmente) -->
          <div class="p-3 border-t border-white/10 bg-slate-900/80 space-y-2">
            <div class="flex items-center gap-2">
              <input type="text" id="chat-interactive-input" value="Qual produto mais vendido hoje?" class="flex-1 bg-black/60 border border-white/10 rounded-xl px-3 py-2 text-xs text-slate-200 font-sans focus:outline-none focus:border-cyan-400 transition-colors" placeholder="Digite uma dúvida executiva...">
              <button onclick="window.auraTour.simulateChatSubmit()" id="btn-simulate-chat-flow" class="btn-aura-glow-soft px-3.5 py-2 rounded-xl bg-gradient-to-r from-cyan-500 to-purple-500 hover:brightness-105 text-white font-bold text-xs flex items-center gap-1.5 active:scale-95 transition-all border border-white/10" title="Simular Novamente">
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
        <div id="aura-flowchart-graph" class="lg:col-span-7 flex flex-col glass-panel rounded-2xl border border-white/10 shadow-2xl backdrop-blur-xl bg-obsidian/95 overflow-hidden relative">
          
          <!-- Canvas Overlay de Partículas (Desintegração em Poeira) -->
          <canvas id="dust-particle-canvas"></canvas>

          <!-- Topo da Janela do Backend (Monitor de Telemetria de Borda) -->
          <div class="p-3.5 border-b border-white/10 bg-white/[0.02] flex items-center justify-between relative z-10">
            <div class="flex items-center gap-2">
              <i data-lucide="cpu" class="w-4 h-4 text-cyan-400"></i>
              <span class="text-xs font-bold text-white font-mono" id="stage-viewport-title">aura://backend/simulacao-operacional-borda</span>
            </div>
            <div class="flex items-center gap-2 text-[11px] font-mono text-slate-400">
              <span class="w-2 h-2 rounded-full bg-cyan-400 shadow-[0_0_8px_#22d3ee]"></span>
              <span id="stage-telemetry-badge">SINCRONIZADO AO CHAT EM TEMPO REAL</span>
            </div>
          </div>

          <!-- Sequência de 5 Nós Conectados em Tempo Real -->
          <div class="p-5 flex-1 space-y-2 relative font-sans text-xs z-10">
            
            <!-- NÓ 1: Detecção de Intenção Semântica (< 5ms) -->
            <div id="graph-node-prompt" class="graph-node p-3 rounded-xl bg-slate-900/90 border border-purple-500/30 flex items-center justify-between hover:bg-slate-800 transition-all shadow-sm cursor-pointer" onclick="window.auraTour.inspectGraphNode('prompt')">
              <div class="flex items-center gap-3">
                <div class="w-8 h-8 rounded-lg bg-purple-500/20 text-purple-300 flex items-center justify-center font-bold flex-shrink-0">
                  <i data-lucide="compass" class="w-4 h-4"></i>
                </div>
                <div>
                  <div class="font-bold text-white flex items-center gap-2">
                    <span>1. Compreensão da Pergunta</span>
                    <span class="px-1.5 py-0.2 rounded text-[9px] bg-purple-500/20 text-purple-300 font-mono">vendas_analitico</span>
                  </div>
                  <div class="text-[10px] text-slate-400">Entende linguagem natural direta, sem fórmulas, códigos ou relatórios manuais</div>
                </div>
              </div>
              <div class="flex items-center gap-2">
                <span class="px-2 py-0.5 rounded-full text-[10px] font-mono bg-purple-500/15 text-purple-300">2.1 ms</span>
                <span class="w-2.5 h-2.5 rounded-full bg-purple-400 shadow-[0_0_8px_#a855f7]"></span>
              </div>
            </div>

            <!-- Conector SVG 1 -->
            <div class="flex justify-center -my-1 h-5 items-center relative">
              <svg width="2" height="20" class="overflow-visible">
                <line x1="1" y1="0" x2="1" y2="20" stroke="url(#pipeGrad1)" stroke-width="2" class="flow-path-active" />
                <circle cx="1" cy="10" r="2.5" fill="#a855f7" class="photon-pulse" />
                <defs>
                  <linearGradient id="pipeGrad1" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stop-color="#a855f7" />
                    <stop offset="100%" stop-color="#06b6d4" />
                  </linearGradient>
                </defs>
              </svg>
            </div>

            <!-- NÓ 2: Busca Operacional de Borda (Telemetria & Concentrador) -->
            <div id="pipe-node-1" class="pipeline-node graph-node p-3 rounded-xl bg-slate-900/90 border border-cyan-500/40 flex items-center justify-between hover:bg-slate-800 transition-all shadow-sm cursor-pointer" onclick="window.auraTour.inspectNode('pista')">
              <div class="flex items-center gap-3">
                <div class="w-8 h-8 rounded-lg bg-cyan-500/20 text-cyan-300 flex items-center justify-center font-bold flex-shrink-0">
                  <i data-lucide="gauge" class="w-4 h-4"></i>
                </div>
                <div>
                  <div class="font-bold text-white flex items-center gap-2">
                    <span>2. Telemetria de Pista & Concentrador de PDV</span>
                    <span class="px-1.5 py-0.2 rounded text-[9px] bg-cyan-500/20 text-cyan-300 font-mono">Borda Local</span>
                  </div>
                  <div class="text-[10px] text-slate-400">Leitura direta de encerrantes, bicos, tanques e estoques físicos da loja</div>
                </div>
              </div>
              <div class="flex items-center gap-2">
                <span class="px-2 py-0.5 rounded-full text-[10px] font-mono bg-cyan-500/20 text-cyan-300">+11.8 ms</span>
                <span class="w-2.5 h-2.5 rounded-full bg-cyan-400 shadow-[0_0_8px_#22d3ee]"></span>
              </div>
            </div>

            <!-- Conector SVG 2 -->
            <div class="flex justify-center -my-1 h-5 items-center relative">
              <svg width="2" height="20" class="overflow-visible">
                <line x1="1" y1="0" x2="1" y2="20" stroke="url(#pipeGrad2)" stroke-width="2" class="flow-path-active" />
                <circle cx="1" cy="10" r="2.5" fill="#06b6d4" class="photon-pulse" />
                <defs>
                  <linearGradient id="pipeGrad2" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stop-color="#06b6d4" />
                    <stop offset="100%" stop-color="#10b981" />
                  </linearGradient>
                </defs>
              </svg>
            </div>

            <!-- NÓ 3: Escudo AURA Guard™ & Desintegração em Poeira (LGPD Lei 13.709/2018) -->
            <div id="graph-node-lgpd" class="graph-node p-3.5 rounded-xl bg-slate-900/90 border border-emerald-500/40 space-y-2.5 shadow-sm relative">
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-2.5">
                  <div class="w-8 h-8 rounded-lg bg-emerald-500/20 text-emerald-300 flex items-center justify-center font-bold flex-shrink-0">
                    <i data-lucide="shield-check" class="w-4 h-4"></i>
                  </div>
                  <div>
                    <div class="font-bold text-white flex items-center gap-2">
                      <span>3. Escudo AURA Guard™: Proteção de Dados Pessoais</span>
                      <span class="px-1.5 py-0.2 rounded text-[9px] bg-emerald-500/20 text-emerald-300 font-mono">Lei 13.709/2018</span>
                    </div>
                    <div class="text-[10px] text-slate-400">Identificação e remoção instantânea de dados pessoais em poeira antes da análise • 100% LGPD</div>
                  </div>
                </div>
                <div class="flex items-center gap-2">
                  <span id="dust-status-pill" class="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
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
                <button onclick="window.auraTour.triggerCustomDustDisintegration()" id="btn-custom-disintegrate" class="btn-aura-glow-soft px-2.5 py-1 rounded-lg bg-gradient-to-r from-cyan-500 to-emerald-500 hover:brightness-105 text-slate-950 font-bold text-[10px] font-sans flex items-center gap-1 whitespace-nowrap border border-white/10">
                  <i data-lucide="zap" class="w-3 h-3 fill-current"></i>
                  <span>Testar Proteção em Poeira</span>
                </button>
              </div>
            </div>

            <!-- Conector SVG 3 -->
            <div class="flex justify-center -my-1 h-5 items-center relative">
              <svg width="2" height="20" class="overflow-visible">
                <line x1="1" y1="0" x2="1" y2="20" stroke="url(#pipeGrad3)" stroke-width="2" class="flow-path-active" />
                <circle cx="1" cy="10" r="2.5" fill="#10b981" class="photon-pulse" />
                <defs>
                  <linearGradient id="pipeGrad3" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stop-color="#10b981" />
                    <stop offset="100%" stop-color="#f59e0b" />
                  </linearGradient>
                </defs>
              </svg>
            </div>

            <!-- NÓ 4: Motor Analítico Sub-100ms & Auditoria de Precisão -->
            <div id="pipe-node-2" class="pipeline-node graph-node p-3 rounded-xl bg-slate-900/90 border border-amber-500/40 flex items-center justify-between hover:bg-slate-800 transition-all shadow-sm cursor-pointer" onclick="window.auraTour.inspectNode('anp')">
              <div class="flex items-center gap-3">
                <div class="w-8 h-8 rounded-lg bg-amber-500/20 text-amber-300 flex items-center justify-center font-bold flex-shrink-0">
                  <i data-lucide="scale" class="w-4 h-4"></i>
                </div>
                <div>
                  <div class="font-bold text-white flex items-center gap-2">
                    <span>4. Motor de Auditoria & Conferência Exata</span>
                    <span class="px-1.5 py-0.2 rounded text-[9px] bg-amber-500/20 text-amber-300 font-mono">Auditoria Fiscal</span>
                  </div>
                  <div class="text-[10px] text-slate-400">Conferência matemática direta de estoques, notas fiscais e fechamento de caixa sem erros</div>
                </div>
              </div>
              <div class="flex items-center gap-2">
                <span class="px-2 py-0.5 rounded-full text-[10px] font-mono bg-amber-500/20 text-amber-300">+14.2 ms</span>
                <span class="w-2.5 h-2.5 rounded-full bg-amber-400 shadow-[0_0_8px_#fbbf24]"></span>
              </div>
            </div>

            <!-- Conector SVG 4 -->
            <div class="flex justify-center -my-1 h-5 items-center relative">
              <svg width="2" height="20" class="overflow-visible">
                <line x1="1" y1="0" x2="1" y2="20" stroke="url(#pipeGrad4)" stroke-width="2" class="flow-path-active" />
                <circle cx="1" cy="10" r="2.5" fill="#f59e0b" class="photon-pulse" />
                <defs>
                  <linearGradient id="pipeGrad4" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stop-color="#f59e0b" />
                    <stop offset="100%" stop-color="#10b981" />
                  </linearGradient>
                </defs>
              </svg>
            </div>

            <!-- NÓ 5: Entrega da Decisão Executiva ao Chat (Sub-42ms) -->
            <div id="graph-node-decisao" class="graph-node p-3 rounded-xl bg-slate-900/90 border border-emerald-500/50 flex items-center justify-between hover:bg-slate-800 transition-all shadow-sm cursor-pointer" onclick="window.auraTour.inspectGraphNode('decisao')">
              <div class="flex items-center gap-3">
                <div class="w-8 h-8 rounded-lg bg-emerald-500/20 text-emerald-300 flex items-center justify-center font-bold flex-shrink-0">
                  <i data-lucide="check-circle-2" class="w-4 h-4"></i>
                </div>
                <div>
                  <div class="font-bold text-white flex items-center gap-2">
                    <span>5. Entrega de Decisão & DecisionCard™</span>
                    <span class="px-1.5 py-0.2 rounded text-[9px] bg-emerald-500/20 text-emerald-300 font-mono">1 Clique</span>
                  </div>
                  <div class="text-[10px] text-slate-400">Resumo executivo pronto com botões de ação imediata enviados para o chat</div>
                </div>
              </div>
              <div class="flex items-center gap-2">
                <span class="px-2 py-0.5 rounded-full text-[10px] font-mono bg-emerald-500/20 text-emerald-300 font-bold">Total: 38.1 ms</span>
                <span class="w-2.5 h-2.5 rounded-full bg-emerald-400 shadow-[0_0_8px_#34d399]"></span>
              </div>
            </div>

          </div>

          <!-- Painel Inferior de Inspeção e Auditoria Profunda -->
          <div id="graph-node-detail-panel" class="p-3.5 border-t border-white/10 bg-white/[0.02] text-xs font-sans text-slate-300 flex flex-col sm:flex-row items-center justify-between gap-2 relative z-10">
            <div class="flex items-center gap-2">
              <i data-lucide="info" class="w-4 h-4 text-cyan-400 flex-shrink-0"></i>
              <span id="graph-detail-text">Processamento local instantâneo: dados pessoais protegidos e cálculo exato em menos de 42ms.</span>
            </div>
            <div class="flex items-center gap-2">
              <button onclick="window.auraTour.toggleStep4Tab('companion')" id="tab-step4-companion" class="px-2.5 py-1 rounded-lg bg-purple-500/20 text-purple-300 border border-purple-500/40 text-[10px] font-semibold flex items-center gap-1 hover:bg-purple-500/30 transition-all">
                <i data-lucide="layers" class="w-3 h-3"></i>
                <span>Companion Canvas™</span>
              </button>
            </div>
          </div>

          <!-- Modal / Gaveta do Companion Canvas (Auditoria Profunda de Estoque e ANP) -->
          <div id="view-step4-companion" class="hidden p-4 border-t border-purple-500/30 bg-slate-950/95 space-y-3 font-sans text-xs relative z-20">
            <div class="flex items-center justify-between border-b border-white/10 pb-2">
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
        <div class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-cyan-500/10 border border-cyan-500/25 text-[11px] text-cyan-300 font-sans">
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
        
        <div class="glass-panel p-5 rounded-2xl border border-white/10 space-y-3">
          <div class="w-10 h-10 rounded-xl bg-cyan-500/15 text-cyan-400 flex items-center justify-center">
            <i data-lucide="shield" class="w-5 h-5"></i>
          </div>
          <h3 class="font-bold text-white text-sm">Escudo de Privacidade AURA Guard™</h3>
          <p class="text-xs text-slate-400 leading-relaxed">
            Identificação e remoção instantânea de qualquer dado pessoal de clientes ou funcionários antes de qualquer análise, garantindo proteção total e conformidade com a LGPD.
          </p>
        </div>

        <div class="glass-panel p-5 rounded-2xl border border-white/10 space-y-3">
          <div class="w-10 h-10 rounded-xl bg-emerald-500/15 text-emerald-400 flex items-center justify-center">
            <i data-lucide="server" class="w-5 h-5"></i>
          </div>
          <h3 class="font-bold text-white text-sm">Processamento Local & Soberania dos Dados</h3>
          <p class="text-xs text-slate-400 leading-relaxed">
            Conecta direto na infraestrutura do banco da sua empresa. Sem faturas abusivas por milhões de tokens para processar seus próprios dados: cálculos determinísticos no seu ambiente e inteligência rápida e econômica.
          </p>
        </div>

        <div class="glass-panel p-5 rounded-2xl border border-white/10 space-y-3">
          <div class="w-10 h-10 rounded-xl bg-purple-500/15 text-purple-400 flex items-center justify-center">
            <i data-lucide="calculator" class="w-5 h-5"></i>
          </div>
          <h3 class="font-bold text-white text-sm">Cálculos Exatos e Livres de Erros</h3>
          <p class="text-xs text-slate-400 leading-relaxed">
            Conferência matemática direta das vendas, notas fiscais e fechamento de caixa centavo a centavo. A inteligência nunca chuta nem inventa valores: calcula apenas números reais do seu sistema.
          </p>
        </div>

        <div class="glass-panel p-5 rounded-2xl border border-white/10 space-y-3">
          <div class="w-10 h-10 rounded-xl bg-amber-500/15 text-amber-400 flex items-center justify-center">
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
         PAINEL & MATRIZ DE DIFERENCIAÇÃO OPERACIONAL REFORÇADO (ROI REAL)
         ========================================================================= -->
    <section id="sec-diferenciacao" class="glass-panel p-6 sm:p-8 rounded-3xl border border-white/10 space-y-8 scroll-reveal">
      
      <!-- Cabeçalho do Painel Operacional -->
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 text-[10px] font-mono uppercase tracking-wider mb-2">
            O Valor Real do Produto está na Linha de Frente da Operação
          </div>
          <h3 class="text-xl sm:text-2xl font-bold text-white font-display-title">Matriz de Diferenciação Operacional & ROI</h3>
          <p class="text-xs text-slate-400 font-sans max-w-2xl mt-1">
            Enquanto ERPs convencionais apenas registram prejuízos passados e painéis comuns só desenham gráficos sem ação, a AURA atua no dia a dia da operação. Ela estanca quebras de caixa, identifica desvios de estoque e agiliza decisões em tempo real, conectada diretamente ao banco de dados da sua empresa e sem cobranças abusivas por milhões de tokens.
          </p>
        </div>
        <div class="text-right flex-shrink-0">
          <span class="px-3.5 py-1.5 rounded-xl text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 inline-flex items-center gap-1.5">
            <i data-lucide="trending-up" class="w-3.5 h-3.5"></i>
            <span>ROI Operacional Comprovado</span>
          </span>
        </div>
      </div>

      <!-- 4 Cards de Destaque do Valor Operacional -->
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5 font-sans">
        
        <div class="roi-card p-4 rounded-2xl bg-slate-900/90 border border-emerald-500/30 space-y-2">
          <div class="flex items-center justify-between">
            <span class="text-[10px] font-mono text-emerald-400 uppercase">Prevenção Financeira</span>
            <i data-lucide="scale" class="w-4 h-4 text-emerald-400"></i>
          </div>
          <div class="text-base font-extrabold text-white">Detecção de Quebras de Caixa</div>
          <p class="text-xs text-slate-400 leading-relaxed">
            Identificação de discrepâncias centavo a centavo turno a turno. Estanca sangrias e desvios no mesmo dia, sem surpresas no fim do mês.
          </p>
          <div class="text-[10px] text-emerald-300 font-semibold pt-1">✓ Prejuízo evitado: R$ 3.800 a R$ 12.000 / mês</div>
        </div>

        <div class="roi-card p-4 rounded-2xl bg-slate-900/90 border border-cyan-500/30 space-y-2">
          <div class="flex items-center justify-between">
            <span class="text-[10px] font-mono text-cyan-400 uppercase">Controle Físico Real</span>
            <i data-lucide="boxes" class="w-4 h-4 text-cyan-400"></i>
          </div>
          <div class="text-base font-extrabold text-white">Auditoria de Desvios de Estoque</div>
          <p class="text-xs text-slate-400 leading-relaxed">
            Cruzamento contínuo entre saídas fiscais registradas e estoque físico real em tanques, balcões e gôndolas. Fim da "perda aceita".
          </p>
          <div class="text-[10px] text-cyan-300 font-semibold pt-1">✓ Fim do sumiço oculto de mercadorias</div>
        </div>

        <div class="roi-card p-4 rounded-2xl bg-slate-900/90 border border-purple-500/30 space-y-2">
          <div class="flex items-center justify-between">
            <span class="text-[10px] font-mono text-purple-400 uppercase">Eficiência & Soberania</span>
            <i data-lucide="database" class="w-4 h-4 text-purple-400"></i>
          </div>
          <div class="text-base font-extrabold text-white">Economia Brutal de Tokens</div>
          <p class="text-xs text-slate-400 leading-relaxed">
            Conecta diretamente ao banco da empresa: cálculos estruturados na máquina local e inteligência acionada apenas para conclusões complexas, sem surpresas na fatura.
          </p>
          <div class="text-[10px] text-purple-300 font-semibold pt-1">✓ Redução de 90% a 95% em consumo de tokens</div>
        </div>

        <div class="roi-card p-4 rounded-2xl bg-slate-900/90 border border-amber-500/30 space-y-2">
          <div class="flex items-center justify-between">
            <span class="text-[10px] font-mono text-amber-400 uppercase">Produtividade Gerencial</span>
            <i data-lucide="clock" class="w-4 h-4 text-amber-400"></i>
          </div>
          <div class="text-base font-extrabold text-white">De Horas para 10 Segundos</div>
          <p class="text-xs text-slate-400 leading-relaxed">
            Elimina o preenchimento manual de planilhas e conferência de filipetas. Entrega DecisionCards prontos com ação em 1-toque e Run-Out preditivo.
          </p>
          <div class="text-[10px] text-amber-300 font-semibold pt-1">✓ Mais de 60 horas/mês economizadas por gestor</div>
        </div>

      </div>

      <!-- Bloco de Contraste Estratégico: Mercado Tradicional de IA vs Abordagem AURA -->
      <div class="p-5 sm:p-6 rounded-2xl bg-gradient-to-r from-rose-950/20 via-slate-900/90 to-emerald-950/25 border border-white/10 space-y-4">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-white/10 pb-4">
          <div>
            <div class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-cyan-500/10 text-cyan-300 border border-cyan-500/20 text-[10px] font-mono uppercase tracking-wider mb-1">
              Soberania dos Dados & Arquitetura Inteligente
            </div>
            <h4 class="text-base sm:text-lg font-bold text-white font-display-title">
              O Mercado Tradicional de IA vs A Abordagem Direta no Banco da AURA
            </h4>
          </div>
          <span class="px-3 py-1 rounded-full text-xs font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 inline-flex items-center gap-1.5 w-fit">
            <i data-lucide="sparkles" class="w-3.5 h-3.5"></i>
            Até 95% de Economia em Tokens
          </span>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4 font-sans text-xs">
          <!-- Coluna 1: O Mercado Tradicional de IA -->
          <div class="p-4 rounded-xl bg-rose-950/20 border border-rose-500/30 space-y-2.5">
            <div class="flex items-center justify-between">
              <span class="text-xs font-bold text-rose-300 flex items-center gap-1.5">
                <i data-lucide="alert-triangle" class="w-4 h-4 text-rose-400"></i>
                Como o Mercado Tradicional de IA Opera
              </span>
              <span class="px-2 py-0.5 rounded text-[9px] font-mono bg-rose-500/20 text-rose-300">Ineficiente & Caro</span>
            </div>
            <p class="text-slate-300 leading-relaxed">
              Envia <span class="text-rose-200 font-semibold">dados brutos e desorganizados</span> para servidores externos em nuvem, sem validação prévia e sem organização dos dados. Espera que a inteligência calcule tudo no escuro, consumindo recursos de forma descontrolada e <strong class="text-white">cobrando faturas caras por milhões de tokens para processar informações que já pertencem à sua própria empresa</strong>.
            </p>
            <div class="text-[11px] text-rose-300 font-mono pt-1">
              ✕ O cliente paga caro para processar a sua própria informação.
            </div>
          </div>

          <!-- Coluna 2: A Abordagem AURA -->
          <div class="p-4 rounded-xl bg-emerald-950/25 border border-emerald-500/35 space-y-2.5">
            <div class="flex items-center justify-between">
              <span class="text-xs font-bold text-emerald-300 flex items-center gap-1.5">
                <i data-lucide="shield-check" class="w-4 h-4 text-emerald-400"></i>
                A Abordagem Inteligente da AURA
              </span>
              <span class="px-2 py-0.5 rounded text-[9px] font-mono bg-emerald-500/20 text-emerald-300">Conexão Local Direta</span>
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
              <td class="py-3.5 px-4 bg-emerald-950/20 border-l border-r border-emerald-500/30">
                <span class="inline-flex items-center gap-1 text-[11px] font-bold text-emerald-400 mb-1">✓ Ação em Tempo Real</span>
                <div class="font-medium text-emerald-200">Instantâneo em sub-100ms com reconciliação centavo a centavo; estanca quebras no próprio turno.</div>
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
              <td class="py-3.5 px-4 bg-emerald-950/20 border-l border-r border-emerald-500/30">
                <span class="inline-flex items-center gap-1 text-[11px] font-bold text-emerald-400 mb-1">✓ Conciliação Contínua</span>
                <div class="font-medium text-emerald-200">Cruzamento contínuo entre saídas fiscais e estoque físico real em tempo real; alerta imediato de desvio.</div>
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
              <td class="py-3.5 px-4 bg-emerald-950/20 border-l border-r border-emerald-500/30">
                <span class="inline-flex items-center gap-1 text-[11px] font-bold text-emerald-400 mb-1">✓ Conexão Direta ao Banco Local</span>
                <div class="font-medium text-emerald-200">Conecta direto na infraestrutura do banco do cliente. As contas rodam na máquina local e a inteligência só é acionada para cálculos estruturados e síntese executiva, gerando até 95% de economia em tokens com respostas em milissegundos.</div>
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
              <td class="py-3.5 px-4 bg-emerald-950/20 border-l border-r border-emerald-500/30">
                <span class="inline-flex items-center gap-1 text-[11px] font-bold text-purple-400 mb-1">✓ Resolução em 1 Clique</span>
                <div class="font-medium text-purple-200">Cartões executivos DecisionCards™ autoexplicativos que permitem resolver pendências com apenas 1 clique em menos de 10 segundos.</div>
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
        
        <div class="glass-panel p-5 rounded-2xl border border-white/10 space-y-2">
          <h4 class="font-bold text-slate-100 flex items-center gap-2">
            <i data-lucide="help-circle" class="w-4 h-4 text-cyan-400"></i>
            A AURA substitui o sistema ERP atual da minha empresa?
          </h4>
          <p class="text-slate-400 leading-relaxed">
            Não. A AURA atua como uma supervisora de inteligência e auditoria contínua que se conecta ao seu ERP e automação existente, acelerando a tomada de decisões no dia a dia em postos, lojas, bares ou padarias.
          </p>
        </div>

        <div class="glass-panel p-5 rounded-2xl border border-white/10 space-y-2">
          <h4 class="font-bold text-slate-100 flex items-center gap-2">
            <i data-lucide="lock" class="w-4 h-4 text-emerald-400"></i>
            Meus dados de faturamento e clientes saem da minha empresa?
          </h4>
          <p class="text-slate-400 leading-relaxed">
            Absolutamente não. Em total conformidade com a LGPD (Lei 13.709/2018), qualquer dado de identificação pessoal (como CPF ou nomes) é removido automaticamente antes da análise. Todo o processamento funciona dentro da sua própria estrutura e nada de confidencial é enviado para servidores externos.
          </p>
        </div>

        <div class="glass-panel p-5 rounded-2xl border border-white/10 space-y-2">
          <h4 class="font-bold text-slate-100 flex items-center gap-2">
            <i data-lucide="coins" class="w-4 h-4 text-emerald-400"></i>
            Por que a AURA economiza até 95% em tokens comparada a outras soluções?
          </h4>
          <p class="text-slate-400 leading-relaxed">
            Muitas ferramentas hoje enviam dados brutos e desorganizados para servidores em nuvem, sem validação prévia nem filtros de segurança, cobrando dos clientes faturas caras por milhões de tokens para ler dados que já são deles. A AURA trabalha conectada diretamente à infraestrutura do banco do cliente, realizando todas as contas no próprio ambiente local. A inteligência só é acionada para análises estruturadas e conclusões executivas, garantindo economia de até 95% em consumo de tokens, máxima assertividade, respostas em milissegundos e custo previsível.
          </p>
        </div>

        <div class="glass-panel p-5 rounded-2xl border border-white/10 space-y-2">
          <h4 class="font-bold text-slate-100 flex items-center gap-2">
            <i data-lucide="clock" class="w-4 h-4 text-purple-400"></i>
            Qual é a curva de aprendizado da equipe operacional?
          </h4>
          <p class="text-slate-400 leading-relaxed">
            Zero minutos. A AURA compreende linguagem falada ou escrita natural em português do Brasil e entrega DecisionCards autoexplicativos que qualquer gerente, caixa ou encarregado opera intuitivamente em 1 clique.
          </p>
        </div>

        <div class="glass-panel p-5 rounded-2xl border border-white/10 space-y-2 md:col-span-2">
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
    <div class="glass-panel p-8 rounded-3xl border border-cyan-500/25 text-center space-y-5 bg-gradient-to-r from-cyan-950/30 via-slateSurface to-purple-950/30 shadow-xl scroll-reveal">
      <div class="inline-flex items-center justify-center p-3 rounded-2xl bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">
        <div class="neural-core-orb !w-10 !h-10"></div>
      </div>
      <h2 class="text-2xl sm:text-4xl font-extrabold text-white font-display-title">
        Pronto para Elevar o Padrão Operacional do seu Negócio?
      </h2>
      <p class="text-xs sm:text-sm text-slate-300 font-sans max-w-xl mx-auto">
        Acesse agora o console completo da AURA para conversar com a assistente, consultar o panorama operacional em tempo real ou disparar diagnósticos executivos em 1 clique.
      </p>
      <div class="flex flex-col sm:flex-row items-center justify-center gap-3 pt-2 font-sans">
        <a href="/" class="btn-aura-glow-soft w-full sm:w-auto px-6 py-3 rounded-xl bg-gradient-to-r from-emerald-500 via-cyan-500 to-purple-500 hover:brightness-105 text-slate-950 font-bold text-sm shadow-md active:scale-95 transition-all flex items-center justify-center gap-2 border border-white/15">
          <span>Acessar Console AURA</span>
          <i data-lucide="arrow-right" class="w-4 h-4"></i>
        </a>
        <button onclick="window.auraTour.restartTour()" class="w-full sm:w-auto px-5 py-3 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-300 hover:text-white border border-white/10 text-sm font-semibold transition-colors flex items-center justify-center gap-2 shadow-sm">
          <i data-lucide="rotate-ccw" class="w-4 h-4"></i>
          <span>Rever Animação da AURA ↺</span>
        </button>
      </div>
    </div>

  </main>

  <!-- =========================================================================
       RODAPÉ DO SHOWCASE
       ========================================================================= -->
  <footer class="border-t border-white/10 py-6 px-4 text-center text-xs text-slate-400 font-sans bg-obsidian/80">
    <div class="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
      <div class="flex items-center gap-2">
        <span class="font-display-title font-bold text-slate-200">AURA</span>
        <span>• Autonomous Unified Retail Assistant</span>
      </div>
      <div>
        <span>Design System Obsidian & Liquid Glass Deluxe • LGPD Compliant • Todos os direitos reservados</span>
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
        // Mantém os dados confidenciais (CNPJ, CPF, Transação Fiscal, Saldo, Credenciais)
        // nitidamente visíveis em destaque para que o usuário leia antes de serem pulverizados!
        if (statusPill) {
          statusPill.textContent = 'DADOS PESSOAIS IDENTIFICADOS';
          statusPill.className = 'px-2 py-0.5 rounded text-[10px] font-mono bg-rose-500/20 text-rose-300 border border-rose-500/40 animate-pulse';
        }
        if (thinkingText) {
          thinkingText.textContent = 'Escudo AURA Guard™: dados confidenciais detectados no fluxo. Lendo e isolando...';
        }
        if (piiList) {
          piiList.classList.add('border-rose-500/40', 'shadow-[0_0_15px_rgba(244,63,94,0.15)]');
        }

        if (playSfx) playTone(480, 'sine', 0.12, 0.03);

        // 2. FASE DE PULVERIZAÇÃO EM POEIRA (APÓS TEMPO DE LEITURA CONFORTÁVEL)
        const tStartDust = setTimeout(() => {
          if (statusPill) {
            statusPill.textContent = 'DESINTEGRANDO EM POEIRA (LGPD)...';
            statusPill.className = 'px-2 py-0.5 rounded text-[10px] font-mono bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 animate-pulse';
          }
          if (thinkingText) {
            thinkingText.textContent = 'Desintegrando dados confidenciais em poeira (100% LGPD)...';
          }
          if (piiList) {
            piiList.classList.remove('border-rose-500/40', 'shadow-[0_0_15px_rgba(244,63,94,0.15)]');
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

            // Pausa de apreciação do resultado sanitizado antes de continuar o fluxo
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
          piiList.classList.remove('border-rose-500/40', 'shadow-[0_0_15px_rgba(244,63,94,0.15)]');
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
          // Pergunta enviada!
          playTone(600, 'sine', 0.05, 0.04);

          // 2. Aciona o Indicador de Análise no chat e ativa o Nó 1 no Backend (Detecção de Intenção Semântica)
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

            // Dispara a desintegração com tempo confortável de leitura prévia dos dados pessoais (2.4s)!
            triggerDustDisintegration(true, 2400, () => {
              // 5. Nó 4: Motor Analítico Sub-100ms & Auditoria de Precisão (inicia APÓS pulverização completa)
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

                  // Exibe a linha de resposta da AURA e inicia STREAMING em tempo real!
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

        const sections = ['top', 'sec-chat-graph', 'sec-blindagem', 'sec-diferenciacao', 'sec-faq'];
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

        // Seção entra confortavelmente na área de leitura do usuário
        const inComfortableView = (rect.top <= vh * 0.72) && (rect.bottom >= vh * 0.20);

        if (inComfortableView) {
          if (!hasStartedForCurrentView && !tourState.isSimulating) {
            hasStartedForCurrentView = true;
            tourState.hasAutoStarted = true;
            runAutonomousShowcase();
          }
        } else {
          // Se o usuário rolou completamente para fora (acima ou abaixo), reseta para permitir replay na volta
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

                // Animação de realce nos cards de ROI ao rolar até eles
                if (entry.target.id === 'sec-diferenciacao') {
                  const cards = entry.target.querySelectorAll('.roi-card');
                  cards.forEach((c, i) => {
                    setTimeout(() => {
                      c.classList.add('ring-1', 'ring-emerald-400/60');
                      setTimeout(() => c.classList.remove('ring-1', 'ring-emerald-400/60'), 700);
                    }, i * 120);
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
        scrollToSection
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
