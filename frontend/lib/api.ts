const PRIMARY_API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000"
const API_FALLBACK_CANDIDATES = Array.from(
  new Set([PRIMARY_API_BASE_URL, "http://localhost:8010", "http://127.0.0.1:8010"])
)

let activeApiBaseUrl = PRIMARY_API_BASE_URL
let executiveKpisSupported: boolean | null = null

export interface TelemetryInput {
  energy: number
  temperature: number
  gridLoad: number
  location: string
}

interface BackendDecisionPayload {
  timestamp?: string
  rl_action?: string
  forecast?: {
    predicted_energy_usage?: number
    high_usage_flag?: boolean
  }
  optimized_decision?: {
    recommended_reduction?: number
    cost_saving_estimate?: number
    stability_score?: number
    confidence_score?: number
    recommended_action?: string
    recommended_window?: string
    estimated_savings_inr?: number
    rationale?: string
  }
}

export interface GenerateDecisionResponse {
  status?: string
  decision?: BackendDecisionPayload
}

export interface UiDecision {
  rlAction: string
  reduction: number
  costSaved: number
  stabilityScore: number
  confidenceScore: number
  recommendedAction: string
  recommendedWindow: string
  projectedSavingsInr: number
  rationale: string
  timestamp: string
}

export interface SystemStatusResponse {
  timestamp?: string
  components?: Record<string, unknown>
}

export interface LiveTelemetry {
  timestamp: string
  hostname: string
  platform: string
  cpu_percent: number
  memory_percent: number
  disk_percent: number
  battery_percent: number | null
  power_plugged: boolean | null
  process_count: number
  edge_profile?: {
    cpu_cores?: number | null
    physical_cpu_cores?: number | null
    memory_total_gb?: number | null
    disk_total_gb?: number | null
    network_type?: string | null
    source?: string | null
  }
}

export interface LiveHistoryPoint {
  timestamp: string
  time: string
  optimization: number
  energy: number
}

export interface LiveEvent {
  id: number
  type: "INFO" | "WARN" | "ERROR" | "SUCCESS"
  message: string
  time: string
}

export interface LiveAlert {
  id: number
  severity: "warning" | "critical"
  title: string
  message: string
  time: string
  source?: string
}

export interface RuntimeHealthItem {
  name: string
  value: number
}

export type RuntimeMode = "LIVE_EDGE" | "SIMULATION" | "HYBRID"
export type SimulationScenario = "normal" | "peak_load" | "low_load" | "grid_failure"

export interface IndustrialMetrics {
  site_id: string
  energy_usage_kwh: number
  thermal_index_c: number
  grid_load: number
  grid_status: string
  fault_flag: boolean
}

export interface LiveDashboardResponse {
  status: string
  mode: RuntimeMode
  scenario?: SimulationScenario
  timestamp: string
  telemetry: LiveTelemetry & {
    scan_mode?: RuntimeMode
    scenario?: SimulationScenario
    fault_flag?: boolean
    grid_status?: string
    industrial_metrics?: IndustrialMetrics
  }
  decision: BackendDecisionPayload
  runtime_health: RuntimeHealthItem[]
  history: LiveHistoryPoint[]
  events: LiveEvent[]
  alerts: LiveAlert[]
  service_health?: {
    running: boolean
    scan_interval_seconds: number
    auto_apply_power_profile: boolean
    runtime_mode?: RuntimeMode
    scenario?: SimulationScenario
    supported_modes?: RuntimeMode[]
    supported_scenarios?: SimulationScenario[]
    latest_timestamp?: string
    last_scan_error?: string | null
  }
}

export interface RuntimeControlResponse {
  status: string
  mode?: RuntimeMode
  scenario?: SimulationScenario
  cycles?: number
  timestamp: string
}

export interface ExecutiveKpiMetrics {
  energy_reduction_percent: number
  cost_optimization_percent: number
  carbon_reduction_kg: number
  forecast_accuracy_percent: number
  anomaly_filtered_percent: number
  automated_decisions_percent: number
}

export interface ExecutiveKpiResponse {
  status: string
  timestamp: string
  metrics: ExecutiveKpiMetrics
  sample_sizes?: {
    telemetry_points?: number
    forecast_samples?: number
    event_samples?: number
  }
}

export type ReportWindow = "1d" | "1w" | "1m"
export type ReportFormat = "json" | "markdown"
export type ReportDownloadFormat = "json" | "markdown" | "pdf"

export interface MonitoringExecutiveSummary {
  uptime_percent: number
  records_analyzed: number
  window_days: number
  total_energy_kwh: number
  average_energy_kwh: number
  average_load_percent: number
  energy_optimized_kwh: number
  forecast_accuracy_percent: number
  critical_alerts: number
  warning_alerts: number
  quarantined_records: number
}

export interface MonitoringReportPayload {
  report_id: string
  generated_at: string
  window: string
  window_label: string
  executive_summary: MonitoringExecutiveSummary
  system_health_dashboard: Array<{
    instance: string
    role: string
    status: string
    cpu_load_percent: number
    ram_usage_percent: number
    notes: string
  }>
  performance: {
    peak_hour: string
    peak_load_percent: number
    avg_energy_kwh: number
    hourly_load_profile: Array<{
      hour: string
      avg_load_percent: number
    }>
  }
  security_incidents: {
    anomaly_filtered_records: number
    critical_alerts: number
    warning_alerts: number
    notable_events_count: number
    notable_events: string[]
  }
  strategic_recommendations: string[]
}

