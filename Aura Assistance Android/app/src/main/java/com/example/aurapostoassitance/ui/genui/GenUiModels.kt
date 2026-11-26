package com.example.aurapostoassitance.ui.genui

import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.booleanOrNull
import kotlinx.serialization.json.doubleOrNull
import kotlinx.serialization.json.intOrNull
import kotlinx.serialization.json.jsonObject

data class GenUiKpi(
    val label: String,
    val value: String,
    val delta: String?,
    val trend: String,
    val status: String,
    val subtext: String?
)

data class GenUiComparisonRow(
    val name: String,
    val primary: String,
    val secondary: String,
    val gap: String?,
    val status: String,
    val observation: String?
)

data class GenUiRankItem(
    val rank: Int,
    val title: String,
    val subtitle: String?,
    val value: String,
    val tag: String?,
    val status: String
)

data class GenUiTimelineEvent(
    val timestamp: String,
    val title: String,
    val description: String?,
    val status: String
)

data class GenUiAlert(
    val title: String,
    val message: String,
    val severity: String,
    val actionLabel: String?
)

data class GenUiTank(
    val code: String,
    val fuel: String,
    val capacityL: Double,
    val balanceL: Double,
    val occupancyPct: Double,
    val autonomyHours: Double?,
    val critical: Boolean,
    val operationalStatus: String
)

data class GenUiAction(
    val actionId: String,
    val label: String,
    val type: String,
    val variant: String,
    val requiresConfirmation: Boolean,
    val isDestructive: Boolean,
    val targetRole: String? = null,
    val contextSummary: String? = null,
    val targetPhone: String? = null,
    val targetContactName: String? = null,
    val includeAttachment: Boolean = true
)

fun GenUiAction.isHandoffAction(): Boolean =
    type.equals("handoff", ignoreCase = true) || actionId.startsWith("handoff_", ignoreCase = true)

object AuraWhatsAppReportFormatter {

    fun markdownToWhatsApp(raw: String): String {
        if (raw.isBlank()) return ""
        val lines = raw.replace("\r\n", "\n").lines()
        val formatted = lines.map { line ->
            val trimmed = line.trim()
            when {
                trimmed.startsWith("### ") -> "*${trimmed.removePrefix("### ").trim()}*"
                trimmed.startsWith("## ") -> "*${trimmed.removePrefix("## ").trim()}*"
                trimmed.startsWith("# ") -> "*${trimmed.removePrefix("# ").trim()}*"
                trimmed.startsWith("- ") -> "• ${convertInlineMarkdown(trimmed.removePrefix("- ").trim())}"
                trimmed.startsWith("* ") -> "• ${convertInlineMarkdown(trimmed.removePrefix("* ").trim())}"
                else -> convertInlineMarkdown(trimmed)
            }
        }
        return formatted.joinToString("\n").replace(Regex("\n{3,}"), "\n\n").trim()
    }

    private fun convertInlineMarkdown(text: String): String {
        return text
            .replace(Regex("\\*\\*(.+?)\\*\\*"), "*$1*")
            .replace(Regex("__(.+?)__"), "_$1_")
    }

