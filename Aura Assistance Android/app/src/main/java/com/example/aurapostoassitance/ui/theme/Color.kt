package com.example.aurapostoassitance.ui.theme

import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color

// Paleta legada (mantida para compatibilidade com telas ainda nao migradas)
val Purple80 = Color(0xFFD0BCFF)
val PurpleGrey80 = Color(0xFFCCC2DC)
val Pink80 = Color(0xFFEFB8C8)
val Purple40 = Color(0xFF6650A4)
val PurpleGrey40 = Color(0xFF625B71)
val Pink40 = Color(0xFF7D5260)

// Acentos Aurora
val AuraEmerald = Color(0xFF10B981)
val AuraCyan = Color(0xFF22D3EE)
val AuraPurple = Color(0xFF8B5CF6)

// Obsidian: camadas de superficie AMOLED (do mais fundo ao mais elevado)
val ObsidianDeep = Color(0xFF030407)
val ObsidianBase = Color(0xFF07090E)
val ObsidianLow = Color(0xFF0C1018)
val ObsidianMid = Color(0xFF121722)
val ObsidianHigh = Color(0xFF1A2130)
val ObsidianBright = Color(0xFF232C3F)

// Compatibilidade: telas antigas usam estes nomes
val AuraDarkBackground = ObsidianBase
val AuraDarkSurface = ObsidianMid

// Texto
val TextPrimary = Color(0xFFF1F5F9)
val TextSecondary = Color(0xFF94A3B8)
val TextMuted = Color(0xFF64748B)

// Bordas suaves (vidro)
val OutlineSoft = Color(0x14FFFFFF)
val OutlineStrong = Color(0x29FFFFFF)
val GlassHighlight = Color(0x28FFFFFF)
val GlassBorderSoft = Color(0x18FFFFFF)
val GlassBorderStrong = Color(0x35FFFFFF)

// Glow & Reflexo
val AuraGlowCyan = Color(0x3322D3EE)
val AuraGlowEmerald = Color(0x3310B981)

// Status semantico
val StatusSuccess = Color(0xFF34D399)
val StatusWarning = Color(0xFFFBBF24)
val StatusDanger = Color(0xFFF87171)
val StatusInfo = Color(0xFF38BDF8)

// Gradientes de marca
val AuraBrandBlue = Color(0xFF38BDF8) // Azul celeste vibrante
val AuraBrandPetroleum = Color(0xFF0D9488) // Verde Petroleo / Teal escuro
val AuraBrandPurple = Color(0xFFA855F7) // Roxo elegante

val AuraBrandGradient: Brush = Brush.horizontalGradient(
    colors = listOf(AuraBrandBlue, AuraBrandPetroleum, AuraBrandPurple)
)

val AuroraBrush: Brush = Brush.linearGradient(listOf(AuraCyan, AuraEmerald))
val AuroraBrushSoft: Brush = Brush.linearGradient(
    listOf(AuraCyan.copy(alpha = 0.18f), AuraEmerald.copy(alpha = 0.18f))
)
val GlassCardBrush: Brush = Brush.verticalGradient(
    listOf(ObsidianHigh.copy(alpha = 0.85f), ObsidianLow.copy(alpha = 0.95f))
)
val GlassBorderBrush: Brush = Brush.verticalGradient(
    listOf(GlassBorderStrong, GlassBorderSoft)
)

