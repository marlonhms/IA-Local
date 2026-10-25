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
    val isDestructive: Boolean
)

/** Blocos nativos renderizaveis pelo app (equivalentes aos "blocos Lego" do painel web). */
sealed class GenUiBlock {
    data class KpiGrid(val title: String?, val subtitle: String?, val kpis: List<GenUiKpi>) : GenUiBlock()
    data class Comparison(val title: String?, val subtitle: String?, val rows: List<GenUiComparisonRow>) : GenUiBlock()
    data class Ranking(val title: String?, val subtitle: String?, val items: List<GenUiRankItem>) : GenUiBlock()
    data class Timeline(val title: String?, val subtitle: String?, val events: List<GenUiTimelineEvent>) : GenUiBlock()
    data class AlertCallout(val alert: GenUiAlert) : GenUiBlock()
    data class Tanks(val title: String?, val tanks: List<GenUiTank>, val hiddenInactive: Int) : GenUiBlock()
    data class Note(val title: String?, val text: String) : GenUiBlock()
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
            "auditoria_turno" to "Conciliação de Turno"
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

        // Fallback textual quando nao ha bloco estruturado
        if (blocks.isEmpty()) {
            val summary = root.str("executive_summary") ?: root.str("summary_text")
            val diag = props.str("diagnosis")
            val subt = props.str("subtitle")
            if (!summary.isNullOrBlank() && summary != diag && summary != subt) {
                blocks += GenUiBlock.Note(null, summary)
            }
        }

        val actions = (root["actions"] as? JsonArray).orEmpty().mapNotNull { el ->
            val o = el as? JsonObject ?: return@mapNotNull null
            val type = o.str("action_type") ?: "mutation"
            // "inspection" abre o Companion Canvas do painel web: sem equivalente no app
            if (type == "inspection") return@mapNotNull null
            GenUiAction(
                actionId = o.str("action_id") ?: return@mapNotNull null,
                label = o.str("label") ?: return@mapNotNull null,
                type = type,
                variant = o.str("variant") ?: "primary",
                requiresConfirmation = o.bool("requires_confirmation") ?: true,
                isDestructive = o.bool("is_destructive") ?: false
            )
        }

        GenUiCard(
            componentName = component,
            title = title,
            subtitle = props.str("subtitle"),
            diagnosis = props.str("diagnosis"),
            confidence = props.dbl("confidence_score")?.toFloat(),
            severity = severity,
            blocks = blocks,
            actions = actions,
            limitations = (props["limitations"] as? JsonArray).orEmpty().mapNotNull { (it as? JsonPrimitive)?.content }
        )
    }.getOrNull()

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

            "custom_content" -> o.str("custom_content")?.let { GenUiBlock.Note(title, it) }
            else -> null
        }
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
