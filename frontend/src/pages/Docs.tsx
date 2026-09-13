import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  ArrowLeft,
  CheckCircle2,
  Copy,
  ExternalLink,
  Play,
  Terminal,
  Zap,
  Code2,
  Server
} from 'lucide-react'
import { API_BASE, DOCS_URL, api } from '../lib/api'
import { Footer } from '../components/Footer'

interface Endpoint {
  method: 'GET'
  path: string
  title: string
  description: string
  params?: { name: string; type: string; required: boolean; default?: string; desc: string }[]
  testFn: () => Promise<any>
}

export default function Docs() {
  const [activeTab, setActiveTab] = useState<'explorer' | 'swagger'>('explorer')
  const [selectedEndpointIndex, setSelectedEndpointIndex] = useState<number>(0)
  const [liveResponse, setLiveResponse] = useState<string | null>(null)
  const [loading, setLoading] = useState<boolean>(false)
  const [latency, setLatency] = useState<number | null>(null)
  const [copied, setCopied] = useState<boolean>(false)

  const endpoints: Endpoint[] = [
    {
      method: 'GET',
      path: '/api/v1/search',
      title: 'Unified Environmental Telemetry Search',
      description: 'Fetches live Canadian FWI fire risk, CPCB air quality, weather conditions, and nearby active satellite fires for any Indian district or coordinates.',
      params: [
        { name: 'query', type: 'string', required: false, default: 'Jalgaon / Bhusawal', desc: 'Indian district or city name (e.g. Pune, Nainital, Leh)' },
        { name: 'lat', type: 'float', required: false, desc: 'Latitude (-90 to 90)' },
        { name: 'lon', type: 'float', required: false, desc: 'Longitude (-180 to 180)' }
      ],
      testFn: () => api.search('Jalgaon / Bhusawal')
    },
    {
      method: 'GET',
      path: '/api/v1/fires/active',
      title: 'Live NASA VIIRS Active Satellite Hotspots',
      description: 'Streams genuine 375m thermal anomaly hotspots from NASA Suomi-NPP VIIRS across the Indian subcontinent.',
      params: [
        { name: 'format', type: 'string', required: false, default: 'geojson', desc: 'Output format: "geojson" or "list"' }
      ],
      testFn: () => api.getActiveFires()
    },
    {
      method: 'GET',
      path: '/health',
      title: 'System & Supabase Database Health Check',
      description: 'Reports backend service operational status, loaded districts count, and live Supabase PostgreSQL connection state.',
      testFn: () => api.getHealth()
    },
    {
      method: 'GET',
      path: '/api/v1/telemetry/recent',
      title: 'Supabase Audit Trail Query',
      description: 'Queries recent environmental query audit records logged to the Supabase PostgreSQL database.',
      params: [
        { name: 'limit', type: 'int', required: false, default: '6', desc: 'Number of audit records (1-50)' }
      ],
      testFn: () => api.getRecentTelemetry(5)
    },
    {
      method: 'GET',
      path: '/api/v1/districts',
      title: 'List Seeded Indian Districts',
      description: 'Returns the catalog of 39 Indian districts with PostGIS geodetic coordinates and ecological zones.',
      params: [
        { name: 'search', type: 'string', required: false, desc: 'Filter by district or state name' }
      ],
      testFn: () => api.getDistricts()
    }
  ]

  const currentEndpoint = endpoints[selectedEndpointIndex]

  const handleTest = async () => {
    setLoading(true)
    setLiveResponse(null)
    setLatency(null)
    const start = performance.now()
    try {
      const data = await currentEndpoint.testFn()
      const end = performance.now()
      setLatency(Math.round(end - start))
      setLiveResponse(JSON.stringify(data, null, 2))
    } catch (err: any) {
      const end = performance.now()
      setLatency(Math.round(end - start))
      setLiveResponse(JSON.stringify({ error: true, message: err?.message || 'Request failed' }, null, 2))
    } finally {
      setLoading(false)
    }
  }

  const copyCurl = () => {
    const curlCmd = `curl -X GET "${API_BASE}${currentEndpoint.path}" -H "Accept: application/json"`
    navigator.clipboard.writeText(curlCmd)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="min-h-screen bg-[#090A0C] text-zinc-100 font-sans antialiased p-4 sm:p-6 lg:p-8">
      <div className="mx-auto max-w-7xl space-y-6">
        {/* Top Header Bar */}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-zinc-800/80 pb-5">
          <div className="flex items-center gap-3">
            <Link
              to="/"
              className="flex items-center gap-1.5 rounded-xl border border-zinc-800 bg-zinc-900/60 px-3 py-1.5 text-xs font-medium text-zinc-300 hover:border-cyan-500/50 hover:text-white transition-all cursor-pointer"
            >
              <ArrowLeft className="h-3.5 w-3.5" />
              <span>Back to Defense Console</span>
            </Link>
            <div className="h-4 w-[1px] bg-zinc-800" />
            <h1 className="text-lg font-bold text-white tracking-tight flex items-center gap-2">
              <Zap className="h-4 w-4 text-cyan-400" />
              Interactive API Specification
            </h1>
          </div>

          {/* View Mode Switcher */}
          <div className="flex items-center rounded-xl border border-zinc-800 bg-zinc-900/80 p-1 text-xs">
            <button
              onClick={() => setActiveTab('explorer')}
              className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 font-medium transition-all cursor-pointer ${
                activeTab === 'explorer'
                  ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/30'
                  : 'text-zinc-400 hover:text-zinc-200'
              }`}
            >
              <Code2 className="h-3.5 w-3.5" />
              <span>Native API Explorer</span>
            </button>
            <button
              onClick={() => setActiveTab('swagger')}
              className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 font-medium transition-all cursor-pointer ${
                activeTab === 'swagger'
                  ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/30'
                  : 'text-zinc-400 hover:text-zinc-200'
              }`}
            >
              <Server className="h-3.5 w-3.5" />
              <span>FastAPI Swagger UI</span>
            </button>
          </div>
        </div>

        {/* Tab 1: Native Interactive API Explorer */}
        {activeTab === 'explorer' && (
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
            {/* Endpoints Sidebar */}
            <div className="lg:col-span-4 space-y-2">
              <p className="text-[10px] font-mono uppercase tracking-[0.2em] text-zinc-500 mb-2">Available Endpoints</p>
              {endpoints.map((ep, idx) => (
                <button
                  key={ep.path}
                  onClick={() => {
                    setSelectedEndpointIndex(idx)
                    setLiveResponse(null)
                    setLatency(null)
                  }}
                  className={`w-full text-left p-3.5 rounded-xl border transition-all cursor-pointer flex flex-col gap-1 ${
                    selectedEndpointIndex === idx
                      ? 'border-cyan-500/40 bg-cyan-950/20 text-white shadow-lg shadow-cyan-950/20'
                      : 'border-zinc-800/80 bg-zinc-900/40 text-zinc-400 hover:border-zinc-700 hover:text-zinc-200'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-[11px] font-bold text-cyan-400 bg-cyan-950/60 border border-cyan-500/30 rounded px-1.5 py-0.5">
                      {ep.method}
                    </span>
                    <span className="font-mono text-[11px] text-zinc-300 font-semibold">{ep.path}</span>
                  </div>
                  <p className="text-xs text-zinc-400 font-medium truncate mt-1">{ep.title}</p>
                </button>
              ))}

              <div className="mt-6 rounded-xl border border-zinc-800/60 bg-zinc-900/30 p-4 text-xs space-y-2">
                <p className="font-semibold text-zinc-300 flex items-center gap-1.5">
                  <Terminal className="h-3.5 w-3.5 text-cyan-400" />
                  Base API URL
                </p>
                <div className="font-mono text-[11px] text-zinc-400 bg-black/40 p-2 rounded-lg border border-zinc-800/80 break-all select-all">
                  {API_BASE}
                </div>
              </div>
            </div>

            {/* Endpoint Inspector & Live Runner */}
            <div className="lg:col-span-8 space-y-5">
              <div className="rounded-2xl border border-zinc-800 bg-zinc-900/50 p-6 space-y-5 shadow-xl shadow-black/20">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between border-b border-zinc-800/80 pb-4">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="rounded bg-emerald-500/10 border border-emerald-500/30 px-2 py-0.5 font-mono text-xs font-bold text-emerald-400">
                        {currentEndpoint.method}
                      </span>
                      <span className="font-mono text-sm font-bold text-white">{currentEndpoint.path}</span>
                    </div>
                    <h2 className="text-base font-semibold text-zinc-200">{currentEndpoint.title}</h2>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={copyCurl}
                      className="flex items-center gap-1.5 rounded-xl border border-zinc-700 bg-zinc-800/60 px-3 py-2 text-xs font-medium text-zinc-300 hover:text-white transition-all cursor-pointer"
                    >
                      {copied ? <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
                      <span>{copied ? 'Copied' : 'Copy cURL'}</span>
                    </button>
                    <button
                      onClick={handleTest}
                      disabled={loading}
                      className="flex items-center gap-1.5 rounded-xl bg-cyan-400 px-4 py-2 text-xs font-bold text-black hover:bg-cyan-300 transition-all cursor-pointer shadow-lg shadow-cyan-400/20 disabled:opacity-50"
                    >
                      <Play className="h-3.5 w-3.5 fill-black" />
                      <span>{loading ? 'Executing...' : 'Test Live'}</span>
                    </button>
                  </div>
                </div>

                <p className="text-xs text-zinc-300 leading-relaxed">{currentEndpoint.description}</p>

                {/* Query Parameters */}
                {currentEndpoint.params && currentEndpoint.params.length > 0 && (
                  <div className="space-y-2">
                    <p className="text-[10px] font-mono uppercase tracking-[0.18em] text-zinc-500">Query Parameters</p>
                    <div className="overflow-x-auto rounded-xl border border-zinc-800/80 bg-black/30">
                      <table className="w-full text-left text-xs">
                        <thead className="border-b border-zinc-800 bg-zinc-900/60 font-mono text-[10px] text-zinc-400 uppercase">
                          <tr>
                            <th className="p-2.5">Parameter</th>
                            <th className="p-2.5">Type</th>
                            <th className="p-2.5">Required</th>
                            <th className="p-2.5">Default</th>
                            <th className="p-2.5">Description</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-zinc-800/60 font-mono text-[11px] text-zinc-300">
                          {currentEndpoint.params.map((p) => (
                            <tr key={p.name} className="hover:bg-white/[0.02]">
                              <td className="p-2.5 font-bold text-cyan-400">{p.name}</td>
                              <td className="p-2.5 text-zinc-400">{p.type}</td>
                              <td className="p-2.5">{p.required ? <span className="text-rose-400 font-bold">Yes</span> : <span className="text-zinc-500">No</span>}</td>
                              <td className="p-2.5 text-zinc-400">{p.default ?? '—'}</td>
                              <td className="p-2.5 font-sans text-xs text-zinc-300">{p.desc}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                {/* Live Response Panel */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <p className="text-[10px] font-mono uppercase tracking-[0.18em] text-zinc-500">Live JSON Response</p>
                    {latency !== null && (
                      <span className="rounded bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 font-mono text-[10px] font-bold text-emerald-400">
                        HTTP 200 OK // {latency}ms
                      </span>
                    )}
                  </div>
                  <div className="rounded-xl border border-zinc-800 bg-black/60 p-4 font-mono text-[11px] text-zinc-300 overflow-x-auto max-h-[380px] shadow-inner">
                    {loading ? (
                      <div className="flex items-center gap-2 text-cyan-400 py-8 justify-center">
                        <div className="h-4 w-4 animate-spin rounded-full border-2 border-cyan-400 border-t-transparent" />
                        <span>Connecting to live backend endpoint...</span>
                      </div>
                    ) : liveResponse ? (
                      <pre className="whitespace-pre-wrap">{liveResponse}</pre>
                    ) : (
                      <p className="text-zinc-600 text-center py-8">Click "Test Live" above to query this endpoint in real-time.</p>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Tab 2: Embedded Swagger UI Iframe */}
        {activeTab === 'swagger' && (
          <div className="rounded-2xl border border-zinc-800 bg-zinc-900/50 p-4 space-y-4 shadow-xl shadow-black/20">
            <div className="flex items-center justify-between border-b border-zinc-800/80 pb-3">
              <div>
                <h3 className="text-sm font-semibold text-white">Full OpenAPI / Swagger UI</h3>
                <p className="text-xs text-zinc-400">Embedded directly from FastAPI backend engine</p>
              </div>
              <a
                href={DOCS_URL}
                target="_blank"
                rel="noreferrer"
                className="flex items-center gap-1 text-xs text-cyan-400 hover:text-cyan-300 transition-colors"
              >
                <span>Open in Full Browser Window</span>
                <ExternalLink className="h-3 w-3" />
              </a>
            </div>

            <div className="h-[750px] w-full overflow-hidden rounded-xl border border-zinc-800 bg-white">
              <iframe
                src={DOCS_URL}
                title="FastAPI Swagger Documentation"
                className="h-full w-full border-0"
              />
            </div>
          </div>
        )}
      </div>
      <Footer />
    </div>
  )
}
