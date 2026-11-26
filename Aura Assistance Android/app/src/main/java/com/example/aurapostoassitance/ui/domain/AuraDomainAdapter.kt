package com.example.aurapostoassitance.ui.domain

import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.rounded.Chat
import androidx.compose.material.icons.automirrored.rounded.TrendingDown
import androidx.compose.material.icons.rounded.Assessment
import androidx.compose.material.icons.rounded.Build
import androidx.compose.material.icons.rounded.DocumentScanner
import androidx.compose.material.icons.rounded.Inventory2
import androidx.compose.material.icons.rounded.LocalGasStation
import androidx.compose.material.icons.rounded.LocalShipping
import androidx.compose.material.icons.rounded.MedicalServices
import androidx.compose.material.icons.rounded.People
import androidx.compose.material.icons.rounded.Storefront
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import com.example.aurapostoassitance.ui.theme.AuraCyan
import com.example.aurapostoassitance.ui.theme.AuraEmerald
import com.example.aurapostoassitance.ui.theme.AuraPurple
import com.example.aurapostoassitance.ui.theme.StatusWarning

data class DomainTrigger(
    val title: String,
    val description: String,
    val icon: ImageVector,
    val accentColor: Color,
    val query: String
)

data class DomainSuggestion(
    val tag: String,
    val label: String,
    val prompt: String
)

data class DomainPackUiProfile(
    val packId: String,
    val legacySegmentKey: String,
    val displayName: String,
    val shortLabel: String,
    val subtitle: String,
    val icon: ImageVector,
    val resourceTabLabel: String,
    val resourceTabIcon: ImageVector,
    val resourceTabQuery: String,
    val composerPlaceholder: String,
    val emptyHeadline: String,
    val emptySubtitle: String,
    val complianceButtonLabel: String,
    val complianceAuditPromptPrefix: String,
    val complianceTrailLabel: String,
    val quickPrompts: List<String>,
    val emptySuggestions: List<DomainSuggestion>,
    val triggers: List<DomainTrigger>
)

/**
 * Adaptador visual multi-vertical sincronizado com os 5 Domain Packs oficiais do Carbon Core:
 * fuel_convenience, pharmacy_health, retail_supermarket, autocenter_parts e wholesale_distribution.
 */
object AuraDomainAdapter {

    const val PACK_FUEL = "fuel_convenience"
    const val PACK_PHARMACY = "pharmacy_health"
    const val PACK_RETAIL = "retail_supermarket"
    const val PACK_AUTOCENTER = "autocenter_parts"
    const val PACK_WHOLESALE = "wholesale_distribution"

    private val legacyToPackMap = mapOf(
        "postos_redes" to PACK_FUEL,
        "postos" to PACK_FUEL,
        "fuel_convenience" to PACK_FUEL,
        "saude_clinicas" to PACK_PHARMACY,
        "pharmacy_health" to PACK_PHARMACY,
        "varejo" to PACK_RETAIL,
        "retail_supermarket" to PACK_RETAIL,
        "ecommerce" to PACK_RETAIL,
        "autocenter_parts" to PACK_AUTOCENTER,
        "logistica" to PACK_WHOLESALE,
        "wholesale_distribution" to PACK_WHOLESALE,
        "saas_b2b" to PACK_WHOLESALE
    )

    fun normalizePackId(raw: String?): String {
        val key = raw?.trim()?.lowercase().orEmpty()
        return legacyToPackMap[key] ?: PACK_FUEL
    }

