"use client"

import { motion } from "framer-motion"
import { BarChart3, CircleDollarSign, CloudSun, Leaf, ShieldCheck, Workflow } from "lucide-react"
import type { ExecutiveKpiMetrics } from "@/lib/api"

function formatNumber(value: number, digits = 1): string {
  if (!Number.isFinite(value)) {
    return "0"
  }
  return Number(value).toFixed(digits)
}

export function ExecutiveSummary({ metrics }: { metrics: ExecutiveKpiMetrics | null }) {
  const cards = [
    {
      label: "Energy Reduction",
      value: `${formatNumber(metrics?.energy_reduction_percent ?? 0)}%`,
      icon: <BarChart3 className="size-4 text-neon-cyan" />,
    },
    {
      label: "Cost Optimization",
      value: `${formatNumber(metrics?.cost_optimization_percent ?? 0)}%`,
      icon: <CircleDollarSign className="size-4 text-neon-amber" />,
    },
    {
      label: "Carbon Saved",
      value: `${formatNumber(metrics?.carbon_reduction_kg ?? 0, 0)} kg`,
      icon: <Leaf className="size-4 text-neon-green" />,
    },
    {
      label: "Forecast Accuracy",
      value: `${formatNumber(metrics?.forecast_accuracy_percent ?? 0)}%`,
      icon: <CloudSun className="size-4 text-neon-purple" />,
    },
    {
      label: "Anomaly Filtered",
      value: `${formatNumber(metrics?.anomaly_filtered_percent ?? 0)}%`,
      icon: <ShieldCheck className="size-4 text-neon-red" />,
    },
    {
      label: "Automated Decisions",
      value: `${formatNumber(metrics?.automated_decisions_percent ?? 0)}%`,
      icon: <Workflow className="size-4 text-neon-cyan" />,
    },
  ]

  return (
    <motion.div
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.01, duration: 0.35 }}
      className="rounded-xl border border-border bg-card p-4"
    >
      <div className="mb-3 flex items-center justify-between">
        <h3 className="font-mono text-[10px] uppercase tracking-widest text-neon-cyan">
          Executive Impact Snapshot
        </h3>
        <span className="rounded border border-neon-cyan/30 bg-neon-cyan/10 px-2 py-0.5 font-mono text-[9px] text-neon-cyan">
          KPI LIVE
        </span>
      </div>

      <div className="grid grid-cols-2 gap-2 lg:grid-cols-6">
        {cards.map((card) => (
          <div key={card.label} className="rounded-lg border border-border bg-secondary/25 p-3">
            <div className="mb-2 flex items-center justify-between">
              <span className="font-mono text-[9px] uppercase tracking-wider text-muted-foreground">
                {card.label}
              </span>
              {card.icon}
            </div>
            <div className="font-mono text-base font-bold text-foreground">{card.value}</div>
          </div>
        ))}
      </div>
    </motion.div>
  )
}
