import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { motion } from 'framer-motion'
import DeckGL from '@deck.gl/react'
import { ScatterplotLayer, TextLayer } from '@deck.gl/layers'
import type { MapViewState, ViewStateChangeParameters } from '@deck.gl/core'
import { Map as MapLibreMap } from 'react-map-gl/maplibre'
import maplibregl from 'maplibre-gl'

import { AuroraBackground } from '@/components/aurora-background'
import { cn } from '@/lib/utils'

const DEFAULT_RUN_DATA_PATH = './run-locations.json'
const RUN_DATA_URL = import.meta.env.VITE_RUN_DATA_URL ?? DEFAULT_RUN_DATA_PATH
const MAP_STYLE = 'https://basemaps.cartocdn.com/gl/dark-matter-nolabels-gl-style/style.json'
const MAP_PIN_OFFSET = 800

type RunLocation = {
  runid: string
  run_name?: string
  coordinates: [number, number]
  config?: string | number | null
  year?: number | null
  has_sbs?: boolean
  hillslopes?: number | string | null
  ash_hillslopes?: number | string | null
  access_count?: number | null
  last_accessed?: string | null
}

type AppState = {
  user?: {
    is_authenticated?: boolean
    email?: string | null
    name?: string | null
  }
}

declare global {
  interface Window {
    __WEPP_STATE__?: AppState
  }
}

const INITIAL_VIEW_STATE: MapViewState = {
  longitude: -98.5795,
  latitude: 39.8283,
  zoom: 3.5,
  maxZoom: 14,
  pitch: 35,
  bearing: 0,
}

const POINT_SCALE = 1

