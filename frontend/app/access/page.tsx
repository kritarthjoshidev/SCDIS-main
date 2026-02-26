"use client"

import { useEffect, useState } from "react"
import dynamic from "next/dynamic"
import { useRouter } from "next/navigation"
import { AnimatePresence, motion } from "framer-motion"
import { Building2, Lock, Shield, Sparkles } from "lucide-react"
import {
  loginEnterpriseAdmin,
  loginEnterpriseOrganization,
  registerOrganizationAccount,
  type EnterpriseAuthResponse,
} from "@/lib/api"

const DotLottieReact = dynamic(
  () => import("@lottiefiles/dotlottie-react").then((module) => module.DotLottieReact),
  { ssr: false }
)

const WELCOME_LOTTIE_SRC =
  "https://lottie.host/85b3b1ca-5e99-45c5-b1aa-ce2549d6059b/ksHdDBkWXc.lottie"

type IntroStage = "welcome" | "transition" | "ready"

import { persistAuthSession } from "@/lib/auth-session"

function persistSession(payload: EnterpriseAuthResponse) {
  // keep the token in session storage so that closing the browser/window
  // forces a fresh login; this is a bit more secure than localStorage.
  persistAuthSession(payload)
}

export default function AccessPage() {
  const router = useRouter()
  const [message, setMessage] = useState<string>("")
  const [messageType, setMessageType] = useState<"success" | "error" | null>(null)
  const [loading, setLoading] = useState(false)
  const [introStage, setIntroStage] = useState<IntroStage>("welcome")

  const [adminEmail, setAdminEmail] = useState("admin@scdis.local")
  const [adminPassword, setAdminPassword] = useState("admin123")

  const [orgName, setOrgName] = useState("")
  const [orgEmail, setOrgEmail] = useState("")
  const [orgPassword, setOrgPassword] = useState("")

  useEffect(() => {
    if (introStage !== "transition") {
      return
    }

    const timer = window.setTimeout(() => {
      setIntroStage("ready")
    }, 1700)

    return () => window.clearTimeout(timer)
  }, [introStage])

  const startAccessFlow = () => {
    if (introStage !== "welcome") {
      return
    }
    setIntroStage("transition")
  }

  const handleAdminLogin = async () => {
    setLoading(true)
    setMessage("")
    setMessageType(null)
    try {
      const session = await loginEnterpriseAdmin(adminEmail, adminPassword)
      persistSession(session)
      setMessage("Welcome back! You are now logged in as administrator.")
      setMessageType("success")
      router.push("/")
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Something went wrong signing you in as admin.")
      setMessageType("error")
    } finally {
      setLoading(false)
    }
  }

  const handleOrganizationSignup = async () => {
    setLoading(true)
    setMessage("")
    setMessageType(null)
    try {
      const signup = await registerOrganizationAccount(orgName, orgEmail, orgPassword)
      persistSession(signup)
      setMessage("Organization account created. You're now logged in and ready to go!")
      setMessageType("success")
      router.push("/")
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "We couldn't create your organization account.")
      setMessageType("error")
    } finally {
      setLoading(false)
    }
  }

  const handleOrganizationLogin = async () => {
    setLoading(true)
    setMessage("")
    setMessageType(null)
    try {
      const session = await loginEnterpriseOrganization(orgEmail, orgPassword)
      persistSession(session)
      setMessage("Organization login successful.")
      setMessageType("success")
      router.push("/")
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to sign in to organization account.")
      setMessageType("error")
    } finally {
      setLoading(false)
    }
  }

  const overlayActive = introStage !== "ready"

  return (
    <>
      <AnimatePresence mode="wait">
        {introStage === "welcome" && (
          <motion.div
            key="welcome-intro"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.35 }}
            className="fixed inset-0 z-50"
          >
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(0,236,255,0.16),transparent_45%),radial-gradient(circle_at_bottom,_rgba(128,44,255,0.22),transparent_50%),#050914]" />
            <div className="absolute inset-0 bg-[linear-gradient(to_bottom,rgba(0,236,255,0.08),transparent_35%,rgba(128,44,255,0.08))]" />
            <div className="relative flex h-full items-center justify-center px-6">
              <motion.div
                initial={{ opacity: 0, y: 24, scale: 0.97 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                transition={{ duration: 0.55, ease: "easeOut" }}
                className="w-full max-w-3xl rounded-2xl border border-neon-cyan/30 bg-black/35 p-6 shadow-[0_0_60px_rgba(0,236,255,0.18)] backdrop-blur-md"
              >
                <div className="mx-auto w-full max-w-[320px]">
                  <DotLottieReact src={WELCOME_LOTTIE_SRC} loop autoplay />
                </div>

                <div className="mt-2 text-center">
                  <div className="mb-2 inline-flex items-center gap-2 rounded-full border border-neon-cyan/30 bg-neon-cyan/10 px-3 py-1 font-mono text-[10px] uppercase tracking-[0.18em] text-neon-cyan">
                    <Sparkles className="size-3" />
                    Welcome Sequence Ready
                  </div>
                  <h1 className="font-mono text-xl uppercase tracking-[0.28em] text-foreground">Welcome to SCDIS</h1>
                  <p className="mt-2 font-mono text-xs text-muted-foreground">
                    Click to enter secure enterprise access
                  </p>

                  <button
                    onClick={startAccessFlow}
                    className="mt-5 rounded-lg border border-neon-cyan/60 bg-neon-cyan/10 px-5 py-2 font-mono text-[11px] uppercase tracking-wider text-neon-cyan transition hover:bg-neon-cyan/20"
                  >
                    Enter Access Portal
                  </button>
                </div>
              </motion.div>
            </div>
          </motion.div>
        )}

        {introStage === "transition" && (
          <motion.div
            key="intro-transition"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="fixed inset-0 z-50"
          >
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,_rgba(0,236,255,0.18),transparent_55%),#030712]" />
            <div className="relative flex h-full items-center justify-center px-6">
              <div className="w-full max-w-xl rounded-2xl border border-neon-cyan/25 bg-black/40 p-6 backdrop-blur-md">
                <div className="relative mx-auto mb-4 size-24">
                  <motion.div
                    className="absolute inset-0 rounded-full border border-neon-cyan/60"
                    animate={{ scale: [1, 1.25], opacity: [0.8, 0] }}
                    transition={{ duration: 1.1, repeat: Number.POSITIVE_INFINITY, ease: "easeOut" }}
                  />
                  <motion.div
                    className="absolute inset-2 rounded-full border border-neon-purple/60"
                    animate={{ scale: [1, 1.2], opacity: [0.9, 0] }}
                    transition={{ duration: 1.1, repeat: Number.POSITIVE_INFINITY, ease: "easeOut", delay: 0.22 }}
                  />
                  <div className="absolute inset-[22px] rounded-full bg-neon-cyan/70 shadow-[0_0_24px_rgba(0,236,255,0.75)]" />
                </div>

                <p className="text-center font-mono text-[11px] uppercase tracking-[0.2em] text-neon-cyan">
                  Authenticating Secure Access Layer
                </p>

                <div className="mt-4 h-1.5 overflow-hidden rounded-full bg-border/70">
                  <motion.div
                    className="h-full w-1/2 bg-gradient-to-r from-transparent via-neon-cyan to-transparent"
                    initial={{ x: "-120%" }}
                    animate={{ x: "220%" }}
                    transition={{ duration: 1.15, repeat: Number.POSITIVE_INFINITY, ease: "linear" }}
                  />
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <main
        className={`flex min-h-screen items-center justify-center bg-background p-6 text-foreground ${
          overlayActive ? "pointer-events-none" : ""
        }`}
      >
        <motion.div
          initial={{ opacity: 0, y: 16, scale: 0.985 }}
          animate={{ opacity: introStage === "ready" ? 1 : 0, y: introStage === "ready" ? 0 : 14, scale: introStage === "ready" ? 1 : 0.985 }}
          transition={{ duration: 0.45, ease: "easeOut" }}
          className="w-full max-w-5xl"
        >
          <div className="mb-4 text-center">
            <h1 className="font-mono text-base uppercase tracking-[0.22em] text-neon-cyan">Enterprise Access Console</h1>
            <p className="mt-1 font-mono text-xs text-muted-foreground">
              Sign in with admin or organization credentials
            </p>
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            <section className="rounded-xl border border-border bg-card p-5">
              <div className="mb-4 flex items-center gap-2">
                <Shield className="size-4 text-neon-cyan" />
                <h2 className="font-mono text-sm uppercase tracking-widest text-neon-cyan">Administration Access</h2>
              </div>

              <div className="space-y-3">
                <input
                  value={adminEmail}
                  onChange={(e) => setAdminEmail(e.target.value)}
                  placeholder="Admin email"
                  className="w-full rounded-lg border border-border bg-background px-3 py-2 font-mono text-xs"
                />
                <input
                  type="password"
                  value={adminPassword}
                  onChange={(e) => setAdminPassword(e.target.value)}
                  placeholder="Admin password"
                  className="w-full rounded-lg border border-border bg-background px-3 py-2 font-mono text-xs"
                />
                <button
                  onClick={handleAdminLogin}
                  disabled={loading}
                  className="inline-flex items-center gap-2 rounded-lg border border-neon-cyan bg-neon-cyan/10 px-4 py-2 font-mono text-xs uppercase tracking-wider text-neon-cyan disabled:opacity-60"
                >
                  <Lock className="size-3.5" />
                  Login Admin
                </button>
              </div>
            </section>

            <section className="rounded-xl border border-border bg-card p-5">
              <div className="mb-4 flex items-center gap-2">
                <Building2 className="size-4 text-neon-purple" />
                <h2 className="font-mono text-sm uppercase tracking-widest text-neon-purple">Organization Access</h2>
              </div>

              <div className="space-y-3">
                <input
                  value={orgName}
                  onChange={(e) => setOrgName(e.target.value)}
                  placeholder="Organization name"
                  className="w-full rounded-lg border border-border bg-background px-3 py-2 font-mono text-xs"
                />
                <input
                  value={orgEmail}
                  onChange={(e) => setOrgEmail(e.target.value)}
                  placeholder="Organization email"
                  className="w-full rounded-lg border border-border bg-background px-3 py-2 font-mono text-xs"
                />
                <input
                  type="password"
                  value={orgPassword}
                  onChange={(e) => setOrgPassword(e.target.value)}
                  placeholder="Password"
                  className="w-full rounded-lg border border-border bg-background px-3 py-2 font-mono text-xs"
                />

                <div className="flex flex-wrap gap-2">
                  <button
                    onClick={handleOrganizationSignup}
                    disabled={loading}
                    className="rounded-lg border border-neon-purple bg-neon-purple/10 px-4 py-2 font-mono text-xs uppercase tracking-wider text-neon-purple disabled:opacity-60"
                  >
                    Create Org
                  </button>
                  <button
                    onClick={handleOrganizationLogin}
                    disabled={loading}
                    className="rounded-lg border border-border px-4 py-2 font-mono text-xs uppercase tracking-wider text-muted-foreground hover:text-foreground disabled:opacity-60"
                  >
                    Org Login
                  </button>
                </div>
              </div>
            </section>
          </div>

          {message && (
            <div
              className={`mx-auto mt-4 max-w-5xl rounded-lg px-3 py-2 font-mono text-xs ${
                messageType === "error"
                  ? "border border-neon-red/30 bg-neon-red/10 text-neon-red"
                  : "border border-neon-cyan/30 bg-neon-cyan/10 text-neon-cyan"
              }`}
            >
              {message}
            </div>
          )}
        </motion.div>
      </main>
    </>
  )
}