export interface MonitoringReportResponse {
  status: string
  window: string
  format: "json" | "markdown"
  report: MonitoringReportPayload
  markdown?: string
}

export interface AiModelRetrainResponse {
  status: string
  result?: Record<string, unknown>
  timestamp: string
}

export type AiModelLogSource = "application" | "errors"

export interface AiModelLogsResponse {
  status: string
  source: AiModelLogSource
  path: string
  line_count: number
  lines: string[]
  timestamp: string
}

export type ExportModelTarget = "forecast" | "anomaly"

export interface AiAssistantEvidence {
  line: number
  text: string
  score: number
}

export interface AiAssistantLogQueryResponse {
  status: string
  timestamp: string
  query: string
  source: AiModelLogSource
  path: string
  provider: "heuristic" | "openai"
  answer: string
  insights: {
    error_count: number
    warning_count: number
    timeout_count: number
    exception_count: number
    total_lines: number
  }
  evidence: AiAssistantEvidence[]
}

export interface AiAssistantRuntimeSummaryResponse {
  status: string
  timestamp: string
  risk_level: "LOW" | "MEDIUM" | "HIGH"
  summary: string
  recommendations: string[]
  signals: {
    cpu_percent: number
    memory_percent: number
    grid_load: number
    fault_flag: boolean
    runtime_health_items: number
    alerts: number
    events: number
  }
}

export interface AiAssistantOpsRecommendation {
  priority: "LOW" | "MEDIUM" | "HIGH"
  action: string
  reason: string
  expected_impact: string
}

export interface AiAssistantOpsRecommendationResponse {
  status: string
  timestamp: string
  risk_level: "LOW" | "MEDIUM" | "HIGH"
  recommendations: AiAssistantOpsRecommendation[]
  signals: {
    cpu_percent: number
    memory_percent: number
    grid_load: number
    fault_flag: boolean
    runtime_health_items: number
    alerts: number
    events: number
  }
}

export interface ImpactMetrics {
  energy_reduction_pct: number
  saved_energy_kwh_day: number
  cost_saved_inr_day: number
  co2_reduced_kg_day: number
  uptime_improvement_pct: number
  decision_stability_pct: number
  window_points: number
}

export interface ImpactMetricsResponse {
  status: string
  timestamp: string
  metrics: ImpactMetrics
}

export interface DecisionExplanationFactor {
  signal: string
  value: number
  impact: "low" | "medium" | "high"
  reason: string
}

export interface DecisionExplanation {
  action: string
  confidence_pct: number
  summary: string
  factors: DecisionExplanationFactor[]
}

export interface DecisionExplanationResponse {
  status: string
  timestamp: string
  explanation: DecisionExplanation
}

export interface IncidentRunbookStep {
  step: number
  title: string
  owner: string
  eta_min: number
  status: "pending" | "completed"
}

export interface IncidentRunbookResponse {
  status: string
  timestamp: string
  incident_type: string
  auto_execute: boolean
  runbook: IncidentRunbookStep[]
}

export interface GovernanceAuditItem {
  id: number
  timestamp: string
  actor: string
  category: string
  action: string
  status: string
  details: Record<string, unknown>
}

export interface GovernanceAuditResponse {
  status: string
  timestamp: string
  count: number
  items: GovernanceAuditItem[]
}

export interface ModelReliability {
  reliability_status: "STABLE" | "WATCH" | "AT_RISK"
  decision_stability_pct: number
  drift_score: number
  drift_monitor_status: string
  model_performance_pct: number
  champion_model: string | null
  candidate_model: string | null
  recommended_action: string
}

export interface ModelReliabilityResponse {
  status: string
  timestamp: string
  reliability: ModelReliability
}

export interface StressScenarioResult {
  scenario: "peak_load" | "low_load" | "grid_failure"
  cycles: number
  avg_resilience_score: number
  estimated_failover_triggered: boolean
  result: "PASS" | "FAIL"
}

export interface StressValidationReport {
  status: string
  total_scenarios: number
  passed: number
  failed: number
  results: StressScenarioResult[]
}

export interface StressValidationResponse {
  status: string
  timestamp: string
  report: StressValidationReport
}

export interface RoiProjectionRow {
  year: number
  sites: number
  estimated_cost_saved_inr: number
  estimated_co2_reduced_kg: number
  cumulative_cost_saved_inr: number
  cumulative_co2_reduced_kg: number
}

export interface RoiProjectionResponse {
  status: string
  timestamp: string
  site_count: number
  annual_growth_pct: number
  horizon_years: number
  projection: RoiProjectionRow[]
  summary: {
    total_cost_saved_inr: number
    total_co2_reduced_kg: number
  }
}

export interface EdgeAgentTelemetry {
  edge_id: string
  timestamp: string
  hostname: string
  platform: string
  cpu_percent: number
  memory_percent: number
  disk_percent: number
  battery_percent: number | null
  power_plugged: boolean | null
  process_count: number
  network_type?: string | null
  source?: string | null
}

export interface EdgeAgentIngestResponse {
  status: string
  timestamp: string
  telemetry: EdgeAgentTelemetry
}

export interface EdgeAgentLatestResponse {
  status: string
  timestamp: string
  edge_count: number
  edges: EdgeAgentTelemetry[]
}

