"use client"

import { useEffect, useRef, useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { SidebarNav, type TabId } from "@/components/dashboard/sidebar-nav"
import { DashboardHeader } from "@/components/dashboard/dashboard-header"
import { ExecutiveSummary } from "@/components/dashboard/executive-summary"
import { StatusCards } from "@/components/dashboard/status-cards"
import { TelemetryPanel } from "@/components/dashboard/telemetry-panel"
import { DecisionOutput, type DecisionResult } from "@/components/dashboard/decision-output"
import { RuntimeHealth } from "@/components/dashboard/runtime-health"
import { EventStream } from "@/components/dashboard/event-stream"
import { AlertsPanel } from "@/components/dashboard/alerts-panel"
import { OptimizationChart } from "@/components/dashboard/optimization-chart"
import { ReportGeneratorCard } from "@/components/dashboard/report-generator-card"
import { DecisionsTab } from "@/components/dashboard/tabs/decisions-tab"
import { AIModelsTab } from "@/components/dashboard/tabs/ai-models-tab"
import { EventsTab } from "@/components/dashboard/tabs/events-tab"
import { AlertsTab } from "@/components/dashboard/tabs/alerts-tab"
import { SettingsTab } from "@/components/dashboard/tabs/settings-tab"
import { ScrollArea } from "@/components/ui/scroll-area"
import { ScrollReveal } from "@/components/ui/scroll-reveal"
import { useRouter } from "next/navigation"
import { clearAuthSession, readAuthSession, type StoredAuthSession } from "@/lib/auth-session"
import {
  getLiveLaptopDashboard,
  getExecutiveKpis,
  mapDecisionForUi,
  setRuntimeMode,
  setSimulationScenario,
  type ExecutiveKpiMetrics,
  type LiveDashboardResponse,
  type RuntimeMode,
  type SimulationScenario,
  type RuntimeHealthItem,
} from "@/lib/api"

const defaultRuntimeHealth: RuntimeHealthItem[] = [
  { name: "CPU Headroom", value: 0 },
  { name: "Memory Headroom", value: 0 },
  { name: "Disk Headroom", value: 0 },
  { name: "Power Health", value: 0 },
  { name: "Decision Stability", value: 0 },
]

function deriveFallbackKpis(payload: LiveDashboardResponse): ExecutiveKpiMetrics {
  const history = payload.history ?? []
  const alerts = payload.alerts ?? []
  const events = payload.events ?? []
  const optimizedDecision = payload.decision?.optimized_decision

  let energyReduction = 0
  let costOptimization = 0
  let carbonReduction = 0

  if (history.length >= 8) {
    const midpoint = Math.floor(history.length / 2)
    const baselineSlice = history.slice(0, midpoint)
    const optimizedSlice = history.slice(midpoint)
    const baseline = baselineSlice.reduce((sum, point) => sum + point.energy, 0) / Math.max(1, baselineSlice.length)
    const optimized = optimizedSlice.reduce((sum, point) => sum + point.energy, 0) / Math.max(1, optimizedSlice.length)
    if (baseline > 0) {
      energyReduction = Math.max(0, ((baseline - optimized) / baseline) * 100)
      costOptimization = energyReduction * 0.8
      carbonReduction = Math.max(0, (baseline - optimized) * optimizedSlice.length * 0.82)
    }
  }

  const confidence = Number(optimizedDecision?.confidence_score ?? 0.65)
  const forecastAccuracy = Math.max(45, Math.min(99, confidence * 100))

  const alertVolume = alerts.length
  const anomalyFiltered = Math.max(0, Math.min(100, 100 - alertVolume * 3.5))

  const scanEvents = events.filter((event) => event.message.includes("scan_complete")).length
  const automatedDecisionPercent = events.length > 0 ? (scanEvents / events.length) * 100 : 0

  return {
    energy_reduction_percent: Number(energyReduction.toFixed(2)),
    cost_optimization_percent: Number(costOptimization.toFixed(2)),
    carbon_reduction_kg: Number(carbonReduction.toFixed(2)),
    forecast_accuracy_percent: Number(forecastAccuracy.toFixed(2)),
    anomaly_filtered_percent: Number(anomalyFiltered.toFixed(2)),
    automated_decisions_percent: Number(automatedDecisionPercent.toFixed(2)),
  }
}

function DashboardOverview() {
  const [liveData, setLiveData] = useState<LiveDashboardResponse | null>(null)
  const [executiveKpis, setExecutiveKpis] = useState<ExecutiveKpiMetrics | null>(null)
  const [decision, setDecision] = useState<DecisionResult | null>(null)
  const [decisionError, setDecisionError] = useState<string | null>(null)
  const [controlStatus, setControlStatus] = useState<string | null>(null)
  const [isScanning, setIsScanning] = useState(false)
  const [runtimeMode, setRuntimeModeState] = useState<RuntimeMode>("LIVE_EDGE")
  const [scenario, setScenarioState] = useState<SimulationScenario>("normal")
  const [isModeUpdating, setIsModeUpdating] = useState(false)
  const [isScenarioUpdating, setIsScenarioUpdating] = useState(false)
  const requestLock = useRef(false)

  const fetchLiveData = async (options?: { force?: boolean }) => {
    if (requestLock.current && !options?.force) {
      return
    }

    requestLock.current = true
    setIsScanning(true)

    try {
      const payload = await getLiveLaptopDashboard()
      const kpiPayload = await getExecutiveKpis().catch(() => null)
      setLiveData(payload)
      setExecutiveKpis(kpiPayload?.metrics ?? deriveFallbackKpis(payload))
      if (payload.mode) {
        setRuntimeModeState(payload.mode)
      }
      if (payload.scenario) {
        setScenarioState(payload.scenario)
      }
      setDecision(mapDecisionForUi({ decision: payload.decision }))
      setDecisionError(null)
    } catch (error) {
      setDecisionError(error instanceof Error ? error.message : "Live scan request failed")
    } finally {
      setIsScanning(false)
      requestLock.current = false
    }
  }

  useEffect(() => {
    fetchLiveData()
    const interval = setInterval(fetchLiveData, 5000)
    return () => clearInterval(interval)
  }, [])

  const updateRuntimeMode = async (nextMode: RuntimeMode) => {
    if (isModeUpdating) {
      return
    }

    setIsModeUpdating(true)
    setRuntimeModeState(nextMode)
    setControlStatus(`Applying mode ${nextMode.replace("_", " ")}...`)
    try {
      const response = await setRuntimeMode(nextMode)
      const appliedMode = (response.mode as RuntimeMode | undefined) ?? nextMode
      setRuntimeModeState(appliedMode)
      setControlStatus(`Runtime mode set to ${appliedMode.replace("_", " ")}`)
      await fetchLiveData({ force: true })
    } catch (error) {
      setDecisionError(error instanceof Error ? error.message : "Failed to change mode")
      setControlStatus(null)
    } finally {
      setIsModeUpdating(false)
    }
  }

  const triggerScenario = async (nextScenario: SimulationScenario) => {
    if (isScenarioUpdating) {
      return
    }

    setIsScenarioUpdating(true)
    setScenarioState(nextScenario)
    setControlStatus(`Injecting scenario ${nextScenario.replace("_", " ")}...`)
    try {
      const response = await setSimulationScenario(nextScenario, nextScenario === "normal" ? 0 : 12)
      const appliedScenario = (response.scenario as SimulationScenario | undefined) ?? nextScenario
      setScenarioState(appliedScenario)
      setControlStatus(`Scenario active: ${appliedScenario.replace("_", " ")}`)
      await fetchLiveData({ force: true })
    } catch (error) {
      setDecisionError(error instanceof Error ? error.message : "Failed to set scenario")
      setControlStatus(null)
    } finally {
      setIsScenarioUpdating(false)
    }
  }

  const optimizationScore =
    liveData?.history && liveData.history.length > 0
      ? liveData.history[liveData.history.length - 1].optimization
      : null

  return (
    <>
      <ScrollReveal className="mb-4 rounded-xl border border-border bg-card p-4" delay={0.01}>
        <div className="grid gap-3 lg:grid-cols-2">
          <div>
            <div className="mb-2 font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
              Runtime Mode
            </div>
            <div className="flex flex-wrap gap-2">
              {(["LIVE_EDGE", "SIMULATION", "HYBRID"] as RuntimeMode[]).map((mode) => (
                <button
                  key={mode}
                  onClick={() => updateRuntimeMode(mode)}
                  disabled={isModeUpdating}
                  className={`rounded-lg border px-3 py-1.5 font-mono text-[10px] uppercase tracking-wider transition-colors ${
                    runtimeMode === mode
                      ? "border-neon-cyan bg-neon-cyan/10 text-neon-cyan"
                      : "border-border text-muted-foreground hover:border-neon-cyan/30 hover:text-foreground"
                  }`}
                >
                  {mode.replace("_", " ")}
                </button>
              ))}
            </div>
          </div>

          <div>
            <div className="mb-2 font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
              Validation Scenario
            </div>
            <div className="flex flex-wrap gap-2">
              {(["normal", "peak_load", "low_load", "grid_failure"] as SimulationScenario[]).map((item) => (
                <button
                  key={item}
                  onClick={() => triggerScenario(item)}
                  disabled={isScenarioUpdating}
                  className={`rounded-lg border px-3 py-1.5 font-mono text-[10px] uppercase tracking-wider transition-colors ${
                    scenario === item
                      ? item === "grid_failure"
                        ? "border-neon-red bg-neon-red/10 text-neon-red"
                        : "border-neon-amber bg-neon-amber/10 text-neon-amber"
                      : "border-border text-muted-foreground hover:border-neon-cyan/30 hover:text-foreground"
                  }`}
                >
                  {item.replace("_", " ")}
                </button>
              ))}
            </div>
          </div>
        </div>
      </ScrollReveal>

      {decisionError && (
        <div className="mb-4 rounded-lg border border-neon-red/30 bg-neon-red/10 px-3 py-2 font-mono text-xs text-neon-red">
          {decisionError}
        </div>
      )}

      {controlStatus && (
        <div className="mb-4 rounded-lg border border-neon-green/30 bg-neon-green/10 px-3 py-2 font-mono text-xs text-neon-green">
          {controlStatus}
        </div>
      )}

      <ScrollReveal className="mb-4" delay={0.015}>
        <ExecutiveSummary metrics={executiveKpis} />
      </ScrollReveal>

      <ScrollReveal className="mb-6" delay={0.02}>
        <StatusCards
          telemetry={liveData?.telemetry ?? null}
          optimizationScore={optimizationScore}
          runtimeMode={runtimeMode}
          scenario={scenario}
        />
      </ScrollReveal>

      <ScrollReveal className="mb-6 grid gap-4 lg:grid-cols-3" delay={0.06}>
        <TelemetryPanel telemetry={liveData?.telemetry ?? null} isScanning={isScanning} />
        <DecisionOutput result={decision} error={decisionError} />
        <RuntimeHealth items={liveData?.runtime_health ?? defaultRuntimeHealth} />
      </ScrollReveal>

      <ScrollReveal className="grid gap-4 lg:grid-cols-3" delay={0.1}>
        <div className="grid gap-4 lg:col-span-2">
          <OptimizationChart history={liveData?.history ?? []} />
          <ReportGeneratorCard />
        </div>
        <div className="grid gap-4">
          <AlertsPanel alerts={liveData?.alerts ?? []} />
        </div>
      </ScrollReveal>

      <ScrollReveal className="mt-4" delay={0.14}>
        <EventStream events={liveData?.events ?? []} />
      </ScrollReveal>
    </>
  )
}

const tabTitles: Record<TabId, string> = {
  dashboard: "Overview",
  decisions: "AI Decisions",
  "ai-models": "AI Models",
  events: "Event Stream",
  alerts: "Alerts Center",
  settings: "Settings",
}

export default function DashboardPage() {
  const router = useRouter()
  const [activeTab, setActiveTab] = useState<TabId>("dashboard")
  const [authReady, setAuthReady] = useState(false)
  const [authRole, setAuthRole] = useState<"admin" | "org_admin" | null>(null)
  const [authSession, setAuthSession] = useState<StoredAuthSession | null>(null)

  useEffect(() => {
    const session = readAuthSession()
    if (!session) {
      router.replace("/access")
      return
    }

    const expiresAt = new Date(session.expiresAt)
    if (Number.isNaN(expiresAt.getTime()) || expiresAt.getTime() <= Date.now()) {
      clearAuthSession()
      router.replace("/access")
      return
    }

    if (session.role === "admin" || session.role === "org_admin") {
      setAuthRole(session.role)
      setAuthSession(session)
      setAuthReady(true)
      return
    }

    router.replace("/access")
  }, [router])

  if (!authReady) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background p-6">
        <div className="rounded-xl border border-border bg-card px-6 py-4 font-mono text-xs uppercase tracking-widest text-neon-cyan">
          Validating enterprise session...
        </div>
      </div>
    )
  }

  return (
    <div className="flex h-[100dvh] min-h-0 overflow-hidden bg-background">
      <SidebarNav activeTab={activeTab} onTabChange={setActiveTab} role={authRole} />

      <div className="flex min-h-0 min-w-0 flex-1 flex-col">
        <DashboardHeader
          role={authRole}
          email={authSession?.email ?? ""}
          organizationName={authSession?.organizationName ?? ""}
        />

        <ScrollArea className="min-h-0 flex-1">
          <main className="p-4 lg:p-6">
            <motion.div
              key={activeTab}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              className="mb-6"
            >
              <h2 className="font-mono text-lg font-bold uppercase tracking-widest text-foreground">
                {tabTitles[activeTab]}
              </h2>
              <div className="mt-1 h-px bg-gradient-to-r from-neon-cyan/50 via-neon-purple/30 to-transparent" />
            </motion.div>

            <AnimatePresence mode="wait">
              <motion.div
                key={activeTab}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -12 }}
                transition={{ duration: 0.25 }}
              >
                {activeTab === "dashboard" && <DashboardOverview />}
                {activeTab === "decisions" && <DecisionsTab />}
                {activeTab === "ai-models" &&
                  (authRole === "admin" ? (
                    <AIModelsTab />
                  ) : (
                    <div className="rounded-lg border border-neon-amber/30 bg-neon-amber/10 px-4 py-3 font-mono text-xs text-neon-amber">
                      AI Models tab is restricted to administration accounts.
                    </div>
                  ))}
                {activeTab === "events" && <EventsTab />}
                {activeTab === "alerts" && <AlertsTab />}
                {activeTab === "settings" && <SettingsTab />}
              </motion.div>
            </AnimatePresence>
          </main>
        </ScrollArea>
      </div>
    </div>
  )
}