    val allProfiles: List<DomainPackUiProfile> = listOf(
        DomainPackUiProfile(
            packId = PACK_FUEL,
            legacySegmentKey = "postos_redes",
            displayName = "Postos & Conveniência",
            shortLabel = "Postos",
            subtitle = "Tanques, LMC ANP, Pista & Conveniência",
            icon = Icons.Rounded.LocalGasStation,
            resourceTabLabel = "Tanques",
            resourceTabIcon = Icons.Rounded.LocalGasStation,
            resourceTabQuery = "Faça a previsão de esgotamento (Run-Out) dos tanques e mostre a autonomia de cada combustível.",
            composerPlaceholder = "Pergunte sobre tanques, LMC, turno ou margem...",
            emptyHeadline = "Como posso acelerar\nsua operação hoje?",
            emptySubtitle = "Peça diagnósticos determinísticos, simule cenários What-If ou audite LMC e turnos.",
            complianceButtonLabel = "Auditar ANP",
            complianceAuditPromptPrefix = "Audite a conformidade deste dado segundo as normas da ANP, LMC (±0.60%) e critérios fiscais",
            complianceTrailLabel = "Trilha auditável SQL Read-Only, Motor Python e conformidade ANP",
            quickPrompts = listOf(
                "Previsão de Ruptura 24h",
                "Fuga Invisível de Margem",
                "Simular Preço What-If",
                "ROI Realizado do Mês",
                "Auditoria LMC ANP",
                "Clientes VIP em Risco"
            ),
            emptySuggestions = listOf(
                DomainSuggestion("Tanques", "Autonomia e lastro dos tanques", "Qual a autonomia atual dos tanques e quais precisam de compra preventiva?"),
                DomainSuggestion("Simulador", "Simular ajuste de preço What-If", "Simule um cenário What-If de ajuste de preço e margem na gasolina comum"),
                DomainSuggestion("Diretoria", "Diagnóstico executivo do turno", "Monte um diagnóstico executivo modular do turno e divergências de caixa"),
                DomainSuggestion("Compliance", "Auditar LMC ANP", "Audite a conformidade do LMC dos tanques de combustível hoje")
            ),
            triggers = listOf(
                DomainTrigger(
                    title = "Previsão de Ruptura & Autonomia",
                    description = "Lastro, autonomia em horas e compras preventivas antecipadas.",
                    icon = Icons.Rounded.LocalGasStation,
                    accentColor = AuraCyan,
                    query = "Faça a previsão de esgotamento (Run-Out) e compras antecipadas dos tanques."
                ),
                DomainTrigger(
                    title = "Detector de Fuga Invisível",
                    description = "Descontos sem alçada, divergências de caixa e vazamento de margem.",
                    icon = Icons.AutoMirrored.Rounded.TrendingDown,
                    accentColor = StatusWarning,
                    query = "Audite as fugas invisíveis de lucro, desvios de caixa e descontos sem alçada."
                ),
                DomainTrigger(
                    title = "Máquina Anti-Churn RFM",
                    description = "Clientes frotistas e VIPs em risco com mensagens de reativação.",
                    icon = Icons.Rounded.People,
                    accentColor = AuraPurple,
                    query = "Gere o lote de clientes VIPs em risco de churn com mensagens de reativação no WhatsApp."
                ),
                DomainTrigger(
                    title = "Conciliação & LMC ANP",
                    description = "Fechamento de turnos, conformidade ANP e conciliação de sangrias.",
                    icon = Icons.Rounded.Assessment,
                    accentColor = AuraEmerald,
                    query = "Audite o fechamento de turno de hoje e conformidade LMC ANP."
                ),
                DomainTrigger(
                    title = "Olhos da AURA (Scanner NPU)",
                    description = "Extração instantânea na NPU de DANFE, notas fiscais e comprovantes.",
                    icon = Icons.Rounded.DocumentScanner,
                    accentColor = AuraPurple,
                    query = "VISION_SCANNER_TRIGGER"
                ),
                DomainTrigger(
                    title = "Monitor de Gatilhos",
                    description = "Acompanhe entrega e retornos dos alertas enviados via WhatsApp.",
                    icon = Icons.AutoMirrored.Rounded.Chat,
                    accentColor = AuraEmerald,
                    query = "OPEN_WHATSAPP_RETURNS"
                )
            )
        ),
        DomainPackUiProfile(
            packId = PACK_PHARMACY,
            legacySegmentKey = "saude_clinicas",
            displayName = "Farmácias & Saúde",
            shortLabel = "Farmácia",
            subtitle = "Curva A, PBM, Validade & SNGPC",
            icon = Icons.Rounded.MedicalServices,
            resourceTabLabel = "Estoque",
            resourceTabIcon = Icons.Rounded.Inventory2,
            resourceTabQuery = "Faça a previsão de ruptura de medicamentos Curva A e lotes próximos do vencimento.",
            composerPlaceholder = "Pergunte sobre ruptura Curva A, PBM, SNGPC ou margem...",
            emptyHeadline = "Inteligência operacional\npara sua farmácia",
            emptySubtitle = "Monitore ruptura Curva A, conciliação PBM, lotes críticos e conformidade SNGPC/ANVISA.",
            complianceButtonLabel = "SNGPC",
            complianceAuditPromptPrefix = "Audite a conformidade deste dado segundo as normas SNGPC/ANVISA e regras fiscais",
            complianceTrailLabel = "Trilha auditável SQL Read-Only, Motor Python e conformidade SNGPC",
            quickPrompts = listOf(
                "Ruptura Curva A",
                "Fechamento Caixa PBM",
                "Conformidade SNGPC",
                "Lotes a Vencer 30d",
                "Simular Margem What-If",
                "ROI Realizado"
            ),
            emptySuggestions = listOf(
                DomainSuggestion("Estoque", "Ruptura de Curva A", "Quais medicamentos Curva A têm risco de ruptura nas próximas 48 horas?"),
                DomainSuggestion("PBM", "Conciliação de caixa PBM", "Audite o fechamento de caixa e repasses PBM do turno atual"),
                DomainSuggestion("ANVISA", "Conformidade SNGPC", "Verifique pendências de escrituração SNGPC e lotes controlados"),
                DomainSuggestion("Margem", "Simular ajuste What-If", "Simule o impacto na margem líquida de reajuste na linha OTC")
            ),
            triggers = listOf(
                DomainTrigger(
                    title = "Ruptura Curva A & Validade",
                    description = "Previsão de esgotamento de SKUs essenciais e alerta de vencimento.",
                    icon = Icons.Rounded.MedicalServices,
                    accentColor = AuraCyan,
                    query = "Faça a previsão de ruptura Curva A e liste lotes críticos próximos do vencimento."
                ),
                DomainTrigger(
                    title = "Auditoria de Margem & PBM",
                    description = "Divergências de repasse PBM, descontos fora de alçada e caixa.",
                    icon = Icons.AutoMirrored.Rounded.TrendingDown,
                    accentColor = StatusWarning,
                    query = "Audite divergências de fechamento de caixa PBM e vazamento de margem."
                ),
                DomainTrigger(
                    title = "Reativação Uso Contínuo",
                    description = "Pacientes de uso contínuo próximos da recompra com lembrete VIP.",
                    icon = Icons.Rounded.People,
                    accentColor = AuraPurple,
                    query = "Gere o lote de clientes de uso contínuo em risco de churn para reativação."
                ),
                DomainTrigger(
                    title = "Conformidade SNGPC",
                    description = "Auditoria de controlados, balanços e rastreabilidade ANVISA.",
                    icon = Icons.Rounded.Assessment,
                    accentColor = AuraEmerald,
                    query = "Audite a conformidade SNGPC e pendências regulatórias de hoje."
                ),
                DomainTrigger(
                    title = "Olhos da AURA (Scanner NPU)",
                    description = "Leitura instantânea de DANFE de distribuidoras e lotes fiscais.",
                    icon = Icons.Rounded.DocumentScanner,
                    accentColor = AuraPurple,
                    query = "VISION_SCANNER_TRIGGER"
                ),
                DomainTrigger(
                    title = "Monitor de Gatilhos",
                    description = "Acompanhe retornos e aprovações enviadas via WhatsApp.",
                    icon = Icons.AutoMirrored.Rounded.Chat,
                    accentColor = AuraEmerald,
                    query = "OPEN_WHATSAPP_RETURNS"
                )
            )
        ),
        DomainPackUiProfile(
            packId = PACK_RETAIL,
            legacySegmentKey = "varejo",
            displayName = "Supermercados & Varejo",
            shortLabel = "Varejo",
            subtitle = "Gôndola, Quebra, PDV & Giro",
            icon = Icons.Rounded.Storefront,
            resourceTabLabel = "Estoque",
            resourceTabIcon = Icons.Rounded.Inventory2,
            resourceTabQuery = "Faça a previsão de ruptura de gôndola e produtos de alto giro.",
            composerPlaceholder = "Pergunte sobre ruptura, quebras, PDV ou margem...",
            emptyHeadline = "Copiloto executivo\ndo seu varejo",
            emptySubtitle = "Identifique rupturas de gôndola, quebras de margem, descontos sem alçada e cross-sell.",
            complianceButtonLabel = "Fiscal",
            complianceAuditPromptPrefix = "Audite a conformidade fiscal, NFC-e e divergências operacionais deste dado",
            complianceTrailLabel = "Trilha auditável SQL Read-Only, Motor Python e auditoria fiscal",
            quickPrompts = listOf(
                "Ruptura de Gôndola",
                "Fuga Invisível PDV",
                "Cross-Sell Cesta",
                "Capital Parado",
                "Simular Preço What-If",
                "ROI Realizado"
            ),
            emptySuggestions = listOf(
                DomainSuggestion("Gôndola", "Ruptura de alto giro", "Quais SKUs de alto giro estão em risco de ruptura hoje?"),
                DomainSuggestion("PDV", "Auditoria de cancelamentos", "Audite cancelamentos, sangrias e descontos sem alçada no PDV"),
                DomainSuggestion("Cesta", "Oportunidades de cross-sell", "Quais combinações de produtos têm maior potencial de cross-sell?"),
                DomainSuggestion("Simulador", "Cenário What-If de margem", "Simule um cenário What-If de promoção nos itens líderes de tráfego")
            ),
            triggers = listOf(
                DomainTrigger(
                    title = "Ruptura de Gôndola & Giro",
                    description = "Itens Curva A em risco de falta e sugestão de pedido de reposição.",
                    icon = Icons.Rounded.Storefront,
                    accentColor = AuraCyan,
                    query = "Faça a previsão de ruptura de estoque e pedidos prioritários de reposição."
                ),
                DomainTrigger(
                    title = "Detector de Fuga no PDV",
                    description = "Cancelamentos anômalos, descontos sem alçada e quebras operacionais.",
                    icon = Icons.AutoMirrored.Rounded.TrendingDown,
                    accentColor = StatusWarning,
                    query = "Audite as fugas invisíveis de lucro, cancelamentos e desvios de caixa no PDV."
                ),
                DomainTrigger(
                    title = "Reativação & Cross-Sell",
                    description = "Clientes recorrentes em risco e oportunidades de aumento de ticket.",
                    icon = Icons.Rounded.People,
                    accentColor = AuraPurple,
                    query = "Gere a análise de clientes em risco de churn e ações de reativação."
                ),
                DomainTrigger(
                    title = "Fechamento de Turno & Caixa",
                    description = "Conciliação de operadores, sangrias e conformidade fiscal NFC-e.",
                    icon = Icons.Rounded.Assessment,
                    accentColor = AuraEmerald,
                    query = "Audite o fechamento de caixa e conciliação de turnos de hoje."
                ),
                DomainTrigger(
                    title = "Olhos da AURA (Scanner NPU)",
                    description = "Extração instantânea de notas fiscais (DANFE) e recebimento.",
                    icon = Icons.Rounded.DocumentScanner,
                    accentColor = AuraPurple,
                    query = "VISION_SCANNER_TRIGGER"
                ),
                DomainTrigger(
                    title = "Monitor de Gatilhos",
                    description = "Acompanhe entrega e respostas dos alertas enviados via WhatsApp.",
                    icon = Icons.AutoMirrored.Rounded.Chat,
                    accentColor = AuraEmerald,
                    query = "OPEN_WHATSAPP_RETURNS"
                )
            )
        ),
        DomainPackUiProfile(
            packId = PACK_AUTOCENTER,
            legacySegmentKey = "autocenter_parts",
            displayName = "Autocentro & Peças",
            shortLabel = "Autocentro",
            subtitle = "OS, Peças, Lubrificantes & Box",
            icon = Icons.Rounded.Build,
            resourceTabLabel = "Peças",
            resourceTabIcon = Icons.Rounded.Inventory2,
            resourceTabQuery = "Mostre a previsão de esgotamento de peças, pneus e lubrificantes críticos.",
            composerPlaceholder = "Pergunte sobre estoque de peças, OS, margem ou box...",
            emptyHeadline = "Precisão operacional\nno seu autocentro",
            emptySubtitle = "Acompanhe giro de peças e lubrificantes, rentabilidade por OS e retorno de clientes.",
            complianceButtonLabel = "Fiscal",
            complianceAuditPromptPrefix = "Audite a conformidade fiscal, garantias e margens operacionais deste dado",
            complianceTrailLabel = "Trilha auditável SQL Read-Only, Motor Python e auditoria de OS",
            quickPrompts = listOf(
                "Ruptura de Peças",
                "Margem por OS",
                "Capital Parado SKUs",
                "Revisões em Atraso",
                "Simular Combo What-If",
                "ROI Realizado"
            ),
            emptySuggestions = listOf(
                DomainSuggestion("Peças", "Estoque crítico de giro", "Quais peças e lubrificantes estão com risco de falta esta semana?"),
                DomainSuggestion("Oficina", "Fuga de margem em OS", "Audite descontos sem alçada e divergências de caixa nas OS"),
                DomainSuggestion("Retorno", "Clientes para revisão", "Liste clientes VIPs com revisão vencida para reativação via WhatsApp"),
                DomainSuggestion("Simulador", "Simular combo de serviços", "Simule um cenário What-If de precificação para troca de óleo + filtros")
            ),
            triggers = listOf(
                DomainTrigger(
                    title = "Ruptura de Peças & Lubrificantes",
                    description = "Previsão de esgotamento de SKUs de alta demanda no box.",
                    icon = Icons.Rounded.Build,
                    accentColor = AuraCyan,
                    query = "Faça a previsão de ruptura de peças, filtros e lubrificantes críticos."
                ),
                DomainTrigger(
                    title = "Fuga de Margem em OS",
                    description = "Descontos fora de política, retrabalho e desvios de caixa.",
                    icon = Icons.AutoMirrored.Rounded.TrendingDown,
                    accentColor = StatusWarning,
                    query = "Audite fugas invisíveis de margem nas ordens de serviço e caixa."
                ),
                DomainTrigger(
                    title = "Radar de Revisões RFM",
                    description = "Clientes prontos para revisão preventiva com disparo personalizado.",
                    icon = Icons.Rounded.People,
                    accentColor = AuraPurple,
                    query = "Gere o lote de clientes em risco de churn ou revisão pendente."
                ),
                DomainTrigger(
                    title = "Conciliação de Turno & Caixa",
                    description = "Fechamento diário de caixa, cartões e conformidade fiscal.",
                    icon = Icons.Rounded.Assessment,
                    accentColor = AuraEmerald,
                    query = "Audite o fechamento de caixa e conciliação operacional de hoje."
                ),
                DomainTrigger(
                    title = "Olhos da AURA (Scanner NPU)",
                    description = "Leitura instantânea de DANFE de autopeças e ordens de compra.",
                    icon = Icons.Rounded.DocumentScanner,
                    accentColor = AuraPurple,
                    query = "VISION_SCANNER_TRIGGER"
                ),
                DomainTrigger(
                    title = "Monitor de Gatilhos",
                    description = "Acompanhe retornos e aprovações enviadas via WhatsApp.",
                    icon = Icons.AutoMirrored.Rounded.Chat,
                    accentColor = AuraEmerald,
                    query = "OPEN_WHATSAPP_RETURNS"
                )
            )
        ),
        DomainPackUiProfile(
            packId = PACK_WHOLESALE,
            legacySegmentKey = "logistica",
            displayName = "Atacado & Distribuição",
            shortLabel = "Atacado",
            subtitle = "Lotes, Giro B2B, Rotas & Margem",
            icon = Icons.Rounded.LocalShipping,
            resourceTabLabel = "Estoque",
            resourceTabIcon = Icons.Rounded.Inventory2,
            resourceTabQuery = "Faça a previsão de cobertura de estoque B2B e capital imobilizado por categoria.",
            composerPlaceholder = "Pergunte sobre lotes, carteira B2B, margem ou cobertura...",
            emptyHeadline = "Comando estratégico\nda sua distribuição",
            emptySubtitle = "Monitore cobertura de estoque, carteira B2B em risco, descontos comerciais e ROI.",
            complianceButtonLabel = "Fiscal",
            complianceAuditPromptPrefix = "Audite a conformidade fiscal NF-e, ST e critérios comerciais deste dado",
            complianceTrailLabel = "Trilha auditável SQL Read-Only, Motor Python e auditoria B2B",
            quickPrompts = listOf(
                "Cobertura Estoque B2B",
                "Carteira B2B em Risco",
                "Erosão de Margem",
                "Capital Ocioso",
                "Simular Lote What-If",
                "ROI Realizado"
            ),
            emptySuggestions = listOf(
                DomainSuggestion("Cobertura", "Risco de ruptura em lotes", "Quais categorias do CD estão abaixo da cobertura mínima de estoque?"),
                DomainSuggestion("Comercial", "Descontos fora de alçada", "Audite fugas de margem e descontos comerciais fora da política"),
                DomainSuggestion("Carteira", "Clientes B2B inativos", "Identifique contas B2B recorrentes em risco de churn para reativação"),
                DomainSuggestion("Simulador", "Simular lote de compra", "Simule um cenário What-If de compra em lote com desconto progressivo")
            ),
            triggers = listOf(
                DomainTrigger(
                    title = "Cobertura & Ruptura de Lotes",
                    description = "Previsão de esgotamento no CD e dimensionamento de reposição.",
                    icon = Icons.Rounded.LocalShipping,
                    accentColor = AuraCyan,
                    query = "Faça a previsão de esgotamento (Run-Out) e reposição de lotes no estoque."
                ),
                DomainTrigger(
                    title = "Detector de Erosão B2B",
                    description = "Descontos fora de tabela, bonificações anômalas e desvios.",
                    icon = Icons.AutoMirrored.Rounded.TrendingDown,
                    accentColor = StatusWarning,
                    query = "Audite as fugas invisíveis de margem e descontos sem alçada na carteira B2B."
                ),
                DomainTrigger(
                    title = "Reativação de Carteira RFM",
                    description = "Contas B2B recorrentes sem pedido com roteiro de reativação.",
                    icon = Icons.Rounded.People,
                    accentColor = AuraPurple,
                    query = "Gere o lote de clientes B2B VIPs em risco de churn para reativação."
                ),
                DomainTrigger(
                    title = "Conciliação & Faturamento",
                    description = "Fechamento diário de faturamento, baixas e conformidade NF-e.",
                    icon = Icons.Rounded.Assessment,
                    accentColor = AuraEmerald,
                    query = "Audite o fechamento financeiro e operacional de hoje."
                ),
                DomainTrigger(
                    title = "Olhos da AURA (Scanner NPU)",
                    description = "Extração instantânea de DANFE, CT-e e romaneios na NPU.",
                    icon = Icons.Rounded.DocumentScanner,
                    accentColor = AuraPurple,
                    query = "VISION_SCANNER_TRIGGER"
                ),
                DomainTrigger(
                    title = "Monitor de Gatilhos",
                    description = "Acompanhe entrega e respostas dos alertas enviados via WhatsApp.",
                    icon = Icons.AutoMirrored.Rounded.Chat,
                    accentColor = AuraEmerald,
                    query = "OPEN_WHATSAPP_RETURNS"
                )
            )
        )
    )

    fun profileFor(packIdOrLegacy: String?): DomainPackUiProfile {
        val normalized = normalizePackId(packIdOrLegacy)
        return allProfiles.firstOrNull { it.packId == normalized } ?: allProfiles.first()
    }
}
