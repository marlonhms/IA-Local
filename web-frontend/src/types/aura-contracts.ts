/**
 * Contratos Estaticos TypeScript alinhados 1:1 com os Schemas Pydantic v2 da AURA (P2-6).
 * Garante tipagem forte em tempo de compilacao entre Backend Python (FastAPI) e Frontend.
 * Zero travessoes em todo o arquivo.
 */

export type AuraChunkType =
  | "delta"
  | "intent"
  | "tool_start"
  | "tool_result"
  | "ui_skeleton"
  | "ui_delta"
  | "ui_complete"
  | "ui_action_result"
  | "ui_action_feedback"
  | "cache_hit"
  | "telemetry"
  | "stream_reset"
  | "proactive_alert"
  | "error"
  | "done";

export interface AuraMessage {
  id?: number | string;
  session_id: string;
  role: "user" | "assistant" | "system" | "tool";
  content: string;
  intent?: string | null;
  tool_call_id?: string | null;
  name?: string | null;
  metadata?: Record<string, unknown> | null;
  created_at?: string;
}

export interface GenUIActionOption {
  action_id: string;
  label: string;
  action_type: "mutation" | "inspection" | "navigation";
  variant: "primary" | "secondary" | "danger" | "ghost";
  is_destructive: boolean;
  requires_confirmation: boolean;
  payload: Record<string, unknown>;
}

export interface GenUIEnvelope<TProps = Record<string, unknown>> {
  schema_version: string;
  tool_call_id: string;
  component_name: string;
  client_component?: string | null;
  intent: string;
  executive_summary: string;
  props: TProps;
  actions: GenUIActionOption[];
  created_at: string;
  ttl_seconds: number;
}

export interface GenUIEvent<TProps = Record<string, unknown>> {
  chunk_type: AuraChunkType;
  text?: string | null;
  data?: Record<string, unknown> | null;
  session_id?: string | null;
  tool_call_id?: string | null;
  component_name?: string | null;
  title?: string | null;
  envelope?: GenUIEnvelope<TProps> | null;
}

export interface ActionExecuteRequest {
  session_id: string;
  tool_call_id: string;
  action_id: string;
  action_name: string;
  action_type: "mutation" | "inspection" | "navigation";
  payload: Record<string, unknown>;
  operator_id?: string | null;
  operator_role?: "frentista" | "caixa" | "gerente" | "administrador" | string | null;
  idempotency_key?: string | null;
}

export interface ActionVoucher {
  voucher_id: string;
  action_id: string;
  tool_call_id: string;
  status: "APPROVED" | "EXECUTED" | "ROLLED_BACK";
  timestamp: string;
  action_name: string;
  details: Record<string, unknown>;
  signature: string;
}

export interface ActionAuditLogRecord {
  audit_id: string;
  timestamp: string;
  session_id?: string | null;
  tool_call_id: string;
  action_id: string;
  action_name: string;
  action_type: string;
  operator_id?: string | null;
  operator_role?: string | null;
  authorized: boolean;
  status: "APPROVED" | "REJECTED_FORBIDDEN" | "FAILED" | "ROLLED_BACK";
  details: Record<string, unknown>;
  client_ip?: string | null;
}

export interface ExecutiveMetric {
  label: string;
  current_value: unknown;
  benchmark_value?: unknown;
  trend: "up" | "down" | "neutral";
  status: "success" | "warning" | "danger" | "neutral";
  unit?: string | null;
  delta_percent?: number | null;
}

export interface ExecutiveImpactProjection {
  summary: string;
  estimated_financial_impact?: number | null;
  timeframe?: string | null;
  confidence?: number | null;
}

export interface ExecutiveEvidenceItem {
  title: string;
  detail: string;
  value?: unknown;
  source?: string | null;
}

export interface ExecutiveDecisionProps {
  diagnosis: string;
  confidence_score: number;
  metrics: ExecutiveMetric[];
  limitations: string[];
  impact_projection?: string | Record<string, unknown> | ExecutiveImpactProjection | null;
  evidence_items: Array<string | Record<string, unknown> | ExecutiveEvidenceItem>;
  suggested_actions: GenUIActionOption[];
}

