"use client"

import { useEffect, useRef, useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import {
  ShieldAlert,
  AlertTriangle,
  Flame,
  CheckCircle,
  XCircle,
  Bell,
  BellOff,
} from "lucide-react"
import { ScrollArea } from "@/components/ui/scroll-area"
import { ScrollReveal } from "@/components/ui/scroll-reveal"
import { getLiveLaptopDashboard, type LiveAlert } from "@/lib/api"

interface AlertRow extends LiveAlert {
  acknowledged: boolean
  source: string
}

const severityConfig = {
  critical: {
    icon: Flame,
    color: "text-neon-red",
    bg: "bg-neon-red/5",
    border: "border-neon-red/30",
    badge: "bg-neon-red/10 text-neon-red",
  },
  warning: {
    icon: AlertTriangle,
    color: "text-neon-amber",
    bg: "bg-neon-amber/5",
    border: "border-neon-amber/30",
    badge: "bg-neon-amber/10 text-neon-amber",
  },
}

type FilterType = "all" | "critical" | "warning"

function inferSource(alert: LiveAlert): string {
  const text = `${alert.title} ${alert.message}`.toLowerCase()
  if (text.includes("cpu")) {
    return "CPU Monitor"
  }
  if (text.includes("memory")) {
    return "Memory Monitor"
  }
  if (text.includes("grid")) {
    return "Grid Controller"
  }
  if (text.includes("battery")) {
    return "Power Manager"
  }
  if (text.includes("stability")) {
    return "Decision Engine"
  }
  return "Runtime Supervisor"
}

export function AlertsTab() {
  const [alerts, setAlerts] = useState<AlertRow[]>([])
  const [filter, setFilter] = useState<FilterType>("all")
  const [isLoading, setIsLoading] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const ackStateRef = useRef<Record<number, boolean>>({})
  const dismissedRef = useRef<Set<number>>(new Set())
  const requestLockRef = useRef(false)

  const fetchAlerts = async () => {
    if (requestLockRef.current) {
      return
    }

    requestLockRef.current = true
    setIsLoading(true)
    try {
      const payload = await getLiveLaptopDashboard()
      const nextAlerts = (payload.alerts ?? [])
        .filter((alert) => !dismissedRef.current.has(alert.id))
        .map((alert) => ({
          ...alert,
          source: alert.source ?? inferSource(alert),
          acknowledged: ackStateRef.current[alert.id] ?? false,
        }))
        .sort((a, b) => b.id - a.id)

      setAlerts(nextAlerts)
      setErrorMessage(null)
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Failed to load alerts")
    } finally {
      setIsLoading(false)
      requestLockRef.current = false
    }
  }

  useEffect(() => {
    fetchAlerts()
    const interval = setInterval(fetchAlerts, 5000)
    return () => clearInterval(interval)
  }, [])

  const toggleAcknowledge = (id: number) => {
    const next = !(ackStateRef.current[id] ?? false)
    ackStateRef.current[id] = next
    setAlerts((prev) => prev.map((alert) => (alert.id === id ? { ...alert, acknowledged: next } : alert)))
  }

  const acknowledgeAll = () => {
    for (const alert of alerts) {
      ackStateRef.current[alert.id] = true
    }
    setAlerts((prev) => prev.map((alert) => ({ ...alert, acknowledged: true })))
  }

  const dismissAlert = (id: number) => {
    dismissedRef.current.add(id)
    setAlerts((prev) => prev.filter((alert) => alert.id !== id))
  }

  const filteredAlerts = alerts.filter((alert) => (filter === "all" ? true : alert.severity === filter))

  const counts = {
    all: alerts.length,
    critical: alerts.filter((alert) => alert.severity === "critical").length,
    warning: alerts.filter((alert) => alert.severity === "warning").length,
  }

  return (
    <div className="space-y-4">
      <ScrollReveal className="grid grid-cols-3 gap-3" delay={0.02}>
        {(["all", "critical", "warning"] as FilterType[]).map((type) => {
          const isActive = filter === type
          const colors =
            type === "all"
              ? "border-neon-cyan/30 text-foreground"
              : `${severityConfig[type].border} ${severityConfig[type].color}`
          return (
            <motion.button
              key={type}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              onClick={() => setFilter(type)}
              className={`rounded-xl border p-4 font-mono transition-all ${
                isActive
                  ? `${colors} ${
                      type === "all" ? "bg-neon-cyan/5" : severityConfig[type as Exclude<FilterType, "all">].bg
                    }`
                  : "border-border bg-card hover:border-neon-cyan/20"
              }`}
            >
              <div className="text-[10px] uppercase tracking-widest text-muted-foreground">
                {type === "all" ? "Total" : type}
              </div>
              <div
                className={`mt-1 text-2xl font-bold ${
                  type === "all" ? "text-foreground" : severityConfig[type as Exclude<FilterType, "all">].color
                }`}
              >
                {counts[type]}
              </div>
            </motion.button>
          )
        })}
      </ScrollReveal>

      <ScrollReveal className="rounded-xl border border-border bg-card p-5" delay={0.08}>
        <div className="mb-4 flex items-center gap-2">
          <ShieldAlert className="size-4 text-neon-red" />
          <h3 className="font-mono text-xs uppercase tracking-widest text-neon-red">
            Active Alerts
          </h3>
          <div className="ml-auto flex items-center gap-2">
            <button
              onClick={acknowledgeAll}
              className="flex items-center gap-1.5 rounded-lg border border-border px-3 py-1.5 font-mono text-[10px] uppercase tracking-wider text-muted-foreground transition-colors hover:border-neon-green/30 hover:text-neon-green"
            >
              <CheckCircle className="size-3" />
              Ack All
            </button>
          </div>
        </div>

        {isLoading && alerts.length === 0 && (
          <div className="mb-3 rounded-lg border border-neon-cyan/20 bg-neon-cyan/5 p-3 font-mono text-[10px] text-neon-cyan">
            Syncing live runtime alerts...
          </div>
        )}

        {errorMessage && (
          <div className="mb-3 rounded-lg border border-neon-red/30 bg-neon-red/10 p-3 font-mono text-[10px] text-neon-red">
            {errorMessage}
          </div>
        )}

        <ScrollArea className="h-[480px]">
          <div className="space-y-2">
            <AnimatePresence mode="popLayout">
              {filteredAlerts.length === 0 && (
                <motion.div
                  key="no-alerts"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="rounded-lg border border-neon-green/30 bg-neon-green/5 p-3 font-mono text-[10px] text-neon-green"
                >
                  No active runtime alerts.
                </motion.div>
              )}

              {filteredAlerts.map((alert) => {
                const cfg = severityConfig[alert.severity]
                const Icon = cfg.icon
                return (
                  <motion.div
                    key={alert.id}
                    layout
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: alert.acknowledged ? 0.5 : 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.95 }}
                    transition={{ duration: 0.25 }}
                    className={`rounded-lg border p-4 ${cfg.border} ${cfg.bg}`}
                  >
                    <div className="flex items-start gap-3">
                      <Icon className={`mt-0.5 size-4 shrink-0 ${cfg.color}`} />
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center justify-between gap-2">
                          <span className={`font-mono text-sm font-bold ${cfg.color}`}>{alert.title}</span>
                          <div className="flex shrink-0 items-center gap-2">
                            <span className="font-mono text-[9px] text-muted-foreground">{alert.time}</span>
                            <div className={`rounded-md border px-1.5 py-0.5 font-mono text-[9px] font-bold uppercase ${cfg.badge} ${cfg.border}`}>
                              {alert.severity}
                            </div>
                          </div>
                        </div>
                        <p className="mt-1 font-mono text-[11px] leading-relaxed text-muted-foreground">
                          {alert.message}
                        </p>
                        <div className="mt-2 flex items-center justify-between">
                          <span className="font-mono text-[10px] text-muted-foreground/70">{alert.source}</span>
                          <div className="flex items-center gap-2">
                            <button
                              onClick={() => toggleAcknowledge(alert.id)}
                              className={`flex items-center gap-1 rounded px-2 py-1 font-mono text-[9px] uppercase tracking-wider transition-colors ${
                                alert.acknowledged
                                  ? "bg-neon-green/10 text-neon-green"
                                  : "bg-secondary text-muted-foreground hover:text-foreground"
                              }`}
                            >
                              {alert.acknowledged ? <BellOff className="size-2.5" /> : <Bell className="size-2.5" />}
                              {alert.acknowledged ? "Acked" : "Ack"}
                            </button>
                            <button
                              onClick={() => dismissAlert(alert.id)}
                              className="flex items-center gap-1 rounded bg-secondary px-2 py-1 font-mono text-[9px] uppercase tracking-wider text-muted-foreground transition-colors hover:bg-neon-red/10 hover:text-neon-red"
                            >
                              <XCircle className="size-2.5" />
                              Dismiss
                            </button>
                          </div>
                        </div>
                      </div>
                    </div>
                  </motion.div>
                )
              })}
            </AnimatePresence>
          </div>
        </ScrollArea>
      </ScrollReveal>
    </div>
  )
}
