package com.example.aurapostoassitance.ui.theme

import android.app.Activity
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Shapes
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.SideEffect
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.platform.LocalView
import androidx.compose.ui.unit.dp
import androidx.core.view.WindowCompat

// Tema unico "Obsidian Aurora": sempre escuro, coerente com o painel web.
private val ObsidianColorScheme = darkColorScheme(
    primary = AuraCyan,
    onPrimary = ObsidianBase,
    secondary = AuraEmerald,
    onSecondary = ObsidianBase,
    tertiary = AuraPurple,
    background = ObsidianBase,
    onBackground = TextPrimary,
    surface = ObsidianLow,
    onSurface = TextPrimary,
    surfaceVariant = ObsidianMid,
    onSurfaceVariant = TextSecondary,
    surfaceContainer = ObsidianMid,
    surfaceContainerHigh = ObsidianHigh,
    surfaceContainerHighest = ObsidianBright,
    outline = OutlineStrong,
    outlineVariant = OutlineSoft,
    error = StatusDanger
)

private val AuraShapes = Shapes(
    extraSmall = RoundedCornerShape(8.dp),
    small = RoundedCornerShape(12.dp),
    medium = RoundedCornerShape(16.dp),
    large = RoundedCornerShape(24.dp),
    extraLarge = RoundedCornerShape(32.dp)
)

@Composable
fun AuraPostoAssitanceTheme(content: @Composable () -> Unit) {
    val view = LocalView.current
    if (!view.isInEditMode) {
        SideEffect {
            val window = (view.context as Activity).window
            window.statusBarColor = ObsidianBase.toArgb()
            window.navigationBarColor = ObsidianBase.toArgb()
            val controller = WindowCompat.getInsetsController(window, view)
            controller.isAppearanceLightStatusBars = false
            controller.isAppearanceLightNavigationBars = false
        }
    }

    MaterialTheme(
        colorScheme = ObsidianColorScheme,
        typography = Typography,
        shapes = AuraShapes,
        content = content
    )
}
