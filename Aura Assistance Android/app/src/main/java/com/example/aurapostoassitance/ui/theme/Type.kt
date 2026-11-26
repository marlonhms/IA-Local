package com.example.aurapostoassitance.ui.theme

import androidx.compose.material3.Typography
import androidx.compose.ui.text.ExperimentalTextApi
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.Font
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontVariation
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp
import com.example.aurapostoassitance.R

@OptIn(ExperimentalTextApi::class)
private fun variableFont(resId: Int, weight: FontWeight, vararg extra: FontVariation.Setting) = Font(
    resId = resId,
    weight = weight,
    variationSettings = FontVariation.Settings(
        FontVariation.weight(weight.weight),
        *extra
    )
)

// Editorial (titulos): Newsreader
val NewsreaderFamily = FontFamily(
    variableFont(R.font.newsreader_variable, FontWeight.Normal),
    variableFont(R.font.newsreader_variable, FontWeight.Medium),
    variableFont(R.font.newsreader_variable, FontWeight.SemiBold)
)

// Interface e numeros: Geist
val GeistFamily = FontFamily(
    variableFont(R.font.geist_variable, FontWeight.Normal),
    variableFont(R.font.geist_variable, FontWeight.Medium),
    variableFont(R.font.geist_variable, FontWeight.SemiBold),
    variableFont(R.font.geist_variable, FontWeight.Bold)
)

/**
 * Estilos especializados para números tabulares (tnum) em KPIs executivos,
 * deltas financeiros e trilhas de auditoria monoespaçadas (Carbon Obsidian 2.0).
 */
object AuraTypographyExt {
    val kpiHero = TextStyle(
        fontFamily = GeistFamily,
        fontWeight = FontWeight.Bold,
        fontSize = 28.sp,
        lineHeight = 32.sp,
        letterSpacing = (-0.6).sp,
        fontFeatureSettings = "tnum"
    )

    val kpiValue = TextStyle(
        fontFamily = GeistFamily,
        fontWeight = FontWeight.SemiBold,
        fontSize = 18.sp,
        lineHeight = 22.sp,
        letterSpacing = (-0.3).sp,
        fontFeatureSettings = "tnum"
    )

    val kpiCompact = TextStyle(
        fontFamily = GeistFamily,
        fontWeight = FontWeight.SemiBold,
        fontSize = 14.sp,
        lineHeight = 18.sp,
        fontFeatureSettings = "tnum"
    )

    val monoAudit = TextStyle(
        fontFamily = FontFamily.Monospace,
        fontWeight = FontWeight.Medium,
        fontSize = 11.sp,
        lineHeight = 16.sp,
        fontFeatureSettings = "tnum"
    )
}

val Typography = Typography(
    displayLarge = TextStyle(fontFamily = NewsreaderFamily, fontWeight = FontWeight.Normal, fontSize = 48.sp, lineHeight = 54.sp, letterSpacing = (-0.5).sp),
    displayMedium = TextStyle(fontFamily = NewsreaderFamily, fontWeight = FontWeight.Normal, fontSize = 36.sp, lineHeight = 42.sp, letterSpacing = (-0.4).sp),
    headlineLarge = TextStyle(fontFamily = NewsreaderFamily, fontWeight = FontWeight.Normal, fontSize = 30.sp, lineHeight = 36.sp),
    headlineMedium = TextStyle(fontFamily = NewsreaderFamily, fontWeight = FontWeight.Normal, fontSize = 24.sp, lineHeight = 30.sp),
    headlineSmall = TextStyle(fontFamily = NewsreaderFamily, fontWeight = FontWeight.Normal, fontSize = 21.sp, lineHeight = 27.sp),
    titleLarge = TextStyle(fontFamily = NewsreaderFamily, fontWeight = FontWeight.Medium, fontSize = 20.sp, lineHeight = 26.sp),
    titleMedium = TextStyle(fontFamily = GeistFamily, fontWeight = FontWeight.SemiBold, fontSize = 16.sp, lineHeight = 22.sp),
    titleSmall = TextStyle(fontFamily = GeistFamily, fontWeight = FontWeight.Medium, fontSize = 14.sp, lineHeight = 20.sp),
    bodyLarge = TextStyle(fontFamily = GeistFamily, fontWeight = FontWeight.Normal, fontSize = 15.5.sp, lineHeight = 24.sp, letterSpacing = 0.1.sp),
    bodyMedium = TextStyle(fontFamily = GeistFamily, fontWeight = FontWeight.Normal, fontSize = 14.sp, lineHeight = 21.sp),
    bodySmall = TextStyle(fontFamily = GeistFamily, fontWeight = FontWeight.Normal, fontSize = 12.sp, lineHeight = 18.sp),
    labelLarge = TextStyle(fontFamily = GeistFamily, fontWeight = FontWeight.SemiBold, fontSize = 14.sp, lineHeight = 20.sp, letterSpacing = 0.1.sp),
    labelMedium = TextStyle(fontFamily = GeistFamily, fontWeight = FontWeight.Medium, fontSize = 12.sp, lineHeight = 16.sp, letterSpacing = 0.25.sp),
    labelSmall = TextStyle(fontFamily = GeistFamily, fontWeight = FontWeight.Medium, fontSize = 11.sp, lineHeight = 14.sp, letterSpacing = 0.45.sp)
)