export interface EdgeAgentLatestByIdResponse {
  status: string
  timestamp: string
  edge_id: string
  latest: EdgeAgentTelemetry | null
  history: EdgeAgentTelemetry[]
}

const locationToBuildingId: Record<string, number> = {
  Mumbai: 1,
  Delhi: 2,
  Bangalore: 3,
  Chennai: 4,
  Kolkata: 5,
  Hyderabad: 6,
}

type ValidationIssue = {
  type?: string
  loc?: Array<string | number>
  msg?: string
  ctx?: Record<string, unknown>
}

class ApiRequestError extends Error {
  status: number
  detail?: unknown

  constructor(status: number, message: string, detail?: unknown) {
    super(message)
    this.name = "ApiRequestError"
    this.status = status
    this.detail = detail
  }
}

function toFieldLabel(raw: string): string {
  return raw
    .replace(/_/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase())
    .trim()
}

function mapValidationIssue(issue: ValidationIssue): string {
  const location = Array.isArray(issue.loc) ? issue.loc : []
  const fieldName = location.length > 0 ? String(location[location.length - 1]) : "field"
  const fieldLabel = toFieldLabel(fieldName)
  const issueType = String(issue.type ?? "").toLowerCase()
  const issueMsg = String(issue.msg ?? "").trim()

  if (issueType.includes("missing") || issueMsg.toLowerCase().includes("field required")) {
    return `${fieldLabel} is required.`
  }

  if (issueType.includes("string_too_short")) {
    const minLength = Number(issue.ctx?.min_length)
    if (Number.isFinite(minLength) && minLength > 0) {
      return `${fieldLabel} must be at least ${minLength} characters.`
    }
    return `${fieldLabel} is too short.`
  }

  if (issueType.includes("value_error.email") || fieldName.toLowerCase().includes("email")) {
    return `${fieldLabel} format is invalid.`
  }

  if (issueMsg) {
    return `${fieldLabel}: ${issueMsg}`
  }

  return `${fieldLabel} is invalid.`
}

function normalizeApiErrorMessage(status: number, detail: unknown): string {
  if (Array.isArray(detail)) {
    const mapped = detail
      .map((item) => mapValidationIssue(item as ValidationIssue))
      .filter(Boolean)
      .slice(0, 4)
    if (mapped.length > 0) {
      return mapped.join(" ")
    }
  }

  if (typeof detail === "string" && detail.trim().length > 0) {
    const normalized = detail.trim()
    const lowered = normalized.toLowerCase()
    if (lowered.startsWith("<!doctype") || lowered.startsWith("<html")) {
      if (status >= 500) {
        return "Server error occurred. Please try again in a moment."
      }
      return "Request failed. Please try again."
    }
    if (lowered.includes("invalid credentials")) {
      return "Email or password is incorrect."
    }
    if (lowered.includes("session expired")) {
      return "Session expired. Please login again."
    }
    if (lowered.includes("missing bearer token")) {
      return "Please login first to continue."
    }
    if (lowered.includes("organization already exists")) {
      return "This organization is already registered."
    }
    if (lowered.includes("email already registered")) {
      return "This email is already registered."
    }
    if (lowered.includes("admin access required")) {
      return "This action is allowed only for admin users."
    }
    return normalized
  }

  if (status === 401) {
    return "Authentication failed. Please login and try again."
  }
  if (status === 403) {
    return "You do not have permission to perform this action."
  }
  if (status === 404) {
    return "Requested service endpoint was not found."
  }
  if (status === 422) {
    return "Some fields are invalid. Please check your input and try again."
  }
  if (status >= 500) {
    return "Server error occurred. Please try again in a moment."
  }

  return "Request failed. Please try again."
}

function parseErrorDetail(rawBody: string): unknown {
  const trimmed = String(rawBody ?? "").trim()
  if (!trimmed) {
    return undefined
  }

  try {
    const parsed = JSON.parse(trimmed) as { detail?: unknown }
    if (typeof parsed === "object" && parsed !== null && "detail" in parsed) {
      return parsed.detail
    }
    return parsed
  } catch {
    return trimmed
  }
}

async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers)
  if (!headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json")
  }
  const requestInit = {
    ...init,
    headers,
  }

  const triedBases = new Set<string>()
  const candidateBases = [activeApiBaseUrl, ...API_FALLBACK_CANDIDATES.filter((base) => base !== activeApiBaseUrl)]
  let lastError: Error | null = null

  for (const baseUrl of candidateBases) {
    if (triedBases.has(baseUrl)) {
      continue
    }
    triedBases.add(baseUrl)

    try {
      const response = await fetch(`${baseUrl}${path}`, requestInit)
      if (!response.ok) {
        const rawMessage = await response.text()
        const detail = parseErrorDetail(rawMessage)
        const userMessage = normalizeApiErrorMessage(response.status, detail)
        const responseError = new ApiRequestError(response.status, userMessage, detail)

        // If endpoint isn't available on current server, try next candidate.
        if (response.status === 404) {
          lastError = responseError
          continue
        }

        throw responseError
      }

      activeApiBaseUrl = baseUrl
      return response.json() as Promise<T>
    } catch (error) {
      if (error instanceof ApiRequestError) {
        lastError = error
      } else if (error instanceof Error) {
        const lowered = error.message.toLowerCase()
        if (lowered.includes("failed to fetch") || lowered.includes("network")) {
          lastError = new Error("Unable to connect to backend service. Please check deployment status.")
        } else {
          lastError = error
        }
      } else {
        lastError = new Error("Request failed. Please try again.")
      }
    }
  }

  throw lastError ?? new Error("Request failed. Please try again.")
}