export interface FuelMarginItem {
  combustivel: string;
  volume_litros: number;
  preco_venda: number;
  custo_aquisicao: number;
  margem_liquida_pct: number;
  margem_alvo_pct?: number | null;
  benchmark_mercado?: number | null;
  elasticidade?: string | null;
}

export interface PaymentFeeImpactItem {
  modalidade: string;
  taxa_media_pct: number;
  volume_financeiro: number;
  desconto_taxas_reais: number;
  impacto_margem_pct: number;
}

export interface MarginAnalysisProps {
  diagnosis: string;
  confidence_score: number;
  consolidated_margin_pct: number;
  target_margin_pct?: number | null;
  gross_revenue?: number | null;
  net_profit?: number | null;
  total_desconto_tef?: number | null;
  periodo_analisado?: Record<string, unknown> | null;
  fuel_margins: FuelMarginItem[];
  top_produtos_margem?: Array<Record<string, unknown>>;
  payment_fee_impact: PaymentFeeImpactItem[];
  elasticity_projection?: string | Record<string, unknown> | ExecutiveImpactProjection | null;
  limitations: string[];
  suggested_actions: GenUIActionOption[];
}

export interface ScenarioPoint {
  preco_medio: number;
  volume_projetado: number;
  receita_liquida: number;
  margem_contribuicao_pct: number;
}

export interface PredictiveScenarioProps {
  scenario_title: string;
  hypothesis: string;
  base_scenario: ScenarioPoint;
  simulated_scenario: ScenarioPoint;
  delta_volume_pct: number;
  delta_revenue: number;
  delta_margin_pct: number;
  confidence_score: number;
  diagnosis: string;
  elasticity_coefficient?: number | null;
  assumptions: string[];
  limitations: string[];
  suggested_actions: GenUIActionOption[];
}

export interface BenchmarkComparisonItem {
  kpi_name: string;
  filial_value: unknown;
  benchmark_value: unknown;
  gap_value?: string | null;
  status: "success" | "warning" | "danger" | "neutral";
  observation?: string | null;
}

export interface BenchmarkComparisonProps {
  diagnosis: string;
  confidence_score: number;
  competitiveness_score: number;
  entity_name: string;
  benchmark_group: string;
  market_position?: string | null;
  comparison_items: BenchmarkComparisonItem[];
  limitations: string[];
  suggested_actions: GenUIActionOption[];
  ranking_postos_anp?: Record<string, unknown> | null;
}

export interface FinancialLeakItem {
  category: string;
  description: string;
  amount: number;
  status: "critical" | "warning" | "resolved" | "investigating";
  pdv_or_terminal?: string | null;
  leak_type?: string | null;
  amount_reais?: number | null;
  severity?: string | null;
  source?: string | null;
  mitigation_action?: string | null;
}

export interface FinancialLeakAuditProps {
  diagnosis: string;
  severity: "normal" | "attention" | "critical";
  confidence_score: number;
  total_leak_value: number;
  cash_break_value: number;
  pending_bleed_value: number;
  tef_divergence_value: number;
  total_divergence_reais?: number | null;
  risk_level?: string | null;
  audited_shift?: string | number | null;
  cashier_name?: string | null;
  leak_items: FinancialLeakItem[];
  limitations: string[];
  suggested_actions: GenUIActionOption[];
}

export interface UpsellComboItem {
  anchor_product: string;
  recommended_product: string;
  lift: number;
  confidence_pct: number;
  support_pct: number;
  additional_ticket_reais: number;
  script_pitch: string;
  category?: string | null;
}

export interface BasketUpsellStrategyProps {
  diagnosis: string;
  confidence_score: number;
  projected_ticket_increase: number;
  projected_monthly_revenue_lift?: number | null;
  category_focus?: string | null;
  top_combos: UpsellComboItem[];
  limitations: string[];
  suggested_actions: GenUIActionOption[];
  total_transacoes?: number | null;
  pct_multiplos_itens?: number | null;
  maior_lift?: number | null;
  regras_forte_sinergia_count?: number | null;
}