    fun buildReport(
        card: GenUiCard?,
        narrativeText: String?,
        actionLabel: String,
        unitLabel: String = "Posto 01"
    ): String {
        val nowStr = java.text.SimpleDateFormat("dd/MM/yyyy HH:mm", java.util.Locale("pt", "BR"))
            .format(java.util.Date())

        return buildString {
            appendLine("*AURA | RELATÓRIO DE AUDITORIA EXECUTIVA*")
            appendLine("*Unidade:* $unitLabel  •  *Emissão:* $nowStr")
            appendLine("━━━━━━━━━━━━━━━━━━━━━━")

            if (card != null) {
                appendLine()
                appendLine("*📌 ${card.title}*")
                (card.diagnosis ?: card.subtitle)?.takeIf { it.isNotBlank() }?.let { diag ->
                    appendLine(diag.trim())
                }

                card.blocks.filterIsInstance<GenUiBlock.AlertCallout>().forEach { blk ->
                    appendLine()
                    appendLine("*🚨 Alerta Identificado*")
                    appendLine("• *${blk.alert.title}*")
                    if (blk.alert.message.isNotBlank()) {
                        appendLine("  _${blk.alert.message}_")
                    }
                }

                val kpiBlocks = card.blocks.filterIsInstance<GenUiBlock.KpiGrid>()
                if (kpiBlocks.isNotEmpty()) {
                    appendLine()
                    appendLine("*📊 Parâmetros & Indicadores*")
                    kpiBlocks.forEach { grid ->
                        grid.kpis.forEach { kpi ->
                            val extra = kpi.delta?.let { " ($it)" } ?: ""
                            appendLine("• *${kpi.label}:* ${kpi.value}$extra")
                        }
                    }
                }

                val compBlocks = card.blocks.filterIsInstance<GenUiBlock.Comparison>()
                if (compBlocks.isNotEmpty()) {
                    appendLine()
                    appendLine("*⚖️ Comparativo*")
                    compBlocks.forEach { comp ->
                        comp.rows.take(5).forEach { row ->
                            val gapTxt = row.gap?.let { " | Dif: $it" } ?: ""
                            appendLine("• *${row.name}:* ${row.primary} (Ref: ${row.secondary})$gapTxt")
                        }
                    }
                }
            }

            val cleanNarrative = markdownToWhatsApp(narrativeText.orEmpty())
            if (cleanNarrative.isNotBlank()) {
                appendLine()
                appendLine("*🧾 Parecer Técnico Completo*")
                appendLine(cleanNarrative.take(1500))
            }

            val notes = card?.blocks?.filterIsInstance<GenUiBlock.Note>().orEmpty()
            if (notes.isNotEmpty()) {
                appendLine()
                appendLine("*🛠️ Procedimento Recomendado no ERP*")
                notes.forEach { note ->
                    note.title?.takeIf { it.isNotBlank() }?.let { t ->
                        appendLine("*${t.trim()}*")
                    }
                    note.text.split("\n").map { it.trim() }.filter { it.isNotBlank() }.forEach { p ->
                        val colon = p.indexOf(':')
                        if (colon in 3..32) {
                            val prefix = p.substring(0, colon + 1)
                            val body = p.substring(colon + 1).trimStart()
                            appendLine("• *$prefix* $body")
                        } else {
                            appendLine("• $p")
                        }
                    }
                }
            }

            appendLine()
            appendLine("━━━━━━━━━━━━━━━━━━━━━━")
            append("_Solicitação: ${actionLabel}_")
        }.trim()
    }
}

/** Blocos nativos renderizaveis pelo app (equivalentes aos "blocos Lego" do painel web). */
sealed class GenUiBlock {
    data class KpiGrid(val title: String?, val subtitle: String?, val kpis: List<GenUiKpi>) : GenUiBlock()
    data class Comparison(val title: String?, val subtitle: String?, val rows: List<GenUiComparisonRow>) : GenUiBlock()
    data class Ranking(val title: String?, val subtitle: String?, val items: List<GenUiRankItem>) : GenUiBlock()
    data class Timeline(val title: String?, val subtitle: String?, val events: List<GenUiTimelineEvent>) : GenUiBlock()
    data class AlertCallout(val alert: GenUiAlert) : GenUiBlock()
    data class Tanks(val title: String?, val tanks: List<GenUiTank>, val hiddenInactive: Int) : GenUiBlock()
    data class Note(val title: String?, val text: String) : GenUiBlock()

    /** Core P1.3 / P2.4: Simulador interativo What-If de elasticidade preço-volume-margem. */
    data class WhatIfSimulator(
        val title: String?,
        val productScope: String,
        val baseMonthlyProfit: Double,
        val baseMarginPct: Double,
        val initialPriceDeltaPct: Double = 0.0,
        val initialVolumeDeltaPct: Double = 0.0,
        val initialBatchDeltaPct: Double = 0.0,
        val elasticityFactor: Double = -1.2,
        val recommendation: String? = null
    ) : GenUiBlock()

    /** Core P1.3: Scorecard de ROI Realizado (Outcome Tracker: Projetado vs Realizado). */
    data class RealizedRoiScorecard(
        val title: String?,
        val totalRoiValue: String,
        val roiMultiple: String?,
        val leaksStopped: String,
        val marginGain: String,
        val captureRatePct: String,
        val auditedVouchers: List<GenUiTimelineEvent> = emptyList()
    ) : GenUiBlock()

