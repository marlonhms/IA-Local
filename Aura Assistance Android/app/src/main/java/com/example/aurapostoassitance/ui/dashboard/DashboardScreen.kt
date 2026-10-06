package com.example.aurapostoassitance.ui.dashboard

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DashboardScreen(
    onNavigateToChat: (String?) -> Unit
) {
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("AURA Dashboard") },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.background,
                    titleContentColor = MaterialTheme.colorScheme.primary
                )
            )
        }
    ) { paddingValues ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
                .padding(16.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            
            Text(
                text = "Gatilhos Rápidos",
                style = MaterialTheme.typography.titleLarge,
                fontWeight = FontWeight.Bold,
                modifier = Modifier.align(Alignment.Start)
            )

            // Shortcut Cards
            DashboardCard(
                title = "📊 LMC ANP",
                description = "Auditoria de tolerância (± 0.6%)",
                onClick = { onNavigateToChat("Gere o relatório completo do LMC ANP de hoje.") }
            )
            DashboardCard(
                title = "⛽ Run-Out Forecast",
                description = "Previsão de esgotamento de tanques",
                onClick = { onNavigateToChat("Faça a previsão de esgotamento (Run-Out) dos tanques.") }
            )
            DashboardCard(
                title = "💰 Auditoria de Turno",
                description = "Conciliação Caixa vs Pista",
                onClick = { onNavigateToChat("Audite o fechamento de turno de hoje.") }
            )
            DashboardCard(
                title = "🛒 Conveniência",
                description = "Vendas cruzadas e cestas",
                onClick = { onNavigateToChat("Faça a análise de cestas e vendas cruzadas da loja de conveniência.") }
            )

            Spacer(modifier = Modifier.weight(1f))

            Button(
                onClick = { onNavigateToChat(null) },
                modifier = Modifier
                    .fillMaxWidth()
                    .height(56.dp)
            ) {
                Text(
                    text = "Falar com a AURA", 
                    fontWeight = FontWeight.Bold,
                    style = MaterialTheme.typography.titleMedium
                )
            }
        }
    }
}

@Composable
fun DashboardCard(
    title: String,
    description: String,
    onClick: () -> Unit
) {
    Card(
        onClick = onClick,
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surfaceVariant
        )
    ) {
        Column(
            modifier = Modifier.padding(16.dp)
        ) {
            Text(
                text = title, 
                style = MaterialTheme.typography.titleMedium,
                color = MaterialTheme.colorScheme.primary,
                fontWeight = FontWeight.Bold
            )
            Spacer(modifier = Modifier.height(4.dp))
            Text(
                text = description, 
                style = MaterialTheme.typography.bodyMedium
            )
        }
    }
}
