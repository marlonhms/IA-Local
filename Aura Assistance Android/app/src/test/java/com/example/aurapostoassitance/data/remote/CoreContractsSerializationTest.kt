package com.example.aurapostoassitance.data.remote

import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

class CoreContractsSerializationTest {

    private val json = Json {
        ignoreUnknownKeys = true
        isLenient = true
        encodeDefaults = true
    }

    @Test
    fun `deserializes SimulationRecomputeResponse with Monte Carlo bands violated rules and provenance`() {
        val payload = """
            {
              "simulation_id": "sim_20261126_01",
              "tenant_id": "posto_01",
              "pack_id": "fuel_convenience",
              "scenario_type": "price_discount_change",
              "horizon_days": 30,
              "monte_carlo": {
                "p10": 18450.25,
                "p50": 24120.80,
                "p90": 29890.10,
                "mean": 24150.00,
                "std_dev": 3120.45,
                "prob_positive_pct": 94.6,
                "iterations": 5000,
                "seed": 42
              },
              "projected_metrics": {
                "margin_pct": 11.4,
                "net_cashflow_brl": 24120.80
              },
              "sensitivity": [
                {
                  "parameter": "price_delta_pct",
                  "impact_brl": 5400.0,
                  "impact_pct": 22.4,
                  "direction": "positive"
                }
              ],
              "violated_rules": [
                {
                  "rule_id": "rule_min_margin",
                  "source": "business_memory",
                  "rule_key": "min_fuel_margin_pct",
                  "metric": "margin_pct",
                  "operator": ">=",
                  "threshold": 12.0,
                  "threshold_upper": null,
                  "observed_value": 11.4,
                  "severity": "CRITICAL",
                  "message": "Margem projetada (11.4%) abaixo do piso institucional (12.0%)"
                }
              ],
              "is_compliant": false,
              "elapsed_ms": 18.4,
              "llm_calls": 0,
              "provenance": {
                "baseline_source": "erp_historical",
                "active_rules_count": 4,
                "yaml_rules_count": 2,
                "memory_rules_count": 2,
                "cited_documents": ["politica_comercial_2026.pdf"]
              }
            }
        """.trimIndent()

        val dto = json.decodeFromString<SimulationRecomputeResponseDto>(payload)
        assertEquals("sim_20261126_01", dto.simulation_id)
        assertEquals("fuel_convenience", dto.pack_id)
        assertEquals(18450.25, dto.monte_carlo.p10, 0.001)
        assertEquals(24120.80, dto.monte_carlo.p50, 0.001)
        assertEquals(29890.10, dto.monte_carlo.p90, 0.001)
        assertFalse(dto.is_compliant)
        assertEquals(0, dto.llm_calls)
        assertEquals(1, dto.violated_rules.size)
        assertEquals("rule_min_margin", dto.violated_rules.first().rule_id)
        assertEquals("erp_historical", dto.provenance.baseline_source)
        assertEquals(listOf("politica_comercial_2026.pdf"), dto.provenance.cited_documents)

        val requestJson = json.encodeToString(
            SimulationRecomputeRequestDto(
                tenant_id = "posto_01",
                pack_id = "fuel_convenience",
                scenario_type = "price_discount_change",
                shocks = ShockVectorDto(price_delta_pct = -2.5, discount_pct = 1.0)
            )
        )
        assertTrue(requestJson.contains("\"horizon_days\":30"))
        assertTrue(requestJson.contains("\"price_delta_pct\":-2.5"))
    }

