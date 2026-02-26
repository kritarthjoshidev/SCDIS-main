"use client"

import { useEffect, useMemo, useState } from "react"
import { motion } from "framer-motion"
import {
  Bell,
  Brain,
  Database,
  Download,
  Gauge,
  Globe,
  Moon,
  Save,
  Settings,
  Shield,
  Target,
  ToggleLeft,
  ToggleRight,
  Wrench,
  Zap,
} from "lucide-react"
import { Slider } from "@/components/ui/slider"
import { ScrollArea } from "@/components/ui/scroll-area"
import { ScrollReveal } from "@/components/ui/scroll-reveal"
import { useClientEdgeProfile } from "@/hooks/use-client-edge-profile"
import {
  exportRoiProjectionCsv,
  generateIncidentRunbook,
  getDecisionExplanation,
  getEdgeAgentLatest,
  getGovernanceAudit,
  getImpactMetrics,
  getModelReliability,
  getRoiProjection,
  ingestEdgeAgentTelemetry,
  runStressValidation,
  type DecisionExplanation,
  type EdgeAgentTelemetry,
  type GovernanceAuditItem,
  type ImpactMetrics,
  type IncidentRunbookStep,
  type ModelReliability,
  type RoiProjectionResponse,
  type StressValidationReport,
} from "@/lib/api"

interface SettingToggle {
  id: string
  label: string
  description: string
  enabled: boolean
  icon: typeof Bell
}

type IncidentPreset = "auto" | "grid_failure" | "peak_load" | "cpu_pressure" | "normal_ops"