export function App() {
  const [data, setData] = useState<RunLocation[]>([])
  const [yearFilter, setYearFilter] = useState<string>('all')
  const [isLoading, setIsLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)
  const [panelOpen, setPanelOpen] = useState<boolean>(false)
  const [viewState, setViewState] = useState<MapViewState>(INITIAL_VIEW_STATE)
  const [appState] = useState<AppState>(() => (typeof window !== 'undefined' ? window.__WEPP_STATE__ ?? {} : {}))
  const [heroProgress, setHeroProgress] = useState<number>(0)

  const isAuthenticated = Boolean(appState.user?.is_authenticated)
  const heroHeadline = 'Watershed intelligence for response teams'
  const mapEyebrow = 'Run atlas'
  const mapTitle = 'Explore Active WEPPcloud Projects'
  const mapSubtitle =
    'Every WEPPcloud run with a recorded centroid appears on this map. Use it to highlight recent wildfire response studies, watershed planning campaigns, and the scale of collaboration across the platform.'
  const offsetCache = useRef(new Map<string, [number, number]>())

  useEffect(() => {
    const controller = new AbortController()

    async function loadRunLocations(): Promise<void> {
      setIsLoading(true)
      setError(null)
      try {
        const response = await fetch(resolveDataUrl(RUN_DATA_URL), {
          cache: 'no-store',
          signal: controller.signal,
        })
        if (!response.ok) {
          throw new Error(`Request failed with status ${response.status}`)
        }
        const payload: unknown = await response.json()
        if (!Array.isArray(payload)) {
          throw new Error('Unexpected response payload')
        }
        setData(payload as RunLocation[])
      } catch (err) {
        if (controller.signal.aborted) {
          return
        }
        const message = err instanceof Error ? err.message : 'Unable to load run data'
        setError(message)
      } finally {
        if (!controller.signal.aborted) {
          setIsLoading(false)
        }
      }
    }

    loadRunLocations()

    return () => controller.abort()
  }, [])

  useEffect(() => {
    function handleScroll() {
      const viewport = window.innerHeight || 1
      const threshold = Math.max(viewport * 0.6, 1)
      const progress = Math.min(Math.max(window.scrollY / threshold, 0), 1)
      setHeroProgress(progress)
    }
    handleScroll()
    window.addEventListener('scroll', handleScroll, { passive: true })
    window.addEventListener('resize', handleScroll)
    return () => {
      window.removeEventListener('scroll', handleScroll)
      window.removeEventListener('resize', handleScroll)
    }
  }, [])

  const filteredData = useMemo(() => {
    if (yearFilter === 'all') {
      return data
    }
    return data.filter((entry) => String(entry.year ?? '') === yearFilter)
  }, [data, yearFilter])

  const sortedData = useMemo(() => {
    if (filteredData.length <= 1) {
      return filteredData
    }
    return [...filteredData].sort((a, b) => {
      const aDate = a.last_accessed ?? ''
      const bDate = b.last_accessed ?? ''
      return bDate.localeCompare(aDate)
    })
  }, [filteredData])

  const yearOptions = useMemo(() => {
    const years = new Set<number>()
    data.forEach((entry) => {
      if (typeof entry.year === 'number' && Number.isFinite(entry.year)) {
        years.add(entry.year)
      }
    })
    return Array.from(years).sort((a, b) => b - a)
  }, [data])

  const aggregateStats = useMemo(() => {
    const totalHillslopes = data.reduce((sum, entry) => sum + normaliseNumber(entry.hillslopes), 0)
    const lastAccessed = data.length ? data[0]?.last_accessed : null
    return {
      totalRuns: data.length,
      totalHillslopes,
      lastAccessedParts: formatDateParts(lastAccessed),
    }
  }, [data])

  const filteredStats = useMemo(() => {
    const hills = sortedData.reduce((sum, entry) => sum + normaliseNumber(entry.hillslopes), 0)
    return {
      count: sortedData.length,
      message:
        sortedData.length > 0
          ? `Showing ${sortedData.length.toLocaleString()} run${sortedData.length === 1 ? '' : 's'}`
          : 'No georeferenced runs were found. Check again later.',
      hillslopes: hills,
    }
  }, [sortedData])

  const handleViewStateChange = useCallback(
    ({ viewState: next }: ViewStateChangeParameters) => {
      setViewState(next)
    },
    [],
  )

  const getLabelOffset = useCallback(
    (entry: RunLocation): [number, number] => {
      const key =
        entry.runid ||
        (Array.isArray(entry.coordinates) ? entry.coordinates.join(':') : 'fallback-run')
      if (offsetCache.current.has(key)) {
        return offsetCache.current.get(key)!
      }
      const hash = hashString(key)
      const angle = Math.abs(hash % 360) * (Math.PI / 180)
      const magnitude = 4 + Math.abs(hash % 7)
      const offset: [number, number] = [
        Math.round(6 + Math.cos(angle) * magnitude),
        Math.round(Math.sin(angle) * magnitude),
      ]
      offsetCache.current.set(key, offset)
      return offset
    },
    [],
  )

  const labelSize = useMemo(() => {
    const zoom = viewState?.zoom ?? 1
    return Math.min(10, Math.max(1, zoom))
  }, [viewState])

  const deckLayers = useMemo(() => {
    if (!sortedData.length) {
      return []
    }
    const scatterLayer = new ScatterplotLayer({
      id: 'run-centroids',
      data: sortedData,
      pickable: true,
      radiusUnits: 'pixels',
      radiusScale: 1,
      radiusMinPixels: 4,
      radiusMaxPixels: 60,
      getPosition: (d) => d.coordinates,
      getRadius: (d) => Math.max(6, (d.access_count ?? 1) * POINT_SCALE),
      getFillColor: (d) => (d.has_sbs ? [124, 58, 237, 190] : [14, 165, 233, 190]),
      getLineColor: [255, 255, 255, 180],
      lineWidthMinPixels: 1,
    })

    const textLayer = new TextLayer({
      id: 'run-labels',
      data: sortedData,
      pickable: false,
      getPosition: (d) => d.coordinates,
      getText: (d) => (d.run_name || '').trim(),
      getSize: labelSize,
      getAngle: 0,
      getColor: [236, 248, 255, 220],
      getTextAnchor: 'start',
      getAlignmentBaseline: 'bottom',
      getPixelOffset: (d) => getLabelOffset(d),
      maxWidth: 120,
      sizeUnits: 'pixels',
    })

    return [scatterLayer, textLayer]
  }, [sortedData, labelSize, getLabelOffset])

  const tooltipBuilder = useCallback(({ object }: { object?: RunLocation | null }) => {
    if (!object) {
      return null
    }
    const lines = [
      object.run_name || 'Unnamed run',
      object.runid ? `ID: ${object.runid}` : null,
      object.config ? `Config: ${object.config}` : null,
      object.access_count ? `Accesses: ${object.access_count}` : null,
      object.last_accessed ? `Last accessed: ${formatDate(object.last_accessed)}` : null,
    ].filter(Boolean)
    return lines.join('\n')
  }, [])

  const statusMessage = useMemo(() => {
    if (error) {
      return error
    }
    if (isLoading) {
      return 'Loading run data...'
    }
    return ''
  }, [error, isLoading])

  const navItems = useMemo(
    () => [
      { label: 'Interface', href: '/weppcloud/' },
      { label: 'Docs', href: '/weppcloud/docs/' },
      { label: 'Research', href: 'https://wepp.cloud/research', external: true },
      {
        label: isAuthenticated ? 'Runs' : 'Login',
        href: isAuthenticated ? '/weppcloud/runs/' : '/weppcloud/login/',
      },
    ],
    [isAuthenticated],
  )

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <section id="hero" className="flex min-h-[100svh] z-20">
        <AuroraBackground className="flex-1 min-h-[100svh]" opacity={Math.max(0, 1 - heroProgress)}>
          <div className="relative mx-auto flex h-full max-w-5xl flex-col items-center justify-start gap-12 px-6 py-16 pt-[600px] text-center sm:py-24 lg:py-32">
            <motion.div
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, ease: 'easeOut' }}
              className="space-y-4"
            >
              <p className="text-xs uppercase tracking-[0.4em] text-sky-200">WEPPcloud</p>
              <h1 className="text-4xl font-semibold leading-tight text-white sm:text-5xl lg:text-6xl">
                <TypewriterText text={heroHeadline} speed={2} delay={200} />
              </h1>
              <p className="text-base text-slate-200 sm:text-lg">
                Launch tools, explore documentation, or jump into the latest analytics. Scroll to
                reveal live WEPPcloud runs rendered in real time.
              </p>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.9, ease: 'easeOut', delay: 0.15 }}
              className="flex flex-wrap items-center justify-center gap-4"
            >
              {navItems.map((item, idx) => (
                <motion.a
                  key={item.label}
                  className="inline-flex items-center rounded-full border border-white/20 bg-white/5 px-6 py-2 text-sm font-semibold uppercase tracking-wide text-white transition hover:border-white/60"
                  href={item.href}
                  target={item.external ? '_blank' : undefined}
                  rel={item.external ? 'noreferrer' : undefined}
                  whileHover={{ scale: 1.03 }}
                  whileTap={{ scale: 0.98 }}
                  transition={{ duration: 0.15, delay: idx * 0.05 }}
                >
                  {item.label}
                </motion.a>
              ))}
            </motion.div>
          </div>
          <div className="hero-fade" />
        </AuroraBackground>
      </section>

      <section
        id="map"
        className="relative z-30 bg-[#020617] px-4 pb-16 pt-12 sm:px-6 lg:px-12"
        style={{ minHeight: `calc(100vh + ${MAP_PIN_OFFSET}px)` }}
      >
        <div className="map-top-fade" aria-hidden="true" />
        <div className="map-pin-wrapper" style={{ minHeight: `calc(100vh + ${MAP_PIN_OFFSET}px)` }}>
          <div className="map-pin-container space-y-8">
            <motion.div
              initial={{ opacity: 0, y: 50 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.2 }}
              transition={{ duration: 0.8, ease: 'easeOut' }}
              className="mx-auto max-w-5xl"
            >
              <div className="space-y-4 text-center">
                <p className="text-xs uppercase tracking-[0.4em] text-sky-200">{mapEyebrow}</p>
                <h2 className="text-3xl font-semibold text-white sm:text-4xl">{mapTitle}</h2>
                <p className="text-base text-slate-300">{mapSubtitle}</p>
              </div>
              <div className="mt-6 grid gap-6 sm:grid-cols-3">
                <MetricCard label="Unique runs" value={aggregateStats.totalRuns} />
                <MetricCard label="Total hillslopes" value={aggregateStats.totalHillslopes} />
                <MetricCard
                  label="Latest access"
                  value={
                    aggregateStats.lastAccessedParts
                      ? `${aggregateStats.lastAccessedParts.date}\n${aggregateStats.lastAccessedParts.time}`
                      : '--'
                  }
                  multiline
                />
              </div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 60 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.3 }}
              transition={{ duration: 0.9, ease: 'easeOut', delay: 0.1 }}
              className="relative min-h-[520px] border border-white/10 bg-slate-950/80 shadow-2xl shadow-black/40"
            >
            <div className="relative h-[65vh] min-h-[520px] overflow-hidden">
              <div className="map-legend">
                <span className="legend-chip">
                  <span className="legend-dot bg-sky-400" />
                  Standard runs
                </span>
                <span className="legend-chip">
                  <span className="legend-dot bg-violet-500" />
                  Runs with SBS
                </span>
                <span className="legend-chip">
                  <span className="legend-dot bg-emerald-400" />
                  Filtered hillslopes: {filteredStats.hillslopes.toLocaleString()}
                </span>
              </div>
              <div
                className="absolute inset-0"
                onWheelCapture={(event) => {
                  if (!event.ctrlKey) {
                    event.stopPropagation()
                  }
                }}
              >
                {sortedData.length > 0 ? (
                  <DeckGL
                    controller
                    initialViewState={INITIAL_VIEW_STATE}
                    layers={deckLayers}
                    viewState={viewState}
                    onViewStateChange={handleViewStateChange}
                    getTooltip={tooltipBuilder}
                    style={{ position: 'absolute', top: '0', right: '0', bottom: '0', left: '0' }}
                  >
                    <MapLibreMap
                      reuseMaps
                      mapLib={maplibregl}
                      mapStyle={MAP_STYLE}
                      attributionControl={false}
                    />
                  </DeckGL>
                ) : (
                  <div className="absolute inset-0 flex items-center justify-center bg-slate-950">
                    <p className="text-sm text-slate-400">Preparing map...</p>
                  </div>
                )}
              </div>

              <div className="absolute bottom-6 right-6 rounded-xl border border-white/10 bg-slate-950/80 px-4 py-2 text-xs text-slate-300">
                Tip: Hold <span className="font-semibold text-white">Ctrl</span> while scrolling to
                zoom the map.
              </div>

              <button
                type="button"
                className="control-toggle"
                aria-expanded={panelOpen}
                onClick={() => setPanelOpen((open) => !open)}
              >
                <span className="icon" aria-hidden="true" />
                <span className="label">{panelOpen ? 'Close controls' : 'Map controls'}</span>
              </button>

              <aside
                className={cn(
                  'control-panel',
                  'absolute right-6 top-24 w-72 rounded-2xl border border-slate-800/80 bg-slate-950/95 p-6 text-sm transition-all',
                  panelOpen ? 'pointer-events-auto opacity-100' : 'pointer-events-none opacity-0',
                )}
              >
                <h2 className="text-base font-semibold text-slate-100">Display options</h2>
                <div className="mt-4 space-y-3">
                  <label className="block text-xs uppercase tracking-wider text-slate-400">
                    Year
                    <select
                      className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 shadow-none transition focus:border-sky-400 focus:outline-none"
                      value={yearFilter}
                      onChange={(event) => setYearFilter(event.target.value)}
                    >
                      <option value="all">All years</option>
                      {yearOptions.map((year) => (
                        <option key={year} value={String(year)}>
                          {year}
                        </option>
                      ))}
                    </select>
                  </label>
                  <p className="text-xs text-slate-400">
                    Zoom to reveal run labels. Marker size scales with access count and is fixed at
                    1x for consistency.
                  </p>
                </div>
              </aside>

              {statusMessage && (
                <div className="absolute bottom-6 left-6 rounded-2xl border border-white/10 bg-slate-950/80 px-4 py-3 text-xs text-slate-300">
                  {statusMessage}
                </div>
              )}
            </div>
          </motion.div>
        </div>
      </div>
      </section>
    </div>
  )
}

