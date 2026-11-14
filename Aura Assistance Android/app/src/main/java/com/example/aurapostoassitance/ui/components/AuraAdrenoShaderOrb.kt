package com.example.aurapostoassitance.ui.components

import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import com.example.aurapostoassitance.ui.theme.AuraCyan

/**
 * Consciência Holográfica Viva da AURA.
 * Delega para o AuraLivingOrb, garantindo fluxo orgânico líquido,
 * halo transparente e reatividade harmônica à voz sem descontinuidades ou opacidade rígida.
 */
@Composable
fun AuraAdrenoShaderOrb(
    modifier: Modifier = Modifier,
    size: Dp = 100.dp,
    amplitude: Float = 0.05f,
    activeColor: Color = AuraCyan
) {
    AuraLivingOrb(
        modifier = modifier,
        sizeDp = size,
        voiceRms = amplitude,
        pulsing = true
    )
}
