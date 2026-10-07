"""
Gerador da Página de Apresentação e Showcase Executivo AURA (web/showcase.html)
Atualizado com:
1. Scrollytelling e animações dinâmicas no scroll (barra de progresso, rail lateral, reveal suave).
2. Generalização dos termos de negócio (multissetorial: postos, padarias, bares, lojas, franquias).
   - "CNPJ" (em vez de "CNPJ da revenda")
   - "CPF" (em vez de "CPF do frentista")
   - "IDENTIFICADOR FISCAL DE TRANSAÇÃO" (em vez de "CARTÃO FATURADO")
   - "CREDENCIAIS" (em vez de "CREDENCIAL DA PISTA")
3. Mini Janela de Chat da AURA + Fluxograma / Grafo Moderno Lado a Lado:
   - Cenários multissetoriais rápidos
   - Fluxograma de 5 nós conectados (Prompt -> LGPD -> Motor -> Regras -> DecisionCard)
   - Destaque explícito para a LGPD (Lei 13.709/2018)
4. Suavização de efeitos de glow nos botões (estética Obsidian & Liquid Glass de luxo).
5. Painel e Matriz de Diferenciação Operacional reforçados (onde está o verdadeiro valor do produto).
"""

from pathlib import Path

def generate_showcase_html():
    html = """<!DOCTYPE html>
<html lang="pt-BR" class="scroll-smooth">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
  <meta name="theme-color" content="#07090e">
  <title>AURA // Apresentação & Tour Executivo (Showcase Multissetorial)</title>
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
      border: 1px solid rgba(6, 182, 212, 0.22);
      box-shadow: 0 12px 36px 0 rgba(0, 0, 0, 0.45), 0 0 14px 0 rgba(6, 182, 212, 0.08);
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
    }

    .glass-card-glow-emerald {
      background: rgba(12, 18, 30, 0.88);
      border: 1px solid rgba(16, 185, 129, 0.22);
      box-shadow: 0 12px 36px 0 rgba(0, 0, 0, 0.45), 0 0 14px 0 rgba(16, 185, 129, 0.08);
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
    }

    .glass-card-glow-purple {
      background: rgba(12, 18, 30, 0.88);
      border: 1px solid rgba(124, 58, 237, 0.22);
      box-shadow: 0 12px 36px 0 rgba(0, 0, 0, 0.45), 0 0 14px 0 rgba(124, 58, 237, 0.08);
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
    }

    /* Pipeline & Graph Node Pulse Animation */
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

    /* Step Transition Smooth Fade */
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

    /* Text Redaction & Disintegration States */
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

    /* Dust Canvas Container */
    #dust-particle-canvas {
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      pointer-events: none;
      z-index: 30;
    }

    /* Custom Stepper Progress Pill */
    .step-pill {
      transition: all 0.3s ease;
    }
    .step-pill.active {
      border-color: #06b6d4;
      background: rgba(6, 182, 212, 0.12);
      color: #ffffff;
      box-shadow: 0 0 12px rgba(6, 182, 212, 0.25);
    }
    .step-pill.completed {
      border-color: #10b981;
      background: rgba(16, 185, 129, 0.08);
      color: #34d399;
    }

    /* Pipeline Node Glowing States */
    .pipeline-node {
      transition: all 0.3s ease;
    }
    .pipeline-node.pulse-highlight {
      border-color: #34d399 !important;
      box-shadow: 0 0 16px rgba(16, 185, 129, 0.35);
      transform: scale(1.015);
    }

    /* Graph Nodes (Seção de Chat & Fluxograma Core) */
    .graph-node {
      transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
      cursor: pointer;
    }
    .graph-node.active-glow {
      border-color: #22d3ee !important;
      box-shadow: 0 0 16px rgba(6, 182, 212, 0.32), inset 0 0 10px rgba(6, 182, 212, 0.08);
      transform: scale(1.015);
    }
    .graph-node.success-glow {
      border-color: #34d399 !important;
      box-shadow: 0 0 16px rgba(16, 185, 129, 0.32), inset 0 0 10px rgba(16, 185, 129, 0.08);
      transform: scale(1.015);
    }

    /* Cylindrical Tank Liquid Animation */
    @keyframes liquid-shimmer {
      0% { transform: translateY(0); }
      50% { transform: translateY(-3px); }
      100% { transform: translateY(0); }
    }
    .liquid-wave {
      animation: liquid-shimmer 3s ease-in-out infinite;
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
    .graph-node.active-selected {
      border-color: #22d3ee !important;
      background: rgba(15, 23, 42, 0.95) !important;
      box-shadow: 0 0 16px rgba(6, 182, 212, 0.35);
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
    <button onclick="window.auraTour.scrollToSection('sec-tour')" class="scroll-nav-dot" title="02. Tour Interativo (4 Etapas)" data-section="sec-tour"></button>
    <button onclick="window.auraTour.scrollToSection('sec-chat-graph')" class="scroll-nav-dot" title="03. Chat Executivo & Grafo Core LGPD" data-section="sec-chat-graph"></button>
    <button onclick="window.auraTour.scrollToSection('sec-blindagem')" class="scroll-nav-dot" title="04. Blindagem Fiduciária & LGPD" data-section="sec-blindagem"></button>
    <button onclick="window.auraTour.scrollToSection('sec-diferenciacao')" class="scroll-nav-dot" title="05. Diferenciação Operacional & ROI" data-section="sec-diferenciacao"></button>
    <button onclick="window.auraTour.scrollToSection('sec-faq')" class="scroll-nav-dot" title="06. FAQ Executivo" data-section="sec-faq"></button>
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

      <!-- Links de Atalho das Etapas e Seções -->
      <nav class="hidden md:flex items-center gap-1 text-xs font-sans">
        <button onclick="window.auraTour.goToStep(1); window.auraTour.scrollToSection('sec-tour');" class="px-2.5 py-1.5 rounded-lg text-slate-300 hover:text-white hover:bg-white/5 transition-colors">
          1. A Pergunta
        </button>
        <button onclick="window.auraTour.goToStep(2); window.auraTour.scrollToSection('sec-tour');" class="px-2.5 py-1.5 rounded-lg text-slate-300 hover:text-white hover:bg-white/5 transition-colors">
          2. Escudo AURA Guard™
        </button>
        <button onclick="window.auraTour.goToStep(3); window.auraTour.scrollToSection('sec-tour');" class="px-2.5 py-1.5 rounded-lg text-slate-300 hover:text-white hover:bg-white/5 transition-colors">
          3. Motor Sub-100ms
        </button>
        <button onclick="window.auraTour.goToStep(4); window.auraTour.scrollToSection('sec-tour');" class="px-2.5 py-1.5 rounded-lg text-slate-300 hover:text-white hover:bg-white/5 transition-colors">
          4. DecisionCard™
        </button>
        <button onclick="window.auraTour.scrollToSection('sec-chat-graph')" class="px-2.5 py-1.5 rounded-lg text-cyan-300 hover:text-white hover:bg-cyan-500/10 transition-colors font-medium">
          Chat & Grafo Core
        </button>
        <button onclick="window.auraTour.scrollToSection('sec-diferenciacao')" class="px-2.5 py-1.5 rounded-lg text-emerald-300 hover:text-white hover:bg-emerald-500/10 transition-colors font-medium">
          Diferenciação
        </button>
      </nav>

      <!-- Botões de Ação Direta -->
      <div class="flex items-center gap-2.5">
        <button id="btn-toggle-sfx-showcase" class="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-slate-900/80 hover:bg-slate-800 text-slate-300 hover:text-white border border-white/10 text-xs transition-colors shadow-sm" title="Alternar Efeitos Sonoros do Tour">
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
       HERO & APRESENTAÇÃO GUIADA INTERATIVA
       ========================================================================= -->
  <main class="flex-1 max-w-7xl w-full mx-auto px-4 py-8 sm:py-12 space-y-16">
    
    <!-- Hero Header Multissetorial -->
    <div class="text-center max-w-3xl mx-auto space-y-4 scroll-reveal scroll-reveal-visible">
      <div class="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-cyan-500/10 border border-cyan-500/25 text-xs font-sans text-cyan-300">
        <span class="w-2 h-2 rounded-full bg-cyan-400 animate-ping"></span>
        <span class="font-semibold tracking-wider uppercase text-[10px]">Arquitetura Universal: Postos • Padarias • Bares • Lojas • Franquias</span>
      </div>
      <h1 class="text-3xl sm:text-5xl font-extrabold tracking-tight text-white leading-tight font-display-title">
        O Cérebro Operacional de Qualquer Comércio ou Ponto de Venda. <br>
        <span class="bg-gradient-to-r from-cyan-400 via-emerald-300 to-purple-400 bg-clip-text text-transparent">
          Com Blindagem Fiduciária Total & LGPD Nativa.
        </span>
      </h1>
      <p class="text-sm sm:text-base text-slate-300 leading-relaxed font-sans max-w-2xl mx-auto">
        Acompanhe abaixo o fluxo em tempo real: veja como perguntas executivas são respondidas com telemetria direta de estoques e caixa, enquanto dados sensíveis fiscais e de colaboradores são desintegrados na borda com conformidade integral à LGPD (Lei 13.709/2018).
      </p>
    </div>

    <!-- Barra de Controle do Tour Guiado (Play / Pause / Steps / Timer) -->
    <section id="sec-tour" class="glass-panel p-4 rounded-2xl border border-white/10 shadow-xl backdrop-blur-xl bg-slateSurface/80 space-y-3 scroll-reveal">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        
        <!-- Player Controls -->
        <div class="flex items-center gap-2.5">
          <button id="btn-tour-play-pause" class="btn-aura-glow-soft flex items-center gap-2 px-4 py-2.5 rounded-xl bg-gradient-to-r from-emerald-500 to-cyan-500 hover:brightness-105 text-slate-950 font-bold text-xs font-sans transition-all active:scale-95 border border-white/10">
            <i data-lucide="play" id="icon-play-pause" class="w-4 h-4 fill-current"></i>
            <span id="label-play-pause">Reproduzir Tour Automático</span>
          </button>

          <button id="btn-tour-prev" class="p-2.5 rounded-xl bg-slate-900/90 hover:bg-slate-800 text-slate-300 hover:text-white border border-white/10 transition-colors" title="Etapa Anterior (←)">
            <i data-lucide="chevron-left" class="w-4 h-4"></i>
          </button>

          <button id="btn-tour-next" class="p-2.5 rounded-xl bg-slate-900/90 hover:bg-slate-800 text-slate-300 hover:text-white border border-white/10 transition-colors" title="Próxima Etapa (→)">
            <i data-lucide="chevron-right" class="w-4 h-4"></i>
          </button>

          <button id="btn-tour-replay" class="p-2.5 rounded-xl bg-slate-900/90 hover:bg-slate-800 text-slate-400 hover:text-white border border-white/10 transition-colors" title="Reiniciar do Início">
            <i data-lucide="rotate-ccw" class="w-4 h-4"></i>
          </button>
        </div>

        <!-- Indicador de Status & Velocidade -->
        <div class="flex items-center gap-3">
          <div class="flex items-center gap-2 text-xs font-sans text-slate-400">
            <span class="w-2 h-2 rounded-full bg-cyan-400 animate-pulse"></span>
            <span id="tour-status-text" class="text-slate-300 font-medium">Modo Interativo</span>
          </div>

          <div class="flex items-center rounded-lg bg-slate-900 p-0.5 border border-white/10 text-xs font-sans">
            <button id="btn-speed-1x" class="px-2.5 py-1 rounded-md bg-slate-800 text-white font-semibold">1x</button>
            <button id="btn-speed-2x" class="px-2.5 py-1 rounded-md text-slate-400 hover:text-white">2x</button>
          </div>
        </div>

      </div>

      <!-- Barra de Progresso Suave da Etapa Atual -->
      <div class="w-full bg-slate-950/80 rounded-full h-1.5 overflow-hidden border border-white/5">
        <div id="tour-progress-bar" class="bg-gradient-to-r from-cyan-400 via-emerald-400 to-purple-400 h-full w-0 transition-all duration-100 ease-linear"></div>
      </div>

      <!-- 4 Pílulas Seletoras de Etapa (Tabs / Stepper) -->
      <div class="grid grid-cols-2 lg:grid-cols-4 gap-2 pt-1 font-sans">
        <button onclick="window.auraTour.goToStep(1)" class="step-pill active flex items-center gap-2.5 p-2.5 rounded-xl border border-white/10 text-left text-xs" data-step-target="1">
          <span class="w-6 h-6 rounded-lg bg-white/10 font-bold flex items-center justify-center text-[11px] flex-shrink-0">1</span>
          <div class="min-w-0">
            <div class="font-semibold text-white truncate">A Pergunta</div>
            <div class="text-[10px] text-slate-400 truncate">Demanda Executiva</div>
          </div>
        </button>

        <button onclick="window.auraTour.goToStep(2)" class="step-pill flex items-center gap-2.5 p-2.5 rounded-xl border border-white/10 text-left text-xs" data-step-target="2">
          <span class="w-6 h-6 rounded-lg bg-white/10 font-bold flex items-center justify-center text-[11px] flex-shrink-0">2</span>
          <div class="min-w-0">
            <div class="font-semibold text-white truncate">Escudo AURA Guard™</div>
            <div class="text-[10px] text-slate-400 truncate">Desintegração de PII (LGPD)</div>
          </div>
        </button>

        <button onclick="window.auraTour.goToStep(3)" class="step-pill flex items-center gap-2.5 p-2.5 rounded-xl border border-white/10 text-left text-xs" data-step-target="3">
          <span class="w-6 h-6 rounded-lg bg-white/10 font-bold flex items-center justify-center text-[11px] flex-shrink-0">3</span>
          <div class="min-w-0">
            <div class="font-semibold text-white truncate">Motor Sub-100ms</div>
            <div class="text-[10px] text-slate-400 truncate">Telemetria & Fisco</div>
          </div>
        </button>

        <button onclick="window.auraTour.goToStep(4)" class="step-pill flex items-center gap-2.5 p-2.5 rounded-xl border border-white/10 text-left text-xs" data-step-target="4">
          <span class="w-6 h-6 rounded-lg bg-white/10 font-bold flex items-center justify-center text-[11px] flex-shrink-0">4</span>
          <div class="min-w-0">
            <div class="font-semibold text-white truncate">DecisionCard™</div>
            <div class="text-[10px] text-slate-400 truncate">Ação em 1-Toque</div>
          </div>
        </button>
      </div>
    </section>

    <!-- =======================================================================
         STAGE PRINCIPAL: WORKSPACE DINÂMICO DE 2 COLUNAS
         ======================================================================= -->
    <div class="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch scroll-reveal">
      
      <!-- COLUNA DA ESQUERDA: NARRATIVA EXECUTIVA & CONTROLES ESPECÍFICOS (5 Cols) -->
      <div class="lg:col-span-5 flex flex-col justify-between glass-panel p-6 rounded-2xl border border-white/10 shadow-xl backdrop-blur-xl bg-slateSurface/90 relative overflow-hidden">
        
        <!-- Conteúdo Dinâmico da Narrativa por Etapa -->
        <div id="step-narrative-container" class="space-y-5">
          
          <!-- ETAPA 1: Narrativa -->
          <div id="narrative-step-1" class="step-content-pane active-pane space-y-4">
            <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-purple-500/15 border border-purple-500/30 text-purple-300 text-xs font-semibold">
              <i data-lucide="help-circle" class="w-3.5 h-3.5"></i>
              <span>Etapa 01 de 04 • Demanda de Negócio</span>
            </div>
            <h2 class="text-2xl font-bold text-white font-display-title">
              A Pergunta Executiva: O Ponto de Partida da Decisão
            </h2>
            <p class="text-sm text-slate-300 leading-relaxed font-sans">
              O gestor ou supervisor — seja de um posto de combustível, padaria, bar, loja de varejo ou franquia — precisa saber instantaneamente se haverá falta de estoque ou se ocorreu quebra de caixa no fechamento de turno, sem precisar abrir planilhas complexas.
            </p>
            <div class="p-3.5 rounded-xl bg-white/[0.03] border border-white/5 space-y-2 text-xs font-sans">
              <div class="flex items-center gap-2 text-emerald-400 font-semibold">
                <i data-lucide="check" class="w-4 h-4"></i>
                <span>Compreensão Direta em Linguagem Natural</span>
              </div>
              <div class="flex items-center gap-2 text-emerald-400 font-semibold">
                <i data-lucide="check" class="w-4 h-4"></i>
                <span>Contextualização Automática da Filial & Turno</span>
              </div>
              <div class="flex items-center gap-2 text-emerald-400 font-semibold">
                <i data-lucide="check" class="w-4 h-4"></i>
                <span>Zero Fórmulas ou SQL Exigidos do Usuário</span>
              </div>
            </div>
            <div class="pt-2">
              <button onclick="window.auraTour.simulateStep1Question()" class="w-full py-2.5 px-4 rounded-xl bg-slate-800 hover:bg-slate-700 text-cyan-300 hover:text-white border border-cyan-500/30 text-xs font-semibold transition-all flex items-center justify-center gap-2 shadow-sm">
                <i data-lucide="sparkles" class="w-3.5 h-3.5"></i>
                <span>Alternar Pergunta de Exemplo Multissetorial</span>
              </button>
            </div>
          </div>

          <!-- ETAPA 2: Narrativa -->
          <div id="narrative-step-2" class="step-content-pane hidden-pane space-y-4">
            <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-500/15 border border-cyan-500/30 text-cyan-300 text-xs font-semibold">
              <i data-lucide="shield-alert" class="w-3.5 h-3.5"></i>
              <span>Etapa 02 de 04 • Blindagem Fiduciária & LGPD</span>
            </div>
            <h2 class="text-2xl font-bold text-white font-display-title">
              Escudo AURA Guard™: Desintegração Instantânea de PII
            </h2>
            <p class="text-sm text-slate-300 leading-relaxed font-sans">
              Antes de qualquer raciocínio ou orquestração, todos os dados confidenciais (CNPJ, CPF de colaboradores e clientes, chaves de transação fiscal, saldos e credenciais) são identificados em tempo real na borda e <strong>desintegrados em partículas</strong>, sendo substituídos por tokens neutros homologados, em conformidade integral com a LGPD (Lei 13.709/2018).
            </p>
            <div class="p-3.5 rounded-xl bg-white/[0.03] border border-white/5 space-y-2 text-xs font-sans">
              <div class="flex items-center gap-2 text-cyan-400 font-semibold">
                <i data-lucide="shield-check" class="w-4 h-4"></i>
                <span>100% LGPD Fiduciária & Privacy by Design</span>
              </div>
              <div class="flex items-center gap-2 text-cyan-400 font-semibold">
                <i data-lucide="shield-check" class="w-4 h-4"></i>
                <span>Zero Vazamento de Dados Pessoais para a Nuvem</span>
              </div>
              <div class="flex items-center gap-2 text-cyan-400 font-semibold">
                <i data-lucide="shield-check" class="w-4 h-4"></i>
                <span>Preservação Estrita do Significado Contábil</span>
              </div>
            </div>
            <div class="pt-2">
              <button onclick="window.auraTour.triggerDustDisintegration(true)" class="btn-aura-glow-soft w-full py-2.5 px-4 rounded-xl bg-gradient-to-r from-cyan-500 to-emerald-500 hover:brightness-105 text-slate-950 font-bold text-xs transition-all flex items-center justify-center gap-2 active:scale-95 border border-white/10">
                <i data-lucide="zap" class="w-4 h-4 fill-current"></i>
                <span>Disparar Efeito de Desintegração em Poeira</span>
              </button>
            </div>
          </div>

          <!-- ETAPA 3: Narrativa -->
          <div id="narrative-step-3" class="step-content-pane hidden-pane space-y-4">
            <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 text-xs font-semibold">
              <i data-lucide="cpu" class="w-3.5 h-3.5"></i>
              <span>Etapa 03 de 04 • Motor Analítico</span>
            </div>
            <h2 class="text-2xl font-bold text-white font-display-title">
              Motor Sub-100ms: Operação Multissetorial & Fisco
            </h2>
            <p class="text-sm text-slate-300 leading-relaxed font-sans">
              Com o payload 100% higienizado, o motor neural de borda cruza em paralelo a telemetria física de sensores e sondas, encerrantes de PDV, conciliação fiduciária contábil, previsão de run-out e regras da Portaria 26 da ANP (tolerância de ±0.60%) e NFC-e/SAT em postos, lojas, bares e padarias.
            </p>
            <div class="p-3.5 rounded-xl bg-white/[0.03] border border-white/5 space-y-2 text-xs font-sans">
              <div class="flex items-center gap-2 text-emerald-400 font-semibold">
                <i data-lucide="gauge" class="w-4 h-4"></i>
                <span>Latência Total de Execução: 35ms a 42ms</span>
              </div>
              <div class="flex items-center gap-2 text-emerald-400 font-semibold">
                <i data-lucide="check-circle-2" class="w-4 h-4"></i>
                <span>Zero Alucinação: Verificação Matemática Estrita</span>
              </div>
              <div class="flex items-center gap-2 text-emerald-400 font-semibold">
                <i data-lucide="database" class="w-4 h-4"></i>
                <span>Conexão Nativa com Telemetria de Pista, PDVs & Sensores</span>
              </div>
            </div>
            <div class="pt-2">
              <button onclick="window.auraTour.simulatePipelinePulse()" class="w-full py-2.5 px-4 rounded-xl bg-slate-800 hover:bg-slate-700 text-emerald-300 hover:text-white border border-emerald-500/30 text-xs font-semibold transition-all flex items-center justify-center gap-2 shadow-sm">
                <i data-lucide="play-circle" class="w-3.5 h-3.5"></i>
                <span>Disparar Pulso do Pipeline (Sub-42ms)</span>
              </button>
            </div>
          </div>

          <!-- ETAPA 4: Narrativa -->
          <div id="narrative-step-4" class="step-content-pane hidden-pane space-y-4">
            <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-purple-500/15 border border-purple-500/30 text-purple-300 text-xs font-semibold">
              <i data-lucide="sparkles" class="w-3.5 h-3.5"></i>
              <span>Etapa 04 de 04 • Resolução Acionável</span>
            </div>
            <h2 class="text-2xl font-bold text-white font-display-title">
              DecisionCard™ & Canvas: Diagnóstico de Luxo em 1-Toque
            </h2>
            <p class="text-sm text-slate-300 leading-relaxed font-sans">
              O resultado não é um texto longo e vago, mas sim um <strong>DecisionCard (AURA Precision Glass)</strong> acoplado ao <strong>Companion Canvas</strong> com diagnóstico visual imediato, métricas exatas e botões de ação executiva com disparo em 1 clique.
            </p>
            <div class="p-3.5 rounded-xl bg-white/[0.03] border border-white/5 space-y-2 text-xs font-sans">
              <div class="flex items-center gap-2 text-purple-400 font-semibold">
                <i data-lucide="mouse-pointer-click" class="w-4 h-4"></i>
                <span>Ações Rápidas: Reposição de Estoque, Pedidos & Fechamento</span>
              </div>
              <div class="flex items-center gap-2 text-purple-400 font-semibold">
                <i data-lucide="layers" class="w-4 h-4"></i>
                <span>AURA Companion Canvas: Auditoria Profunda de Estoque & ANP</span>
              </div>
              <div class="flex items-center gap-2 text-purple-400 font-semibold">
                <i data-lucide="clock" class="w-4 h-4"></i>
                <span>Horas de Planilhas Reduzidas a 10 Segundos</span>
              </div>
            </div>
            <div class="pt-2">
              <button onclick="window.auraTour.simulateActionClick('pedido')" class="btn-aura-glow-soft w-full py-2.5 px-4 rounded-xl bg-gradient-to-r from-purple-500 to-cyan-500 hover:brightness-105 text-white font-bold text-xs transition-all flex items-center justify-center gap-2 active:scale-95 border border-white/10">
                <i data-lucide="send" class="w-3.5 h-3.5"></i>
                <span>Simular Disparo de Pedido em 1-Clique</span>
              </button>
            </div>
          </div>

        </div>

        <!-- Rodapé do Card da Narrativa -->
        <div class="pt-6 border-t border-white/10 flex items-center justify-between text-xs font-sans">
          <span class="text-slate-400">Tour Interativo AURA v2.9</span>
          <button onclick="window.auraTour.nextStep()" class="text-cyan-400 hover:text-cyan-300 font-semibold flex items-center gap-1 group">
            <span>Avançar Etapa</span>
            <i data-lucide="arrow-right" class="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform"></i>
          </button>
        </div>

      </div>

      <!-- COLUNA DA DIREITA: PALCO VISUAL DINÂMICO INTERATIVO (7 Cols) -->
      <div class="lg:col-span-7 flex flex-col glass-panel rounded-2xl border border-white/10 shadow-xl backdrop-blur-xl bg-obsidian/95 relative overflow-hidden min-h-[460px]">
        
        <!-- Topo da Janela do Palco (Estilo macOS / Terminal de Luxo) -->
        <div class="p-3.5 border-b border-white/10 bg-white/[0.02] flex items-center justify-between">
          <div class="flex items-center gap-2">
            <span class="w-3 h-3 rounded-full bg-rose-500/80"></span>
            <span class="w-3 h-3 rounded-full bg-amber-500/80"></span>
            <span class="w-3 h-3 rounded-full bg-emerald-500/80"></span>
            <span class="ml-2 text-xs font-mono text-slate-400" id="stage-viewport-title">aura://executivo/pergunta-entrada</span>
          </div>
          <div class="flex items-center gap-2 text-[11px] font-mono text-slate-400">
            <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping"></span>
            <span id="stage-telemetry-badge">MOTOR SOBERANO ONLINE</span>
          </div>
        </div>

        <!-- Palco Visual 1: A Pergunta Executiva -->
        <div id="visual-stage-1" class="step-content-pane active-pane flex-1 p-6 space-y-5">
          <div class="flex items-center justify-between">
            <span class="text-xs font-mono text-cyan-400">TERMINAL DE ENTRADA DO GESTOR</span>
            <span class="px-2 py-0.5 rounded text-[10px] font-mono bg-cyan-500/10 text-cyan-300 border border-cyan-500/20">CANAL SEGURO TLS 1.3</span>
          </div>

          <!-- Chat Prompt Card Simulado -->
          <div class="p-4 rounded-xl bg-slate-900/90 border border-white/10 space-y-3 shadow-inner">
            <div class="flex items-center gap-2">
              <div class="w-7 h-7 rounded-lg bg-purple-500/20 text-purple-300 flex items-center justify-center font-bold text-xs">
                G
              </div>
              <div>
                <div class="text-xs font-semibold text-white">Gerente Executivo (Unidade Central)</div>
                <div class="text-[10px] text-slate-400">Enviado às 17:42 • Posto #042 & PDV Central</div>
              </div>
            </div>
            
            <div class="p-3 rounded-lg bg-black/40 border border-white/5 font-sans text-sm text-cyan-200 leading-relaxed" id="step1-typed-text">
              "Qual a previsão de esgotamento do Tanque 02 de Gasolina Comum e tivemos furo no fechamento do último turno?"
            </div>
          </div>

          <!-- Tags de Contexto da Unidade Detectadas Automaticamente -->
          <div class="space-y-2">
            <span class="text-[11px] font-mono uppercase tracking-wider text-slate-400">Metadados de Contexto Vinculados:</span>
            <div class="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs font-sans">
              <div class="p-2.5 rounded-lg bg-white/[0.02] border border-white/5">
                <div class="text-[10px] text-slate-400">Unidade / Filial</div>
                <div class="font-bold text-slate-200">Operação #042</div>
              </div>
              <div class="p-2.5 rounded-lg bg-white/[0.02] border border-white/5">
                <div class="text-[10px] text-slate-400">Turno Ativo</div>
                <div class="font-bold text-slate-200">Turno 3 (Noite)</div>
              </div>
              <div class="p-2.5 rounded-lg bg-white/[0.02] border border-white/5">
                <div class="text-[10px] text-slate-400">Sondas & Sensores</div>
                <div class="font-bold text-emerald-400">10/10 Online</div>
              </div>
              <div class="p-2.5 rounded-lg bg-white/[0.02] border border-white/5">
                <div class="text-[10px] text-slate-400">Bicos / PDVs</div>
                <div class="font-bold text-cyan-400">16 Conectados</div>
              </div>
            </div>
          </div>

          <!-- Animated Pulse Direcionando para o Escudo -->
          <div class="p-3 rounded-xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-between text-xs font-sans text-purple-300">
            <div class="flex items-center gap-2">
              <span class="w-2 h-2 rounded-full bg-purple-400 animate-ping"></span>
              <span>Encaminhando payload bruto ao Escudo AURA Guard™...</span>
            </div>
            <button onclick="window.auraTour.goToStep(2)" class="text-cyan-400 hover:text-white underline font-semibold">
              Ver Sanitização →
            </button>
          </div>
        </div>

        <!-- Palco Visual 2: Escudo AURA Guard & Efeito de Desintegração em Poeira (Generalizado) -->
        <div id="visual-stage-2" class="step-content-pane hidden-pane flex-1 p-6 space-y-4 relative overflow-hidden">
          
          <!-- Canvas Overlay de Partículas (Desintegração em Poeira) -->
          <canvas id="dust-particle-canvas"></canvas>

          <div class="flex items-center justify-between relative z-10">
            <span class="text-xs font-mono text-emerald-400">CÂMARA DE SANITIZAÇÃO CRIPTOGRÁFICA DE BORDA (LGPD)</span>
            <span class="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-500/10 text-emerald-300 border border-emerald-500/20" id="dust-status-pill">
              ESCUDO ATIVO
            </span>
          </div>

          <!-- Container do Payload: Antes e Depois da Desintegração -->
          <div class="p-4 rounded-xl bg-slate-900/90 border border-white/10 space-y-3 relative z-10 shadow-xl">
            <div class="flex items-center justify-between border-b border-white/5 pb-2 text-xs">
              <span class="font-mono text-slate-400">DADOS SENSÍVEIS IDENTIFICADOS NA OPERAÇÃO:</span>
              <span class="text-[11px] font-semibold text-cyan-400" id="pii-counter-label">5 Itens Sensíveis</span>
            </div>

            <!-- Lista de Itens com Efeito de Dissolução e Substituição Generalizada -->
            <div class="space-y-2.5 font-mono text-xs" id="pii-items-list">
              <div class="flex items-center justify-between p-2 rounded bg-black/40 border border-white/5" id="pii-row-1">
                <span class="text-slate-400">CNPJ:</span>
                <span class="pii-raw font-bold text-rose-400" id="pii-val-1">14.285.910/0001-44</span>
                <span class="pii-redacted font-bold text-emerald-400 hidden" id="pii-token-1">[CNPJ_BLINDADO:HASH_9A]</span>
              </div>
              <div class="flex items-center justify-between p-2 rounded bg-black/40 border border-white/5" id="pii-row-2">
                <span class="text-slate-400">CPF:</span>
                <span class="pii-raw font-bold text-rose-400" id="pii-val-2">529.982.247-25</span>
                <span class="pii-redacted font-bold text-emerald-400 hidden" id="pii-token-2">[CPF_BLINDADO:HASH_4B]</span>
              </div>
              <div class="flex items-center justify-between p-2 rounded bg-black/40 border border-white/5" id="pii-row-3">
                <span class="text-slate-400">IDENTIFICADOR FISCAL DE TRANSAÇÃO:</span>
                <span class="pii-raw font-bold text-rose-400" id="pii-val-3">NFCe-352609-14285910</span>
                <span class="pii-redacted font-bold text-emerald-400 hidden" id="pii-token-3">[TRANSACAO_FISCAL_TOKENIZADA]</span>
              </div>
              <div class="flex items-center justify-between p-2 rounded bg-black/40 border border-white/5" id="pii-row-4">
                <span class="text-slate-400">SALDO EM CAIXA:</span>
                <span class="pii-raw font-bold text-rose-400" id="pii-val-4">R$ 42.850,00</span>
                <span class="pii-redacted font-bold text-emerald-400 hidden" id="pii-token-4">[VALOR_CONFIDENCIAL_HASH]</span>
              </div>
              <div class="flex items-center justify-between p-2 rounded bg-black/40 border border-white/5" id="pii-row-5">
                <span class="text-slate-400">CREDENCIAIS:</span>
                <span class="pii-raw font-bold text-rose-400" id="pii-val-5">token_sessao_pdv_881</span>
                <span class="pii-redacted font-bold text-emerald-400 hidden" id="pii-token-5">[CREDENCIAL_ELIMINADA]</span>
              </div>
            </div>
          </div>

          <!-- Sandbox Interativo: Experimente com seu próprio dado -->
          <div class="p-3.5 rounded-xl bg-cyan-950/20 border border-cyan-500/25 space-y-2 relative z-10 font-sans text-xs">
            <div class="flex items-center justify-between">
              <span class="font-semibold text-cyan-300 flex items-center gap-1.5">
                <i data-lucide="sparkles" class="w-3.5 h-3.5"></i>
                Experimente você mesmo (Sandbox Tátil):
              </span>
              <span class="text-[10px] text-slate-400">Qualquer CNPJ / CPF</span>
            </div>
            <div class="flex items-center gap-2">
              <input type="text" id="custom-pii-input" value="CNPJ 24.582.110/0001-88" class="flex-1 bg-black/50 border border-white/10 rounded-lg px-3 py-1.5 text-xs text-white font-mono focus:outline-none focus:border-cyan-400" placeholder="Digite um CNPJ, CPF ou valor...">
              <button onclick="window.auraTour.triggerCustomDustDisintegration()" id="btn-custom-disintegrate" class="btn-aura-glow-soft px-3 py-1.5 rounded-lg bg-gradient-to-r from-cyan-500 to-emerald-500 hover:brightness-105 text-slate-950 font-bold text-xs font-sans transition-all active:scale-95 flex items-center gap-1 whitespace-nowrap border border-white/10">
                <i data-lucide="zap" class="w-3 h-3 fill-current"></i>
                <span>Pulverizar</span>
              </button>
            </div>
          </div>

          <!-- Métricas de Blindagem -->
          <div class="grid grid-cols-3 gap-2 text-center text-xs font-sans relative z-10">
            <div class="p-2.5 rounded-xl bg-white/[0.02] border border-white/5">
              <div class="text-[10px] text-slate-400">Vazamento Externo</div>
              <div class="font-extrabold text-emerald-400 text-sm">0 Bytes</div>
            </div>
            <div class="p-2.5 rounded-xl bg-white/[0.02] border border-white/5">
              <div class="text-[10px] text-slate-400">Tempo de Pulverização</div>
              <div class="font-extrabold text-cyan-400 text-sm">3.8 ms</div>
            </div>
            <div class="p-2.5 rounded-xl bg-white/[0.02] border border-white/5">
              <div class="text-[10px] text-slate-400">Conformidade LGPD</div>
              <div class="font-extrabold text-purple-400 text-sm">100% Blindado</div>
            </div>
          </div>

        </div>

        <!-- Palco Visual 3: Processamento Analítico em Sub-100ms -->
        <div id="visual-stage-3" class="step-content-pane hidden-pane flex-1 p-6 space-y-4">
          <div class="flex items-center justify-between">
            <span class="text-xs font-mono text-cyan-400">PIPELINE DE AUDITORIA PARALELA DE BORDA</span>
            <span class="px-2 py-0.5 rounded text-[10px] font-mono bg-cyan-500/10 text-cyan-300 border border-cyan-500/20" id="pipeline-total-badge">
              TEMPO TOTAL: 42 MS
            </span>
          </div>

          <!-- Diagrama de Pipeline de 4 Nós Conectados com Pulso SVG Dinâmico -->
          <div class="space-y-2 relative font-sans text-xs">
            
            <!-- Nó 1: Telemetria de Pista -->
            <div id="pipe-node-1" class="pipeline-node p-3 rounded-xl bg-slate-900/90 border border-emerald-500/40 flex items-center justify-between shadow-sm cursor-pointer hover:bg-slate-800 transition-all" onclick="window.auraTour.inspectNode('pista')">
              <div class="flex items-center gap-3">
                <div class="w-8 h-8 rounded-lg bg-emerald-500/20 text-emerald-300 flex items-center justify-center font-bold">
                  <i data-lucide="gauge" class="w-4 h-4"></i>
                </div>
                <div>
                  <div class="font-bold text-white">Telemetria de Pista, PDVs & Sensores</div>
                  <div class="text-[10px] text-slate-400">Sondas de nível, encerrantes de PDV, balanças e concentrador</div>
                </div>
              </div>
              <div class="flex items-center gap-2">
                <span class="px-2 py-0.5 rounded-full text-[10px] font-mono bg-emerald-500/20 text-emerald-300">12 ms</span>
                <span class="w-2.5 h-2.5 rounded-full bg-emerald-400 shadow-[0_0_8px_#34d399]"></span>
              </div>
            </div>

            <!-- Conector SVG 1 -->
            <div class="flex justify-center -my-1 h-5 items-center relative">
              <svg width="2" height="20" class="overflow-visible">
                <line x1="1" y1="0" x2="1" y2="20" stroke="url(#pipeGrad1)" stroke-width="2" class="flow-path-active" />
                <circle cx="1" cy="10" r="2.5" fill="#10b981" class="photon-pulse" />
                <defs>
                  <linearGradient id="pipeGrad1" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stop-color="#10b981" />
                    <stop offset="100%" stop-color="#06b6d4" />
                  </linearGradient>
                </defs>
              </svg>
            </div>

            <!-- Nó 2: Auditoria Fiscal ANP Portaria 26 -->
            <div id="pipe-node-2" class="pipeline-node p-3 rounded-xl bg-slate-900/90 border border-cyan-500/40 flex items-center justify-between shadow-sm cursor-pointer hover:bg-slate-800 transition-all" onclick="window.auraTour.inspectNode('anp')">
              <div class="flex items-center gap-3">
                <div class="w-8 h-8 rounded-lg bg-cyan-500/20 text-cyan-300 flex items-center justify-center font-bold">
                  <i data-lucide="book-check" class="w-4 h-4"></i>
                </div>
                <div>
                  <div class="font-bold text-white">Auditoria Fiscal ANP (Portaria 26/1992)</div>
                  <div class="text-[10px] text-slate-400">Tolerância regulamentar volumétrica de ±0.60% (LMC)</div>
                </div>
              </div>
              <div class="flex items-center gap-2">
                <span class="px-2 py-0.5 rounded-full text-[10px] font-mono bg-cyan-500/20 text-cyan-300">18 ms</span>
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
                    <stop offset="100%" stop-color="#7c3aed" />
                  </linearGradient>
                </defs>
              </svg>
            </div>

            <!-- Nó 3: Conciliação de Turno & POS -->
            <div id="pipe-node-3" class="pipeline-node p-3 rounded-xl bg-slate-900/90 border border-purple-500/40 flex items-center justify-between shadow-sm cursor-pointer hover:bg-slate-800 transition-all" onclick="window.auraTour.inspectNode('caixa')">
              <div class="flex items-center gap-3">
                <div class="w-8 h-8 rounded-lg bg-purple-500/20 text-purple-300 flex items-center justify-center font-bold">
                  <i data-lucide="scale" class="w-4 h-4"></i>
                </div>
                <div>
                  <div class="font-bold text-white">Conciliação Fiduciária de Turno & Caixa</div>
                  <div class="text-[10px] text-slate-400">Cruzamento de bicos faturados vs cartões e dinheiro recebidos</div>
                </div>
              </div>
              <div class="flex items-center gap-2">
                <span class="px-2 py-0.5 rounded-full text-[10px] font-mono bg-purple-500/20 text-purple-300">24 ms</span>
                <span class="w-2.5 h-2.5 rounded-full bg-purple-400 shadow-[0_0_8px_#a855f7]"></span>
              </div>
            </div>

            <!-- Conector SVG 3 -->
            <div class="flex justify-center -my-1 h-5 items-center relative">
              <svg width="2" height="20" class="overflow-visible">
                <line x1="1" y1="0" x2="1" y2="20" stroke="url(#pipeGrad3)" stroke-width="2" class="flow-path-active" />
                <circle cx="1" cy="10" r="2.5" fill="#7c3aed" class="photon-pulse" />
                <defs>
                  <linearGradient id="pipeGrad3" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stop-color="#7c3aed" />
                    <stop offset="100%" stop-color="#10b981" />
                  </linearGradient>
                </defs>
              </svg>
            </div>

            <!-- Nó 4: Previsão de Esgotamento (Run-Out) -->
            <div id="pipe-node-4" class="pipeline-node p-3 rounded-xl bg-slate-900/90 border border-emerald-500/40 flex items-center justify-between shadow-sm cursor-pointer hover:bg-slate-800 transition-all" onclick="window.auraTour.inspectNode('runout')">
              <div class="flex items-center gap-3">
                <div class="w-8 h-8 rounded-lg bg-emerald-500/20 text-emerald-300 flex items-center justify-center font-bold">
                  <i data-lucide="trending-down" class="w-4 h-4"></i>
                </div>
                <div>
                  <div class="font-bold text-white">Previsão Preditiva de Esgotamento (Run-Out)</div>
                  <div class="text-[10px] text-slate-400">Curva horária de vazão por bico e cálculo de segurança</div>
                </div>
              </div>
              <div class="flex items-center gap-2">
                <span class="px-2 py-0.5 rounded-full text-[10px] font-mono bg-emerald-500/20 text-emerald-300">35 ms</span>
                <span class="w-2.5 h-2.5 rounded-full bg-emerald-400 shadow-[0_0_8px_#34d399]"></span>
              </div>
            </div>

          </div>

          <!-- Detalhe do Inspetor Interativo do Nó -->
          <div id="pipeline-node-inspector" class="p-3 rounded-xl bg-white/[0.02] border border-white/5 text-xs text-slate-300 flex items-center justify-between">
            <span id="pipeline-inspector-text">Clique em qualquer etapa acima para inspecionar os parâmetros de cálculo em tempo real.</span>
            <span class="text-cyan-400 font-mono text-[11px] font-semibold">ZERO ALUCINAÇÃO</span>
          </div>
        </div>

        <!-- Palco Visual 4: DecisionCard & Companion Canvas -->
        <div id="visual-stage-4" class="step-content-pane hidden-pane flex-1 p-6 space-y-4">
          
          <!-- Seletor de Visão do Palco 4 -->
          <div class="flex items-center justify-between border-b border-white/10 pb-3">
            <div class="flex items-center gap-2 text-xs font-sans">
              <button onclick="window.auraTour.toggleStep4Tab('decisioncard')" id="tab-step4-decisioncard" class="px-3 py-1.5 rounded-lg bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 font-semibold transition-all">
                DecisionCard™
              </button>
              <button onclick="window.auraTour.toggleStep4Tab('companion')" id="tab-step4-companion" class="px-3 py-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/5 border border-transparent font-semibold transition-all flex items-center gap-1.5">
                <span>Companion Canvas™</span>
                <span class="px-1.5 py-0.2 rounded text-[9px] bg-purple-500/20 text-purple-300">Auditoria</span>
              </button>
            </div>
            <span class="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
              PRONTO PARA DECISÃO
            </span>
          </div>

          <!-- Painel 4A: DecisionCard de Luxo -->
          <div id="view-step4-decisioncard" class="space-y-4">
            <div class="p-5 rounded-2xl glass-card-glow-cyan border border-cyan-500/30 space-y-4 shadow-xl relative">
              <div class="flex items-center justify-between border-b border-white/10 pb-3">
                <div class="flex items-center gap-2.5">
                  <div class="neural-core-orb !w-6 !h-6"></div>
                  <div>
                    <h3 class="font-bold text-white text-sm">Diagnóstico Operacional Consolidado</h3>
                    <p class="text-[10px] text-slate-400 font-sans">Tanque 02 (Gasolina Comum) • Posto #042</p>
                  </div>
                </div>
                <span class="px-2.5 py-1 rounded-full text-[10px] font-bold bg-rose-500/20 text-rose-300 border border-rose-500/30 animate-pulse">
                  PEDIDO RECOMENDADO
                </span>
              </div>

              <!-- Grid de 4 Indicadores Cruciais -->
              <div class="grid grid-cols-2 gap-3 text-xs font-sans">
                <div class="p-3 rounded-xl bg-slate-900/80 border border-white/5">
                  <div class="text-[10px] text-slate-400">Autonomia Restante</div>
                  <div class="text-base font-extrabold text-amber-300">18.4 Horas</div>
                  <div class="text-[10px] text-slate-400">Esgotamento: 04:30 AM amanhã</div>
                </div>
                <div class="p-3 rounded-xl bg-slate-900/80 border border-white/5">
                  <div class="text-[10px] text-slate-400">Volume Físico no Tanque</div>
                  <div class="text-base font-extrabold text-white">4.820 Litros</div>
                  <div class="text-[10px] text-slate-400">Capacidade: 30.000 L (16%)</div>
                </div>
                <div class="p-3 rounded-xl bg-slate-900/80 border border-white/5">
                  <div class="text-[10px] text-slate-400">Conformidade ANP (LMC)</div>
                  <div class="text-base font-extrabold text-emerald-400">+0.28%</div>
                  <div class="text-[10px] text-slate-400">Dentro da tolerância (±0.60%)</div>
                </div>
                <div class="p-3 rounded-xl bg-slate-900/80 border border-white/5">
                  <div class="text-[10px] text-slate-400">Auditoria de Caixa (Turno 3)</div>
                  <div class="text-base font-extrabold text-emerald-400">R$ 0,00 Furo</div>
                  <div class="text-[10px] text-slate-400">100% de conciliação fiscal</div>
                </div>
              </div>

              <!-- Botões Executivos em 1-Clique com Glow Suavizado -->
              <div class="space-y-2 pt-1 font-sans">
                <span class="text-[10px] uppercase font-mono tracking-wider text-slate-400">Ações Recomendadas em 1-Toque:</span>
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  <button onclick="window.auraTour.simulateActionClick('pedido')" id="action-btn-pedido" class="btn-aura-glow-soft py-2.5 px-3 rounded-xl bg-gradient-to-r from-cyan-500 to-emerald-500 hover:brightness-105 text-slate-950 font-bold text-xs flex items-center justify-center gap-1.5 active:scale-95 transition-all border border-white/10">
                    <i data-lucide="truck" class="w-3.5 h-3.5"></i>
                    <span>Emitir Pedido (30.000 L)</span>
                  </button>
                  <button onclick="window.auraTour.simulateActionClick('lmc')" id="action-btn-lmc" class="py-2.5 px-3 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold flex items-center justify-center gap-1.5 border border-white/10 active:scale-95 transition-all shadow-sm">
                    <i data-lucide="file-text" class="w-3.5 h-3.5"></i>
                    <span>Gerar Extrato LMC Oficial</span>
                  </button>
                </div>
              </div>

              <!-- Toast de Confirmação Instantâneo -->
              <div id="action-feedback-toast" class="hidden p-3 rounded-xl bg-emerald-500/20 border border-emerald-500/40 text-xs font-sans text-emerald-200 flex items-center gap-2">
                <i data-lucide="check-circle" class="w-4 h-4 text-emerald-400 flex-shrink-0"></i>
                <span id="action-feedback-message">Ordem executada com sucesso em 1 toque!</span>
              </div>
            </div>
          </div>

          <!-- Painel 4B: AURA Companion Canvas -->
          <div id="view-step4-companion" class="hidden space-y-4">
            <div class="p-5 rounded-2xl glass-card-glow-purple border border-purple-500/30 space-y-4 shadow-xl">
              <div class="flex items-center justify-between border-b border-white/10 pb-3">
                <div class="flex items-center gap-2">
                  <i data-lucide="layers" class="w-4 h-4 text-purple-400"></i>
                  <span class="font-bold text-white text-xs">AURA Companion Canvas • Telemetria Profunda</span>
                </div>
                <span class="text-[10px] font-mono text-purple-300">Posto 042 / Sonda S-02</span>
              </div>

              <!-- Visualizador Gráfico de Nível de Tanque -->
              <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 font-sans text-xs">
                
                <div class="p-3.5 rounded-xl bg-slate-900/80 border border-white/5 space-y-2.5">
                  <div class="flex items-center justify-between text-[11px]">
                    <span class="text-slate-400">Nível Físico Tanque 02</span>
                    <span class="font-bold text-amber-300">16% (Crítico)</span>
                  </div>
                  <div class="w-full bg-slate-950 rounded-lg h-7 p-1 border border-white/10 relative overflow-hidden flex items-center">
                    <div class="h-full bg-gradient-to-r from-rose-500 via-amber-500 to-emerald-500 rounded text-[10px] font-bold text-white flex items-center justify-end pr-2 liquid-wave" style="width: 16%;">
                      4.820 L
                    </div>
                    <div class="absolute top-0 bottom-0 left-[20%] w-0.5 bg-rose-400 border-l border-dashed border-rose-300" title="Limite Mínimo de Segurança (20%)"></div>
                  </div>
                  <div class="flex items-center justify-between text-[10px] text-slate-400">
                    <span>Vazão: 245 L/h</span>
                    <span class="text-rose-400 font-semibold">Alerta de Ruptura Ativo</span>
                  </div>
                </div>

                <div class="p-3.5 rounded-xl bg-slate-900/80 border border-white/5 space-y-2.5">
                  <div class="flex items-center justify-between text-[11px]">
                    <span class="text-slate-400">Corredor Portaria 26 ANP</span>
                    <span class="font-bold text-emerald-400">+0.28% (Conforme)</span>
                  </div>
                  <div class="w-full bg-slate-950 rounded-lg h-7 p-1 border border-white/10 relative flex items-center justify-between text-[9px] font-mono text-slate-400 px-2">
                    <span class="text-rose-400">-0.60%</span>
                    <span class="text-slate-500">0.00%</span>
                    <span class="text-rose-400">+0.60%</span>
                    <div class="absolute top-1 bottom-1 left-[73%] w-2 bg-emerald-400 rounded-full shadow-[0_0_8px_#34d399]" title="Variação Atual: +0.28%"></div>
                  </div>
                  <div class="flex items-center justify-between text-[10px] text-slate-400">
                    <span>LMC Diário: Escriturado</span>
                    <span class="text-emerald-400 font-semibold">Zero Risco Fiscal</span>
                  </div>
                </div>

              </div>

              <!-- Fechamento Consolidado POS vs Medidores -->
              <div class="p-3 rounded-xl bg-black/40 border border-white/5 text-xs font-mono space-y-1.5">
                <div class="text-[10px] text-slate-400 uppercase tracking-wider">Fechamento Turno 3: Conciliação Centavo a Centavo</div>
                <div class="grid grid-cols-3 gap-2 text-[11px]">
                  <div>POS / Cartões: <span class="text-white font-bold">R$ 31.420,00</span></div>
                  <div>PIX / Dinheiro: <span class="text-white font-bold">R$ 11.430,00</span></div>
                  <div>Diferença: <span class="text-emerald-400 font-bold">R$ 0,00 (Exato)</span></div>
                </div>
              </div>

              <div class="pt-1 flex justify-end">
                <button onclick="window.auraTour.simulateActionClick('lmc')" class="py-2 px-4 rounded-xl bg-slate-800 hover:bg-slate-700 text-purple-300 hover:text-white border border-purple-500/30 text-xs font-semibold flex items-center gap-2 transition-all shadow-sm">
                  <i data-lucide="file-check" class="w-3.5 h-3.5"></i>
                  <span>Exportar Auditoria Companion Canvas</span>
                </button>
              </div>
            </div>
          </div>

        </div>

      </div>

    </div>

    <!-- =======================================================================
         NOVA SEÇÃO CORE: MINI JANELA DE CHAT DA AURA + FLUXOGRAMA / GRAFO MODERNO
         (Demonstrando o fluxo em tempo real com base em LGPD)
         ======================================================================= -->
    <section id="sec-chat-graph" class="space-y-6 pt-6 scroll-reveal">
      
      <!-- Cabeçalho da Seção -->
      <div class="text-center max-w-3xl mx-auto space-y-3">
        <div class="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-purple-500/10 border border-purple-500/25 text-xs font-sans text-purple-300">
          <i data-lucide="shield-check" class="w-3.5 h-3.5 text-emerald-400"></i>
          <span class="font-semibold uppercase text-[10px] tracking-wider">Conformidade LGPD (Lei 13.709/2018) • Privacy by Design</span>
        </div>
        <h2 class="text-2xl sm:text-4xl font-extrabold text-white font-display-title">
          Chat Executivo & Grafo Cognitivo Lado a Lado
        </h2>
        <p class="text-xs sm:text-sm text-slate-300 leading-relaxed font-sans max-w-2xl mx-auto">
          Veja a jornada completa: o gestor digita uma dúvida no chat e, em milissegundos, a requisição percorre o grafo fiduciário — higienizada pelo Escudo LGPD, auditada no motor de borda e entregue como DecisionCard pronto para ação.
        </p>
      </div>

      <!-- Grid Lado a Lado: Mini Janela de Chat (5 Cols) vs Grafo Conectado (7 Cols) -->
      <div class="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
        
        <!-- COLUNA ESQUERDA: MINI JANELA DO CHAT DA AURA (5 Cols) -->
        <div id="mini-chat-aura" class="lg:col-span-5 flex flex-col glass-panel rounded-2xl border border-white/10 shadow-xl backdrop-blur-xl bg-slateSurface/95 overflow-hidden">
          
          <!-- Topo da Janela do Chat -->
          <div class="p-3.5 border-b border-white/10 bg-white/[0.02] flex items-center justify-between">
            <div class="flex items-center gap-2">
              <div class="neural-core-orb !w-5 !h-5"></div>
              <div>
                <span class="text-xs font-bold text-white">AURA Chat Executivo</span>
                <span class="text-[10px] text-slate-400 block sm:inline sm:ml-1 font-mono">borda local • TLS 1.3</span>
              </div>
            </div>
            <span class="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 flex items-center gap-1">
              <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping"></span>
              LGPD BLINDADO
            </span>
          </div>

          <!-- Seletor de Cenários Multissetoriais Rápidos -->
          <div class="p-3 border-b border-white/5 bg-slate-950/40 space-y-1.5 font-sans">
            <div class="flex items-center justify-between text-[11px] text-slate-400">
              <span class="font-medium">Selecione um segmento para simular:</span>
              <span class="text-cyan-400 text-[10px] font-mono">4 CENÁRIOS</span>
            </div>
            <div class="grid grid-cols-2 gap-1.5 text-[11px]">
              <button onclick="window.auraTour.selectChatScenario('varejo')" id="scenario-btn-varejo" class="px-2.5 py-1.5 rounded-lg bg-cyan-500/20 text-cyan-200 border border-cyan-500/40 font-semibold truncate transition-all text-left flex items-center gap-1.5">
                <span>🏪</span>
                <span class="truncate">Padaria / Bar</span>
              </button>
              <button onclick="window.auraTour.selectChatScenario('posto')" id="scenario-btn-posto" class="px-2.5 py-1.5 rounded-lg bg-slate-900/80 text-slate-300 hover:text-white border border-white/10 truncate transition-all text-left flex items-center gap-1.5">
                <span>⛽</span>
                <span class="truncate">Postos & Tanques</span>
              </button>
              <button onclick="window.auraTour.selectChatScenario('loja')" id="scenario-btn-loja" class="px-2.5 py-1.5 rounded-lg bg-slate-900/80 text-slate-300 hover:text-white border border-white/10 truncate transition-all text-left flex items-center gap-1.5">
                <span>🏬</span>
                <span class="truncate">Loja & Varejo</span>
              </button>
              <button onclick="window.auraTour.selectChatScenario('fiscal')" id="scenario-btn-fiscal" class="px-2.5 py-1.5 rounded-lg bg-slate-900/80 text-slate-300 hover:text-white border border-white/10 truncate transition-all text-left flex items-center gap-1.5">
                <span>⚖️</span>
                <span class="truncate">Auditoria Fiscal</span>
              </button>
            </div>
          </div>

          <!-- Área de Histórico de Mensagens do Chat -->
          <div class="p-4 flex-1 space-y-3.5 overflow-y-auto max-h-[380px] font-sans text-xs" id="chat-messages-container">
            
            <!-- Mensagem do Gestor -->
            <div class="flex items-start gap-2.5">
              <div class="w-6 h-6 rounded-lg bg-purple-500/20 text-purple-300 flex items-center justify-center font-bold text-[10px] flex-shrink-0 mt-0.5">
                G
              </div>
              <div class="flex-1 space-y-1">
                <div class="flex items-center justify-between text-[10px] text-slate-400">
                  <span class="font-semibold text-slate-300" id="chat-user-label">Gestor Operacional (Padaria Central)</span>
                  <span id="chat-timestamp-label">17:48</span>
                </div>
                <div class="p-3 rounded-2xl rounded-tl-sm bg-slate-900 border border-white/10 text-slate-200 leading-relaxed shadow-sm" id="chat-user-query-text">
                  "Qual o índice de quebra no fechamento do caixa da manhã e temos risco de ruptura de insumos críticos?"
                </div>
              </div>
            </div>

            <!-- Resposta da AURA com Mini DecisionCard Incrustado -->
            <div class="flex items-start gap-2.5">
              <div class="neural-core-orb !w-6 !h-6 flex-shrink-0 mt-0.5"></div>
              <div class="flex-1 space-y-2">
                <div class="flex items-center justify-between text-[10px] text-slate-400">
                  <span class="font-bold text-cyan-300">AURA Cognitiva</span>
                  <span class="text-emerald-400 font-mono text-[9px]">34 ms • 100% LGPD</span>
                </div>
                
                <!-- Balão de Texto da Resposta -->
                <div class="p-3 rounded-2xl rounded-tl-sm bg-cyan-950/20 border border-cyan-500/30 text-slate-200 leading-relaxed space-y-2" id="chat-aura-response-bubble">
                  <p id="chat-response-narrative">
                    Turno da manhã auditado em 31ms. Não houve divergência de caixa (R$ 0,00). No entanto, o insumo café especial em grãos atingiu 14% do ponto de segurança, com previsão de esgotamento hoje às 20h30.
                  </p>

                  <!-- Mini DecisionCard Incrustado -->
                  <div class="p-3 rounded-xl bg-black/60 border border-cyan-500/20 space-y-2.5 font-sans">
                    <div class="flex items-center justify-between border-b border-white/5 pb-1.5">
                      <div class="flex items-center gap-1.5">
                        <i data-lucide="check-circle" class="w-3.5 h-3.5 text-emerald-400"></i>
                        <span class="font-bold text-white text-[11px]" id="mini-dc-title">Auditoria de PDV & Estoque Crítico</span>
                      </div>
                      <span class="px-2 py-0.5 rounded text-[9px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30" id="mini-dc-badge">
                        REPOSIÇÃO SUGERIDA
                      </span>
                    </div>

                    <!-- 2 Indicadores Chave -->
                    <div class="grid grid-cols-2 gap-2 text-[10px]">
                      <div class="p-2 rounded bg-white/[0.02] border border-white/5">
                        <div class="text-slate-400" id="mini-metric-label-1">Auditoria de Caixa</div>
                        <div class="font-bold text-emerald-400 text-xs" id="mini-metric-val-1">R$ 0,00 Furo</div>
                      </div>
                      <div class="p-2 rounded bg-white/[0.02] border border-white/5">
                        <div class="text-slate-400" id="mini-metric-label-2">Insumo em Risco</div>
                        <div class="font-bold text-amber-300 text-xs" id="mini-metric-val-2">Café Grãos (14%)</div>
                      </div>
                    </div>

                    <!-- Botão de Ação Imediata com Glow Suave -->
                    <button onclick="window.auraTour.simulateChatActionClick()" id="mini-dc-action-btn" class="btn-aura-glow-soft w-full py-2 px-2.5 rounded-lg bg-gradient-to-r from-cyan-500 to-emerald-500 hover:brightness-105 text-slate-950 font-bold text-[11px] flex items-center justify-center gap-1.5 active:scale-95 transition-all border border-white/10">
                      <i data-lucide="send" class="w-3 h-3"></i>
                      <span id="mini-dc-action-text">Emitir Ordem de Reposição</span>
                    </button>

                    <!-- Toast de Confirmação Suave Inline no Mini Chat -->
                    <div id="mini-chat-action-toast" class="hidden p-2 rounded-lg bg-emerald-500/20 border border-emerald-500/40 text-[10px] font-sans text-emerald-200 flex items-center gap-1.5 transition-all">
                      <i data-lucide="check-circle" class="w-3.5 h-3.5 text-emerald-400 flex-shrink-0"></i>
                      <span id="mini-chat-toast-message">Ordem executada em 1 toque!</span>
                    </div>
                  </div>
                </div>

                <!-- Rodapé de Governança e LGPD -->
                <div class="text-[10px] text-slate-400 font-mono flex items-center justify-between px-1">
                  <span>LGPD: 0 dados pessoais transmitidos</span>
                  <span class="text-emerald-400 font-semibold">Decisão Pronta ✓</span>
                </div>
              </div>
            </div>

          </div>

          <!-- Barra de Input Interativa do Chat -->
          <div class="p-3 border-t border-white/10 bg-slate-900/80 space-y-2">
            <div class="flex items-center gap-2">
              <input type="text" id="chat-interactive-input" value="Qual o índice de quebra no fechamento do caixa da manhã e temos risco de ruptura de insumos críticos?" class="flex-1 bg-black/60 border border-white/10 rounded-xl px-3 py-2 text-xs text-slate-200 font-sans focus:outline-none focus:border-cyan-400 transition-colors" placeholder="Digite uma dúvida executiva...">
              <button onclick="window.auraTour.simulateChatSubmit()" id="btn-simulate-chat-flow" class="btn-aura-glow-soft px-3.5 py-2 rounded-xl bg-gradient-to-r from-cyan-500 to-purple-500 hover:brightness-105 text-white font-bold text-xs flex items-center gap-1.5 active:scale-95 transition-all border border-white/10" title="Disparar Pergunta e Animar o Grafo ao Lado">
                <i data-lucide="send" class="w-3.5 h-3.5"></i>
                <span class="hidden sm:inline">Simular</span>
              </button>
            </div>
            <div class="flex items-center justify-between text-[10px] text-slate-400 font-sans px-1">
              <span>Clique em Simular para acionar a cascata do grafo ao lado</span>
              <span class="text-cyan-400 font-mono">Latência: sub-42ms</span>
            </div>
          </div>

        </div>

        <!-- COLUNA DIREITA: FLUXOGRAMA / GRAFO MODERNO CONECTADO EM TEMPO REAL (7 Cols) -->
        <div id="aura-flowchart-graph" class="lg:col-span-7 flex flex-col glass-panel rounded-2xl border border-white/10 shadow-xl backdrop-blur-xl bg-obsidian/95 overflow-hidden">
          
          <!-- Topo da Janela do Grafo -->
          <div class="p-3.5 border-b border-white/10 bg-white/[0.02] flex items-center justify-between">
            <div class="flex items-center gap-2">
              <i data-lucide="git-branch" class="w-4 h-4 text-cyan-400"></i>
              <span class="text-xs font-bold text-white font-mono">aura://grafo/fluxo-cognitivo-borda</span>
            </div>
            <div class="flex items-center gap-2 text-[11px] font-mono text-slate-400">
              <span class="w-2 h-2 rounded-full bg-cyan-400 shadow-[0_0_8px_#22d3ee]"></span>
              <span>5 NÓS CONECTADOS EM TEMPO REAL</span>
            </div>
          </div>

          <!-- Diagrama Vertical do Grafo com Conectores Dinâmicos e SVG Animado -->
          <div class="p-5 flex-1 space-y-2 relative font-sans text-xs">
            
            <!-- NÓ 1: Prompt do Gestor (Linguagem Natural) -->
            <div id="graph-node-prompt" class="graph-node p-3 rounded-xl bg-slate-900/90 border border-purple-500/30 flex items-center justify-between hover:bg-slate-800 transition-all shadow-sm" onclick="window.auraTour.inspectGraphNode('prompt')">
              <div class="flex items-center gap-3">
                <div class="w-8 h-8 rounded-lg bg-purple-500/20 text-purple-300 flex items-center justify-center font-bold flex-shrink-0">
                  <i data-lucide="message-square" class="w-4 h-4"></i>
                </div>
                <div>
                  <div class="font-bold text-white flex items-center gap-2">
                    <span>1. Entrada em Linguagem Natural</span>
                    <span class="px-1.5 py-0.2 rounded text-[9px] bg-purple-500/20 text-purple-300 font-mono">Multicanal</span>
                  </div>
                  <div class="text-[10px] text-slate-400">Prompt do gestor recebido via chat ou voz (sem SQL ou fórmulas)</div>
                </div>
              </div>
              <div class="flex items-center gap-2">
                <span class="px-2 py-0.5 rounded-full text-[10px] font-mono bg-purple-500/15 text-purple-300">0.0 ms</span>
                <span class="w-2 h-2 rounded-full bg-purple-400"></span>
              </div>
            </div>

            <!-- Conector SVG 1 -->
            <div class="flex justify-center -my-1 h-5 items-center relative">
              <svg width="2" height="20" class="overflow-visible">
                <line x1="1" y1="0" x2="1" y2="20" stroke="url(#graphGrad1)" stroke-width="2" class="flow-path-active" />
                <circle cx="1" cy="10" r="2.5" fill="#a855f7" class="photon-pulse" />
                <defs>
                  <linearGradient id="graphGrad1" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stop-color="#a855f7" />
                    <stop offset="100%" stop-color="#10b981" />
                  </linearGradient>
                </defs>
              </svg>
            </div>

            <!-- NÓ 2: Escudo LGPD & Sanitização de Borda (Lei 13.709/2018) -->
            <div id="graph-node-lgpd" class="graph-node p-3 rounded-xl bg-slate-900/90 border border-emerald-500/40 flex items-center justify-between hover:bg-slate-800 transition-all shadow-sm" onclick="window.auraTour.inspectGraphNode('lgpd')">
              <div class="flex items-center gap-3">
                <div class="w-8 h-8 rounded-lg bg-emerald-500/20 text-emerald-300 flex items-center justify-center font-bold flex-shrink-0">
                  <i data-lucide="shield-check" class="w-4 h-4"></i>
                </div>
                <div>
                  <div class="font-bold text-white flex items-center gap-2">
                    <span>2. Escudo LGPD & Sanitização de Borda</span>
                    <span class="px-1.5 py-0.2 rounded text-[9px] bg-emerald-500/20 text-emerald-300 font-mono">Lei 13.709/2018</span>
                  </div>
                  <div class="text-[10px] text-slate-400">Desintegração de CPFs, CNPJs e credenciais. Privacy by Design absoluta</div>
                </div>
              </div>
              <div class="flex items-center gap-2">
                <span class="px-2 py-0.5 rounded-full text-[10px] font-mono bg-emerald-500/20 text-emerald-300">+3.8 ms</span>
                <span class="w-2 h-2 rounded-full bg-emerald-400 shadow-[0_0_8px_#34d399]"></span>
              </div>
            </div>

            <!-- Conector SVG 2 -->
            <div class="flex justify-center -my-1 h-5 items-center relative">
              <svg width="2" height="20" class="overflow-visible">
                <line x1="1" y1="0" x2="1" y2="20" stroke="url(#graphGrad2)" stroke-width="2" class="flow-path-active" />
                <circle cx="1" cy="10" r="2.5" fill="#10b981" class="photon-pulse" />
                <defs>
                  <linearGradient id="graphGrad2" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stop-color="#10b981" />
                    <stop offset="100%" stop-color="#06b6d4" />
                  </linearGradient>
                </defs>
              </svg>
            </div>

            <!-- NÓ 3: Motor Analítico Soberano de Borda -->
            <div id="graph-node-motor" class="graph-node p-3 rounded-xl bg-slate-900/90 border border-cyan-500/40 flex items-center justify-between hover:bg-slate-800 transition-all shadow-sm" onclick="window.auraTour.inspectGraphNode('motor')">
              <div class="flex items-center gap-3">
                <div class="w-8 h-8 rounded-lg bg-cyan-500/20 text-cyan-300 flex items-center justify-center font-bold flex-shrink-0">
                  <i data-lucide="cpu" class="w-4 h-4"></i>
                </div>
                <div>
                  <div class="font-bold text-white flex items-center gap-2">
                    <span>3. Motor Analítico Soberano de Borda</span>
                    <span class="px-1.5 py-0.2 rounded text-[9px] bg-cyan-500/20 text-cyan-300 font-mono">Sub-100ms</span>
                  </div>
                  <div class="text-[10px] text-slate-400">Processamento em memória privada: faturamento, vendas e telemetria física</div>
                </div>
              </div>
              <div class="flex items-center gap-2">
                <span class="px-2 py-0.5 rounded-full text-[10px] font-mono bg-cyan-500/20 text-cyan-300">+14 ms</span>
                <span class="w-2 h-2 rounded-full bg-cyan-400 shadow-[0_0_8px_#22d3ee]"></span>
              </div>
            </div>

            <!-- Conector SVG 3 -->
            <div class="flex justify-center -my-1 h-5 items-center relative">
              <svg width="2" height="20" class="overflow-visible">
                <line x1="1" y1="0" x2="1" y2="20" stroke="url(#graphGrad3)" stroke-width="2" class="flow-path-active" />
                <circle cx="1" cy="10" r="2.5" fill="#06b6d4" class="photon-pulse" />
                <defs>
                  <linearGradient id="graphGrad3" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stop-color="#06b6d4" />
                    <stop offset="100%" stop-color="#f59e0b" />
                  </linearGradient>
                </defs>
              </svg>
            </div>

            <!-- NÓ 4: Regras de Negócio & Auditoria Fiduciária -->
            <div id="graph-node-regras" class="graph-node p-3 rounded-xl bg-slate-900/90 border border-amber-500/40 flex items-center justify-between hover:bg-slate-800 transition-all shadow-sm" onclick="window.auraTour.inspectGraphNode('regras')">
              <div class="flex items-center gap-3">
                <div class="w-8 h-8 rounded-lg bg-amber-500/20 text-amber-300 flex items-center justify-center font-bold flex-shrink-0">
                  <i data-lucide="scale" class="w-4 h-4"></i>
                </div>
                <div>
                  <div class="font-bold text-white flex items-center gap-2">
                    <span>4. Regras de Negócio & Auditoria Fiduciária</span>
                    <span class="px-1.5 py-0.2 rounded text-[9px] bg-amber-500/20 text-amber-300 font-mono">Zero Alucinação</span>
                  </div>
                  <div class="text-[10px] text-slate-400">Detecção de quebras de caixa, prevenção de desvios e limites fiscais</div>
                </div>
              </div>
              <div class="flex items-center gap-2">
                <span class="px-2 py-0.5 rounded-full text-[10px] font-mono bg-amber-500/20 text-amber-300">+10 ms</span>
                <span class="w-2 h-2 rounded-full bg-amber-400 shadow-[0_0_8px_#fbbf24]"></span>
              </div>
            </div>

            <!-- Conector SVG 4 -->
            <div class="flex justify-center -my-1 h-5 items-center relative">
              <svg width="2" height="20" class="overflow-visible">
                <line x1="1" y1="0" x2="1" y2="20" stroke="url(#graphGrad4)" stroke-width="2" class="flow-path-active" />
                <circle cx="1" cy="10" r="2.5" fill="#f59e0b" class="photon-pulse" />
                <defs>
                  <linearGradient id="graphGrad4" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stop-color="#f59e0b" />
                    <stop offset="100%" stop-color="#10b981" />
                  </linearGradient>
                </defs>
              </svg>
            </div>

            <!-- NÓ 5: DecisionCard™ Executivo em 1-Toque -->
            <div id="graph-node-decisao" class="graph-node p-3 rounded-xl bg-slate-900/90 border border-emerald-500/50 flex items-center justify-between hover:bg-slate-800 transition-all shadow-sm" onclick="window.auraTour.inspectGraphNode('decisao')">
              <div class="flex items-center gap-3">
                <div class="w-8 h-8 rounded-lg bg-emerald-500/20 text-emerald-300 flex items-center justify-center font-bold flex-shrink-0">
                  <i data-lucide="sparkles" class="w-4 h-4"></i>
                </div>
                <div>
                  <div class="font-bold text-white flex items-center gap-2">
                    <span>5. DecisionCard™ Executivo em 1-Toque</span>
                    <span class="px-1.5 py-0.2 rounded text-[9px] bg-emerald-500/20 text-emerald-300 font-mono">Ação Imediata</span>
                  </div>
                  <div class="text-[10px] text-slate-400">Diagnóstico consolidado com botões de disparo executivo pronto</div>
                </div>
              </div>
              <div class="flex items-center gap-2">
                <span class="px-2 py-0.5 rounded-full text-[10px] font-mono bg-emerald-500/20 text-emerald-300">Total: 34 ms</span>
                <span class="w-2.5 h-2.5 rounded-full bg-emerald-400 shadow-[0_0_8px_#34d399]"></span>
              </div>
            </div>

          </div>

          <!-- Painel de Inspeção do Grafo -->
          <div id="graph-node-detail-panel" class="p-3.5 border-t border-white/10 bg-white/[0.02] text-xs font-sans text-slate-300 flex items-center justify-between">
            <div class="flex items-center gap-2">
              <i data-lucide="info" class="w-4 h-4 text-cyan-400 flex-shrink-0"></i>
              <span id="graph-detail-text">Clique em qualquer nó do grafo para auditar os parâmetros técnicos e o tratamento LGPD.</span>
            </div>
            <span class="text-cyan-400 font-mono text-[10px] whitespace-nowrap hidden sm:inline">BORDA ATIVA</span>
          </div>

        </div>

      </div>
    </section>

    <!-- =======================================================================
         SEÇÃO DE BLINDAGEM FIDUCIÁRIA & PROPRIEDADE INTELECTUAL (LGPD)
         ======================================================================= -->
    <section id="sec-blindagem" class="space-y-8 pt-4 scroll-reveal">
      <div class="text-center max-w-2xl mx-auto space-y-2">
        <div class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-cyan-500/10 border border-cyan-500/25 text-[11px] text-cyan-300 font-sans">
          <i data-lucide="shield" class="w-3.5 h-3.5"></i>
          <span>Privacidade Nativa Conforme Lei 13.709/2018</span>
        </div>
        <h2 class="text-2xl sm:text-3xl font-bold text-white font-display-title">
          Pilares de Blindagem Fiduciária & LGPD da AURA
        </h2>
        <p class="text-xs sm:text-sm text-slate-400 font-sans">
          Projetada para que dados estratégicos de estoque, vendas e clientes permaneçam sob controle soberano do proprietário da empresa.
        </p>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 font-sans">
        
        <div class="glass-panel p-5 rounded-2xl border border-white/10 space-y-3">
          <div class="w-10 h-10 rounded-xl bg-cyan-500/15 text-cyan-400 flex items-center justify-center">
            <i data-lucide="shield" class="w-5 h-5"></i>
          </div>
          <h3 class="font-bold text-white text-sm">Escudo Cognitivo AURA Guard™</h3>
          <p class="text-xs text-slate-400 leading-relaxed">
            Sanitização e desintegração instantânea de qualquer dado pessoal (PII) ou fiscal identificável antes de qualquer processamento analítico, em conformidade com a LGPD.
          </p>
        </div>

        <div class="glass-panel p-5 rounded-2xl border border-white/10 space-y-3">
          <div class="w-10 h-10 rounded-xl bg-emerald-500/15 text-emerald-400 flex items-center justify-center">
            <i data-lucide="server" class="w-5 h-5"></i>
          </div>
          <h3 class="font-bold text-white text-sm">Processamento Neural de Borda</h3>
          <p class="text-xs text-slate-400 leading-relaxed">
            Arquitetura soberana que opera no próprio servidor do estabelecimento ou infraestrutura privada, garantindo sub-100ms sem dependência de nuvem pública.
          </p>
        </div>

        <div class="glass-panel p-5 rounded-2xl border border-white/10 space-y-3">
          <div class="w-10 h-10 rounded-xl bg-purple-500/15 text-purple-400 flex items-center justify-center">
            <i data-lucide="calculator" class="w-5 h-5"></i>
          </div>
          <h3 class="font-bold text-white text-sm">Motor Matemático Fiduciário</h3>
          <p class="text-xs text-slate-400 leading-relaxed">
            Cálculo estrito das tolerâncias regulamentares (Portaria 26 da ANP ±0.60%, regras de NFC-e e SAT) e batimento de caixa centavo a centavo. Zero alucinação em números contábeis.
          </p>
        </div>

        <div class="glass-panel p-5 rounded-2xl border border-white/10 space-y-3">
          <div class="w-10 h-10 rounded-xl bg-amber-500/15 text-amber-400 flex items-center justify-center">
            <i data-lucide="zap" class="w-5 h-5"></i>
          </div>
          <h3 class="font-bold text-white text-sm">Resolução Operacional em 1-Toque</h3>
          <p class="text-xs text-slate-400 leading-relaxed">
            Transforma diagnósticos da operação em ações executivas práticas imediatas, prevenindo rupturas de estoque e quebras antes da abertura do turno.
          </p>
        </div>

      </div>
    </section>

    <!-- =======================================================================
         PAINEL & MATRIZ DE DIFERENCIAÇÃO OPERACIONAL REFORÇADO (ONDE ESTÁ O VALOR REAL)
         ======================================================================= -->
    <section id="sec-diferenciacao" class="glass-panel p-6 sm:p-8 rounded-3xl border border-white/10 space-y-8 scroll-reveal">
      
      <!-- Cabeçalho do Painel Operacional -->
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 text-[10px] font-mono uppercase tracking-wider mb-2">
            O Valor Real do Produto está na Linha de Frente da Operação
          </div>
          <h3 class="text-xl sm:text-2xl font-bold text-white font-display-title">Matriz de Diferenciação Operacional & ROI</h3>
          <p class="text-xs text-slate-400 font-sans max-w-2xl mt-1">
            Enquanto ERPs convencionais são sistemas passivos que registram prejuízos ocorridos semanas atrás, e dashboards de BI apenas desenham gráficos sem ação, a AURA atua proativamente no presente — estancando quebras de caixa, prevenindo desvios de estoque e agilizando decisões em sub-100ms.
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
            <span class="text-[10px] font-mono text-purple-400 uppercase">Continuidade de Negócio</span>
            <i data-lucide="trending-down" class="w-4 h-4 text-purple-400"></i>
          </div>
          <div class="text-base font-extrabold text-white">Prevenção Preditiva (Run-Out)</div>
          <p class="text-xs text-slate-400 leading-relaxed">
            Cálculo dinâmico da curva horária de vazão por produto de alto giro. Dispara ordem de reposição antes de faltar produto ao cliente.
          </p>
          <div class="text-[10px] text-purple-300 font-semibold pt-1">✓ Ruptura zero com alerta antecipado em 48h</div>
        </div>

        <div class="roi-card p-4 rounded-2xl bg-slate-900/90 border border-amber-500/30 space-y-2">
          <div class="flex items-center justify-between">
            <span class="text-[10px] font-mono text-amber-400 uppercase">Produtividade Gerencial</span>
            <i data-lucide="clock" class="w-4 h-4 text-amber-400"></i>
          </div>
          <div class="text-base font-extrabold text-white">De 3 Horas para 10 Segundos</div>
          <p class="text-xs text-slate-400 leading-relaxed">
            Elimina o preenchimento manual de planilhas e conferência de filipetas. Entrega DecisionCards prontos com ação em 1-toque.
          </p>
          <div class="text-[10px] text-amber-300 font-semibold pt-1">✓ Mais de 60 horas/mês economizadas por gestor</div>
        </div>

      </div>

      <!-- Tabela Comparativa Tripla Expandida -->
      <div class="overflow-x-auto font-sans text-xs">
        <table class="w-full text-left border-collapse">
          <thead>
            <tr class="border-b border-white/10 text-slate-400">
              <th class="py-3 px-4 font-semibold w-1/4">Dimensão Operacional</th>
              <th class="py-3 px-4 font-semibold text-rose-300/80 w-1/4">Modelo Tradicional (Planilhas & ERPs Legados)</th>
              <th class="py-3 px-4 font-semibold text-amber-300/80 w-1/4">Dashboards de BI Passivos (Tableau, PowerBI)</th>
              <th class="py-3 px-4 font-semibold text-cyan-300 bg-white/[0.02] rounded-t-xl w-1/4">Plataforma AURA (Inteligência Ativa)</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-white/5">
            <tr>
              <td class="py-3.5 px-4 font-semibold text-slate-200">Auditoria de Fechamento de Turno & Caixa</td>
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
              <td class="py-3.5 px-4 font-semibold text-slate-200">Monitoramento de Estoque & Prevenção de Desvios</td>
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
                <div class="font-medium text-emerald-200">Cruzamento contínuo entre saídas fiscais e estoque físico em tempo real; alerta imediato de desvio.</div>
              </td>
            </tr>
            <tr>
              <td class="py-3.5 px-4 font-semibold text-slate-200">Prevenção de Falta de Mercadorias (Ruptura)</td>
              <td class="py-3.5 px-4 text-slate-400">
                <span class="inline-flex items-center gap-1 text-[11px] font-semibold text-rose-400 mb-1">✕ Perda de Clientes</span>
                <div>Aviso tardio quando o produto já acabou na gôndola/tanque e vendas foram perdidas.</div>
              </td>
              <td class="py-3.5 px-4 text-slate-400">
                <span class="inline-flex items-center gap-1 text-[11px] font-semibold text-amber-400 mb-1">⚠ Média Histórica</span>
                <div>Médias históricas gerais que ignoram sazonalidade do dia ou horário de pico da loja.</div>
              </td>
              <td class="py-3.5 px-4 bg-emerald-950/20 border-l border-r border-emerald-500/30">
                <span class="inline-flex items-center gap-1 text-[11px] font-bold text-emerald-400 mb-1">✓ Previsão Run-Out</span>
                <div class="font-medium text-emerald-200">Cálculo preditivo de run-out por hora com sugestão de pedido protocolado em 1 clique.</div>
              </td>
            </tr>
            <tr>
              <td class="py-3.5 px-4 font-semibold text-slate-200">Conformidade Fiscal & Riscos Regulatórios (ANP / SAT / NFC-e)</td>
              <td class="py-3.5 px-4 text-slate-400">
                <span class="inline-flex items-center gap-1 text-[11px] font-semibold text-rose-400 mb-1">✕ Risco de Autuação</span>
                <div>Escrituração manual sujeita a erros de digitação, multas fiscais surpresa e LMC incorreto.</div>
              </td>
              <td class="py-3.5 px-4 text-slate-400">
                <span class="inline-flex items-center gap-1 text-[11px] font-semibold text-amber-400 mb-1">⚠ Sem Auditoria Fiscal</span>
                <div>Não audita tolerâncias regulamentares volumétricas ou regras tributárias estritas.</div>
              </td>
              <td class="py-3.5 px-4 bg-emerald-950/20 border-l border-r border-emerald-500/30">
                <span class="inline-flex items-center gap-1 text-[11px] font-bold text-emerald-400 mb-1">✓ Fiduciário Determinístico</span>
                <div class="font-medium text-emerald-200">Auditoria matemática determinística (tolerância ±0.60%), validação NFC-e/SAT e extrato oficial.</div>
              </td>
            </tr>
            <tr>
              <td class="py-3.5 px-4 font-semibold text-slate-200">Proteção de Dados & LGPD (Lei 13.709/2018)</td>
              <td class="py-3.5 px-4 text-slate-400">
                <span class="inline-flex items-center gap-1 text-[11px] font-semibold text-rose-400 mb-1">✕ Vulnerabilidade Total</span>
                <div>Planilhas com CPFs e dados fiscais expostas em cópias locais sem qualquer controle de acesso.</div>
              </td>
              <td class="py-3.5 px-4 text-slate-400">
                <span class="inline-flex items-center gap-1 text-[11px] font-semibold text-amber-400 mb-1">⚠ Nuvem Desprotegida</span>
                <div>Exportação de arquivos CSV com dados pessoais desprotegidos para servidores em nuvem.</div>
              </td>
              <td class="py-3.5 px-4 bg-emerald-950/20 border-l border-r border-emerald-500/30">
                <span class="inline-flex items-center gap-1 text-[11px] font-bold text-cyan-400 mb-1">✓ Soberania de Borda</span>
                <div class="font-medium text-cyan-200">Escudo AURA Guard™: pulverização de PII na borda física e zero trânsito de dados pessoais externos.</div>
              </td>
            </tr>
            <tr>
              <td class="py-3.5 px-4 font-semibold text-slate-200">Tempo para Decisão Executiva</td>
              <td class="py-3.5 px-4 text-slate-400">
                <span class="inline-flex items-center gap-1 text-[11px] font-semibold text-rose-400 mb-1">✕ Horas em Planilhas</span>
                <div>Reuniões morosas com relatórios estáticos de papel sem apontar o que fazer.</div>
              </td>
              <td class="py-3.5 px-4 text-slate-400">
                <span class="inline-flex items-center gap-1 text-[11px] font-semibold text-amber-400 mb-1">⚠ Telas Complexas</span>
                <div>Telas complexas com dezenas de filtros que exigem analistas dedicados para interpretar.</div>
              </td>
              <td class="py-3.5 px-4 bg-emerald-950/20 border-l border-r border-emerald-500/30">
                <span class="inline-flex items-center gap-1 text-[11px] font-bold text-purple-400 mb-1">✓ 1-Toque Resolutivo</span>
                <div class="font-medium text-purple-200">DecisionCard com diagnósticos autoexplicativos e disparo resolutivo em 1-toque em menos de 10 segundos.</div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- =======================================================================
         FAQ EXECUTIVO
         ======================================================================= -->
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
            Não. A AURA atua como uma supervisora executiva de inteligência e auditoria contínua que se conecta ao seu ERP e automação existente, potencializando a velocidade de tomada de decisão em postos, lojas, bares ou padarias.
          </p>
        </div>

        <div class="glass-panel p-5 rounded-2xl border border-white/10 space-y-2">
          <h4 class="font-bold text-slate-100 flex items-center gap-2">
            <i data-lucide="lock" class="w-4 h-4 text-emerald-400"></i>
            Meus dados de faturamento e clientes saem da minha empresa?
          </h4>
          <p class="text-slate-400 leading-relaxed">
            Absolutamente não. Em total conformidade com a LGPD (Lei 13.709/2018), os identificadores sensíveis são pulverizados na borda pelo Escudo AURA Guard™ e o processamento neural opera de forma soberana na sua rede privada.
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

        <div class="glass-panel p-5 rounded-2xl border border-white/10 space-y-2">
          <h4 class="font-bold text-slate-100 flex items-center gap-2">
            <i data-lucide="check" class="w-4 h-4 text-amber-400"></i>
            Como a AURA previne alucinações matemáticas?
          </h4>
          <p class="text-slate-400 leading-relaxed">
            A AURA utiliza um motor fiduciário determinístico para cálculos de volume, regras fiscais e conciliação de caixa. Toda conta é auditada matematicamente antes de qualquer resposta ser gerada.
          </p>
        </div>

      </div>
    </section>

    <!-- =======================================================================
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
        <button onclick="window.auraTour.restartTour(); window.auraTour.scrollToSection('sec-tour');" class="w-full sm:w-auto px-5 py-3 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-300 hover:text-white border border-white/10 text-sm font-semibold transition-colors flex items-center justify-center gap-2 shadow-sm">
          <i data-lucide="rotate-ccw" class="w-4 h-4"></i>
          <span>Rever Tour Guiado</span>
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
       MOTOR JAVASCRIPT DO TOUR GUIADO & SIMULAÇÃO DE PARTÍCULAS
       ========================================================================= -->
  <script>
    (function() {
      // Estado do Tour Guiado
      const tourState = {
        currentStep: 1,
        totalSteps: 4,
        isPlaying: false,
        durationPerStep: 6000,
        speedMultiplier: 1,
        stepStartTime: 0,
        animFrameId: null,
        soundEnabled: true,
        userInteracted: false,
        currentScenario: 'varejo'
      };

      // Inicializador do Web Audio API
      let audioCtx = null;
      function playTone(freq = 440, type = 'sine', duration = 0.15, gain = 0.08) {
        if (!tourState.soundEnabled || !tourState.userInteracted) return;
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

      // Função de Desintegração em Poeira (Etapa 2)
      function triggerDustDisintegration(playSfx = true) {
        tourState.userInteracted = true;
        dustTimeouts.forEach(t => clearTimeout(t));
        dustTimeouts = [];

        resetDustDisintegration();
        resizeDustCanvas();

        if (playSfx) playDustSound();

        const statusPill = document.getElementById('dust-status-pill');
        if (statusPill) {
          statusPill.textContent = 'DESINTEGRANDO PII...';
          statusPill.className = 'px-2 py-0.5 rounded text-[10px] font-mono bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 animate-pulse';
        }

        for (let i = 1; i <= 5; i++) {
          const rawVal = document.getElementById(`pii-val-${i}`);
          if (rawVal) {
            const t1 = setTimeout(() => {
              rawVal.classList.add('disintegrating');
              spawnParticlesAtElement(rawVal, 60);
            }, (i - 1) * 80);
            dustTimeouts.push(t1);
          }
        }

        const t2 = setTimeout(() => {
          for (let i = 1; i <= 5; i++) {
            const rawVal = document.getElementById(`pii-val-${i}`);
            const redVal = document.getElementById(`pii-token-${i}`);
            if (rawVal) rawVal.classList.add('hidden');
            if (redVal) {
              redVal.classList.remove('hidden');
              redVal.classList.add('animate-fade-in');
            }
          }
          if (statusPill) {
            statusPill.textContent = '100% SANITIZADO (LGPD)';
            statusPill.className = 'px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-500/20 text-emerald-300 border border-emerald-500/40';
          }
        }, 550);
        dustTimeouts.push(t2);
      }

      function resetDustDisintegration() {
        const statusPill = document.getElementById('dust-status-pill');
        if (statusPill) {
          statusPill.textContent = 'ESCUDO ATIVO';
          statusPill.className = 'px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-500/10 text-emerald-300 border border-emerald-500/20';
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
      // NAVEGAÇÃO ENTRE AS 4 ETAPAS DO TOUR
      // =========================================================================
      function goToStep(stepNumber, shouldPause = false, silent = false) {
        if (stepNumber < 1 || stepNumber > tourState.totalSteps) return;
        tourState.currentStep = stepNumber;
        tourState.stepStartTime = performance.now();

        if (shouldPause) {
          pauseTour();
        }

        if (!silent) {
          tourState.userInteracted = true;
          playChime();
        }

        // 1. Atualiza pílulas seletoras (tabs)
        document.querySelectorAll('.step-pill').forEach(pill => {
          const target = parseInt(pill.getAttribute('data-step-target'), 10);
          pill.classList.remove('active');
          if (target === stepNumber) {
            pill.classList.add('active');
          } else if (target < stepNumber) {
            pill.classList.add('completed');
          } else {
            pill.classList.remove('completed');
          }
        });

        // 2. Alterna painéis da narrativa (esquerda)
        for (let s = 1; s <= 4; s++) {
          const nar = document.getElementById(`narrative-step-${s}`);
          if (nar) {
            if (s === stepNumber) {
              nar.classList.remove('hidden-pane');
              nar.classList.add('active-pane');
            } else {
              nar.classList.remove('active-pane');
              nar.classList.add('hidden-pane');
            }
          }
        }

        // 3. Alterna palcos visuais (direita)
        const viewportTitle = document.getElementById('stage-viewport-title');
        const viewTitles = [
          'aura://executivo/pergunta-entrada',
          'aura://privacidade/escudo-desintegracao',
          'aura://motor/pipeline-sub-100ms',
          'aura://decisao/decision-card-executivo'
        ];
        if (viewportTitle && viewTitles[stepNumber - 1]) {
          viewportTitle.textContent = viewTitles[stepNumber - 1];
        }

        for (let s = 1; s <= 4; s++) {
          const vis = document.getElementById(`visual-stage-${s}`);
          if (vis) {
            if (s === stepNumber) {
              vis.classList.remove('hidden-pane');
              vis.classList.add('active-pane');
            } else {
              vis.classList.remove('active-pane');
              vis.classList.add('hidden-pane');
            }
          }
        }

        // 4. Micro-interações automáticas específicas
        if (stepNumber === 1) {
          // Reset
        } else if (stepNumber === 2) {
          resetDustDisintegration();
          const t = setTimeout(() => {
            triggerDustDisintegration(false);
          }, 350);
          dustTimeouts.push(t);
        } else if (stepNumber === 3) {
          simulatePipelinePulse(false);
        } else if (stepNumber === 4) {
          const toast = document.getElementById('action-feedback-toast');
          if (toast) toast.classList.add('hidden');
          toggleStep4Tab('decisioncard');
        }

        updateProgressBar(0);
      }

      function nextStep() {
        const next = tourState.currentStep >= tourState.totalSteps ? 1 : tourState.currentStep + 1;
        goToStep(next);
      }

      function prevStep() {
        const prev = tourState.currentStep <= 1 ? tourState.totalSteps : tourState.currentStep - 1;
        goToStep(prev);
      }

      // =========================================================================
      // REPRODUÇÃO AUTOMÁTICA & PROGRESS BAR DO TOUR
      // =========================================================================
      function startTour() {
        tourState.userInteracted = true;
        tourState.isPlaying = true;
        tourState.stepStartTime = performance.now();
        const playBtnLabel = document.getElementById('label-play-pause');
        const playBtnIcon = document.getElementById('icon-play-pause');
        const statusText = document.getElementById('tour-status-text');

        if (playBtnLabel) playBtnLabel.textContent = 'Pausar Tour';
        if (playBtnIcon) {
          playBtnIcon.setAttribute('data-lucide', 'pause');
          if (window.lucide) window.lucide.createIcons();
        }
        if (statusText) statusText.textContent = 'Reprodução Automática';

        if (tourState.animFrameId) {
          cancelAnimationFrame(tourState.animFrameId);
        }
        runTourLoop();
      }

      function pauseTour() {
        tourState.isPlaying = false;
        if (tourState.animFrameId) {
          cancelAnimationFrame(tourState.animFrameId);
          tourState.animFrameId = null;
        }
        const playBtnLabel = document.getElementById('label-play-pause');
        const playBtnIcon = document.getElementById('icon-play-pause');
        const statusText = document.getElementById('tour-status-text');

        if (playBtnLabel) playBtnLabel.textContent = 'Reproduzir Tour Automático';
        if (playBtnIcon) {
          playBtnIcon.setAttribute('data-lucide', 'play');
          if (window.lucide) window.lucide.createIcons();
        }
        if (statusText) statusText.textContent = 'Pausado (Interativo)';
      }

      function togglePlayPause() {
        tourState.userInteracted = true;
        if (tourState.isPlaying) {
          pauseTour();
        } else {
          startTour();
        }
      }

      function updateProgressBar(percentage) {
        const bar = document.getElementById('tour-progress-bar');
        if (bar) {
          bar.style.width = `${Math.min(100, Math.max(0, percentage))}%`;
        }
      }

      function runTourLoop() {
        if (!tourState.isPlaying) return;

        const duration = tourState.durationPerStep / tourState.speedMultiplier;
        const elapsed = performance.now() - tourState.stepStartTime;
        const progress = (elapsed / duration) * 100;

        updateProgressBar(progress);

        if (elapsed >= duration) {
          nextStep();
        }

        tourState.animFrameId = requestAnimationFrame(runTourLoop);
      }

      // =========================================================================
      // INTERAÇÕES MULTISSETORIAIS DA ETAPA 1
      // =========================================================================
      const sampleQueries = [
        '"Qual a previsão de esgotamento do Tanque 02 de Gasolina Comum e tivemos furo no fechamento do último turno?"',
        '"Tivemos quebra no fechamento do caixa da padaria e qual o risco de ruptura de café e farinha hoje?"',
        '"Houve divergência entre emissões NFC-e e recebimentos em dinheiro/PIX na loja de conveniência?"',
        '"O balanço de encerramento do bar fechou centavo a centavo sem desvio de bebidas no turno?"'
      ];
      let sampleIndex = 0;

      function simulateStep1Question() {
        tourState.userInteracted = true;
        playTone(600, 'sine', 0.1, 0.05);
        sampleIndex = (sampleIndex + 1) % sampleQueries.length;
        const textEl = document.getElementById('step1-typed-text');
        if (textEl) {
          textEl.style.opacity = '0.3';
          setTimeout(() => {
            textEl.textContent = sampleQueries[sampleIndex];
            textEl.style.opacity = '1';
          }, 150);
        }
      }

      function simulatePipelinePulse(playSfx = true) {
        if (playSfx) {
          tourState.userInteracted = true;
          playTone(550, 'triangle', 0.12, 0.05);
        }
        const inspector = document.getElementById('pipeline-inspector-text');
        if (inspector) {
          inspector.textContent = 'Pulso executado: 4 ferramentas sincronizadas em 38.4ms com telemetria direta.';
        }

        const nodes = [1, 2, 3, 4];
        nodes.forEach((n, idx) => {
          setTimeout(() => {
            const el = document.getElementById(`pipe-node-${n}`);
            if (el) {
              el.classList.add('pulse-highlight');
              if (playSfx) playTone(440 + n * 80, 'sine', 0.08, 0.03);
              setTimeout(() => el.classList.remove('pulse-highlight'), 450);
            }
          }, idx * 120);
        });
      }

      function inspectNode(nodeType) {
        tourState.userInteracted = true;
        playTone(700, 'sine', 0.1, 0.05);
        const inspector = document.getElementById('pipeline-inspector-text');
        if (!inspector) return;

        const msgs = {
          pista: 'Sondas de Tanque: 10/10 Online | Concentrador CBC04: 16 Bicos Ativos | Resposta em 12ms',
          anp: 'Portaria 26 ANP: Variação volumétrica calculada em +0.28% (Conforme limite de ±0.60%) | 18ms',
          caixa: 'Turno 3: Faturamento R$ 42.850,00 vs Litragem Física 100% conciliada (R$ 0,00 diferença) | 24ms',
          runout: 'Tanque 02: Vazão média 245 L/h | Ponto crítico em 18h42m | Recomendado 30.000 L | 35ms'
        };
        inspector.textContent = msgs[nodeType] || 'Parâmetro auditado com precisão fiduciária.';
      }

      function simulateActionClick(actionType) {
        tourState.userInteracted = true;
        playActionSound();
        const toast = document.getElementById('action-feedback-toast');
        const msg = document.getElementById('action-feedback-message');
        if (!toast || !msg) return;

        if (actionType === 'pedido') {
          msg.textContent = '✓ Pedido de 30.000 L de Gasolina Comum protocolado no canal executivo da distribuidora em 1 toque!';
        } else if (actionType === 'lmc') {
          msg.textContent = '✓ Relatório oficial LMC gerado em PDF com certificação de conformidade ANP (±0.28%).';
        } else {
          msg.textContent = '✓ Operação homologada com registro fiduciário na empresa.';
        }

        toast.classList.remove('hidden');
        toast.classList.add('animate-fade-in');
      }

      function toggleStep4Tab(tabName) {
        tourState.userInteracted = true;
        const btnDc = document.getElementById('tab-step4-decisioncard');
        const btnComp = document.getElementById('tab-step4-companion');
        const viewDc = document.getElementById('view-step4-decisioncard');
        const viewComp = document.getElementById('view-step4-companion');

        if (tabName === 'companion') {
          if (btnDc) {
            btnDc.className = 'px-3 py-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/5 border border-transparent font-semibold transition-all';
          }
          if (btnComp) {
            btnComp.className = 'px-3 py-1.5 rounded-lg bg-purple-500/20 text-purple-300 border border-purple-500/40 font-semibold transition-all flex items-center gap-1.5';
          }
          if (viewDc) viewDc.classList.add('hidden');
          if (viewComp) {
            viewComp.classList.remove('hidden');
            viewComp.classList.add('animate-fade-in');
          }
        } else {
          if (btnDc) {
            btnDc.className = 'px-3 py-1.5 rounded-lg bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 font-semibold transition-all';
          }
          if (btnComp) {
            btnComp.className = 'px-3 py-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/5 border border-transparent font-semibold transition-all flex items-center gap-1.5';
          }
          if (viewDc) {
            viewDc.classList.remove('hidden');
            viewDc.classList.add('animate-fade-in');
          }
          if (viewComp) viewComp.classList.add('hidden');
        }
      }

      // =========================================================================
      // DADOS & MÉTODOS DA NOVA SEÇÃO: CHAT DA AURA & GRAFO CORE LGPD
      // =========================================================================
      const chatScenarios = {
        varejo: {
          userLabel: 'Gestor Operacional (Padaria & Bar)',
          time: '17:48',
          query: 'Qual o índice de quebra no fechamento do caixa da manhã e temos risco de ruptura de insumos críticos?',
          response: 'Turno da manhã auditado em 31ms. Não houve divergência de caixa (R$ 0,00). No entanto, o insumo café especial em grãos atingiu 14% do ponto de segurança, com previsão de esgotamento hoje às 20h30.',
          dcTitle: 'Auditoria de PDV & Estoque Crítico',
          badgeText: 'REPOSIÇÃO SUGERIDA',
          badgeClass: 'px-2 py-0.5 rounded text-[9px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30',
          metricLabel1: 'Auditoria de Caixa',
          metricVal1: 'R$ 0,00 Furo',
          metricVal1Class: 'font-bold text-emerald-400 text-xs',
          metricLabel2: 'Insumo em Risco',
          metricVal2: 'Café Grãos (14%)',
          metricVal2Class: 'font-bold text-amber-300 text-xs',
          btnActionText: 'Emitir Ordem de Reposição',
          toastMsg: '✓ Ordem de reposição emitida no canal de suprimentos em 1 clique!'
        },
        posto: {
          userLabel: 'Gerente Geral (Posto #042)',
          time: '17:50',
          query: 'Qual a previsão de esgotamento do Tanque 02 de Gasolina Comum e tivemos furo no fechamento do último turno?',
          response: 'Análise de telemetria concluída em 38ms. O Tanque 02 possui 4.820 L (16%) com autonomia estimada em 18.4 horas. Fechamento do Turno 3 100% conciliado sem nenhuma divergência fiscal.',
          dcTitle: 'Diagnóstico Operacional Consolidado',
          badgeText: 'PEDIDO RECOMENDADO',
          badgeClass: 'px-2 py-0.5 rounded text-[9px] font-bold bg-rose-500/20 text-rose-300 border border-rose-500/30',
          metricLabel1: 'Autonomia Tanque 02',
          metricVal1: '18.4 Horas',
          metricVal1Class: 'font-bold text-amber-300 text-xs',
          metricLabel2: 'Auditoria de Caixa',
          metricVal2: 'R$ 0,00 Furo',
          metricVal2Class: 'font-bold text-emerald-400 text-xs',
          btnActionText: 'Emitir Pedido (30.000 L)',
          toastMsg: '✓ Pedido de 30.000 L protocolado na distribuidora em 1 clique!'
        },
        loja: {
          userLabel: 'Supervisor Regional (Loja & Varejo #12)',
          time: '17:52',
          query: 'Houve discrepância entre cupons NFC-e emitidos e recebimentos em dinheiro e PIX hoje?',
          response: 'Cruzamento fiduciário executado em 29ms. Foram emitidas 412 notas NFC-e totalizando R$ 64.390,00. Todos os pagamentos recebidos conferem centavo a centavo com os comprovantes bancários e gavetas.',
          dcTitle: 'Reconciliação Fiduciária Multiloja',
          badgeText: '100% RECONCILIADO',
          badgeClass: 'px-2 py-0.5 rounded text-[9px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30',
          metricLabel1: 'Vendas Faturadas (NFC-e)',
          metricVal1: 'R$ 64.390,00',
          metricVal1Class: 'font-bold text-white text-xs',
          metricLabel2: 'Discrepância Apurada',
          metricVal2: 'R$ 0,00 (Exato)',
          metricVal2Class: 'font-bold text-emerald-400 text-xs',
          btnActionText: 'Exportar Extrato Consolidado',
          toastMsg: '✓ Extrato executivo consolidado gerado com assinatura digital!'
        },
        fiscal: {
          userLabel: 'Diretor de Operações (Compliance Fiscal)',
          time: '17:55',
          query: 'Existe algum risco de autuação fiscal ou desenquadramento regulatório nas operações de hoje?',
          response: 'Auditoria preventiva realizada em 24ms. Zero inconformidades detectadas. Todas as medições e notas fiscais encontram-se dentro dos limites legais e regulatórios estritos.',
          dcTitle: 'Auditoria Preventiva Contínua',
          badgeText: 'ZERO RISCO FISCAL',
          badgeClass: 'px-2 py-0.5 rounded text-[9px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30',
          metricLabel1: 'Conformidade Legal',
          metricVal1: '100% Homologado',
          metricVal1Class: 'font-bold text-emerald-400 text-xs',
          metricLabel2: 'Vazamento Externo',
          metricVal2: '0 Bytes (LGPD)',
          metricVal2Class: 'font-bold text-cyan-300 text-xs',
          btnActionText: 'Emitir Dossiê de Governança',
          toastMsg: '✓ Dossiê executivo de governança emitido para a diretoria!'
        }
      };

      function selectChatScenario(scenarioKey) {
        tourState.userInteracted = true;
        const data = chatScenarios[scenarioKey];
        if (!data) return;
        tourState.currentScenario = scenarioKey;
        playTone(580, 'sine', 0.1, 0.05);

        // Atualiza botões de cenário
        const keys = ['varejo', 'posto', 'loja', 'fiscal'];
        keys.forEach(k => {
          const btn = document.getElementById(`scenario-btn-${k}`);
          if (btn) {
            if (k === scenarioKey) {
              btn.className = 'px-2.5 py-1.5 rounded-lg bg-cyan-500/20 text-cyan-200 border border-cyan-500/40 font-semibold truncate transition-all text-left flex items-center gap-1.5';
            } else {
              btn.className = 'px-2.5 py-1.5 rounded-lg bg-slate-900/80 text-slate-300 hover:text-white border border-white/10 truncate transition-all text-left flex items-center gap-1.5';
            }
          }
        });

        // Atualiza campos do chat
        const userLabel = document.getElementById('chat-user-label');
        const timestamp = document.getElementById('chat-timestamp-label');
        const queryText = document.getElementById('chat-user-query-text');
        const respText = document.getElementById('chat-response-narrative');
        const dcTitle = document.getElementById('mini-dc-title');
        const dcBadge = document.getElementById('mini-dc-badge');
        const mLabel1 = document.getElementById('mini-metric-label-1');
        const mVal1 = document.getElementById('mini-metric-val-1');
        const mLabel2 = document.getElementById('mini-metric-label-2');
        const mVal2 = document.getElementById('mini-metric-val-2');
        const btnAction = document.getElementById('mini-dc-action-text');
        const chatInput = document.getElementById('chat-interactive-input');

        if (userLabel) userLabel.textContent = data.userLabel;
        if (timestamp) timestamp.textContent = data.time;
        if (queryText) queryText.textContent = `"${data.query}"`;
        if (respText) respText.textContent = data.response;
        if (dcTitle) dcTitle.textContent = data.dcTitle;
        if (dcBadge) {
          dcBadge.textContent = data.badgeText;
          dcBadge.className = data.badgeClass;
        }
        if (mLabel1) mLabel1.textContent = data.metricLabel1;
        if (mVal1) {
          mVal1.textContent = data.metricVal1;
          mVal1.className = data.metricVal1Class;
        }
        if (mLabel2) mLabel2.textContent = data.metricLabel2;
        if (mVal2) {
          mVal2.textContent = data.metricVal2;
          mVal2.className = data.metricVal2Class;
        }
        if (btnAction) btnAction.textContent = data.btnActionText;
        if (chatInput) chatInput.value = data.query;

        // Executa a cascata no grafo ao lado
        runGraphPulseAnimation();
      }

      function simulateChatSubmit() {
        tourState.userInteracted = true;
        const chatInput = document.getElementById('chat-interactive-input');
        const userQueryText = document.getElementById('chat-user-query-text');
        if (chatInput && userQueryText) {
          const val = chatInput.value.trim();
          if (val) {
            userQueryText.textContent = `"${val}"`;
          }
        }
        playTone(620, 'sine', 0.12, 0.05);
        runGraphPulseAnimation();
      }

      function simulateChatActionClick() {
        tourState.userInteracted = true;
        playActionSound();
        const data = chatScenarios[tourState.currentScenario] || chatScenarios.varejo;
        const toast = document.getElementById('mini-chat-action-toast');
        const msg = document.getElementById('mini-chat-toast-message');
        if (toast && msg) {
          msg.textContent = data.toastMsg;
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
            const el = document.getElementById(`graph-node-${nodeId}`);
            if (el) {
              el.classList.add(nodeId === 'decisao' ? 'success-glow' : 'active-glow');
              playTone(400 + idx * 90, 'sine', 0.07, 0.03);
              setTimeout(() => {
                el.classList.remove('active-glow', 'success-glow');
              }, 450);
            }
          }, idx * 110);
        });

        const panel = document.getElementById('graph-detail-text');
        if (panel) {
          panel.textContent = 'Transmissão completa: Prompt higienizado na LGPD, auditado na borda e entregue em 34ms.';
        }
      }

      function inspectGraphNode(nodeKey) {
        tourState.userInteracted = true;
        playTone(660, 'sine', 0.1, 0.05);

        const nodeKeys = ['prompt', 'lgpd', 'motor', 'regras', 'decisao'];
        nodeKeys.forEach(k => {
          const el = document.getElementById(`graph-node-${k}`);
          if (el) {
            if (k === nodeKey) {
              el.classList.add('active-selected');
            } else {
              el.classList.remove('active-selected');
            }
          }
        });

        const panel = document.getElementById('graph-detail-text');
        if (!panel) return;

        const descriptions = {
          prompt: '1. Prompt em Linguagem Natural: O gestor envia consultas operacionais em português corrente (sem SQL ou planilhas). Multicanal: chat, tablet ou voz.',
          lgpd: '2. Escudo LGPD (Lei 13.709/2018): CPFs, CNPJs e credenciais são desintegrados na borda física. Zero trânsito de dados pessoais sensíveis para a nuvem pública.',
          motor: '3. Motor Soberano de Borda: Processamento determinístico em sub-100ms dentro da rede privada da empresa. Sem latência de internet e sem risco de vazamento.',
          regras: '4. Regras & Auditoria Fiduciária: Batimento matemático de tolerâncias fiscais (Portaria 26 ANP, SAT, NFC-e) e conciliação centavo a centavo sem alucinações.',
          decisao: '5. DecisionCard™ em 1-Toque: Resultado executivo consolidado com recomendação acionável e botões de disparo direto (reposição, aprovação ou extrato).'
        };

        panel.textContent = descriptions[nodeKey] || 'Parâmetro auditado pelo motor de borda.';
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

        // Atualiza dot ativo no menu lateral com cálculo preciso por getBoundingClientRect
        const sections = ['top', 'sec-tour', 'sec-chat-graph', 'sec-blindagem', 'sec-diferenciacao', 'sec-faq'];
        for (let i = sections.length - 1; i >= 0; i--) {
          const secId = sections[i];
          if (secId === 'top') {
            if (winScroll < 200) {
              document.querySelectorAll('.scroll-nav-dot').forEach(dot => {
                if (dot.getAttribute('data-section') === 'top') {
                  dot.classList.add('active');
                } else {
                  dot.classList.remove('active');
                }
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
                if (dot.getAttribute('data-section') === secId) {
                  dot.classList.add('active');
                } else {
                  dot.classList.remove('active');
                }
              });
              break;
            }
          }
        }
      }

      // =========================================================================
      // CONTROLES DE INTERFACE & EVENTOS GLOBAIS
      // =========================================================================
      document.addEventListener('DOMContentLoaded', function() {
        if (window.lucide) window.lucide.createIcons();

        // Botões do Player
        const btnPlay = document.getElementById('btn-tour-play-pause');
        if (btnPlay) btnPlay.addEventListener('click', togglePlayPause);

        const btnPrev = document.getElementById('btn-tour-prev');
        if (btnPrev) btnPrev.addEventListener('click', () => { pauseTour(); prevStep(); });

        const btnNext = document.getElementById('btn-tour-next');
        if (btnNext) btnNext.addEventListener('click', () => { pauseTour(); nextStep(); });

        const btnReplay = document.getElementById('btn-tour-replay');
        if (btnReplay) btnReplay.addEventListener('click', () => { goToStep(1); startTour(); });

        // Velocidades
        const btn1x = document.getElementById('btn-speed-1x');
        const btn2x = document.getElementById('btn-speed-2x');
        if (btn1x && btn2x) {
          btn1x.addEventListener('click', () => {
            tourState.userInteracted = true;
            tourState.speedMultiplier = 1;
            btn1x.className = 'px-2.5 py-1 rounded-md bg-slate-800 text-white font-semibold';
            btn2x.className = 'px-2.5 py-1 rounded-md text-slate-400 hover:text-white';
          });
          btn2x.addEventListener('click', () => {
            tourState.userInteracted = true;
            tourState.speedMultiplier = 2;
            btn2x.className = 'px-2.5 py-1 rounded-md bg-slate-800 text-white font-semibold';
            btn1x.className = 'px-2.5 py-1 rounded-md text-slate-400 hover:text-white';
          });
        }

        // Toggle SFX
        const btnSfx = document.getElementById('btn-toggle-sfx-showcase');
        const iconSfx = document.getElementById('icon-sfx');
        if (btnSfx) {
          btnSfx.addEventListener('click', () => {
            tourState.userInteracted = true;
            tourState.soundEnabled = !tourState.soundEnabled;
            if (iconSfx) {
              iconSfx.setAttribute('data-lucide', tourState.soundEnabled ? 'volume-2' : 'volume-x');
              if (window.lucide) window.lucide.createIcons();
            }
          });
        }

        // Teclado
        window.addEventListener('keydown', (e) => {
          if (e.target && (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.isContentEditable)) {
            return;
          }
          if (e.key === ' ' || e.key === 'k') {
            e.preventDefault();
            togglePlayPause();
          } else if (e.key === 'ArrowRight') {
            pauseTour();
            nextStep();
          } else if (e.key === 'ArrowLeft') {
            pauseTour();
            prevStep();
          }
        });

        // Chat input enter key listener
        const chatInput = document.getElementById('chat-interactive-input');
        if (chatInput) {
          chatInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
              e.preventDefault();
              simulateChatSubmit();
            }
          });
        }

        // Scroll listener para barra de progresso
        window.addEventListener('scroll', updateScrollProgress, { passive: true });

        // IntersectionObserver para reveal suave de seções no scroll e animações dinâmicas
        let chatGraphAnimatedOnce = false;
        let diferenciacaoAnimatedOnce = false;

        if (typeof IntersectionObserver !== 'undefined') {
          const revealObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
              if (entry.isIntersecting) {
                entry.target.classList.add('scroll-reveal-visible');

                // Animação disparada organicamente pelo scroll no grafo
                if (entry.target.id === 'sec-chat-graph' && !chatGraphAnimatedOnce) {
                  chatGraphAnimatedOnce = true;
                  setTimeout(() => {
                    runGraphPulseAnimation();
                  }, 250);
                }

                // Efeito de onda nos 4 cards de ROI na rolagem
                if (entry.target.id === 'sec-diferenciacao' && !diferenciacaoAnimatedOnce) {
                  diferenciacaoAnimatedOnce = true;
                  const cards = entry.target.querySelectorAll('.roi-card');
                  cards.forEach((c, i) => {
                    setTimeout(() => {
                      c.classList.add('ring-1', 'ring-emerald-400/60');
                      setTimeout(() => c.classList.remove('ring-1', 'ring-emerald-400/60'), 700);
                    }, i * 140);
                  });
                }
              }
            });
          }, { threshold: 0.12 });

          document.querySelectorAll('.scroll-reveal').forEach(el => {
            revealObserver.observe(el);
          });
        } else {
          // Fallback imediato para navegadores legados
          document.querySelectorAll('.scroll-reveal').forEach(el => {
            el.classList.add('scroll-reveal-visible');
          });
        }

        // Inicializa silenciosamente na Etapa 1
        goToStep(1, false, true);
      });

      // API Pública do Tour AURA
      window.auraTour = {
        goToStep: (s) => goToStep(s, true),
        nextStep: () => { pauseTour(); nextStep(); },
        prevStep: () => { pauseTour(); prevStep(); },
        startTour,
        pauseTour,
        restartTour: () => { goToStep(1); startTour(); },
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