function toSafeNumber(value: unknown, fallback = 0): number {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : fallback
}

function toDisplayTime(timestamp?: string): string {
  if (!timestamp) {
    return new Date().toLocaleTimeString("en-IN", { hour12: false })
  }

  const parsedDate = new Date(timestamp)
  if (Number.isNaN(parsedDate.getTime())) {
    return new Date().toLocaleTimeString("en-IN", { hour12: false })
  }

  return parsedDate.toLocaleTimeString("en-IN", { hour12: false })
}

function reportWindowDays(window: ReportWindow): number {
  if (window === "1w") {
    return 7
  }
  if (window === "1m") {
    return 30
  }
  return 1
}

function reportWindowLabel(window: ReportWindow): string {
  if (window === "1w") {
    return "Last 7 Days"
  }
  if (window === "1m") {
    return "Last 30 Days"
  }
  return "Last 1 Day"
}

function buildReportMarkdown(report: MonitoringReportPayload): string {
  const lines: string[] = [
    "# University IT Infrastructure & Server Performance Report",
    "",
    `**Report ID:** ${report.report_id}`,
    `**Generated At:** ${report.generated_at}`,
    `**Window:** ${report.window_label}`,
    "",
    "## 1. Executive Summary",
    `Uptime remained at **${report.executive_summary.uptime_percent.toFixed(2)}%** with **${report.executive_summary.records_analyzed}** records analyzed.`,
    "",
    "## 2. System Health Dashboard",
    "",
    "| Server Instance | Role | Status | CPU Load | RAM Usage | Notes |",
    "| :--- | :--- | :--- | :--- | :--- | :--- |",
  ]

  for (const row of report.system_health_dashboard) {
    const status = String(row.status ?? "unknown").toLowerCase()
    const emoji = status === "online" ? "🟢" : status === "warning" ? "🟡" : "🔴"
    lines.push(
      `| **${row.instance}** | ${row.role} | ${emoji} ${row.status} | ${row.cpu_load_percent.toFixed(1)}% | ${row.ram_usage_percent.toFixed(1)}% | ${row.notes} |`
    )
  }

  lines.push(
    "",
    "## 3. Performance",
    `- Peak Hour: ${report.performance.peak_hour}`,
    `- Peak Load: ${report.performance.peak_load_percent.toFixed(2)}%`,
    `- Average Energy: ${report.performance.avg_energy_kwh.toFixed(2)} kWh`,
    "",
    "## 4. Security Incident Report",
    `- Anomaly-filtered Records: ${report.security_incidents.anomaly_filtered_records}`,
    `- Critical Alerts: ${report.security_incidents.critical_alerts}`,
    `- Warning Alerts: ${report.security_incidents.warning_alerts}`,
    "",
    "## 5. Strategic Recommendations"
  )

  for (const [index, recommendation] of report.strategic_recommendations.entries()) {
    lines.push(`${index + 1}. ${recommendation}`)
  }

  return lines.join("\n")
}

