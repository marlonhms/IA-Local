package com.example.aurapostoassitance.ui.theme

import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color

// Acentos Carbon Obsidian Canonicos (85-10-5)
val AuraEmerald = Color(0xFF10B981) // Conformidade, ROI positivo, Escudo LGPD, Voucher TEE
val AuraCyan = Color(0xFF22D3EE)    // Dados deterministicos, SQL Read-Only, Foco e Navegacao
val AuraPurple = Color(0xFF8B5CF6)  // Raciocinio cognitivo IA, Sintese, Simulacao What-If

// Obsidian: camadas de superficie AMOLED (do mais fundo ao mais elevado)
val ObsidianDeep = Color(0xFF030407)
val ObsidianBase = Color(0xFF07090E)
val ObsidianLow = Color(0xFF0C1018)
val ObsidianMid = Color(0xFF121722)
val ObsidianHigh = Color(0xFF1A2130)
val ObsidianBright = Color(0xFF232C3F)

// Superficies Glass Canonicas (paridade com AUDITORIA_CARBON_UI.md)
val SurfaceGlass1 = Color(0xC20C111C) // rgba(12, 17, 28, 0.76)
val SurfaceGlass2 = Color(0xE0111827) // rgba(17, 24, 39, 0.88)

// Compatibilidade
val AuraDarkBackground = ObsidianBase
val AuraDarkSurface = ObsidianMid

// Texto
val TextPrimary = Color(0xFFF1F5F9)
val TextSecondary = Color(0xFF94A3B8)
val TextMuted = Color(0xFF64748B)

// Bordas suaves (vidro e hairline silenciosa 7%)
val BorderHairline = Color(0x12FFFFFF)
val OutlineSoft = Color(0x14FFFFFF)
val OutlineStrong = Color(0x29FFFFFF)
val GlassHighlight = Color(0x28FFFFFF)
val GlassBorderSoft = Color(0x18FFFFFF)
val GlassBorderStrong = Color(0x35FFFFFF)

// Glow & Reflexo
val AuraGlowCyan = Color(0x3322D3EE)
val AuraGlowEmerald = Color(0x3310B981)

// Status semantico (Carbon Canonico)
val StatusSuccess = Color(0xFF10B981)
val StatusWarning = Color(0xFFF59E0B)
val StatusDanger = Color(0xFFF43F5E)
val StatusInfo = Color(0xFF22D3EE)

// Gradientes de marca
val AuraBrandBlue = Color(0xFF22D3EE)
val AuraBrandPetroleum = Color(0xFF10B981)
val AuraBrandPurple = Color(0xFF8B5CF6)

val AuraBrandGradient: Brush = Brush.horizontalGradient(
    colors = listOf(AuraBrandBlue, AuraBrandPetroleum, AuraBrandPurple)
)

val AuroraBrush: Brush = Brush.linearGradient(listOf(AuraCyan, AuraEmerald))
val AuroraBrushSoft: Brush = Brush.linearGradient(
    listOf(AuraCyan.copy(alpha = 0.14f), AuraEmerald.copy(alpha = 0.12f))
)
val GlassCardBrush: Brush = Brush.verticalGradient(
    listOf(SurfaceGlass2, SurfaceGlass1)
)
val GlassBorderBrush: Brush = Brush.verticalGradient(
    listOf(GlassBorderSoft, BorderHairline)
)

// Liquid Glassmorphism & Spatial UI Tokens (Contencao 85-10-5)
val LiquidSpecularHighlight = Color(0x38FFFFFF)
val AuraAmbientCyan = Color(0x1422D3EE)
val AuraAmbientPurple = Color(0x128B5CF6)
val AuraAmbientPetroleum = Color(0x1010B981)

val LiquidGlassSurfaceBrush: Brush = Brush.verticalGradient(
    listOf(SurfaceGlass2.copy(alpha = 0.80f), SurfaceGlass1.copy(alpha = 0.92f))
)

val LiquidGlassElevatedBrush: Brush = Brush.verticalGradient(
    listOf(ObsidianHigh.copy(alpha = 0.88f), ObsidianLow.copy(alpha = 0.96f))
)

val LiquidIridescentBorderBrush: Brush = Brush.linearGradient(
    colors = listOf(
        AuraCyan.copy(alpha = 0.55f),
        Color.White.copy(alpha = 0.22f),
        AuraPurple.copy(alpha = 0.45f),
        AuraEmerald.copy(alpha = 0.35f)
    )
)

val LiquidIridescentSubtleBrush: Brush = Brush.linearGradient(
    colors = listOf(
        AuraCyan.copy(alpha = 0.22f),
        Color.White.copy(alpha = 0.10f),
        AuraPurple.copy(alpha = 0.18f)
    )
)
