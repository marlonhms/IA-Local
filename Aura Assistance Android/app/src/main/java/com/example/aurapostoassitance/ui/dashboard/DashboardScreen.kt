package com.example.aurapostoassitance.ui.dashboard

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.IntrinsicSize
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.defaultMinSize
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.rounded.Chat
import androidx.compose.material.icons.rounded.Assessment
import androidx.compose.material.icons.rounded.AutoAwesome
import androidx.compose.material.icons.rounded.LocalGasStation
import androidx.compose.material.icons.rounded.PointOfSale
import androidx.compose.material.icons.rounded.Storefront
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.aurapostoassitance.ui.components.AuraBrandTitle
import com.example.aurapostoassitance.ui.components.AuraCard
import com.example.aurapostoassitance.ui.components.AuraChip
import com.example.aurapostoassitance.ui.components.AuraGradientButton
import com.example.aurapostoassitance.ui.components.SectionLabel
import com.example.aurapostoassitance.ui.components.StatusDot
import com.example.aurapostoassitance.ui.theme.AuraCyan
import com.example.aurapostoassitance.ui.theme.AuraEmerald
import com.example.aurapostoassitance.ui.theme.AuraPurple
import com.example.aurapostoassitance.ui.theme.NewsreaderFamily
import com.example.aurapostoassitance.ui.theme.ObsidianBase
import com.example.aurapostoassitance.ui.theme.ObsidianHigh
import com.example.aurapostoassitance.ui.theme.StatusSuccess
import com.example.aurapostoassitance.ui.theme.StatusWarning
import com.example.aurapostoassitance.ui.theme.TextMuted
import com.example.aurapostoassitance.ui.theme.TextPrimary
import com.example.aurapostoassitance.ui.theme.TextSecondary

private data class QuickTrigger(
    val title: String,
    val description: String,
    val icon: ImageVector,
    val accentColor: Color,
    val query: String
)

private val triggers = listOf(
    QuickTrigger(
        title = "LMC & Conformidade ANP",
        description = "Auditoria de tolerância legal (±0.60%) e perdas térmicas.",
        icon = Icons.Rounded.Assessment,
        accentColor = AuraEmerald,
        query = "Gere o relatório completo do LMC ANP de hoje."
    ),
    QuickTrigger(
        title = "Autonomia & Run-Out",
        description = "Previsão de pane seca e compras em compartimentos de 5.000\u00A0L.",
        icon = Icons.Rounded.LocalGasStation,
        accentColor = AuraCyan,
        query = "Faça a previsão de esgotamento (Run-Out) dos tanques."
    ),
    QuickTrigger(
        title = "Conciliação de Turno",
        description = "Auditoria de sangrias de gaveta vs vendas totais dos bicos.",
        icon = Icons.Rounded.PointOfSale,
        accentColor = AuraPurple,
        query = "Audite o fechamento de turno de hoje."
    ),
    QuickTrigger(
        title = "Conveniência & Cestas",
        description = "Ticket médio da loja, itens de impulso e vendas cruzadas.",
        icon = Icons.Rounded.Storefront,
        accentColor = StatusWarning,
        query = "Faça a análise de cestas e vendas cruzadas da loja de conveniência."
    )
)