async function buildFallbackMonitoringReport(
  window: ReportWindow,
  format: ReportFormat
): Promise<MonitoringReportResponse> {
  const live = await getLiveLaptopDashboard()
  const history = live.history ?? []
  const alerts = live.alerts ?? []
  const events = live.events ?? []
  const telemetry = live.telemetry ?? ({} as LiveDashboardResponse["telemetry"])
  const decision = live.decision ?? {}
  const optimizedDecision = decision.optimized_decision ?? {}

  let kpis: ExecutiveKpiMetrics | null = null
  try {
    const response = await getExecutiveKpis()
    kpis = response.metrics
  } catch {
    kpis = null
  }

  const energyValues = history.map((point) => Number(point.energy) || 0).filter((value) => value > 0)
  const totalEnergy = energyValues.reduce((sum, value) => sum + value, 0)
  const averageEnergy = energyValues.length > 0 ? totalEnergy / energyValues.length : 0
  const optimizedEnergy = Math.max(0, totalEnergy * ((Number(optimizedDecision.recommended_reduction) || 0) / 100))
  const avgLoad =
    history.length > 0
      ? history.reduce((sum, point) => sum + (Number(point.energy) || 0), 0) / Math.max(1, history.length)
      : Number(telemetry.cpu_percent ?? 0)

  const peakPoint = history.reduce(
    (currentPeak, point) => ((Number(point.energy) || 0) > (Number(currentPeak.energy) || 0) ? point : currentPeak),
    history[0] ?? { time: "00:00", energy: 0 }
  )

  const forecastAccuracy = Math.max(
    45,
    Math.min(
      99,
      kpis?.forecast_accuracy_percent ?? (Number(optimizedDecision.confidence_score) || 0.65) * 100
    )
  )

  const groupedByHour = new Map<string, number[]>()
  for (const point of history) {
    const key = String(point.time ?? "--:--")
    if (!groupedByHour.has(key)) {
      groupedByHour.set(key, [])
    }
    groupedByHour.get(key)?.push(Number(point.energy) || 0)
  }

  const hourlyProfile = Array.from(groupedByHour.entries())
    .map(([hour, values]) => ({
      hour,
      avg_load_percent:
        values.length > 0 ? Number((values.reduce((sum, value) => sum + value, 0) / values.length).toFixed(2)) : 0,
    }))
    .slice(0, 24)

  const windowDays = reportWindowDays(window)
  // Note: The CPU/RAM for sub-services are *estimates* based on the main
  // edge node's telemetry. These multipliers represent a typical distribution
  // of resources in a simulated environment, used here for fallback visualization.
  const report: MonitoringReportPayload = {
    report_id: `SCDIS-RPT-LOCAL-${new Date().toISOString().replace(/[:.]/g, "-")}`,
    generated_at: new Date().toISOString(),
    window,
    window_label: reportWindowLabel(window),
    executive_summary: {
      uptime_percent: live.service_health?.running ? 99.9 : 97.5,
      records_analyzed: history.length,
      window_days: windowDays,
      total_energy_kwh: Number(totalEnergy.toFixed(2)),
      average_energy_kwh: Number(averageEnergy.toFixed(2)),
      average_load_percent: Number(avgLoad.toFixed(2)),
      energy_optimized_kwh: Number(optimizedEnergy.toFixed(2)),
      forecast_accuracy_percent: Number(forecastAccuracy.toFixed(2)),
      critical_alerts: alerts.filter((alert) => alert.severity === "critical").length,
      warning_alerts: alerts.filter((alert) => alert.severity === "warning").length,
      quarantined_records: Math.max(0, Math.round((100 - (kpis?.anomaly_filtered_percent ?? 95)) / 2)),
    },
    system_health_dashboard: [
      {
        instance: telemetry.hostname ?? "EDGE-NODE",
        role: "Edge Telemetry Runtime",
        status: live.service_health?.running ? "online" : "warning",
        cpu_load_percent: Number(telemetry.cpu_percent ?? 0),
        ram_usage_percent: Number(telemetry.memory_percent ?? 0),
        notes: telemetry.platform ?? "N/A",
      },
      {
        instance: "AI-DECISION-ENGINE",
        role: "Forecast + Optimization",
        status: decision ? "online" : "warning",
        cpu_load_percent: Number(((Number(telemetry.cpu_percent ?? 0) * 0.62) || 0).toFixed(2)),
        ram_usage_percent: Number(((Number(telemetry.memory_percent ?? 0) * 0.66) || 0).toFixed(2)),
        notes: `Confidence ${Math.round((Number(optimizedDecision.confidence_score) || 0.65) * 100)}%`,
      },
      {
        instance: "SECURITY-FILTER-LAYER",
        role: "Telemetry Trust Filter",
        status: "online",
        cpu_load_percent: Number(((Number(telemetry.cpu_percent ?? 0) * 0.28) || 0).toFixed(2)),
        ram_usage_percent: Number(((Number(telemetry.memory_percent ?? 0) * 0.24) || 0).toFixed(2)),
        notes: "Anomaly gate active",
      },
    ],
    performance: {
      peak_hour: String(peakPoint?.time ?? "N/A"),
      peak_load_percent: Number((Number(peakPoint?.energy ?? 0)).toFixed(2)),
      avg_energy_kwh: Number(averageEnergy.toFixed(2)),
      hourly_load_profile: hourlyProfile,
    },
    security_incidents: {
      anomaly_filtered_records: Math.max(0, Math.round((100 - (kpis?.anomaly_filtered_percent ?? 95)) / 2)),
      critical_alerts: alerts.filter((alert) => alert.severity === "critical").length,
      warning_alerts: alerts.filter((alert) => alert.severity === "warning").length,
      notable_events_count: events.filter((event) =>
        /critical|error|anomaly|failure/i.test(String(event.message ?? ""))
      ).length,
      notable_events: events
        .filter((event) => /critical|error|anomaly|failure/i.test(String(event.message ?? "")))
        .slice(0, 8)
        .map((event) => String(event.message ?? "")),
    },
    strategic_recommendations: [
      "Continue to use adaptive alerting and make it a practice to review critical runtime alerts daily.",
      "Before the next expected peak load period, run the automated model retraining process.",
      "If the average load consistently exceeds 80%, it's a sign that you should increase edge capacity.",
      "Regularly audit quarantined telemetry to identify and recalibrate noisy sensors.",
      "For governance and operational records, export and archive reports on a weekly basis.",
    ],
  }

  const markdown = buildReportMarkdown(report)
  return {
    status: "fallback_local",
    window,
    format: format === "markdown" ? "markdown" : "json",
    report,
    markdown: format === "markdown" ? markdown : undefined,
  }
}

function toDecisionPayload(payload: TelemetryInput) {
  const now = new Date()
  const occupancy = Math.max(1, Math.round((payload.gridLoad / 100) * 1000))

  return {
    building_id: locationToBuildingId[payload.location] ?? 0,
    current_load: payload.energy,
    energy_usage_kwh: payload.energy,
    temperature: payload.temperature,
    humidity: 50,
    occupancy,
    day_of_week: now.getDay(),
    hour: now.getHours(),
    grid_load: payload.gridLoad,
    location: payload.location,
    state: payload.gridLoad >= 85 ? "high_load" : "normal",
  }
}

