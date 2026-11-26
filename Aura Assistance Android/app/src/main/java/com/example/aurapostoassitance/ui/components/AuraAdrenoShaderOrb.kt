package com.example.aurapostoassitance.ui.components

import android.graphics.RuntimeShader
import android.os.Build
import androidx.annotation.RequiresApi
import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.spring
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.size
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.ShaderBrush
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import com.example.aurapostoassitance.ui.theme.AuraCyan
import com.example.aurapostoassitance.ui.theme.AuraEmerald
import com.example.aurapostoassitance.ui.theme.AuraPurple

/**
 * Estados comportamentais do Orbe da AURA:
 * - IDLE: esfera líquida 3D profunda com correntes internas orgânicas e véu sutil de Aurora Boreal.
 * - THINKING: giro orbital sedoso e sincronizado (arcos-cometa contra-rotativos + vórtice suave).
 * - ACTIVE: modulação harmônica reativa à amplitude de voz.
 */
enum class AuraOrbMode {
    IDLE,
    THINKING,
    ACTIVE
}

private const val AURA_LIQUID_PLASMA_AGSL = """
uniform float2 uResolution;
uniform float uTime;
uniform float uRms;
uniform float uThinking;
uniform float uActive;
uniform float3 uPrimary;
uniform float3 uSecondary;
uniform float3 uTertiary;

float hash21(float2 p) {
    p = fract(p * float2(123.34, 456.21));
    p += dot(p, p + 45.32);
    return fract(p.x * p.y);
}

float vnoise(float2 p) {
    float2 i = floor(p);
    float2 f = fract(p);
    float2 u = f * f * (3.0 - 2.0 * f);
    float a = hash21(i);
    float b = hash21(i + float2(1.0, 0.0));
    float c = hash21(i + float2(0.0, 1.0));
    float d = hash21(i + float2(1.0, 1.0));
    return mix(mix(a, b, u.x), mix(c, d, u.x), u.y);
}

float fbm(float2 p) {
    float v = 0.0;
    float amp = 0.52;
    for (int i = 0; i < 3; i++) {
        v += amp * vnoise(p);
        p = float2(p.x * 1.62 - p.y * 1.18, p.x * 1.18 + p.y * 1.62) + float2(1.7, 3.1);
        amp *= 0.5;
    }
    return v;
}

half4 main(float2 fragCoord) {
    float2 uv = (fragCoord - 0.5 * uResolution) / min(uResolution.x, uResolution.y);
    float dist = length(uv);

    // Mascara radial quadratica rigorosa: alpha = 0.0 puro antes da borda (zero quadrado!)
    float edgeMask = smoothstep(0.492, 0.23, dist);
    edgeMask = edgeMask * edgeMask;
    if (edgeMask <= 0.001) {
        return half4(0.0, 0.0, 0.0, 0.0);
    }

    float angle = atan(uv.y, uv.x);

    // Ritmo sereno em IDLE (0.48x) e giro orbital fluido com leve modulacao organica em THINKING
    float tFlow = uTime * 0.48;
    float tOrbit = uTime * 2.15 + sin(uTime * 1.05) * 0.28;

    // 1. Silhueta nobre e sutilmente viva (sem deformacoes triangulares/blob)
    float2 warpCoord = uv * 2.5 + float2(sin(tFlow * 0.618) * 1.1, cos(tFlow * 0.854) * 1.1);
    float organicRipple = (fbm(warpCoord) - 0.5) * 0.022 + sin(2.0 * angle + tFlow) * 0.006;
    float idleBreath = sin(tFlow * 1.15) * 0.008;
    float voiceWave = (sin(3.0 * angle + uTime * 2.0) * 0.022 + cos(2.0 * angle - uTime * 1.5) * 0.016) * uRms * uActive;

    float organicAmt = mix(1.0, 0.15, uThinking);
    float radius = 0.245 + idleBreath + (organicRipple * organicAmt) + voiceWave + (uRms * uActive * 0.028);

    // Corpo principal e profundidade 3D esferica (interior mais profundo -> borda Fresnel iluminada)
    float body = smoothstep(radius + 0.020, radius - 0.018, dist);
    float normR = clamp(dist / max(radius, 0.001), 0.0, 1.0);
    float sphereShade = mix(0.62, 1.0, normR * normR);
    float fresnel = pow(smoothstep(0.35, 1.0, normR), 1.8) * body;

    // 2. Veu sutil de Aurora Boreal emanando ao redor do orbe
    float2 auroraUv = uv * 3.0 + float2(sin(tFlow * 0.45) * 0.8, -tFlow * 0.34);
    float aWarp = fbm(auroraUv);
    float auroraRibbon = sin(angle * 2.0 + aWarp * 4.8 - tFlow * 0.85) * 0.5 + 0.5;
    float curtain = smoothstep(0.28, 0.85, aWarp * 0.60 + auroraRibbon * 0.48);
    float auroraFalloff = exp(-max(dist - radius * 0.82, 0.0) * 6.4);
    float auroraIntensity = curtain * auroraFalloff * edgeMask * (0.48 + uActive * uRms * 0.24);

    float auroraHue = 0.5 + 0.5 * sin(angle * 1.6 + aWarp * 4.2 + tFlow * 0.7);
    float3 auroraColor = mix(uSecondary, uPrimary, auroraHue);
    auroraColor = mix(auroraColor, uTertiary, smoothstep(0.38, 0.85, auroraRibbon) * 0.62);

    // 3. Correntes internas de plasma com contraste real (evita estourar para branco/ciano chapado)
    float2 innerUv = uv * 4.0 + float2(cos(tFlow * 0.58), sin(tFlow * 0.44)) * 1.25;
    float n1 = fbm(innerUv);
    float n2 = fbm(innerUv * 1.35 + float2(n1 * 2.0, -n1 * 1.6) + float2(tFlow * 0.32, -tFlow * 0.24));
    float filament = smoothstep(0.42, 0.78, sin((uv.x * 7.5 - uv.y * 6.0) + n2 * 6.0 - tFlow * 1.2) * 0.5 + 0.5);

    float3 deepBase = mix(uTertiary * 0.28, uSecondary * 0.34, n1);
    float3 idlePlasma = mix(deepBase, uPrimary * 0.72, smoothstep(0.32, 0.80, n2));
    idlePlasma = mix(idlePlasma, uTertiary * 0.88, smoothstep(0.45, 0.85, n1) * 0.65);
    idlePlasma += mix(uSecondary, uPrimary, 0.55) * filament * 0.44;

    // 4. Giro orbital polido em THINKING ("pensando / carregando")
    float spin1 = angle - tOrbit;
    float spin2 = angle + tOrbit * 0.55;
    // Arco-cometa principal sedoso + contra-arco secundario sutil
    float cometMain = pow(0.5 + 0.5 * cos(spin1), 5.0);
    float cometTail = pow(0.5 + 0.5 * cos(spin1 + 0.42), 2.5) * 0.42;
    float cometCounter = pow(0.5 + 0.5 * cos(spin2 + 3.14159), 5.0) * 0.48;

    float ringDist = abs(dist - (radius + 0.044));
    float orbitalArc = max(max(cometMain, cometTail), cometCounter);
    float orbitalRing = exp(-ringDist * 52.0) * (0.14 + 0.96 * orbitalArc) * uThinking * edgeMask;

    // Vórtice espiral suave interno sincronizado com o arco externo
    float spiral = 0.5 + 0.5 * sin(spin1 * 2.0 + dist * 16.0);
    float spiralSoft = smoothstep(0.28, 0.88, spiral);
    float3 thinkingPlasma = mix(uTertiary * 0.35, uPrimary * 0.82, spiralSoft);
    thinkingPlasma = mix(thinkingPlasma, uSecondary * 0.78, pow(0.5 + 0.5 * cos(spin2 * 2.0 - dist * 10.0), 2.0) * 0.55);

    float3 plasma = mix(idlePlasma, thinkingPlasma, uThinking) * sphereShade;

    // 5. Nucleo luminoso sutil e flutuante (dosado para manter textura e profundidade 3D)
    float2 coreDrift = float2(sin(tFlow * 0.81), cos(tFlow * 0.59)) * 0.045 * (1.0 - uThinking * 0.80);
    float coreDist = length(uv - coreDrift);
    float core = exp(-coreDist * (12.5 - uRms * uActive * 2.2));
    float3 coreColor = mix(uPrimary, float3(0.95, 0.99, 1.0), 0.72);

    float3 bodyLight = plasma * body * 0.88
                     + mix(uPrimary, uTertiary, 0.32) * fresnel * 0.52
                     + coreColor * core * (0.48 + 0.16 * cometMain * uThinking);

    float3 ringLight = mix(uPrimary, uTertiary, cometCounter * 0.6) * orbitalRing * 1.25;
    float3 auroraLight = auroraColor * auroraIntensity;

    // Tone-mapping suave (Reinhard leve) para evitar clipping plano nas altas luzes
    float3 rawColor = (bodyLight + auroraLight + ringLight) * edgeMask;
    float3 finalColor = rawColor / (1.0 + rawColor * 0.28);

    float energyAlpha = max(max(finalColor.r, finalColor.g), finalColor.b);
    float finalAlpha = clamp(max(body * 0.96, energyAlpha * 1.22) * edgeMask, 0.0, 1.0);

    return half4(clamp(finalColor, 0.0, 1.0), finalAlpha);
}
"""