function MetricCard(props: {
  label: string
  value: number | string | null | undefined
  multiline?: boolean
}) {
  return (
    <div className="rounded-2xl border border-white/20 bg-slate-900 p-6 shadow-lg shadow-black/30">
      <p className="text-xs uppercase tracking-widest text-slate-400">{props.label}</p>
      <p
        className={cn(
          'mt-3 text-3xl font-semibold text-white whitespace-pre-line',
          props.multiline && 'leading-tight text-2xl',
        )}
      >
        {typeof props.value === 'number' ? props.value.toLocaleString() : props.value ?? '--'}
      </p>
    </div>
  )
}

type TypewriterTextProps = {
  text: string
  speed?: number
  delay?: number
}

function TypewriterText({ text, speed = 40, delay = 200 }: TypewriterTextProps) {
  const [displayed, setDisplayed] = useState<string>('')
  const intervalRef = useRef<number | null>(null)
  const timeoutRef = useRef<number | null>(null)

  useEffect(() => {
    let index = 0
    timeoutRef.current = window.setTimeout(() => {
      intervalRef.current = window.setInterval(() => {
        index += 1
        setDisplayed(text.slice(0, index))
        if (index >= text.length && intervalRef.current) {
          window.clearInterval(intervalRef.current)
          intervalRef.current = null
        }
      }, speed)
    }, delay)

    return () => {
      if (intervalRef.current) {
        window.clearInterval(intervalRef.current)
      }
      if (timeoutRef.current) {
        window.clearTimeout(timeoutRef.current)
      }
    }
  }, [text, speed, delay])

  return (
    <span aria-label={text}>
      {displayed}
      <span className="typewriter-cursor">|</span>
    </span>
  )
}

function normaliseNumber(value: unknown): number {
  const numeric = Number(value)
  if (!Number.isFinite(numeric)) {
    return 0
  }
  return numeric
}

function formatDate(value: string | null | undefined): string | null {
  if (!value) {
    return null
  }
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return null
  }
  return date.toLocaleString()
}

function formatDateParts(value: string | null | undefined):
  | null
  | {
      date: string
      time: string
    } {
  if (!value) {
    return null
  }
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return null
  }
  return {
    date: date.toLocaleDateString(),
    time: date.toLocaleTimeString(),
  }
}

function hashString(value: string): number {
  let hash = 0
  for (let i = 0; i < value.length; i += 1) {
    hash = (hash << 5) - hash + value.charCodeAt(i)
    hash |= 0
  }
  return hash
}

function resolveDataUrl(path: string): string {
  const target = path || DEFAULT_RUN_DATA_PATH
  const isAbsolute = /^https?:\/\//i.test(target)
  if (isAbsolute) {
    return target
  }
  if (target.startsWith('/')) {
    return new URL(target, window.location.origin).toString()
  }
  return new URL(target, window.location.href).toString()
}

export default App