export interface ShiftReconciliationProps {
  schema_version: string;
  response_id: string;
  intent: string;
  context: Record<string, unknown>;
  assessment: {
    finality: "partial" | "final" | "no_movement" | "unavailable";
    severity: "normal" | "attention" | "critical";
    status_code: string;
    title: string;
    limitation?: string | null;
    badge_label: string;
  };
  metrics: {
    automation_revenue: number;
    automation_revenue_cents: number;
    pos_revenue: number;
    pos_revenue_cents: number;
    difference: number;
    difference_cents: number;
    difference_definition: string;
    physical_volume_liters?: number | null;
    physical_volume_state: "not_reported" | "measured" | "zero_registered";
    automation_volume_liters: number;
    is_provisional: boolean;
  };
  pending_items: Array<Record<string, unknown>>;
  sources: Array<Record<string, unknown>>;
  recommended_action: Record<string, unknown>;
  explanation: { text: string };
  suggested_actions?: GenUIActionOption[];
}

export interface TankRunOutPredictionProps {
  schema_version: string;
  response_id: string;
  intent: string;
  context: Record<string, unknown>;
  assessment: {
    status_code: string;
    severity: "normal" | "attention" | "critical";
    title: string;
    limitation?: string | null;
    badge_label: string;
    alerta_fim_de_semana: boolean;
    horizonte_critico_horas?: number | null;
    horizonte_runout_horas?: number | null;
    tanque_mais_critico_cod?: string | null;
  };
  metrics: {
    saldo_total_litros: number;
    capacidade_total_litros: number;
    ocupacao_geral_pct: number;
    autonomia_critica_horas: number;
    autonomia_critica_dias: number;
    autonomia_runout_horas: number;
    autonomia_runout_dias: number;
    espaco_livre_ullage_total_litros: number;
    compartimentos_5k_total: number;
    volume_sugerido_total_litros: number;
    tanques_criticos_count: number;
    tanques_zerados_count: number;
  };
  tanks: Array<Record<string, unknown>>;
  fuel_summary: Array<Record<string, unknown>>;
  order_suggestions: Array<Record<string, unknown>>;
  suggested_actions?: GenUIActionOption[];
}

export interface ComplianceOptInStatus {
  loja_cnpj: string;
  razao_social: string;
  aceite_interoperabilidade_em: string;
  versao_termo: string;
  status: string;
  assinado_por: string;
  hash_termo: string;
  metadata?: Record<string, unknown> | null;
}

export interface ComplianceVerificationResult {
  compliant: boolean;
  loja_cnpj: string;
  razao_social?: string | null;
  versao_termo?: string | null;
  status: string;
  aceite_interoperabilidade_em?: string | null;
  assinado_por?: string | null;
  hash_termo?: string | null;
  hash_atual_termo: string;
  hash_confere: boolean;
  garantia_leitura_exclusiva: boolean;
  isolamento_aups: boolean;
  driver_level_protection: boolean;
  mensagem: string;
}

export interface CompliancePillarItem {
  title: string;
  norma: string;
  status: string;
  description: string;
}

export interface ComplianceStatusProps {
  loja_cnpj: string;
  razao_social?: string | null;
  compliant: boolean;
  status: string;
  versao_termo: string;
  assinado_por?: string | null;
  aceite_interoperabilidade_em?: string | null;
  hash_termo?: string | null;
  hash_atual_termo: string;
  hash_confere: boolean;
  garantia_leitura_exclusiva: boolean;
  isolamento_aups: boolean;
  driver_level_protection: boolean;
  statement_timeout_ms: number;
  lock_timeout_ms: number;
  role_banco: string;
  mensagem: string;
  pilares_legais: CompliancePillarItem[];
  suggested_actions: GenUIActionOption[];
}

export interface LatencyPercentilesSummary {
  avg: number;
  min: number;
  max: number;
  p50: number;
  p90: number;
  p95: number;
  p99: number;
  last: number;
  count: number;
}