export function mapDecisionForUi(response: GenerateDecisionResponse): UiDecision {
  const decision = response.decision ?? {}
  const optimizedDecision = decision.optimized_decision ?? {}

  return {
    rlAction: String(decision.rl_action ?? "unknown_action"),
    reduction: Math.max(0, Math.round(toSafeNumber(optimizedDecision.recommended_reduction))),
    costSaved: Number(toSafeNumber(optimizedDecision.cost_saving_estimate).toFixed(2)),
    stabilityScore: Number(toSafeNumber(optimizedDecision.stability_score).toFixed(2)),
    confidenceScore: Number((toSafeNumber(optimizedDecision.confidence_score, 0.65) * 100).toFixed(0)),
    recommendedAction: String(optimizedDecision.recommended_action ?? "No recommendation available"),
    recommendedWindow: String(optimizedDecision.recommended_window ?? "N/A"),
    projectedSavingsInr: Number(toSafeNumber(optimizedDecision.estimated_savings_inr).toFixed(2)),
    rationale: String(optimizedDecision.rationale ?? "Awaiting telemetry confidence signal"),
    timestamp: toDisplayTime(decision.timestamp),
  }
}

export async function generateDecision(payload: TelemetryInput): Promise<GenerateDecisionResponse> {
  return apiRequest<GenerateDecisionResponse>("/decision/generate", {
    method: "POST",
    body: JSON.stringify(toDecisionPayload(payload)),
  })
}

export async function getSystemStatus(): Promise<SystemStatusResponse> {
  return apiRequest<SystemStatusResponse>("/autonomous-ai/status")
}

export async function runFullCycle(): Promise<Record<string, unknown>> {
  return apiRequest<Record<string, unknown>>("/autonomous-ai/run-full-cycle", {
    method: "POST",
  })
}

export async function getLiveLaptopDashboard(): Promise<LiveDashboardResponse> {
  return apiRequest<LiveDashboardResponse>("/monitoring/laptop/live-dashboard")
}

export async function getExecutiveKpis(): Promise<ExecutiveKpiResponse> {
  if (executiveKpisSupported === false) {
    throw new Error("executive_kpis_unavailable")
  }

  try {
    const response = await apiRequest<ExecutiveKpiResponse>("/monitoring/executive-kpis")
    executiveKpisSupported = true
    return response
  } catch (error) {
    const message = error instanceof Error ? error.message : ""
    if (message.includes("API 404")) {
      executiveKpisSupported = false
    }
    throw error
  }
}

export async function getMonitoringReport(
  window: ReportWindow = "1d",
  format: ReportFormat = "json"
): Promise<MonitoringReportResponse> {
  const params = new URLSearchParams({
    window,
    format,
  })
  try {
    return await apiRequest<MonitoringReportResponse>(`/monitoring/report?${params.toString()}`)
  } catch (error) {
    try {
      return await buildFallbackMonitoringReport(window, format)
    } catch {
      throw error
    }
  }
}

export async function downloadMonitoringReport(
  window: ReportWindow = "1d",
  format: ReportDownloadFormat = "pdf"
): Promise<Blob> {
  const params = new URLSearchParams({
    window,
    format,
  })
  const path = `/monitoring/report/download?${params.toString()}`
  const candidateBases = [activeApiBaseUrl, ...API_FALLBACK_CANDIDATES.filter((base) => base !== activeApiBaseUrl)]
  const triedBases = new Set<string>()
  let lastError: Error | null = null

  for (const baseUrl of candidateBases) {
    if (triedBases.has(baseUrl)) {
      continue
    }
    triedBases.add(baseUrl)

    try {
      const response = await fetch(`${baseUrl}${path}`)
      if (!response.ok) {
        const message = await response.text()
        const responseError = new Error(`API ${response.status}: ${message || "request failed"}`)
        if (response.status === 404) {
          lastError = responseError
          continue
        }
        throw responseError
      }

      activeApiBaseUrl = baseUrl
      return response.blob()
    } catch (error) {
      lastError = error instanceof Error ? error : new Error("request failed")
    }
  }

  try {
    if (format === "pdf") {
      throw lastError ?? new Error("PDF report endpoint unavailable on active backend.")
    }

    const fallback = await getMonitoringReport(window, format === "json" ? "json" : "markdown")
    if (format === "json") {
      return new Blob([JSON.stringify(fallback.report, null, 2)], {
        type: "application/json;charset=utf-8",
      })
    }

    const markdown = fallback.markdown ?? buildReportMarkdown(fallback.report)
    return new Blob([markdown], {
      type: "text/markdown;charset=utf-8",
    })
  } catch {
    throw lastError ?? new Error("request failed")
  }
}

export async function setAutoApplyPowerProfile(enabled: boolean): Promise<Record<string, unknown>> {
  return apiRequest<Record<string, unknown>>("/monitoring/laptop/auto-apply", {
    method: "POST",
    body: JSON.stringify({ enabled }),
  })
}

export async function setRuntimeMode(mode: RuntimeMode): Promise<RuntimeControlResponse> {
  return apiRequest<RuntimeControlResponse>("/monitoring/laptop/mode", {
    method: "POST",
    body: JSON.stringify({ mode }),
  })
}

export async function setSimulationScenario(
  scenario: SimulationScenario,
  cycles = 12
): Promise<RuntimeControlResponse> {
  return apiRequest<RuntimeControlResponse>("/monitoring/laptop/scenario", {
    method: "POST",
    body: JSON.stringify({ scenario, cycles }),
  })
}