    /** Core P1.3: Cartão HITL para confirmação de ação externa MCP / Outbox ERP com TTL e HMAC. */
    data class McpActionConfirmation(
        val title: String?,
        val targetSystem: String,
        val operation: String,
        val reversible: Boolean,
        val ttlSeconds: Int,
        val beforeSummary: String,
        val afterSummary: String,
        val voucherHash: String? = null
    ) : GenUiBlock()
}

data class GenUiCard(
    val componentName: String,
    val title: String,
    val subtitle: String?,
    val diagnosis: String?,
    val confidence: Float?,
    val severity: String,
    val blocks: List<GenUiBlock>,
    val actions: List<GenUiAction>,
    val limitations: List<String>
)

object GenUiParser {

    private val json = Json { ignoreUnknownKeys = true; isLenient = true }

    /** Nunca expoe nome tecnico de componente (ex: render_XyzUI) ao usuario final. */
    fun friendlyTitle(componentName: String, intent: String?): String {
        val map = mapOf(
            "diagnostico_modular" to "Diagnóstico Executivo Modular",
            "render_GenerativeModularCardUI" to "Diagnóstico Executivo Modular",
            "previsao_tanques" to "Tanques e Autonomia",
            "render_TankRunOutForecastUI" to "Tanques e Autonomia",
            "mentoria_decisao" to "Mentor de Decisões",
            "lmc_anp" to "LMC ANP",
            "auditoria_turno" to "Conciliação de Turno",
            "WhatIfSimulatorUI" to "Simulador What-If de Margem",
            "render_WhatIfSimulatorUI" to "Simulador What-If de Margem",
            "WhatIfSimulatorWidget" to "Simulador What-If de Margem",
            "ElasticityBatchSimulatorUI" to "Simulador de Elasticidade & Lote",
            "render_ElasticityBatchSimulatorUI" to "Simulador de Elasticidade & Lote",
            "RealizedRoiScorecardUI" to "Scorecard de ROI Realizado",
            "render_RealizedRoiScorecardUI" to "Scorecard de ROI Realizado",
            "RealizedRoiScorecardWidget" to "Scorecard de ROI Realizado",
            "McpActionConfirmationUI" to "Governança de Ação MCP (HITL)",
            "render_McpActionConfirmationUI" to "Governança de Ação MCP (HITL)",
            "McpActionConfirmationWidget" to "Governança de Ação MCP (HITL)",
            "FinancialErosionUI" to "Auditoria de Erosão de Margem",
            "MarginWaterfallUI" to "Cascata de Margem Operacional",
            "DeadCapitalOpportunityUI" to "Oportunidade de Capital Ocioso",
            "PumpPerformanceUI" to "Performance Operacional",
            "SRETelemetryUI" to "Telemetria Operacional AURA"
        )
        map[intent]?.let { return it }
        map[componentName]?.let { return it }
        val clean = componentName
            .removePrefix("render_")
            .replace(Regex("(CardUI|UI|Widget|Card)$"), "")
            .replace("_", " ")
            .replace(Regex("([a-z])([A-Z])"), "$1 $2")
            .trim()
        return clean.ifBlank { "Resultado da AURA" }.replaceFirstChar { it.uppercase() }
    }