export interface TelemetrySLISnapshot {
  status: string;
  timestamp: string;
  ttft_ms: LatencyPercentilesSummary;
  hydration_ms: LatencyPercentilesSummary;
  vector_search_ms: LatencyPercentilesSummary;
  total_actions_requested: number;
  total_actions_approved: number;
  total_actions_rolled_back: number;
  security_blocks: number;
  action_success_rate_pct: number;
  router_cache_hits: number;
  router_cache_misses: number;
  router_cache_hit_ratio: number;
  db_pool: {
    active_erp: number;
    active_vec: number;
    wait_ms: number;
  };
  tool_executions: Record<string, { success: number; error: number }>;
  feature_flags: Record<string, boolean>;
}


// =============================================================================
// BLOCOS MODULARES GENERATIVOS (LEGO BLOCKS UI - FASE 7+)
// =============================================================================

export interface LegoKpiItem {
  label: string;
  value: string;
  delta?: string | null;
  trend?: string | null;
  status?: string;
  subtext?: string | null;
}

export interface LegoComparisonRow {
  name: string;
  primary_value: string;
  secondary_value: string;
  gap?: string | null;
  status?: string;
  observation?: string | null;
}

export interface LegoRankingItem {
  rank: number;
  title: string;
  subtitle?: string | null;
  value: string;
  tag?: string | null;
  status?: string;
}

export interface LegoTimelineEvent {
  timestamp: string;
  title: string;
  description?: string | null;
  badge?: string | null;
  status?: string;
}

export interface LegoAlertItem {
  title: string;
  message: string;
  severity?: string;
  action_label?: string | null;
}

export interface LegoBlock {
  block_id: string;
  block_type: string;
  title?: string | null;
  subtitle?: string | null;
  kpis?: LegoKpiItem[];
  comparison_rows?: LegoComparisonRow[];
  ranking_items?: LegoRankingItem[];
  timeline_events?: LegoTimelineEvent[];
  alert?: LegoAlertItem | null;
  custom_content?: string | null;
}

export interface GenerativeModularProps {
  title: string;
  subtitle?: string | null;
  diagnosis: string;
  confidence_score: number;
  blocks: LegoBlock[];
  limitations: string[];
  suggested_actions: GenUIActionOption[];
}

export interface ActionableDirectivePayload {
  directive_id: string;
  card_id?: string | null;
  title: string;
  category: string;
  financial_impact_brl: number;
  roteiro_voz_consultor: string;
  treinamento_equipe_15s: string;
  campanha_clientes_whatsapp: string;
  status: "pending" | "queued" | "dispatched" | "executed" | "cancelled" | string;
  canal_despacho: "outbox_webhook" | "in_app_cockpit" | "notificador_desktop" | string;
  idempotency_key?: string | null;
  created_at: string;
  metadata?: Record<string, unknown>;
}

export interface ExecutiveExceptionCard {
  card_id: string;
  title: string;
  category: string;
  severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "INFO" | string;
  financial_impact_brl: number;
  diagnostico_direto: string;
  prova_matematica: string | Record<string, unknown>;
  acao_recomendada_hitl: GenUIActionOption | Record<string, unknown>;
  urgency_timeframe?: string | null;
  directive?: ActionableDirectivePayload | null;
  created_at: string;
  metadata?: Record<string, unknown>;
}

export interface LiveSecurityTelemetry {
  status: string;
  timestamp: string;
  postgresql_session: {
    default_transaction_read_only: string;
    statement_timeout: string;
    lock_timeout: string;
    role: string;
    database: string;
    driver_options: string;
    forensic_safe: boolean;
  };
  hardware_circuit_breaker: {
    cpu_percent: number;
    ram_percent: number;
    circuit_state: string;
    circuit_state_raw: string;
    is_heavy_allowed: boolean;
    tripped_count: number;
  };
  pii_sanitization: {
    total_sanitized_entities: number;
    category_counts: Record<string, number>;
    policy_version: string;
  };
  clean_room_active_term: {
    term_hash_sha256: string;
    term_path: string;
    is_term_present: boolean;
  };
  sql_role_script: string;
  architecture_layers: Array<{
    layer: number;
    name: string;
    component: string;
    description: string;
    status: string;
  }>;
}