export async function retrainAiModels(): Promise<AiModelRetrainResponse> {
  return apiRequest<AiModelRetrainResponse>("/monitoring/ai-models/retrain", {
    method: "POST",
  })
}

export async function getAiModelLogs(
  source: AiModelLogSource = "application",
  lines = 150
): Promise<AiModelLogsResponse> {
  const params = new URLSearchParams({
    source,
    lines: String(Math.max(20, Math.min(lines, 1000))),
  })

  return apiRequest<AiModelLogsResponse>(`/monitoring/ai-models/logs?${params.toString()}`)
}

export async function exportAiModelWeights(model: ExportModelTarget = "forecast"): Promise<Blob> {
  const path = `/monitoring/ai-models/export-weights?model=${encodeURIComponent(model)}`
  const candidateBases = [activeApiBaseUrl, ...API_FALLBACK_CANDIDATES.filter((base) => base !== activeApiBaseUrl)]
  const triedBases = new Set<string>()
  let lastError: Error | null = null

  for (const baseUrl of candidateBases) {
    if (triedBases.has(baseUrl)) {
      continue
    }
    triedBases.add(baseUrl)

    try {
      const response = await fetch(`${baseUrl}${path}`)
      if (!response.ok) {
        const message = await response.text()
        const responseError = new Error(`API ${response.status}: ${message || "request failed"}`)
        if (response.status === 404) {
          lastError = responseError
          continue
        }
        throw responseError
      }

      activeApiBaseUrl = baseUrl
      return response.blob()
    } catch (error) {
      lastError = error instanceof Error ? error : new Error("request failed")
    }
  }

  throw lastError ?? new Error("request failed")
}

async function downloadBlob(path: string): Promise<Blob> {
  const candidateBases = [activeApiBaseUrl, ...API_FALLBACK_CANDIDATES.filter((base) => base !== activeApiBaseUrl)]
  const triedBases = new Set<string>()
  let lastError: Error | null = null

  for (const baseUrl of candidateBases) {
    if (triedBases.has(baseUrl)) {
      continue
    }
    triedBases.add(baseUrl)

    try {
      const response = await fetch(`${baseUrl}${path}`)
      if (!response.ok) {
        const message = await response.text()
        const responseError = new Error(`API ${response.status}: ${message || "request failed"}`)
        if (response.status === 404) {
          lastError = responseError
          continue
        }
        throw responseError
      }
      activeApiBaseUrl = baseUrl
      return response.blob()
    } catch (error) {
      lastError = error instanceof Error ? error : new Error("request failed")
    }
  }

  throw lastError ?? new Error("request failed")
}

export async function queryAiAssistantLogs(
  query: string,
  source: AiModelLogSource = "application",
  maxLines = 700,
  topK = 8
): Promise<AiAssistantLogQueryResponse> {
  return apiRequest<AiAssistantLogQueryResponse>("/monitoring/ai-assistant/query-logs", {
    method: "POST",
    body: JSON.stringify({
      query,
      source,
      max_lines: Math.max(20, Math.min(maxLines, 4000)),
      top_k: Math.max(1, Math.min(topK, 12)),
    }),
  })
}

export async function getAiAssistantAlertSummary(): Promise<AiAssistantRuntimeSummaryResponse> {
  return apiRequest<AiAssistantRuntimeSummaryResponse>("/monitoring/ai-assistant/runtime-summary")
}

export async function getAiAssistantOpsRecommendations(): Promise<AiAssistantOpsRecommendationResponse> {
  return apiRequest<AiAssistantOpsRecommendationResponse>("/monitoring/ai-assistant/ops-recommendations")
}

export async function getImpactMetrics(): Promise<ImpactMetricsResponse> {
  return apiRequest<ImpactMetricsResponse>("/monitoring/impact-metrics")
}

export async function getDecisionExplanation(): Promise<DecisionExplanationResponse> {
  return apiRequest<DecisionExplanationResponse>("/monitoring/decision/explain")
}

export async function generateIncidentRunbook(
  incidentType?: string,
  autoExecute = false
): Promise<IncidentRunbookResponse> {
  return apiRequest<IncidentRunbookResponse>("/monitoring/runbook/generate", {
    method: "POST",
    body: JSON.stringify({
      incident_type: incidentType,
      auto_execute: autoExecute,
    }),
  })
}

export async function getGovernanceAudit(limit = 120): Promise<GovernanceAuditResponse> {
  const params = new URLSearchParams({
    limit: String(Math.max(1, Math.min(limit, 1000))),
  })
  return apiRequest<GovernanceAuditResponse>(`/monitoring/governance/audit?${params.toString()}`)
}

export async function getModelReliability(): Promise<ModelReliabilityResponse> {
  return apiRequest<ModelReliabilityResponse>("/monitoring/model-reliability")
}

export async function runStressValidation(cycles = 12): Promise<StressValidationResponse> {
  return apiRequest<StressValidationResponse>("/monitoring/stress-test/run", {
    method: "POST",
    body: JSON.stringify({ cycles: Math.max(2, Math.min(cycles, 60)) }),
  })
}

