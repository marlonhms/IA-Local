package com.example.aurapostoassitance.ui.entrance

import android.content.Context
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.spring
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.togetherWith
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.State
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalHapticFeedback
import androidx.compose.ui.platform.LocalView
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import com.example.aurapostoassitance.ui.components.AuraHaptics
import com.example.aurapostoassitance.ui.components.AuraLivingOrb
import com.example.aurapostoassitance.ui.components.StatusDot
import com.example.aurapostoassitance.ui.theme.AuraAmbientCyan
import com.example.aurapostoassitance.ui.theme.AuraAmbientPetroleum
import com.example.aurapostoassitance.ui.theme.AuraAmbientPurple
import com.example.aurapostoassitance.ui.theme.AuraCyan
import com.example.aurapostoassitance.ui.theme.LiquidIridescentBorderBrush
import com.example.aurapostoassitance.ui.theme.NewsreaderFamily
import com.example.aurapostoassitance.ui.theme.ObsidianDeep
import com.example.aurapostoassitance.ui.theme.ObsidianMid
import com.example.aurapostoassitance.ui.theme.StatusSuccess
import com.example.aurapostoassitance.ui.theme.StatusWarning
import com.example.aurapostoassitance.ui.theme.TextPrimary
import com.example.aurapostoassitance.ui.theme.TextSecondary
import kotlin.math.roundToInt

/**
 * Lê o sensor de gravidade/acelerômetro do dispositivo em tempo real para proporcionar
 * efeito de paralaxe 3D espacial e sensação de presença física e livre da entidade AURA.
 */
@Composable
fun rememberAuraSpatialTilt(): State<Pair<Float, Float>> {
    val context = LocalContext.current
    val tiltState = remember { mutableStateOf(0f to 0f) }

    DisposableEffect(Unit) {
        val sensorManager = context.getSystemService(Context.SENSOR_SERVICE) as? SensorManager
        val sensor = sensorManager?.getDefaultSensor(Sensor.TYPE_GRAVITY)
            ?: sensorManager?.getDefaultSensor(Sensor.TYPE_ACCELEROMETER)

        var currentRoll = 0f
        var currentPitch = 0f

        val listener = object : SensorEventListener {
            override fun onSensorChanged(event: SensorEvent?) {
                if (event != null && event.values.size >= 2) {
                    val rawX = event.values[0] / 9.81f // Eixo X (Roll: -1..1)
                    val rawY = event.values[1] / 9.81f // Eixo Y (Pitch: -1..1)
                    // Filtro passa-baixa orgânico com amortecimento
                    currentRoll = (currentRoll * 0.82f + (-rawX) * 0.18f).coerceIn(-1f, 1f)
                    currentPitch = (currentPitch * 0.82f + rawY * 0.18f).coerceIn(-1f, 1f)
                    tiltState.value = currentRoll to currentPitch
                }
            }

            override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) {}
        }

        if (sensor != null) {
            sensorManager?.registerListener(listener, sensor, SensorManager.SENSOR_DELAY_GAME)
        }

        onDispose {
            sensorManager?.unregisterListener(listener)
        }
    }

    return tiltState
}

/**
 * Aura Entrance Screen: Entrada triunfal da AURA com emergência fluida e livre (sem bordas ou envoltórios),
 * resposta física ao giroscópio do aparelho e conexão automática com a última rota lembrada.
 */