// ============================================================================
// Contratos GenUI Next-Gen (Fase P1-UI4 & P1-UI5: What-If, ROI, MCP HITL & DomainPack)
// ============================================================================

export type AuraDomainPackId =
  | "fuel_convenience"
  | "pharmacy_health"
  | "retail_supermarket"
  | "autocenter_parts"
  | "wholesale_distribution";

export type SimulationScenarioType =
  | "price_discount_change"
  | "cost_supplier_variation"
  | "payment_term_cashflow";

export type SimulationHorizonDays = 30 | 60 | 90;
export type BusinessRuleStatus = "candidate" | "active" | "rejected";
export type BusinessRuleSeverity = "CRITICAL" | "HIGH" | "MEDIUM" | "INFO";
export type BusinessRuleOperator = ">=" | "<=" | ">" | "<" | "==" | "!=" | "between";

export interface SimulationBaseline {
  unit_price: number;
  unit_cost: number;
  daily_volume: number;
  volume_std_dev_pct?: number;
  cost_std_dev_pct?: number;
  elasticity_mean?: number;
  elasticity_std_dev?: number;
  receivable_days?: number;
  payable_days?: number;
  annual_capital_cost_pct?: number;
  fixed_daily_cost?: number;
  extra_metrics?: Record<string, number>;
}

export interface ShockVector {
  price_delta_pct?: number;
  discount_pct?: number;
  supplier_cost_delta_pct?: number;
  cost_passthrough_pct?: number;
  receivable_days_delta?: number;
  payable_days_delta?: number;
  capital_cost_delta_pct?: number;
  custom_shocks?: Record<string, number>;
}

export interface MonteCarloBands {
  p10: number;
  p50: number;
  p90: number;
  mean: number;
  std_dev: number;
  prob_positive_pct: number;
  iterations: number;
  seed: number;
}

export interface RuleViolation {
  rule_id: string;
  source: "yaml" | "business_memory";
  rule_key: string;
  metric: string;
  operator: BusinessRuleOperator;
  threshold: number;
  threshold_upper?: number | null;
  observed_value: number;
  severity: BusinessRuleSeverity;
  message: string;
}

export interface SensitivityDriver {
  parameter: string;
  impact_brl: number;
  impact_pct: number;
  direction: "positive" | "negative" | "neutral";
}

export interface SimulationProvenance {
  baseline_source: string;
  active_rules_count: number;
  yaml_rules_count: number;
  memory_rules_count: number;
  cited_documents: string[];
}

export interface SimulationRecomputeRequest {
  tenant_id?: string;
  pack_id: string;
  simulation_id?: string | null;
  scenario_type: SimulationScenarioType;
  horizon_days?: SimulationHorizonDays;
  baseline?: SimulationBaseline | null;
  shocks?: ShockVector;
  iterations?: number;
  seed?: number;
  persist_snapshot?: boolean;
  created_by?: string;
}

export interface SimulationRecomputeResponse {
  simulation_id: string;
  tenant_id: string;
  pack_id: string;
  scenario_type: SimulationScenarioType;
  horizon_days: SimulationHorizonDays;
  monte_carlo: MonteCarloBands;
  projected_metrics: Record<string, number>;
  sensitivity: SensitivityDriver[];
  violated_rules: RuleViolation[];
  is_compliant: boolean;
  elapsed_ms: number;
  llm_calls: number;
  provenance?: SimulationProvenance;
}

export interface BusinessMemoryRule {
  rule_id: string;
  tenant_id: string;
  pack_id: string;
  rule_key: string;
  metric: string;
  operator: BusinessRuleOperator;
  threshold_value: number;
  threshold_upper?: number | null;
  severity: BusinessRuleSeverity;
  status: BusinessRuleStatus;
  source: "yaml" | "business_memory";
  origin: string;
  author: string;
  description: string;
}