    fun parse(envelopeJson: String): GenUiCard? = runCatching {
        val root = json.parseToJsonElement(envelopeJson).jsonObject
        val component = root.str("component_name") ?: root.str("client_component") ?: return null
        val intent = root.str("intent")
        val props = root["props"] as? JsonObject ?: JsonObject(emptyMap())

        val blocks = mutableListOf<GenUiBlock>()
        var severity = "info"

        val title = props.str("title")
            ?: (props["assessment"] as? JsonObject)?.str("title")
            ?: friendlyTitle(component, intent)

        // Componente modular generativo: props.blocks
        (props["blocks"] as? JsonArray)?.forEach { el ->
            (el as? JsonObject)?.let { parseBlock(it)?.let(blocks::add) }
        }

        // Previsao de tanques: metricas + medidores
        if (props["tanks"] is JsonArray) {
            (props["assessment"] as? JsonObject)?.str("severity")?.let { severity = it }
            blocks += tankBlocks(props)
        }

        // Core P1.3: WhatIfSimulatorUI / ElasticityBatchSimulatorUI
        val compNorm = component.lowercase()
        if (compNorm.contains("whatif") || compNorm.contains("elasticity")) {
            blocks += parseWhatIfBlock(props)
        }

        // Core P1.3: RealizedRoiScorecardUI
        if (compNorm.contains("realizedroi") || compNorm.contains("roiscorecard")) {
            blocks += parseRealizedRoiBlock(props)
        }

        // Core P1.3: McpActionConfirmationUI
        if (compNorm.contains("mcpaction")) {
            severity = props.str("severity") ?: "warning"
            blocks += parseMcpConfirmationBlock(props)
        }

        // LMC Compliance Report (Portaria ANP 26/1992)
        if (compNorm.contains("lmccompliance") || (blocks.isEmpty() && props.str("status_conformidade") != null)) {
            val lmcStatus = props.str("status_conformidade") ?: props.str("status_geral") ?: "INFO"
            if (lmcStatus.contains("CRITIC", true) || lmcStatus.contains("ALERTA", true)) {
                severity = "critical"
            } else if (lmcStatus.contains("CONFORME", true)) {
                severity = "success"
            }
            blocks += parseLmcComplianceBlocks(props)
        }

        // Fallback textual quando nao ha bloco estruturado
        if (blocks.isEmpty()) {
            val summary = root.str("executive_summary") ?: root.str("summary_text")
            val diag = props.str("diagnosis")
            val subt = props.str("subtitle")
            if (!summary.isNullOrBlank() && summary != diag && summary != subt) {
                blocks += GenUiBlock.Note(null, summary)
            }
        }

        val parsedActions = (root["actions"] as? JsonArray).orEmpty().mapNotNull { el ->
            val o = el as? JsonObject ?: return@mapNotNull null
            val rawType = o.str("action_type") ?: "mutation"
            // "inspection" abre o Companion Canvas do painel web: sem equivalente no app
            if (rawType == "inspection") return@mapNotNull null
            val id = o.str("action_id") ?: return@mapNotNull null
            val label = o.str("label") ?: return@mapNotNull null
            val payloadObj = o["payload"] as? JsonObject
            val payloadIntent = payloadObj?.str("intent").orEmpty()
            val resolvedType = if (
                rawType.equals("handoff", ignoreCase = true) ||
                payloadIntent.startsWith("handoff_", ignoreCase = true) ||
                label.contains("WhatsApp", ignoreCase = true)
            ) {
                "handoff"
            } else {
                rawType
            }
            val inferredRole = inferTargetRole("$id $payloadIntent $label", label)
            GenUiAction(
                actionId = id,
                label = label,
                type = resolvedType,
                variant = o.str("variant") ?: "primary",
                requiresConfirmation = o.bool("requires_confirmation") ?: true,
                isDestructive = o.bool("is_destructive") ?: false,
                targetRole = inferredRole
            )
        }

        val diagnosisText = props.str("diagnosis")
        val fiscalFingerprint = listOfNotNull(title, intent, component, diagnosisText).joinToString(" ").uppercase()
        val isFiscalCard = listOf("SEFAZ", "DANFE", "FISCAL", "REJEI", "NF-E", "NFE", "ICMS", "CFOP", "W07-10").any {
            fiscalFingerprint.contains(it)
        }
        val actions = if (parsedActions.isEmpty() && isFiscalCard) {
            listOf(
                GenUiAction(
                    actionId = "handoff_fiscal_contador",
                    label = "Enviar resumo p/ Contador (WhatsApp)",
                    type = "handoff",
                    variant = "primary",
                    requiresConfirmation = true,
                    isDestructive = false,
                    targetRole = "Contador"
                ),
                GenUiAction(
                    actionId = "fiscal_register_pendencia",
                    label = "Registrar pendência fiscal no Journal",
                    type = "mutation",
                    variant = "secondary",
                    requiresConfirmation = true,
                    isDestructive = false
                )
            )
        } else {
            parsedActions
        }

        GenUiCard(
            componentName = component,
            title = title,
            subtitle = props.str("subtitle"),
            diagnosis = diagnosisText,
            confidence = props.dbl("confidence_score")?.toFloat(),
            severity = severity,
            blocks = blocks,
            actions = actions,
            limitations = (props["limitations"] as? JsonArray).orEmpty().mapNotNull { (it as? JsonPrimitive)?.content }
        )
    }.getOrNull()