@Composable
fun AuraEntranceScreen(
    onNavigateToDashboard: () -> Unit,
    onNavigateToSetup: () -> Unit,
    viewModel: AuraEntranceViewModel = hiltViewModel()
) {
    val step by viewModel.step.collectAsState()
    val tilt by rememberAuraSpatialTilt()
    val haptic = LocalHapticFeedback.current
    val view = LocalView.current

    var emerged by remember { mutableStateOf(false) }

    LaunchedEffect(Unit) {
        emerged = true
        AuraHaptics.heavy(view, haptic)
        viewModel.startEntranceSequence(
            onNavigateToDashboard = onNavigateToDashboard,
            onNavigateToSetup = onNavigateToSetup
        )
    }

    // Suavização do giroscópio com molas físicas
    val roll by animateFloatAsState(
        targetValue = tilt.first,
        animationSpec = spring(dampingRatio = 0.82f, stiffness = 260f),
        label = "gyroRoll"
    )
    val pitch by animateFloatAsState(
        targetValue = tilt.second,
        animationSpec = spring(dampingRatio = 0.82f, stiffness = 260f),
        label = "gyroPitch"
    )

    // Animações de emergência da AURA (orgânica e irrestrita)
    val orbScale by animateFloatAsState(
        targetValue = if (emerged) 1f else 0.18f,
        animationSpec = spring(dampingRatio = 0.68f, stiffness = 160f),
        label = "orbScale"
    )
    val orbAlpha by animateFloatAsState(
        targetValue = if (emerged) 1f else 0f,
        animationSpec = tween(750),
        label = "orbAlpha"
    )
    val textAlpha by animateFloatAsState(
        targetValue = if (emerged) 1f else 0f,
        animationSpec = tween(900, delayMillis = 350),
        label = "textAlpha"
    )

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(ObsidianDeep)
            .clickable(
                interactionSource = remember { MutableInteractionSource() },
                indication = null
            ) {
                // Toque na tela para prosseguir imediatamente se desejado
                AuraHaptics.click(view, haptic)
                when (step) {
                    is EntranceStep.Success, is EntranceStep.OfflineFallback, is EntranceStep.Connecting -> onNavigateToDashboard()
                    is EntranceStep.NeedsSetup -> onNavigateToSetup()
                    else -> {}
                }
            },
        contentAlignment = Alignment.Center
    ) {
        // Camada -1: Nebulosa Cósmica Atmosférica (Paralaxe Inverso de Profundidade)
        Box(
            modifier = Modifier
                .fillMaxSize()
                .offset {
                    IntOffset(
                        x = (roll * -35f).roundToInt(),
                        y = (pitch * -35f).roundToInt()
                    )
                }
                .drawBehind {
                    drawCircle(
                        brush = Brush.radialGradient(
                            colors = listOf(
                                AuraAmbientCyan.copy(alpha = 0.40f),
                                Color.Transparent
                            ),
                            center = Offset(size.width * 0.35f, size.height * 0.30f),
                            radius = size.width * 0.85f
                        )
                    )
                    drawCircle(
                        brush = Brush.radialGradient(
                            colors = listOf(
                                AuraAmbientPurple.copy(alpha = 0.35f),
                                Color.Transparent
                            ),
                            center = Offset(size.width * 0.70f, size.height * 0.65f),
                            radius = size.width * 0.90f
                        )
                    )
                    drawCircle(
                        brush = Brush.radialGradient(
                            colors = listOf(
                                AuraAmbientPetroleum.copy(alpha = 0.45f),
                                Color.Transparent
                            ),
                            center = Offset(size.width * 0.5f, size.height * 0.5f),
                            radius = size.width * 0.70f
                        )
                    )
                }
        )

        // Conteúdo Central
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center,
            modifier = Modifier.padding(horizontal = 24.dp)
        ) {
            // Entidade Viva Holográfica: Orbe da AURA totalmente livre e fluido (sem anéis ou bolhas contendo)
            Box(
                contentAlignment = Alignment.Center,
                modifier = Modifier
                    .size(240.dp)
                    .graphicsLayer {
                        translationX = roll * 52f
                        translationY = pitch * 52f
                        rotationZ = roll * 14f
                        scaleX = orbScale
                        scaleY = orbScale
                        alpha = orbAlpha
                    }
            ) {
                AuraLivingOrb(
                    sizeDp = 195.dp,
                    voiceRms = 0.40f,
                    pulsing = true
                )
            }

            Spacer(modifier = Modifier.height(36.dp))

            // Tipografia Editorial Shimmer
            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
                modifier = Modifier
                    .graphicsLayer {
                        translationX = roll * 20f
                        translationY = pitch * 20f
                        alpha = textAlpha
                    }
            ) {
                Text(
                    text = "AURA",
                    style = MaterialTheme.typography.displayLarge.copy(
                        fontFamily = NewsreaderFamily,
                        fontSize = 44.sp,
                        letterSpacing = 2.sp,
                        fontWeight = FontWeight.Normal
                    ),
                    color = TextPrimary
                )

                Spacer(modifier = Modifier.height(4.dp))

                Text(
                    text = "Inteligência Operacional",
                    style = MaterialTheme.typography.bodyMedium.copy(
                        letterSpacing = 0.4.sp
                    ),
                    color = TextSecondary
                )
            }

            Spacer(modifier = Modifier.height(32.dp))

            // Cápsula de Status e Rota Lembrada
            Box(
                modifier = Modifier
                    .graphicsLayer {
                        translationX = roll * 14f
                        translationY = pitch * 14f
                        alpha = textAlpha
                    }
            ) {
                AnimatedContent(
                    targetState = step,
                    transitionSpec = { fadeIn(tween(400)) togetherWith fadeOut(tween(300)) },
                    label = "entranceStepTransition"
                ) { currentStep ->
                    val (statusText, dotColor, isPulsing) = when (currentStep) {
                        is EntranceStep.Awakening -> Triple(
                            "Despertando consciência operacional...",
                            AuraCyan,
                            true
                        )
                        is EntranceStep.Connecting -> Triple(
                            "Conectando a ${currentStep.route}...",
                            AuraCyan,
                            true
                        )
                        is EntranceStep.Success -> Triple(
                            "Conexão Ativa • Rota Reconhecida",
                            StatusSuccess,
                            false
                        )
                        is EntranceStep.OfflineFallback -> Triple(
                            "Modo Resiliente • Entrando no Cockpit...",
                            StatusWarning,
                            false
                        )
                        is EntranceStep.NeedsSetup -> Triple(
                            "Primeira Inicialização • Configurar Servidor",
                            AuraCyan,
                            true
                        )
                    }

                    Box(
                        modifier = Modifier
                            .clip(RoundedCornerShape(50))
                            .background(ObsidianMid.copy(alpha = 0.85f))
                            .border(1.dp, LiquidIridescentBorderBrush, RoundedCornerShape(50))
                            .padding(horizontal = 16.dp, vertical = 9.dp)
                    ) {
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.spacedBy(8.dp)
                        ) {
                            StatusDot(
                                color = dotColor,
                                size = 7.dp,
                                pulsing = isPulsing
                            )
                            Text(
                                text = statusText,
                                style = MaterialTheme.typography.labelMedium.copy(
                                    fontWeight = FontWeight.Medium,
                                    fontSize = 12.sp
                                ),
                                color = TextPrimary
                            )
                        }
                    }
                }
            }
        }
    }
}