export interface RuleDecisionRequest {
  tenant_id?: string;
  pack_id: string;
  decision: "approve" | "reject";
  decided_by?: string;
  reason?: string;
}

export interface RuleDecisionResponse {
  rule_id: string;
  tenant_id: string;
  pack_id: string;
  previous_status: BusinessRuleStatus;
  new_status: BusinessRuleStatus;
  decided_by: string;
  decided_at: string;
  rule: BusinessMemoryRule;
}

export interface SuggestedSimulationCard {
  card_id: string;
  tenant_id: string;
  pack_id: string;
  topic_key: string;
  entity_type: string;
  metric_key: string;
  hit_count: number;
  recommended_scenario: SimulationScenarioType;
  suggested_shocks: ShockVector;
  title: string;
  reason: string;
}

export interface MemoryGovernanceFeedResponse {
  tenant_id: string;
  pack_id: string;
  candidate_rules: BusinessMemoryRule[];
  suggested_simulations: SuggestedSimulationCard[];
  pending_count: number;
  llm_calls: number;
}

export interface BacktestItemResult {
  simulation_id: string;
  scenario_type: SimulationScenarioType;
  horizon_days: SimulationHorizonDays;
  created_at?: string | null;
  realized_at?: string | null;
  predicted_p10_brl: number;
  predicted_p50_brl: number;
  predicted_p90_brl: number;
  realized_brl: number;
  error_brl: number;
  error_pct: number;
  within_p10_p90: boolean;
}

export interface CalibrationProposal {
  rule_id: string;
  tenant_id: string;
  pack_id: string;
  metric: string;
  current_factor: number;
  suggested_factor: number;
  mean_bias_pct: number;
  sample_size: number;
  status: BusinessRuleStatus;
  reason: string;
}

export interface BacktestRunRequest {
  tenant_id?: string;
  pack_id: string;
  as_of?: string | null;
  limit?: number;
  dry_run?: boolean;
}

export interface BacktestRunResponse {
  tenant_id: string;
  pack_id: string;
  evaluated_count: number;
  items: BacktestItemResult[];
  calibration_proposal?: CalibrationProposal | null;
  llm_calls: number;
}

export interface RealizedRoiScorecardResponse {
  tenant_id: string;
  pack_id: string;
  period_days: number;
  projected_brl: number;
  realized_brl: number;
  total_realized_brl: number;
  hit_rate_pct: number;
  mean_abs_error_pct: number;
  roi_multiple: number;
  audited_actions_count: number;
  items: BacktestItemResult[];
  pending_calibration?: CalibrationProposal | null;
  llm_calls: number;
}

export interface WhatIfSimulatorProps {
  title?: string;
  product_name?: string;
  tenant_id?: string;
  pack_id?: string;
  simulation_id?: string;
  scenario_type?: SimulationScenarioType;
  horizon_days?: SimulationHorizonDays;
  baseline?: SimulationBaseline;
  shocks?: ShockVector;
  monte_carlo?: MonteCarloBands;
  violated_rules?: RuleViolation[];
  sensitivity?: SensitivityDriver[];
  provenance?: SimulationProvenance;
  baseline_margin_brl?: number;
  simulated_margin_brl?: number;
  delta_margin_brl?: number;
  price_delta_pct?: number;
  volume_delta_pct?: number;
  recommendation?: string;
}

export interface RealizedRoiScorecardProps {
  title?: string;
  tenant_id?: string;
  pack_id?: string;
  period_days?: number;
  projected_brl?: number;
  realized_brl?: number;
  total_realized_brl?: number;
  hit_rate_pct?: number;
  mean_abs_error_pct?: number;
  roi_multiple?: number;
  audited_actions_count?: number;
  items?: BacktestItemResult[];
  pending_calibration?: CalibrationProposal | null;
}

export interface McpActionConfirmationProps {
  target_system?: string;
  operation?: string;
  reversible?: boolean;
  ttl_seconds?: number;
  arguments?: Record<string, unknown>;
}
