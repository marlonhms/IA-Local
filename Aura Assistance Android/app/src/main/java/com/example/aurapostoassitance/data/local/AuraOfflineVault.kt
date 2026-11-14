package com.example.aurapostoassitance.data.local

import android.content.Context
import com.example.aurapostoassitance.data.remote.BriefingActionDto
import com.example.aurapostoassitance.data.remote.MorningBriefingResponse
import com.example.aurapostoassitance.data.remote.SegmentBaselineResponse
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class AuraOfflineVault @Inject constructor(
    @param:ApplicationContext private val context: Context,
    private val json: Json
) {
    private val prefs = context.getSharedPreferences("aura_offline_vault", Context.MODE_PRIVATE)

    fun saveBriefing(segment: String, briefing: MorningBriefingResponse) {
        val raw = runCatching { json.encodeToString(briefing) }.getOrNull() ?: return
        prefs.edit()
            .putString("briefing_$segment", raw)
            .putLong("briefing_ts_$segment", System.currentTimeMillis())
            .apply()

        // Notifica o widget na tela inicial para sincronizar os dados
        runCatching {
            com.example.aurapostoassitance.widget.AuraPulseWidgetProvider.updateAllWidgets(context)
        }
    }

    fun getBriefing(segment: String): MorningBriefingResponse {
        val raw = prefs.getString("briefing_$segment", null)
        if (!raw.isNullOrBlank()) {
            val parsed = runCatching { json.decodeFromString<MorningBriefingResponse>(raw) }.getOrNull()
            if (parsed != null) return parsed
        }
        return getSeedBriefing(segment)
    }

    fun saveBaseline(segment: String, baseline: SegmentBaselineResponse) {
        val raw = runCatching { json.encodeToString(baseline) }.getOrNull() ?: return
        prefs.edit()
            .putString("baseline_$segment", raw)
            .putLong("baseline_ts_$segment", System.currentTimeMillis())
            .apply()
    }

    fun getBaseline(segment: String): SegmentBaselineResponse? {
        val raw = prefs.getString("baseline_$segment", null)
        if (!raw.isNullOrBlank()) {
            return runCatching { json.decodeFromString<SegmentBaselineResponse>(raw) }.getOrNull()
        }
        return null
    }

    fun getLastSyncTimestamp(segment: String): Long {
        return prefs.getLong("briefing_ts_$segment", 0L)
    }

    /**
     * Sementes determinísticas de alta fidelidade para todos os 6 segmentos,
     * garantindo funcionamento instantâneo em 0ms (Modo Sócio Offline).
     */
    private fun getSeedBriefing(segment: String): MorningBriefingResponse {
        return when (segment) {
            "varejo" -> MorningBriefingResponse(
                success = true,
                segment = "varejo",
                managerName = "Marlon Henrique",
                businessName = "Varejo & Franquias",
                oralVoiceScript = "Bom dia, Marlon. Aqui é seu copiloto da AURA com o fechamento executivo de Varejo. O produto líder atinge ruptura em apenas 22 horas de giro. A auditoria automática identificou uma fuga invisível de R$ 2.400,00 por mês em descontos sem alçada no caixa. Antecipando o pedido com o fornecedor parceiro agora, você mantém a margem líquida protegida. Para agir de imediato: digite 1 para aprovar a reposição preventiva, 2 para cobrar a equipe de vendas no WhatsApp, ou 3 para silenciar por 6 horas.",
                whatsappExecutiveText = "Radar executivo do Varejo pronto.",
                suggestedActions = listOf(
                    BriefingActionDto("1", "Aprovar Reposição Preventiva", "Antecipar pedido com distribuidor parceiro"),
                    BriefingActionDto("2", "Cobrar Equipe no WhatsApp", "Alinhar teto de descontos no caixa"),
                    BriefingActionDto("3", "Silenciar por 6 Horas", "Manter auditoria em background")
                )
            )
            "saas_b2b" -> MorningBriefingResponse(
                success = true,
                segment = "saas_b2b",
                managerName = "Marlon Henrique",
                businessName = "SaaS & Consultoria B2B",
                oralVoiceScript = "Bom dia, Marlon. Passando com seu radar matinal de gestão SaaS. A equipe técnica possui 48 horas livres para novos projetos, enquanto a auditoria identificou um vazamento de R$ 4.800,00 por mês em horas não faturadas e propostas sem retorno. Temos 3 contratos em risco de descontinuidade. Para resolver: digite 1 para disparar o follow-up preventivo com os clientes, 2 para delegar a cobrança aos consultores responsáveis, ou 3 para silenciar por 6 horas.",
                whatsappExecutiveText = "Radar executivo SaaS pronto.",
                suggestedActions = listOf(
                    BriefingActionDto("1", "Disparar Follow-up Preventivo", "Reativar contratos em risco via WhatsApp"),
                    BriefingActionDto("2", "Delegar Cobrança a Consultores", "Cobrar horas técnicas pendentes"),
                    BriefingActionDto("3", "Silenciar por 6 Horas", "Suspender notificações temporariamente")
                )
            )
            "saude_clinicas" -> MorningBriefingResponse(
                success = true,
                segment = "saude_clinicas",
                managerName = "Marlon Henrique",
                businessName = "Saúde & Clínicas",
                oralVoiceScript = "Bom dia, Marlon. Diagnóstico matinal da clínica. Temos 14 horários vagos na agenda desta semana que podem ser preenchidos imediatamente. A auditoria de perdas apontou R$ 3.500,00 de impacto em faltas sem aviso prévio e pacientes sem retorno preventivo. Digite 1 para acionar a confirmação da fila de espera, 2 para orientar a recepção a cobrar os retornos, ou 3 para silenciar por 6 horas.",
                whatsappExecutiveText = "Radar executivo Clínicas pronto.",
                suggestedActions = listOf(
                    BriefingActionDto("1", "Acionar Fila de Espera", "Preencher horários ociosos via WhatsApp"),
                    BriefingActionDto("2", "Orientar Recepção", "Alinhar protocolo anti-no-show"),
                    BriefingActionDto("3", "Silenciar por 6 Horas", "Manter rotina da clínica")
                )
            )
            "ecommerce" -> MorningBriefingResponse(
                success = true,
                segment = "ecommerce",
                managerName = "Marlon Henrique",
                businessName = "E-commerce & D2C",
                oralVoiceScript = "Bom dia, Marlon. Radar executivo do e-commerce. O produto líder esgota em 18 horas com risco de estoque zero nos anúncios ativos. Detectamos perda de R$ 5.200,00 por mês em carrinhos abandonados de alto ticket sem contato. Digite 1 para autorizar a compra emergencial de reposição, 2 para disparar a recuperação de carrinhos no WhatsApp, ou 3 para silenciar por 6 horas.",
                whatsappExecutiveText = "Radar executivo E-commerce pronto.",
                suggestedActions = listOf(
                    BriefingActionDto("1", "Autorizar Compra de Reposição", "Evitar pausa em campanhas de tráfego"),
                    BriefingActionDto("2", "Recuperar Carrinhos no WhatsApp", "Disparar lote VIP de reativação"),
                    BriefingActionDto("3", "Silenciar por 6 Horas", "Manter operação ativa")
                )
            )
            "logistica" -> MorningBriefingResponse(
                success = true,
                segment = "logistica",
                managerName = "Marlon Henrique",
                businessName = "Logística & Frotas",
                oralVoiceScript = "Bom dia, Marlon. Atualização operacional de frota. Temos capacidade disponível para expedição imediata. A auditoria de rota identificou custo de frete ocioso de R$ 6.100,00 por mês. Além disso, compradores corporativos estão com pedidos atrasados. Digite 1 para consolidar as cargas, 2 para acionar os representantes comerciais, ou 3 para silenciar por 6 horas.",
                whatsappExecutiveText = "Radar executivo Logística pronto.",
                suggestedActions = listOf(
                    BriefingActionDto("1", "Consolidar Cargas Ociosas", "Otimizar rotas e reduzir custo por km"),
                    BriefingActionDto("2", "Acionar Representantes Comerciais", "Acelerar fechamento de pedidos em trânsito"),
                    BriefingActionDto("3", "Silenciar por 6 Horas", "Manter controle de despacho")
                )
            )
            else -> MorningBriefingResponse(
                success = true,
                segment = "postos_redes",
                managerName = "Marlon Henrique",
                businessName = "Postos & Redes",
                oralVoiceScript = "Bom dia, Marlon. Radar executivo matinal da AURA para o Posto. O tanque de Gasolina Comum está com autonomia para 18.5 horas de pista. Antecipar a compra do caminhão-tanque antes do fechamento de pauta economiza cerca de R$ 4.520,00 em compras emergenciais. Nossa auditoria também identificou uma fuga invisível de R$ 3.654,00 por mês entre desvios de medição e descontos sem alçada. Digite 1 para aprovar a compra fracionada com a distribuidora, 2 para alinhar a meta com a equipe de pista, ou 3 para silenciar o alerta por 6 horas.",
                whatsappExecutiveText = "Radar executivo do Posto pronto.",
                suggestedActions = listOf(
                    BriefingActionDto("1", "Aprovar Compra Fracionada", "Garantir 5.000 L com economia de frete"),
                    BriefingActionDto("2", "Alinhar Meta com Equipe de Pista", "Encaminhar metas e conferência de turno"),
                    BriefingActionDto("3", "Silenciar Alerta por 6 Horas", "Manter monitoramento de tancagem ativo")
                )
            )
        }
    }
}