    private fun inferTargetRole(actionId: String, label: String): String? {
        val text = "$actionId $label".lowercase()
        return when {
            text.contains("contador") || text.contains("fiscal") || text.contains("sefaz") -> "Contador"
            text.contains("supplier") || text.contains("fornec") || text.contains("cotac") -> "Fornecedor"
            text.contains("team") || text.contains("equipe") || text.contains("gerente") || text.contains("pista") -> "Gerente de Pista"
            else -> null
        }
    }

    private fun parseBlock(o: JsonObject): GenUiBlock? {
        val title = o.str("title")
        val subtitle = o.str("subtitle")
        return when (o.str("block_type")) {
            "kpi_grid" -> GenUiBlock.KpiGrid(title, subtitle, (o["kpis"] as? JsonArray).orEmpty().mapNotNull {
                val k = it as? JsonObject ?: return@mapNotNull null
                GenUiKpi(
                    label = k.str("label") ?: return@mapNotNull null,
                    value = k.str("value") ?: "-",
                    delta = k.str("delta"),
                    trend = k.str("trend") ?: "neutral",
                    status = k.str("status") ?: "neutral",
                    subtext = k.str("subtext")
                )
            }).takeIf { it.kpis.isNotEmpty() }

            "comparison_table" -> GenUiBlock.Comparison(title, subtitle, (o["comparison_rows"] as? JsonArray).orEmpty().mapNotNull {
                val r = it as? JsonObject ?: return@mapNotNull null
                GenUiComparisonRow(
                    name = r.str("name") ?: return@mapNotNull null,
                    primary = r.str("primary_value") ?: "-",
                    secondary = r.str("secondary_value") ?: "-",
                    gap = r.str("gap"),
                    status = r.str("status") ?: "neutral",
                    observation = r.str("observation")
                )
            }).takeIf { it.rows.isNotEmpty() }

            "ranking_list" -> GenUiBlock.Ranking(title, subtitle, (o["ranking_items"] as? JsonArray).orEmpty().mapNotNull {
                val r = it as? JsonObject ?: return@mapNotNull null
                GenUiRankItem(
                    rank = r.int("rank") ?: 0,
                    title = r.str("title") ?: return@mapNotNull null,
                    subtitle = r.str("subtitle"),
                    value = r.str("value") ?: "-",
                    tag = r.str("tag"),
                    status = r.str("status") ?: "neutral"
                )
            }).takeIf { it.items.isNotEmpty() }

            "timeline_feed" -> GenUiBlock.Timeline(title, subtitle, (o["timeline_events"] as? JsonArray).orEmpty().mapNotNull {
                val e = it as? JsonObject ?: return@mapNotNull null
                GenUiTimelineEvent(
                    timestamp = e.str("timestamp") ?: "",
                    title = e.str("title") ?: return@mapNotNull null,
                    description = e.str("description"),
                    status = e.str("status") ?: "neutral"
                )
            }).takeIf { it.events.isNotEmpty() }

            "alert_callout" -> (o["alert"] as? JsonObject)?.let { a ->
                GenUiBlock.AlertCallout(
                    GenUiAlert(
                        title = a.str("title") ?: return null,
                        message = a.str("message") ?: "",
                        severity = a.str("severity") ?: "info",
                        actionLabel = a.str("action_label")
                    )
                )
            }

            "what_if_simulator" -> parseWhatIfBlock(o)
            "realized_roi_scorecard" -> parseRealizedRoiBlock(o)
            "mcp_action_confirmation" -> parseMcpConfirmationBlock(o)
            "custom_content" -> o.str("custom_content")?.let { GenUiBlock.Note(title, it) }
            else -> null
        }
    }

    private fun parseWhatIfBlock(props: JsonObject): GenUiBlock.WhatIfSimulator {
        return GenUiBlock.WhatIfSimulator(
            title = props.str("title"),
            productScope = props.str("product_or_scope") ?: props.str("product_name") ?: props.str("scope") ?: "Mix Operacional",
            baseMonthlyProfit = props.dbl("base_monthly_profit") ?: props.dbl("base_profit") ?: 48500.0,
            baseMarginPct = props.dbl("base_margin_pct") ?: 14.5,
            initialPriceDeltaPct = props.dbl("price_delta_pct") ?: 0.0,
            initialVolumeDeltaPct = props.dbl("volume_delta_pct") ?: 0.0,
            initialBatchDeltaPct = props.dbl("batch_size_delta_pct") ?: 0.0,
            elasticityFactor = props.dbl("elasticity_factor") ?: -1.15,
            recommendation = props.str("recommendation") ?: props.str("diagnosis")
        )
    }