    @Test
    fun `deserializes MemoryRuleList MemoryGovernanceFeed and RuleDecision responses`() {
        val rulesJson = """
            {
              "tenant_id": "farmacia_01",
              "pack_id": "pharmacy_health",
              "total": 1,
              "rules": [
                {
                  "rule_id": "cand_01",
                  "tenant_id": "farmacia_01",
                  "pack_id": "pharmacy_health",
                  "rule_key": "pbm_min_margin",
                  "metric": "margin_pct",
                  "operator": ">=",
                  "threshold_value": 18.0,
                  "severity": "HIGH",
                  "status": "candidate",
                  "source": "business_memory",
                  "origin": "backtest_calibration",
                  "author": "aura_profiler",
                  "description": "Piso de margem para medicamentos PBM"
                }
              ]
            }
        """.trimIndent()
        val listDto = json.decodeFromString<MemoryRuleListResponseDto>(rulesJson)
        assertEquals("pharmacy_health", listDto.pack_id)
        assertEquals(1, listDto.total)
        assertEquals("candidate", listDto.rules.first().status)

        val feedJson = """
            {
              "tenant_id": "farmacia_01",
              "pack_id": "pharmacy_health",
              "candidate_rules": [],
              "suggested_simulations": [
                {
                  "card_id": "sug_99",
                  "tenant_id": "farmacia_01",
                  "pack_id": "pharmacy_health",
                  "topic_key": "pbm_desconto",
                  "entity_type": "category",
                  "metric_key": "margin_pct",
                  "hit_count": 5,
                  "recommended_scenario": "price_discount_change",
                  "suggested_shocks": {
                    "discount_pct": 4.0
                  },
                  "title": "Simular teto de desconto PBM",
                  "reason": "Consultado 5 vezes nos últimos 7 dias"
                }
              ],
              "pending_count": 1,
              "llm_calls": 0
            }
        """.trimIndent()
        val feedDto = json.decodeFromString<MemoryGovernanceFeedResponseDto>(feedJson)
        assertEquals(1, feedDto.pending_count)
        assertEquals("sug_99", feedDto.suggested_simulations.first().card_id)
        assertEquals(4.0, feedDto.suggested_simulations.first().suggested_shocks.discount_pct, 0.001)

        val decisionJson = """
            {
              "rule_id": "cand_01",
              "tenant_id": "farmacia_01",
              "pack_id": "pharmacy_health",
              "previous_status": "candidate",
              "new_status": "active",
              "decided_by": "operator",
              "decided_at": "2026-11-26T16:30:00Z",
              "rule": {
                "rule_id": "cand_01",
                "tenant_id": "farmacia_01",
                "pack_id": "pharmacy_health",
                "rule_key": "pbm_min_margin",
                "metric": "margin_pct",
                "operator": ">=",
                "threshold_value": 18.0,
                "status": "active"
              }
            }
        """.trimIndent()
        val decisionDto = json.decodeFromString<RuleDecisionResponseDto>(decisionJson)
        assertEquals("candidate", decisionDto.previous_status)
        assertEquals("active", decisionDto.new_status)
        assertEquals("active", decisionDto.rule.status)
    }

    @Test
    fun `deserializes BacktestRunResponse and RealizedRoiScorecardResponse`() {
        val backtestRunJson = """
            {
              "tenant_id": "posto_01",
              "pack_id": "fuel_convenience",
              "evaluated_count": 1,
              "items": [
                {
                  "simulation_id": "sim_01",
                  "scenario_type": "price_discount_change",
                  "horizon_days": 30,
                  "created_at": "2026-10-01T10:00:00Z",
                  "realized_at": "2026-10-31T10:00:00Z",
                  "predicted_p10_brl": 10000.0,
                  "predicted_p50_brl": 12500.0,
                  "predicted_p90_brl": 15000.0,
                  "realized_brl": 13100.0,
                  "error_brl": 600.0,
                  "error_pct": 4.8,
                  "within_p10_p90": true
                }
              ],
              "calibration_proposal": {
                "rule_id": "cal_01",
                "tenant_id": "posto_01",
                "pack_id": "fuel_convenience",
                "metric": "elasticity_calibration_factor",
                "current_factor": 1.0,
                "suggested_factor": 1.04,
                "mean_bias_pct": 4.8,
                "sample_size": 12,
                "status": "candidate",
                "reason": "Elasticidade subestimada em dias de pico"
              },
              "llm_calls": 0
            }
        """.trimIndent()
        val runDto = json.decodeFromString<BacktestRunResponseDto>(backtestRunJson)
        assertEquals(1, runDto.evaluated_count)
        assertTrue(runDto.items.first().within_p10_p90)
        assertNotNull(runDto.calibration_proposal)
        assertEquals(1.04, runDto.calibration_proposal!!.suggested_factor, 0.001)

        val scorecardJson = """
            {
              "tenant_id": "posto_01",
              "pack_id": "fuel_convenience",
              "period_days": 90,
              "projected_brl": 50000.0,
              "realized_brl": 52400.0,
              "total_realized_brl": 52400.0,
              "hit_rate_pct": 88.5,
              "mean_abs_error_pct": 5.2,
              "roi_multiple": 3.4,
              "audited_actions_count": 14,
              "items": [],
              "pending_calibration": null,
              "llm_calls": 0
            }
        """.trimIndent()
        val scorecardDto = json.decodeFromString<RealizedRoiScorecardResponseDto>(scorecardJson)
        assertEquals(50000.0, scorecardDto.projected_brl, 0.001)
        assertEquals(52400.0, scorecardDto.realized_brl, 0.001)
        assertEquals(88.5, scorecardDto.hit_rate_pct, 0.001)
        assertEquals(14, scorecardDto.audited_actions_count)
    }
}