/**
 * Consciência Holográfica Viva da AURA:
 * - Android 13+ (API 33+): Shader AGSL nativo na GPU (RuntimeShader) com Aurora Boreal e modos IDLE/THINKING/ACTIVE.
 * - API 26-32: Fallback Canvas otimizado Zero-GC via AuraLivingOrbCanvas.
 */
@Composable
fun AuraAdrenoShaderOrb(
    modifier: Modifier = Modifier,
    size: Dp = 100.dp,
    amplitude: Float = 0.05f,
    activeColor: Color = AuraCyan,
    pulsing: Boolean = true,
    mode: AuraOrbMode = AuraOrbMode.IDLE
) {
    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
        AuraAgslPlasmaOrb(
            modifier = modifier,
            sizeDp = size,
            voiceRms = amplitude,
            activeColor = activeColor,
            mode = mode
        )
    } else {
        AuraLivingOrbCanvas(
            modifier = modifier,
            sizeDp = size,
            voiceRms = amplitude,
            activeColor = activeColor,
            pulsing = pulsing,
            mode = mode
        )
    }
}

@RequiresApi(Build.VERSION_CODES.TIRAMISU)
@Composable
private fun AuraAgslPlasmaOrb(
    modifier: Modifier,
    sizeDp: Dp,
    voiceRms: Float,
    activeColor: Color,
    mode: AuraOrbMode
) {
    val shader = remember { RuntimeShader(AURA_LIQUID_PLASMA_AGSL) }
    val infiniteTransition = rememberInfiniteTransition(label = "agslOrb")

    val time by infiniteTransition.animateFloat(
        initialValue = 0f,
        targetValue = 120f,
        animationSpec = infiniteRepeatable(
            animation = tween(durationMillis = 120000, easing = LinearEasing),
            repeatMode = RepeatMode.Restart
        ),
        label = "agslTime"
    )

    val thinkingWeight by animateFloatAsState(
        targetValue = if (mode == AuraOrbMode.THINKING) 1f else 0f,
        animationSpec = tween(durationMillis = 550, easing = FastOutSlowInEasing),
        label = "agslThinking"
    )

    val activeWeight by animateFloatAsState(
        targetValue = if (mode == AuraOrbMode.ACTIVE) 1f else 0f,
        animationSpec = tween(durationMillis = 400, easing = FastOutSlowInEasing),
        label = "agslActive"
    )

    val smoothRms by animateFloatAsState(
        targetValue = voiceRms.coerceIn(0.02f, 1.0f),
        animationSpec = spring(stiffness = 190f, dampingRatio = 0.80f),
        label = "agslRms"
    )

    Box(
        modifier = modifier.size(sizeDp),
        contentAlignment = Alignment.Center
    ) {
        Canvas(modifier = Modifier.fillMaxSize()) {
            shader.setFloatUniform("uResolution", size.width, size.height)
            shader.setFloatUniform("uTime", time)
            shader.setFloatUniform("uRms", smoothRms)
            shader.setFloatUniform("uThinking", thinkingWeight)
            shader.setFloatUniform("uActive", activeWeight)
            shader.setFloatUniform("uPrimary", activeColor.red, activeColor.green, activeColor.blue)
            shader.setFloatUniform("uSecondary", AuraEmerald.red, AuraEmerald.green, AuraEmerald.blue)
            shader.setFloatUniform("uTertiary", AuraPurple.red, AuraPurple.green, AuraPurple.blue)
            drawRect(brush = ShaderBrush(shader))
        }
    }
}