export function SettingsTab() {
  const clientEdge = useClientEdgeProfile()
  const [toggles, setToggles] = useState<SettingToggle[]>([
    {
      id: "auto-mode",
      label: "Autonomous Mode",
      description: "Allow AI to make decisions without human approval",
      enabled: true,
      icon: Brain,
    },
    {
      id: "alerts",
      label: "Real-time Alerts",
      description: "Push notifications for critical and warning events",
      enabled: true,
      icon: Bell,
    },
    {
      id: "auto-retrain",
      label: "Auto Model Retraining",
      description: "Automatically retrain models when accuracy dips below threshold",
      enabled: true,
      icon: Database,
    },
    {
      id: "failover",
      label: "Auto Failover",
      description: "Automatically activate backup nodes on failure detection",
      enabled: true,
      icon: Shield,
    },
    {
      id: "dark-mode",
      label: "Dark Interface",
      description: "Use dark color scheme for control center",
      enabled: true,
      icon: Moon,
    },
    {
      id: "telemetry",
      label: "Send Telemetry",
      description: "Share anonymized performance data for system improvement",
      enabled: true,
      icon: Globe,
    },
  ])

  const [accuracyThreshold, setAccuracyThreshold] = useState(90)
  const [alertFrequency, setAlertFrequency] = useState(5)
  const [retentionDays, setRetentionDays] = useState(30)

  const [impactMetrics, setImpactMetrics] = useState<ImpactMetrics | null>(null)
  const [decisionExplanation, setDecisionExplanation] = useState<DecisionExplanation | null>(null)
  const [modelReliability, setModelReliability] = useState<ModelReliability | null>(null)
  const [auditItems, setAuditItems] = useState<GovernanceAuditItem[]>([])
  const [edgeNodes, setEdgeNodes] = useState<EdgeAgentTelemetry[]>([])
  const [stressReport, setStressReport] = useState<StressValidationReport | null>(null)
  const [runbook, setRunbook] = useState<IncidentRunbookStep[]>([])
  const [runbookIncident, setRunbookIncident] = useState<IncidentPreset>("auto")
  const [runbookAutoExecute, setRunbookAutoExecute] = useState(false)

  const [roiSites, setRoiSites] = useState(100)
  const [roiGrowth, setRoiGrowth] = useState(12)
  const [roiYears, setRoiYears] = useState(3)
  const [roiProjection, setRoiProjection] = useState<RoiProjectionResponse | null>(null)

  const [isLoadingPack, setIsLoadingPack] = useState(false)
  const [isGeneratingRunbook, setIsGeneratingRunbook] = useState(false)
  const [isRunningStress, setIsRunningStress] = useState(false)
  const [isGeneratingRoi, setIsGeneratingRoi] = useState(false)
  const [isExportingRoi, setIsExportingRoi] = useState(false)
  const [isSyncingEdge, setIsSyncingEdge] = useState(false)
  const [statusMessage, setStatusMessage] = useState<{ tone: "success" | "error" | "info"; text: string } | null>(
    null
  )

  const toggle = (id: string) => {
    setToggles((prev) => prev.map((item) => (item.id === id ? { ...item, enabled: !item.enabled } : item)))
  }

  const loadFeaturePack = async () => {
    setIsLoadingPack(true)
    try {
      const [impact, explain, reliability, audit, edge] = await Promise.all([
        getImpactMetrics(),
        getDecisionExplanation(),
        getModelReliability(),
        getGovernanceAudit(120),
        getEdgeAgentLatest(),
      ])
      setImpactMetrics(impact.metrics)
      setDecisionExplanation(explain.explanation)
      setModelReliability(reliability.reliability)
      setAuditItems(audit.items)
      setEdgeNodes(edge.edges)
      setStatusMessage({ tone: "success", text: "Enterprise feature pack refreshed." })
    } catch (error) {
      setStatusMessage({
        tone: "error",
        text: error instanceof Error ? error.message : "Unable to refresh enterprise pack",
      })
    } finally {
      setIsLoadingPack(false)
    }
  }

  useEffect(() => {
    loadFeaturePack()
  }, [])

  const handleRunbook = async () => {
    if (isGeneratingRunbook) {
      return
    }
    setIsGeneratingRunbook(true)
    try {
      const response = await generateIncidentRunbook(
        runbookIncident === "auto" ? undefined : runbookIncident,
        runbookAutoExecute
      )
      setRunbook(response.runbook)
      setStatusMessage({
        tone: "success",
        text: `Runbook generated for ${response.incident_type}.`,
      })
    } catch (error) {
      setStatusMessage({
        tone: "error",
        text: error instanceof Error ? error.message : "Runbook generation failed",
      })
    } finally {
      setIsGeneratingRunbook(false)
    }
  }

  const handleStressTest = async () => {
    if (isRunningStress) {
      return
    }
    setIsRunningStress(true)
    try {
      const response = await runStressValidation(12)
      setStressReport(response.report)
      setStatusMessage({
        tone: "success",
        text: `Stress validation completed: ${response.report.passed}/${response.report.total_scenarios} passed.`,
      })
      const audit = await getGovernanceAudit(120)
      setAuditItems(audit.items)
    } catch (error) {
      setStatusMessage({
        tone: "error",
        text: error instanceof Error ? error.message : "Stress validation failed",
      })
    } finally {
      setIsRunningStress(false)
    }
  }

  const handleRoiProjection = async () => {
    if (isGeneratingRoi) {
      return
    }
    setIsGeneratingRoi(true)
    try {
      const response = await getRoiProjection(roiSites, roiGrowth, roiYears)
      setRoiProjection(response)
      setStatusMessage({
        tone: "success",
        text: `ROI projection ready for ${response.site_count} sites.`,
      })
    } catch (error) {
      setStatusMessage({
        tone: "error",
        text: error instanceof Error ? error.message : "ROI projection failed",
      })
    } finally {
      setIsGeneratingRoi(false)
    }
  }

  const handleRoiExport = async () => {
    if (isExportingRoi) {
      return
    }
    setIsExportingRoi(true)
    try {
      const blob = await exportRoiProjectionCsv(roiSites, roiGrowth, roiYears)
      const url = window.URL.createObjectURL(blob)
      const anchor = document.createElement("a")
      anchor.href = url
      anchor.download = `roi_projection_${new Date().toISOString().replace(/[:.]/g, "-")}.csv`
      document.body.appendChild(anchor)
      anchor.click()
      anchor.remove()
      window.URL.revokeObjectURL(url)
      setStatusMessage({ tone: "success", text: "ROI projection exported." })
      const audit = await getGovernanceAudit(120)
      setAuditItems(audit.items)
    } catch (error) {
      setStatusMessage({
        tone: "error",
        text: error instanceof Error ? error.message : "ROI export failed",
      })
    } finally {
      setIsExportingRoi(false)
    }
  }

  const handleSyncEdge = async () => {
    if (isSyncingEdge || !clientEdge) {
      return
    }
    setIsSyncingEdge(true)
    try {
      await ingestEdgeAgentTelemetry({
        edge_id: clientEdge.edgeLabel,
        hostname: clientEdge.edgeLabel,
        platform: clientEdge.platform,
        cpu_percent: 0,
        memory_percent: 0,
        disk_percent: 0,
        battery_percent: clientEdge.batteryPercent,
        power_plugged: clientEdge.powerPlugged,
        process_count: 0,
        network_type: clientEdge.networkType,
        source: "browser-agent",
      })
      const edge = await getEdgeAgentLatest()
      const audit = await getGovernanceAudit(120)
      setEdgeNodes(edge.edges)
      setAuditItems(audit.items)
      setStatusMessage({ tone: "success", text: `Edge agent synced: ${clientEdge.edgeLabel}.` })
    } catch (error) {
      setStatusMessage({
        tone: "error",
        text: error instanceof Error ? error.message : "Edge sync failed",
      })
    } finally {
      setIsSyncingEdge(false)
    }
  }

  const reliabilityTone = useMemo(() => {
    const value = modelReliability?.reliability_status ?? "STABLE"
    if (value === "AT_RISK") {
      return "text-neon-red"
    }
    if (value === "WATCH") {
      return "text-neon-amber"
    }
    return "text-neon-green"
  }, [modelReliability])

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <ScrollReveal className="flex items-center gap-2" delay={0.02}>
        <Settings className="size-5 text-neon-cyan" />
        <h2 className="font-mono text-sm font-bold uppercase tracking-widest text-foreground">
          Enterprise Readiness Console
        </h2>
        <button
          onClick={loadFeaturePack}
          disabled={isLoadingPack}
          className="ml-auto rounded-lg border border-neon-cyan/40 bg-neon-cyan/10 px-3 py-1.5 font-mono text-[10px] uppercase tracking-wider text-neon-cyan transition-colors hover:bg-neon-cyan/20 disabled:opacity-60"
        >
          {isLoadingPack ? "Refreshing..." : "Refresh Pack"}
        </button>
      </ScrollReveal>

      {statusMessage && (
        <div
          className={`rounded-lg border px-3 py-2 font-mono text-[11px] ${
            statusMessage.tone === "error"
              ? "border-neon-red/30 bg-neon-red/10 text-neon-red"
              : statusMessage.tone === "success"
                ? "border-neon-green/30 bg-neon-green/10 text-neon-green"
                : "border-neon-cyan/30 bg-neon-cyan/10 text-neon-cyan"
          }`}
        >
          {statusMessage.text}
        </div>
      )}

      <ScrollReveal className="grid grid-cols-2 gap-3 lg:grid-cols-6" delay={0.06}>
        <div className="rounded-xl border border-border bg-card p-3">
          <div className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">Energy Reduction</div>
          <div className="mt-1 font-mono text-xl font-bold text-neon-green">
            {impactMetrics ? `${impactMetrics.energy_reduction_pct}%` : "--"}
          </div>
        </div>
        <div className="rounded-xl border border-border bg-card p-3">
          <div className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">Cost Saved/Day</div>
          <div className="mt-1 font-mono text-xl font-bold text-neon-amber">
            {impactMetrics ? `Rs ${impactMetrics.cost_saved_inr_day}` : "--"}
          </div>
        </div>
        <div className="rounded-xl border border-border bg-card p-3">
          <div className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">CO2 Reduced/Day</div>
          <div className="mt-1 font-mono text-xl font-bold text-neon-cyan">
            {impactMetrics ? `${impactMetrics.co2_reduced_kg_day} kg` : "--"}
          </div>
        </div>
        <div className="rounded-xl border border-border bg-card p-3">
          <div className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">Uptime Gain</div>
          <div className="mt-1 font-mono text-xl font-bold text-neon-purple">
            {impactMetrics ? `${impactMetrics.uptime_improvement_pct}%` : "--"}
          </div>
        </div>
        <div className="rounded-xl border border-border bg-card p-3">
          <div className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">Decision Confidence</div>
          <div className="mt-1 font-mono text-xl font-bold text-neon-cyan">
            {decisionExplanation ? `${decisionExplanation.confidence_pct}%` : "--"}
          </div>
        </div>
        <div className="rounded-xl border border-border bg-card p-3">
          <div className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">Reliability</div>
          <div className={`mt-1 font-mono text-xl font-bold ${reliabilityTone}`}>
            {modelReliability?.reliability_status ?? "--"}
          </div>
        </div>
      </ScrollReveal>

      <div className="grid gap-6 lg:grid-cols-12">
        <ScrollReveal className="rounded-xl border border-border bg-card p-5 lg:col-span-5" delay={0.1}>
          <h3 className="mb-4 font-mono text-xs uppercase tracking-widest text-muted-foreground">System Controls</h3>
          <div className="space-y-1">
            {toggles.map((setting, index) => {
              const Icon = setting.icon
              return (
                <motion.div
                  key={setting.id}
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.04 }}
                  className="flex items-center justify-between rounded-lg p-3 transition-colors hover:bg-secondary/40"
                >
                  <div className="flex items-center gap-3">
                    <Icon className="size-4 text-muted-foreground" />
                    <div>
                      <div className="font-mono text-xs font-bold text-foreground">{setting.label}</div>
                      <div className="font-mono text-[10px] text-muted-foreground">{setting.description}</div>
                    </div>
                  </div>
                  <button onClick={() => toggle(setting.id)} className="shrink-0">
                    {setting.enabled ? (
                      <ToggleRight className="size-7 text-neon-cyan" />
                    ) : (
                      <ToggleLeft className="size-7 text-muted-foreground" />
                    )}
                  </button>
                </motion.div>
              )
            })}
          </div>

          <div className="mt-5 space-y-5">
            <div>
              <div className="mb-2 flex items-center justify-between">
                <span className="font-mono text-xs text-foreground">Accuracy Retrain Threshold</span>
                <span className="font-mono text-xs text-neon-cyan">{accuracyThreshold}%</span>
              </div>
              <Slider
                value={[accuracyThreshold]}
                onValueChange={([v]) => setAccuracyThreshold(v)}
                min={80}
                max={99}
                step={1}
                className="[&_[data-slot=slider-range]]:bg-neon-cyan [&_[data-slot=slider-thumb]]:border-neon-cyan [&_[data-slot=slider-track]]:bg-neon-cyan/10"
              />
            </div>
            <div>
              <div className="mb-2 flex items-center justify-between">
                <span className="font-mono text-xs text-foreground">Alert Cooldown</span>
                <span className="font-mono text-xs text-neon-amber">{alertFrequency}s</span>
              </div>
              <Slider
                value={[alertFrequency]}
                onValueChange={([v]) => setAlertFrequency(v)}
                min={1}
                max={60}
                step={1}
                className="[&_[data-slot=slider-range]]:bg-neon-amber [&_[data-slot=slider-thumb]]:border-neon-amber [&_[data-slot=slider-track]]:bg-neon-amber/10"
              />
            </div>
            <div>
              <div className="mb-2 flex items-center justify-between">
                <span className="font-mono text-xs text-foreground">Log Retention</span>
                <span className="font-mono text-xs text-neon-purple">{retentionDays}d</span>
              </div>
              <Slider
                value={[retentionDays]}
                onValueChange={([v]) => setRetentionDays(v)}
                min={7}
                max={90}
                step={1}
                className="[&_[data-slot=slider-range]]:bg-neon-purple [&_[data-slot=slider-thumb]]:border-neon-purple [&_[data-slot=slider-track]]:bg-neon-purple/10"
              />
            </div>
          </div>
        </ScrollReveal>

        <ScrollReveal className="space-y-4 lg:col-span-7" delay={0.14}>
          <div className="rounded-xl border border-border bg-card p-5">
            <div className="mb-3 flex items-center gap-2">
              <Wrench className="size-4 text-neon-cyan" />
              <h3 className="font-mono text-xs uppercase tracking-widest text-neon-cyan">Incident Runbook</h3>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <select
                value={runbookIncident}
                onChange={(event) => setRunbookIncident(event.target.value as IncidentPreset)}
                className="rounded-lg border border-border bg-background px-3 py-2 font-mono text-[11px] text-foreground focus:border-neon-cyan focus:outline-none"
              >
                <option value="auto">Auto Detect Incident</option>
                <option value="grid_failure">Grid Failure</option>
                <option value="peak_load">Peak Load</option>
                <option value="cpu_pressure">CPU Pressure</option>
                <option value="normal_ops">Normal Ops</option>
              </select>
              <button
                onClick={() => setRunbookAutoExecute((prev) => !prev)}
                className={`rounded-lg border px-3 py-2 font-mono text-[10px] uppercase tracking-wider ${
                  runbookAutoExecute
                    ? "border-neon-green bg-neon-green/10 text-neon-green"
                    : "border-border text-muted-foreground"
                }`}
              >
                Auto Execute: {runbookAutoExecute ? "ON" : "OFF"}
              </button>
              <button
                onClick={handleRunbook}
                disabled={isGeneratingRunbook}
                className="rounded-lg border border-neon-cyan bg-neon-cyan/10 px-3 py-2 font-mono text-[10px] uppercase tracking-wider text-neon-cyan transition-colors hover:bg-neon-cyan/20 disabled:opacity-60"
              >
                {isGeneratingRunbook ? "Generating..." : "Generate Runbook"}
              </button>
            </div>
            <div className="mt-3 space-y-2">
              {runbook.length === 0 && (
                <div className="rounded border border-border bg-secondary/20 p-2 font-mono text-[10px] text-muted-foreground">
                  No runbook generated yet.
                </div>
              )}
              {runbook.map((step) => (
                <div key={step.step} className="rounded border border-border bg-secondary/20 p-2">
                  <div className="font-mono text-[10px] text-neon-cyan">
                    Step {step.step} | {step.status.toUpperCase()} | {step.owner}
                  </div>
                  <div className="mt-1 font-mono text-[11px] text-foreground">{step.title}</div>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-xl border border-border bg-card p-5">
            <div className="mb-3 flex items-center gap-2">
              <Target className="size-4 text-neon-amber" />
              <h3 className="font-mono text-xs uppercase tracking-widest text-neon-amber">Reliability & Validation</h3>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <button
                onClick={handleStressTest}
                disabled={isRunningStress}
                className="rounded-lg border border-neon-amber bg-neon-amber/10 px-3 py-2 font-mono text-[10px] uppercase tracking-wider text-neon-amber transition-colors hover:bg-neon-amber/20 disabled:opacity-60"
              >
                {isRunningStress ? "Running..." : "Run Stress Validation"}
              </button>
              <span className="font-mono text-[10px] text-muted-foreground">
                Drift: {modelReliability ? modelReliability.drift_score : "--"} | Perf:{" "}
                {modelReliability ? `${modelReliability.model_performance_pct}%` : "--"}
              </span>
            </div>
            <div className="mt-3 space-y-2">
              {stressReport?.results?.map((item) => (
                <div key={item.scenario} className="rounded border border-border bg-secondary/20 p-2">
                  <div className="font-mono text-[10px] text-neon-amber">
                    {item.scenario.toUpperCase()} | {item.result}
                  </div>
                  <div className="mt-1 font-mono text-[11px] text-foreground">
                    resilience={item.avg_resilience_score} | failover={item.estimated_failover_triggered ? "YES" : "NO"}
                  </div>
                </div>
              ))}
              {!stressReport && (
                <div className="rounded border border-border bg-secondary/20 p-2 font-mono text-[10px] text-muted-foreground">
                  Run stress validation to generate a scenario report.
                </div>
              )}
            </div>
          </div>
        </ScrollReveal>
      </div>

      <div className="grid gap-6 lg:grid-cols-12">
        <ScrollReveal className="rounded-xl border border-border bg-card p-5 lg:col-span-7" delay={0.18}>
          <div className="mb-3 flex items-center gap-2">
            <Gauge className="size-4 text-neon-purple" />
            <h3 className="font-mono text-xs uppercase tracking-widest text-neon-purple">Business ROI Projection</h3>
          </div>
          <div className="grid gap-2 lg:grid-cols-4">
            <input
              type="number"
              value={roiSites}
              onChange={(event) => setRoiSites(Number(event.target.value))}
              className="rounded-lg border border-border bg-background px-3 py-2 font-mono text-[11px] text-foreground"
              placeholder="Sites"
            />
            <input
              type="number"
              value={roiGrowth}
              onChange={(event) => setRoiGrowth(Number(event.target.value))}
              className="rounded-lg border border-border bg-background px-3 py-2 font-mono text-[11px] text-foreground"
              placeholder="Growth %"
            />
            <input
              type="number"
              value={roiYears}
              onChange={(event) => setRoiYears(Number(event.target.value))}
              className="rounded-lg border border-border bg-background px-3 py-2 font-mono text-[11px] text-foreground"
              placeholder="Years"
            />
            <div className="flex gap-2">
              <button
                onClick={handleRoiProjection}
                disabled={isGeneratingRoi}
                className="rounded-lg border border-neon-purple bg-neon-purple/10 px-3 py-2 font-mono text-[10px] uppercase tracking-wider text-neon-purple disabled:opacity-60"
              >
                {isGeneratingRoi ? "Generating..." : "Project"}
              </button>
              <button
                onClick={handleRoiExport}
                disabled={isExportingRoi}
                className="rounded-lg border border-border px-3 py-2 font-mono text-[10px] uppercase tracking-wider text-muted-foreground hover:text-foreground disabled:opacity-60"
              >
                <Download className="size-3" />
              </button>
            </div>
          </div>
          <div className="mt-3 space-y-2">
            {roiProjection?.projection?.map((row) => (
              <div key={row.year} className="rounded border border-border bg-secondary/20 p-2">
                <div className="font-mono text-[10px] text-neon-purple">Year {row.year} | Sites {row.sites}</div>
                <div className="mt-1 font-mono text-[11px] text-foreground">
                  Saved Rs {row.estimated_cost_saved_inr} | CO2 {row.estimated_co2_reduced_kg} kg
                </div>
              </div>
            ))}
            {!roiProjection && (
              <div className="rounded border border-border bg-secondary/20 p-2 font-mono text-[10px] text-muted-foreground">
                Generate ROI projection to view annual business impact.
              </div>
            )}
          </div>
        </ScrollReveal>

        <ScrollReveal className="rounded-xl border border-border bg-card p-5 lg:col-span-5" delay={0.22}>
          <div className="mb-3 flex items-center gap-2">
            <Zap className="size-4 text-neon-cyan" />
            <h3 className="font-mono text-xs uppercase tracking-widest text-neon-cyan">Edge Agent Registry</h3>
          </div>
          <button
            onClick={handleSyncEdge}
            disabled={isSyncingEdge || !clientEdge}
            className="rounded-lg border border-neon-cyan bg-neon-cyan/10 px-3 py-2 font-mono text-[10px] uppercase tracking-wider text-neon-cyan disabled:opacity-60"
          >
            {isSyncingEdge ? "Syncing..." : "Sync Current Browser Edge"}
          </button>
          <div className="mt-3 space-y-2">
            {edgeNodes.length === 0 && (
              <div className="rounded border border-border bg-secondary/20 p-2 font-mono text-[10px] text-muted-foreground">
                No edge agent telemetry ingested yet.
              </div>
            )}
            {edgeNodes.map((edge) => (
              <div key={`${edge.edge_id}-${edge.timestamp}`} className="rounded border border-border bg-secondary/20 p-2">
                <div className="font-mono text-[10px] text-neon-cyan">{edge.edge_id}</div>
                <div className="mt-1 font-mono text-[10px] text-muted-foreground">
                  {edge.platform} | battery {edge.battery_percent ?? "N/A"} | source {edge.source ?? "edge-agent"}
                </div>
              </div>
            ))}
          </div>
        </ScrollReveal>
      </div>

      <ScrollReveal className="rounded-xl border border-border bg-card p-5" delay={0.26}>
        <div className="mb-3 flex items-center gap-2">
          <Shield className="size-4 text-neon-green" />
          <h3 className="font-mono text-xs uppercase tracking-widest text-neon-green">Governance Audit Trail</h3>
        </div>
        <ScrollArea className="h-[240px]">
          <div className="space-y-2">
            {auditItems.length === 0 && (
              <div className="rounded border border-border bg-secondary/20 p-2 font-mono text-[10px] text-muted-foreground">
                No audit entries available.
              </div>
            )}
            {auditItems.map((item) => (
              <div key={item.id} className="rounded border border-border bg-secondary/20 p-2">
                <div className="font-mono text-[10px] text-neon-green">
                  {item.timestamp} | {item.category} | {item.action}
                </div>
                <div className="mt-1 font-mono text-[10px] text-muted-foreground">
                  actor={item.actor} status={item.status}
                </div>
              </div>
            ))}
          </div>
        </ScrollArea>
      </ScrollReveal>

      <ScrollReveal className="flex justify-end" delay={0.3}>
        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          className="flex items-center gap-2 rounded-xl border border-neon-cyan bg-neon-cyan/10 px-6 py-3 font-mono text-sm font-bold uppercase tracking-widest text-neon-cyan transition-all hover:bg-neon-cyan/20"
        >
          <Save className="size-4" />
          Save Configuration
        </motion.button>
      </ScrollReveal>
    </div>
  )
}