private val chipPrompts = listOf(
    "Preços ANP na Cidade",
    "Divergência de Caixa",
    "Custo Selic do Estoque",
    "Aferição INMETRO 20L",
    "Histórico de Sangrias"
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DashboardScreen(
    onNavigateToChat: (String?) -> Unit
) {
    Scaffold(
        containerColor = ObsidianBase,
        topBar = {
            TopAppBar(
                title = {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        AuraBrandTitle(
                            text = "AURA",
                            style = MaterialTheme.typography.titleLarge
                        )
                        Spacer(modifier = Modifier.width(10.dp))
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            modifier = Modifier
                                .clip(RoundedCornerShape(50))
                                .background(ObsidianHigh)
                                .padding(horizontal = 10.dp, vertical = 4.dp)
                        ) {
                            StatusDot(color = StatusSuccess, size = 6.dp, pulsing = true)
                            Spacer(modifier = Modifier.width(6.dp))
                            Text(
                                text = "Posto Online",
                                style = MaterialTheme.typography.labelSmall,
                                color = TextSecondary,
                                fontWeight = FontWeight.SemiBold
                            )
                        }
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = ObsidianBase
                )
            )
        }
    ) { paddingValues ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 20.dp, vertical = 12.dp)
        ) {
            // Header Editorial Deluxe
            Text(
                text = "Pulso Operacional",
                style = MaterialTheme.typography.displayMedium.copy(
                    fontFamily = NewsreaderFamily,
                    letterSpacing = (-0.5).sp
                ),
                color = TextPrimary
            )
            Spacer(modifier = Modifier.height(4.dp))
            Text(
                text = "Inteligência de pista, tancagem e prontidão de caixa.",
                style = MaterialTheme.typography.bodyMedium,
                color = TextSecondary
            )

            Spacer(modifier = Modifier.height(20.dp))

            // Pulse Status Bar (Glassmorphism Telemetria)
            AuraCard(
                modifier = Modifier.fillMaxWidth(),
                accent = AuraCyan,
                contentPadding = PaddingValues(16.dp)
            ) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    PulseStatItem(label = "Tanques", value = "100% Ativos", dotColor = StatusSuccess)
                    PulseStatItem(label = "LMC ANP", value = "±0.60% OK", dotColor = StatusSuccess)
                    PulseStatItem(label = "Turno", value = "Em Aberto", dotColor = AuraCyan)
                }
            }

            Spacer(modifier = Modifier.height(24.dp))

            SectionLabel(text = "Gatilhos Executivos da Pista")
            Spacer(modifier = Modifier.height(12.dp))

            // 2x2 Triggers Grid
            Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                triggers.chunked(2).forEach { rowTriggers ->
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(IntrinsicSize.Max),
                        horizontalArrangement = Arrangement.spacedBy(12.dp)
                    ) {
                        rowTriggers.forEach { trigger ->
                            ExecutiveCard(
                                trigger = trigger,
                                modifier = Modifier
                                    .weight(1f)
                                    .fillMaxHeight(),
                                onClick = { onNavigateToChat(trigger.query) }
                            )
                        }
                    }
                }
            }

            Spacer(modifier = Modifier.height(26.dp))

            SectionLabel(text = "Consultas Frequentes")
            Spacer(modifier = Modifier.height(12.dp))

            LazyRow(
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                contentPadding = PaddingValues(bottom = 8.dp)
            ) {
                items(chipPrompts) { prompt ->
                    AuraChip(
                        label = prompt,
                        icon = Icons.Rounded.AutoAwesome,
                        onClick = { onNavigateToChat(prompt) }
                    )
                }
            }

            Spacer(modifier = Modifier.height(28.dp))

            // Main CTA AURA Button
            AuraGradientButton(
                text = "Abrir AURA",
                onClick = { onNavigateToChat(null) },
                icon = Icons.AutoMirrored.Rounded.Chat,
                modifier = Modifier.fillMaxWidth()
            )

            Spacer(modifier = Modifier.height(24.dp))
        }
    }
}

@Composable
private fun PulseStatItem(label: String, value: String, dotColor: Color) {
    Column {
        Text(
            text = label.uppercase(),
            style = MaterialTheme.typography.labelSmall,
            color = TextMuted,
            letterSpacing = 0.5.sp
        )
        Spacer(modifier = Modifier.height(3.dp))
        Row(verticalAlignment = Alignment.CenterVertically) {
            StatusDot(color = dotColor, size = 6.dp, pulsing = true)
            Spacer(modifier = Modifier.width(6.dp))
            Text(
                text = value,
                style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.SemiBold),
                color = TextPrimary
            )
        }
    }
}

@Composable
private fun ExecutiveCard(
    trigger: QuickTrigger,
    modifier: Modifier = Modifier,
    onClick: () -> Unit
) {
    AuraCard(
        modifier = modifier.defaultMinSize(minHeight = 170.dp),
        accent = trigger.accentColor,
        onClick = onClick,
        contentPadding = PaddingValues(14.dp)
    ) {
        Column(
            modifier = Modifier.fillMaxSize(),
            verticalArrangement = Arrangement.SpaceBetween
        ) {
            Box(
                modifier = Modifier
                    .size(38.dp)
                    .clip(CircleShape)
                    .background(trigger.accentColor.copy(alpha = 0.14f)),
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    imageVector = trigger.icon,
                    contentDescription = null,
                    tint = trigger.accentColor,
                    modifier = Modifier.size(20.dp)
                )
            }

            Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text(
                    text = trigger.title,
                    style = MaterialTheme.typography.titleMedium.copy(
                        fontWeight = FontWeight.SemiBold,
                        lineHeight = 19.sp
                    ),
                    color = TextPrimary
                )
                Text(
                    text = trigger.description,
                    style = MaterialTheme.typography.bodySmall.copy(
                        lineHeight = 15.sp
                    ),
                    color = TextSecondary,
                    maxLines = 3,
                    overflow = TextOverflow.Ellipsis
                )
            }
        }
    }
}