export async function getRoiProjection(
  siteCount = 100,
  annualGrowthPct = 12,
  horizonYears = 3
): Promise<RoiProjectionResponse> {
  const params = new URLSearchParams({
    site_count: String(Math.max(1, Math.min(siteCount, 5000))),
    annual_growth_pct: String(Math.max(0, Math.min(annualGrowthPct, 200))),
    horizon_years: String(Math.max(1, Math.min(horizonYears, 10))),
  })
  return apiRequest<RoiProjectionResponse>(`/monitoring/roi/projection?${params.toString()}`)
}

export async function exportRoiProjectionCsv(
  siteCount = 100,
  annualGrowthPct = 12,
  horizonYears = 3
): Promise<Blob> {
  const params = new URLSearchParams({
    site_count: String(Math.max(1, Math.min(siteCount, 5000))),
    annual_growth_pct: String(Math.max(0, Math.min(annualGrowthPct, 200))),
    horizon_years: String(Math.max(1, Math.min(horizonYears, 10))),
  })
  return downloadBlob(`/monitoring/roi/projection/export?${params.toString()}`)
}

export async function ingestEdgeAgentTelemetry(payload: {
  edge_id: string
  hostname: string
  platform: string
  cpu_percent: number
  memory_percent: number
  disk_percent: number
  battery_percent: number | null
  power_plugged: boolean | null
  process_count: number
  network_type?: string | null
  source?: string | null
}): Promise<EdgeAgentIngestResponse> {
  return apiRequest<EdgeAgentIngestResponse>("/monitoring/edge-agent/ingest", {
    method: "POST",
    body: JSON.stringify(payload),
  })
}

export async function getEdgeAgentLatest(): Promise<EdgeAgentLatestResponse> {
  return apiRequest<EdgeAgentLatestResponse>("/monitoring/edge-agent/latest")
}

export async function getEdgeAgentLatestById(edgeId: string): Promise<EdgeAgentLatestByIdResponse> {
  return apiRequest<EdgeAgentLatestByIdResponse>(`/monitoring/edge-agent/latest/${encodeURIComponent(edgeId)}`)
}

export interface EnterpriseAuthResponse {
  status: string
  timestamp: string
  user_id: number
  organization_id: number | null
  organization_name?: string | null
  email: string
  role: "admin" | "org_admin"
  token: string
  expires_at: string
}

export interface EnterpriseSessionResponse {
  status: string
  timestamp: string
  session: {
    user_id: number
    email: string
    role: "admin" | "org_admin"
    organization_id: number | null
    organization_name?: string | null
  }
}

export interface EnterpriseTrainingStatsResponse {
  status: string
  timestamp: string
  stats: {
    pending_samples: number
    training_run_count: number
    auto_trainer_running: boolean
    auto_trainer_interval_sec: number
    auto_trainer_min_samples: number
    database_backend?: "sqlite" | "postgresql"
    grouped: Array<{ model_name: string; status: string; cnt: number }>
    last_run?: Record<string, unknown> | null
  }
}

async function apiRequestWithBearer<T>(path: string, token: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers)
  headers.set("Authorization", `Bearer ${token}`)
  if (!headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json")
  }

  return apiRequest<T>(path, {
    ...init,
    headers,
  })
}

export async function registerOrganizationAccount(
  organizationName: string,
  adminEmail: string,
  password: string
): Promise<EnterpriseAuthResponse> {
  return apiRequest<EnterpriseAuthResponse>("/enterprise/auth/register-organization", {
    method: "POST",
    body: JSON.stringify({
      organization_name: organizationName,
      admin_email: adminEmail,
      password,
    }),
  })
}

export async function loginEnterpriseAdmin(email: string, password: string): Promise<EnterpriseAuthResponse> {
  return apiRequest<EnterpriseAuthResponse>("/enterprise/auth/login-admin", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  })
}

export async function loginEnterpriseOrganization(email: string, password: string): Promise<EnterpriseAuthResponse> {
  return apiRequest<EnterpriseAuthResponse>("/enterprise/auth/login-org", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  })
}

export async function getEnterpriseMe(token: string): Promise<EnterpriseSessionResponse> {
  return apiRequestWithBearer<EnterpriseSessionResponse>("/enterprise/auth/me", token)
}

export async function logoutEnterprise(token: string): Promise<{ status: string; timestamp: string }> {
  return apiRequestWithBearer<{ status: string; timestamp: string }>("/enterprise/auth/logout", token, {
    method: "POST",
  })
}

export async function ingestTrainingSample(
  token: string,
  payload: {
    model_name: "forecast" | "anomaly" | "rl"
    payload: Record<string, unknown>
    error_tag?: string
  }
): Promise<{ status: string; timestamp: string }> {
  return apiRequestWithBearer<{ status: string; timestamp: string }>("/training-data/ingest", token, {
    method: "POST",
    body: JSON.stringify(payload),
  })
}

export async function runTrainingNow(
  token: string,
  payload?: { model_name?: string; max_samples?: number; purge_after_train?: boolean }
): Promise<Record<string, unknown>> {
  return apiRequestWithBearer<Record<string, unknown>>("/training-data/run-now", token, {
    method: "POST",
    body: JSON.stringify({
      model_name: payload?.model_name,
      max_samples: payload?.max_samples ?? 500,
      purge_after_train: payload?.purge_after_train ?? true,
    }),
  })
}

export async function getEnterpriseTrainingStats(token: string): Promise<EnterpriseTrainingStatsResponse> {
  return apiRequestWithBearer<EnterpriseTrainingStatsResponse>("/training-data/stats", token)
}
