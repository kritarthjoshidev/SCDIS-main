"use client"

import { useState } from "react"
import { Download, FileText, RefreshCw } from "lucide-react"
import {
  downloadMonitoringReport,
  getMonitoringReport,
  type MonitoringReportPayload,
  type ReportWindow,
} from "@/lib/api"

const reportWindowOptions: Array<{ id: ReportWindow; label: string }> = [
  { id: "1d", label: "1 Day" },
  { id: "1w", label: "1 Week" },
  { id: "1m", label: "1 Month" },
]

export function ReportGeneratorCard() {
  const [reportWindow, setReportWindow] = useState<ReportWindow>("1d")
  const [isGeneratingReport, setIsGeneratingReport] = useState(false)
  const [isDownloadingReport, setIsDownloadingReport] = useState(false)
  const [reportStatus, setReportStatus] = useState<string | null>(null)
  const [latestReport, setLatestReport] = useState<MonitoringReportPayload | null>(null)

  const handleGenerateReport = async () => {
    if (isGeneratingReport) {
      return
    }

    setIsGeneratingReport(true)
    setReportStatus("Generating report preview...")

    try {
      const response = await getMonitoringReport(reportWindow, "json")
      setLatestReport(response.report)
      const sourceLabel = response.status === "fallback_local" ? "local fallback" : "live API"
      setReportStatus(`Report generated via ${sourceLabel}: ${response.report.report_id}`)
    } catch (error) {
      setReportStatus(error instanceof Error ? error.message : "Failed to generate report")
    } finally {
      setIsGeneratingReport(false)
    }
  }

  const handleDownloadReport = async () => {
    if (isDownloadingReport) {
      return
    }

    setIsDownloadingReport(true)
    setReportStatus("Preparing report download...")

    try {
      const blob = await downloadMonitoringReport(reportWindow, "pdf")
      const url = window.URL.createObjectURL(blob)
      const timestamp = new Date().toISOString().replace(/[:.]/g, "-")
      const anchor = document.createElement("a")
      anchor.href = url
      anchor.download = `scdis_report_${reportWindow}_${timestamp}.pdf`
      document.body.appendChild(anchor)
      anchor.click()
      anchor.remove()
      window.URL.revokeObjectURL(url)
      setReportStatus("Detailed PDF report downloaded successfully.")
    } catch (error) {
      setReportStatus(error instanceof Error ? error.message : "Failed to download report")
    } finally {
      setIsDownloadingReport(false)
    }
  }

  return (
    <div className="rounded-xl border border-border bg-card p-5">
      <div className="mb-4 flex items-center gap-2">
        <FileText className="size-4 text-neon-cyan" />
        <h3 className="font-mono text-xs uppercase tracking-widest text-neon-cyan">Report Generator</h3>
        <span className="ml-auto rounded-md border border-neon-cyan/30 bg-neon-cyan/10 px-2 py-0.5 font-mono text-[9px] text-neon-cyan">
          1 Day / 1 Week / 1 Month
        </span>
      </div>

      <div className="mb-4 flex flex-wrap items-center gap-2">
        {reportWindowOptions.map((option) => (
          <button
            key={option.id}
            onClick={() => setReportWindow(option.id)}
            className={`rounded-lg border px-3 py-1.5 font-mono text-[10px] uppercase tracking-wider transition-colors ${
              reportWindow === option.id
                ? "border-neon-cyan bg-neon-cyan/10 text-neon-cyan"
                : "border-border text-muted-foreground hover:border-neon-cyan/30 hover:text-foreground"
            }`}
          >
            {option.label}
          </button>
        ))}
      </div>

      <div className="flex flex-wrap gap-2">
        <button
          onClick={handleGenerateReport}
          disabled={isGeneratingReport}
          className="inline-flex items-center gap-2 rounded-lg border border-neon-cyan bg-neon-cyan/10 px-3 py-2 font-mono text-[10px] uppercase tracking-wider text-neon-cyan transition-colors hover:bg-neon-cyan/20 disabled:cursor-not-allowed disabled:opacity-60"
        >
          <RefreshCw className={`size-3 ${isGeneratingReport ? "animate-spin" : ""}`} />
          {isGeneratingReport ? "Generating..." : "Generate Report"}
        </button>

        <button
          onClick={handleDownloadReport}
          disabled={isDownloadingReport}
          className="inline-flex items-center gap-2 rounded-lg border border-neon-purple bg-neon-purple/10 px-3 py-2 font-mono text-[10px] uppercase tracking-wider text-neon-purple transition-colors hover:bg-neon-purple/20 disabled:cursor-not-allowed disabled:opacity-60"
        >
          <Download className="size-3" />
          {isDownloadingReport ? "Downloading..." : "Download PDF Report"}
        </button>
      </div>

      {reportStatus && (
        <div className="mt-3 rounded-lg border border-border bg-secondary/30 px-3 py-2 font-mono text-[10px] text-muted-foreground">
          {reportStatus}
        </div>
      )}

      {latestReport && (
        <div className="mt-4 rounded-lg border border-border bg-secondary/30 p-3">
          <div className="mb-2 font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
            Latest Report Snapshot
          </div>
          <div className="grid grid-cols-2 gap-2 lg:grid-cols-4">
            <div className="rounded border border-border bg-card px-2 py-2">
              <div className="font-mono text-[9px] uppercase tracking-wider text-muted-foreground">Report ID</div>
              <div className="mt-1 font-mono text-[10px] text-foreground">{latestReport.report_id}</div>
            </div>
            <div className="rounded border border-border bg-card px-2 py-2">
              <div className="font-mono text-[9px] uppercase tracking-wider text-muted-foreground">Uptime</div>
              <div className="mt-1 font-mono text-[10px] text-foreground">
                {latestReport.executive_summary.uptime_percent.toFixed(2)}%
              </div>
            </div>
            <div className="rounded border border-border bg-card px-2 py-2">
              <div className="font-mono text-[9px] uppercase tracking-wider text-muted-foreground">Energy</div>
              <div className="mt-1 font-mono text-[10px] text-foreground">
                {latestReport.executive_summary.total_energy_kwh.toFixed(2)} kWh
              </div>
            </div>
            <div className="rounded border border-border bg-card px-2 py-2">
              <div className="font-mono text-[9px] uppercase tracking-wider text-muted-foreground">Forecast Acc.</div>
              <div className="mt-1 font-mono text-[10px] text-foreground">
                {latestReport.executive_summary.forecast_accuracy_percent.toFixed(2)}%
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