    private fun parseRealizedRoiBlock(props: JsonObject): GenUiBlock.RealizedRoiScorecard {
        val vouchers = (props["vouchers"] as? JsonArray ?: props["audited_actions"] as? JsonArray).orEmpty().mapNotNull { el ->
            val o = el as? JsonObject ?: return@mapNotNull null
            GenUiTimelineEvent(
                timestamp = o.str("timestamp") ?: o.str("date") ?: "",
                title = o.str("title") ?: o.str("action_label") ?: return@mapNotNull null,
                description = o.str("impact_value") ?: o.str("description"),
                status = o.str("status") ?: "success"
            )
        }
        return GenUiBlock.RealizedRoiScorecard(
            title = props.str("title"),
            totalRoiValue = props.str("total_roi_formatted") ?: props.str("realized_roi") ?: "R$ 0,00",
            roiMultiple = props.str("roi_multiple"),
            leaksStopped = props.str("leaks_stopped") ?: "R$ 0,00",
            marginGain = props.str("margin_gain") ?: "R$ 0,00",
            captureRatePct = props.str("capture_rate_pct") ?: "0%",
            auditedVouchers = vouchers
        )
    }

    private fun parseMcpConfirmationBlock(props: JsonObject): GenUiBlock.McpActionConfirmation {
        return GenUiBlock.McpActionConfirmation(
            title = props.str("title"),
            targetSystem = props.str("target_system") ?: props.str("connector") ?: "ERP Local",
            operation = props.str("operation") ?: props.str("action_name") ?: "Atualização Operacional",
            reversible = props.bool("reversible") ?: true,
            ttlSeconds = props.int("ttl_seconds") ?: 300,
            beforeSummary = props.str("before_summary") ?: props.str("current_state") ?: "Estado atual",
            afterSummary = props.str("after_summary") ?: props.str("proposed_state") ?: "Estado proposto",
            voucherHash = props.str("voucher_hmac") ?: props.str("voucher_id")
        )
    }

    private fun parseLmcComplianceBlocks(props: JsonObject): List<GenUiBlock> {
        val out = mutableListOf<GenUiBlock>()
        val statusConf = props.str("status_conformidade") ?: props.str("status_geral") ?: "AUDITORIA"
        val varPct = props.dbl("variacao_volumetrica_pct")
        val tolPct = props.dbl("tolerancia_legal_pct") ?: 0.60
        val isCrit = statusConf.contains("CRITIC", true) || statusConf.contains("ALERTA", true)

        val kpis = mutableListOf<GenUiKpi>()
        kpis += GenUiKpi(
            label = "Variação Volumétrica LMC",
            value = varPct?.let { "${"%+.2f".format(it)}%" } ?: statusConf,
            delta = "Tolerância ±${"%.2f".format(tolPct)}%",
            trend = if (isCrit) "down" else "up",
            status = if (isCrit) "danger" else "success",
            subtext = "Portaria ANP 26/1992"
        )
        props.dbl("total_vendas_litros")?.let {
            kpis += GenUiKpi("Vendas", "${fmtNumber(it)} L", null, "neutral", "info", null)
        }
        props.dbl("total_estoque_fisico_litros")?.let {
            kpis += GenUiKpi("Físico", "${fmtNumber(it)} L", null, "neutral", "neutral", null)
        }
        props.dbl("total_estoque_escriturado_litros")?.let {
            kpis += GenUiKpi("Escriturado", "${fmtNumber(it)} L", null, "neutral", "neutral", null)
        }
        if (kpis.isNotEmpty()) {
            out += GenUiBlock.KpiGrid("Auditoria LMC ANP", null, kpis)
        }

        props.str("parecer_regulatorio")?.let { parecer ->
            out += GenUiBlock.AlertCallout(
                GenUiAlert(
                    title = if (isCrit) "Risco Regulatório ANP" else "Conformidade ANP",
                    message = parecer,
                    severity = if (isCrit) "danger" else "success",
                    actionLabel = null
                )
            )
        }

        val tanquesRows = (props["tanques"] as? JsonArray).orEmpty().mapNotNull { el ->
            val t = el as? JsonObject ?: return@mapNotNull null
            val name = t.str("combustivel") ?: t.str("tanque") ?: return@mapNotNull null
            val fis = t.dbl("estoque_final_fisico_litros")?.let { "${fmtNumber(it)} L" } ?: "-"
            val esc = t.dbl("estoque_contabil_litros")?.let { "${fmtNumber(it)} L" } ?: "-"
            val vp = t.dbl("variacao_pct")?.let { "${"%+.2f".format(it)}%" }
            val st = if ((t.str("status_anp") ?: "").contains("ALERTA", true) || (t.str("status_anp") ?: "").contains("CRIT", true)) "danger" else "success"
            GenUiComparisonRow(name = name, primary = fis, secondary = esc, gap = vp, status = st, observation = null)
        }
        if (tanquesRows.isNotEmpty()) {
            out += GenUiBlock.Comparison("Conciliação por Tanque (Físico vs Escriturado)", null, tanquesRows)
        }
        return out
    }

    private fun tankBlocks(props: JsonObject): List<GenUiBlock> {
        val out = mutableListOf<GenUiBlock>()
        (props["assessment"] as? JsonObject)?.let { a ->
            val msg = a.str("limitation")
            val sev = a.str("severity") ?: "info"
            a.str("title")?.let { t ->
                out += GenUiBlock.AlertCallout(GenUiAlert(t, a.str("badge_label") ?: msg.orEmpty(), sev, null))
            }
        }
        (props["metrics"] as? JsonObject)?.let { m ->
            val kpis = mutableListOf<GenUiKpi>()
            m.dbl("saldo_total_litros")?.let {
                kpis += GenUiKpi("Saldo Total", "${fmtNumber(it)} L", null, "neutral", "neutral", "Capacidade ${fmtNumber(m.dbl("capacidade_total_litros") ?: 0.0)} L")
            }
            m.dbl("ocupacao_geral_pct")?.let {
                kpis += GenUiKpi("Ocupação", "${"%.1f".format(it)}%", null, "neutral", if (it < 20) "warning" else "success", null)
            }
            m.int("tanques_criticos_count")?.let {
                kpis += GenUiKpi("Tanques Críticos", "$it", null, "neutral", if (it > 0) "danger" else "success", "Abaixo da reserva de 15%")
            }
            m.dbl("espaco_livre_ullage_total_litros")?.let {
                kpis += GenUiKpi("Espaço Livre", "${fmtNumber(it)} L", null, "neutral", "neutral", "Capacidade de descarga")
            }
            if (kpis.isNotEmpty()) out += GenUiBlock.KpiGrid("Visão Geral", null, kpis)
        }
        val all = (props["tanks"] as? JsonArray).orEmpty().mapNotNull { el ->
            val t = el as? JsonObject ?: return@mapNotNull null
            GenUiTank(
                code = t.str("codtan") ?: "-",
                fuel = t.str("combustivel") ?: "Combustível",
                capacityL = t.dbl("capacidade_litros") ?: 0.0,
                balanceL = t.dbl("saldo_atual_litros") ?: 0.0,
                occupancyPct = t.dbl("ocupacao_pct") ?: 0.0,
                autonomyHours = t.dbl("autonomia_critica_horas"),
                critical = t.bool("alerta_critico") ?: false,
                operationalStatus = t.str("status_operacional") ?: ""
            )
        }
        val active = all.filter { !it.operationalStatus.equals("INATIVO", ignoreCase = true) }
        if (active.isNotEmpty() || all.isNotEmpty()) {
            out += GenUiBlock.Tanks("Tanques", active.ifEmpty { all }, if (active.isEmpty()) 0 else all.size - active.size)
        }
        return out
    }

    fun fmtNumber(v: Double): String = java.text.NumberFormat.getIntegerInstance(java.util.Locale("pt", "BR")).format(v)

    private fun JsonObject.str(key: String): String? =
        (this[key] as? JsonPrimitive)?.takeIf { it.isString || it.content != "null" }?.content?.takeIf { it.isNotBlank() }

    private fun JsonObject.dbl(key: String): Double? = (this[key] as? JsonPrimitive)?.doubleOrNull
    private fun JsonObject.int(key: String): Int? = (this[key] as? JsonPrimitive)?.intOrNull
    private fun JsonObject.bool(key: String): Boolean? = (this[key] as? JsonPrimitive)?.booleanOrNull
    private fun JsonArray?.orEmpty(): JsonArray = this ?: JsonArray(emptyList())
}
