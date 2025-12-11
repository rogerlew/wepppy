import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { motion } from 'framer-motion'
import DeckGL from '@deck.gl/react'
import { ScatterplotLayer, TextLayer } from '@deck.gl/layers'
import type { MapViewState, ViewStateChangeParameters } from '@deck.gl/core'
import { Map as MapLibreMap } from 'react-map-gl/maplibre'
import maplibregl from 'maplibre-gl'
import {
  CloudRain,
  FileText,
  Flame,
  Globe,
  Server,
  Settings,
  Sprout,
  Zap,
  type LucideIcon,
} from 'lucide-react'

import { AuroraBackground } from '@/components/aurora-background'
import { cn } from '@/lib/utils'

const DEFAULT_RUN_DATA_PATH = './run-locations.json'
const RUN_DATA_URL = import.meta.env.VITE_RUN_DATA_URL ?? DEFAULT_RUN_DATA_PATH
const MAP_STYLE = 'https://basemaps.cartocdn.com/gl/dark-matter-nolabels-gl-style/style.json'
const MAP_PIN_OFFSET = 800

type HelpResource = {
  title: string
  description: string
  href: string
  icon: 'zap' | 'youtube' | 'github'
}

const CONTACT_ICON_MAP = {
  server: Server,
  settings: Settings,
  flame: Flame,
  cloudRain: CloudRain,
  sprout: Sprout,
  fileText: FileText,
} satisfies Record<string, LucideIcon>

const CONTACT_ACCENTS = {
  violet: {
    border: 'border-violet-500/40',
    glow: 'from-violet-500/20 via-violet-500/5 to-transparent',
    icon: 'bg-violet-500/15 text-violet-100',
    chip: 'bg-violet-500/10 text-violet-100',
  },
  sky: {
    border: 'border-sky-500/40',
    glow: 'from-sky-500/20 via-sky-500/5 to-transparent',
    icon: 'bg-sky-500/15 text-sky-100',
    chip: 'bg-sky-500/10 text-sky-100',
  },
  amber: {
    border: 'border-amber-400/40',
    glow: 'from-amber-400/25 via-amber-400/5 to-transparent',
    icon: 'bg-amber-400/15 text-amber-100',
    chip: 'bg-amber-400/10 text-amber-100',
  },
  emerald: {
    border: 'border-emerald-400/40',
    glow: 'from-emerald-400/20 via-emerald-400/5 to-transparent',
    icon: 'bg-emerald-400/15 text-emerald-100',
    chip: 'bg-emerald-400/10 text-emerald-100',
  },
  lime: {
    border: 'border-lime-400/40',
    glow: 'from-lime-400/20 via-lime-400/5 to-transparent',
    icon: 'bg-lime-400/15 text-lime-100',
    chip: 'bg-lime-400/10 text-lime-100',
  },
  cyan: {
    border: 'border-cyan-400/40',
    glow: 'from-cyan-400/20 via-cyan-400/5 to-transparent',
    icon: 'bg-cyan-400/15 text-cyan-100',
    chip: 'bg-cyan-400/10 text-cyan-100',
  },
} as const

type ContactAccent = keyof typeof CONTACT_ACCENTS
type ContactIcon = keyof typeof CONTACT_ICON_MAP

type Contact = {
  name: string
  title: string
  institution: string
  email: string
  expertise: string[]
  icon: ContactIcon
  accent: ContactAccent
}

const HELP_RESOURCES: HelpResource[] = [
  {
    title: 'Quick Start',
    description: 'Follow the walkthrough to configure a run end-to-end.',
    href: 'https://doc.wepp.cloud/QuickStart.html',
    icon: 'zap',
  },
  {
    title: 'WEPPcloud YouTube',
    description: 'Video tutorials, release notes, and demos.',
    href: 'https://www.youtube.com/@fswepp4700',
    icon: 'youtube',
  },
  {
    title: 'wepppy on GitHub',
    description: 'Source code, issues, and AI-friendly docs.',
    href: 'https://github.com/rogerlew/wepppy',
    icon: 'github',
  },
]

const CONTACTS: Contact[] = [
  {
    name: 'Roger Lew',
    title: 'WEPPcloud DevOps Architect, Associate Research Professor',
    institution: 'University of Idaho',
    email: 'rogerlew@uidaho.edu',
    expertise: ['WEPPcloud', 'WEPP inputs & outputs', 'Data pipelines', 'Analytics'],
    icon: 'server',
    accent: 'violet',
  },
  {
    name: 'Mariana Dobre',
    title: 'Assistant Professor',
    institution: 'University of Idaho',
    email: 'mdobre@uidaho.edu',
    expertise: ['Hydrology', 'Soil science', 'Calibration', 'Forests'],
    icon: 'settings',
    accent: 'sky',
  },
  {
    name: 'Pete Robichaud',
    title: 'Research Engineer',
    institution: 'USDA Forest Service, Rocky Mountain Research Station',
    email: 'peter.robichaud@usda.gov',
    expertise: ['Forest response', 'WEPP', 'Post-fire erosion', 'Ash transport'],
    icon: 'flame',
    accent: 'amber',
  },
  {
    name: 'Anurag Srivastava',
    title: 'Research Scientist',
    institution: 'University of Idaho',
    email: 'srivanu@uidaho.edu',
    expertise: ['WEPP model', 'Hydrology', 'Soil erosion', 'Climate datasets'],
    icon: 'cloudRain',
    accent: 'emerald',
  },
  {
    name: 'Erin Brooks',
    title: 'Professor',
    institution: 'University of Idaho',
    email: 'ebrooks@uidaho.edu',
    expertise: ['Landscape hydrology', 'Precision agriculture', 'Nutrient cycling', 'Water quality'],
    icon: 'sprout',
    accent: 'lime',
  },
  {
    name: 'Brian (Scott) Sheppard',
    title: 'Research Hydrologist',
    institution: 'USDA Forest Service, Rocky Mountain Research Station',
    email: 'brian.sheppard@usda.gov',
    expertise: ['Hydrology', 'Fire response modeling'],
    icon: 'fileText',
    accent: 'cyan',
  },
]

type Affiliation = {
  name: string
  caption: string
  logo: string
  link: string
}

const AFFILIATIONS: Affiliation[] = [
  {
    name: 'University of Idaho',
    caption: 'Go Vandals! University of Idaho',
    logo: '/weppcloud/static/images/University_of_Idaho_logo.svg',
    link: 'https://www.uidaho.edu/',
  },
  {
    name: 'Swansea University',
    caption: 'Gweddw Crefft Heb Ei Dawn - Technical Skill is Bereft Without Culture',
    logo: '/weppcloud/static/images/Swansea_University_logo.png',
    link: 'https://www.swansea.ac.uk/',
  },
  {
    name: 'USDA Forest Service',
    caption: 'Caring for the land and serving people. Rocky Mountain Research Station',
    logo: '/weppcloud/static/images/Logo_of_the_United_States_Forest_Service.svg',
    link: 'https://www.fs.usda.gov/rmrs/',
  },
  {
    name: 'UI Research Computing & Data Services',
    caption: 'Proudly hosted by the University of Idaho Research Computing + Data Services',
    logo: '/weppcloud/static/images/RCDS_Logo-horizontal.svg',
    link: 'https://www.uidaho.edu/research/computing',
  },
  {
    name: 'Rangeland Analysis Platform',
    caption: 'Big data for big landscapes - combining satellite imagery with thousands of on-the-ground vegetation measurements',
    logo: '/weppcloud/static/images/rapIconSmall.png',
    link: 'https://rangelands.app/',
  },
  {
    name: 'Michigan Technological University',
    caption: 'Tomorrow needs Michigan Tech - R1 flagship technological research university',
    logo: '/weppcloud/static/images/michigan-tech-logo-full-yellow.svg',
    link: 'https://www.mtu.edu/',
  },
  {
    name: 'Washington State University',
    caption: 'World-class research university dedicated to solving problems and improving lives',
    logo: '/weppcloud/static/images/Washington-State-University-Logo.png',
    link: 'https://www.wsu.edu/',
  },
]

type Sponsor = {
  name: string
  caption: string
  logo: string
  link: string
}

const SPONSORS: Sponsor[] = [
  {
    name: 'NSF Idaho EPSCoR',
    caption: 'This work was made possible by the NSF Idaho EPSCoR Program and by the National Science Foundation under award number IIA-1301792.',
    logo: '/weppcloud/static/images/Idaho_epscor_logo_no_white_background.png',
    link: 'https://www.idahoepscor.org/',
  },
  {
    name: 'USDA NIFA',
    caption: 'This work is supported by AFRI program [grant no. 2016-67020-25320/project accession no. 1009827] from the USDA National Institute of Food and Agriculture.',
    logo: '/weppcloud/static/images/USDA_logo.png',
    link: 'https://www.nifa.usda.gov/',
  },
  {
    name: 'UKRI NERC',
    caption: 'The Wildfire Ash Transport And Risk estimation tool (WATAR) was made possible with funding provided by UK NERC Grant NE/R011125/1 and European Commission (H2020 FirEUrisk project no. 101003890).',
    logo: '/weppcloud/static/images/ukri-nerc-logo-600x160.png',
    link: 'https://www.ukri.org/councils/nerc/',
  },
  {
    name: 'NASA WWAO',
    caption: "The revegetation module in WEPPcloud was supported by NASA's Western Water Application Office (WWAO).",
    logo: '/weppcloud/static/images/nasa_logo.svg',
    link: 'https://wwao.jpl.nasa.gov/',
  },
]

const CONTRIBUTORS = [
  'Garrit Bass',
  'Marta Basso',
  'Erin Brooks',
  'Subhankar Das',
  'Chinmay Deval',
  'Mariana Dobre',
  'Stefan Doerr',
  'Helen Dow',
  'William Elliot',
  'Ames Fowler',
  'Jim Frakenberger',
  'Roger Lew',
  'Mary E. Miller',
  'Jonay Neris',
  'Pete Robichaud',
  'Cristina Santin',
  'Brian (Scott) Sheppard',
  'Anurag Srivastava',
  'Alex Watanabe'
]

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
      { label: 'Docs', href: 'https://doc.wepp.cloud' },
      { label: 'Research', href: 'https://forest.moscowfsl.wsu.edu/library/', external: true },
      { label: 'Interfaces', href: '/weppcloud/interfaces/' },
      {
        label: isAuthenticated ? 'My Runs' : 'Login',
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
                <TypewriterText text={heroHeadline} speed={1} delay={1000} />
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
        id="about"
        className="relative z-30 bg-[#020617] px-4 py-16 sm:px-6 lg:px-12"
      >
        <motion.div
          initial={{ opacity: 0, y: 50 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.2 }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
          className="mx-auto max-w-4xl text-center"
        >
          <p className="text-xs uppercase tracking-[0.4em] text-sky-200">About</p>
          <h2 className="mt-4 text-3xl font-semibold text-white sm:text-4xl">What is WEPPcloud?</h2>
          <p className="mt-6 text-lg leading-relaxed text-slate-300">
            WEPPcloud is an online interface for running WEPP (Water Erosion Prediction Project) Model. WEPP is a
            physically based erosion model built to replace the Universal Soil Loss Equation (USLE) model. The interface
            simplifies the acquisition and preparation of topography, soil, management, and climate inputs for WEPP.
          </p>
        </motion.div>
      </section>

      <section
        id="map"
        className="relative z-30 bg-[#020617] px-4 pb-16 pt-12 sm:px-6 lg:px-12"
      >
        <div className="map-top-fade" aria-hidden="true" />
        <div className="map-pin-container space-y-8">
          <motion.div
            initial={{ opacity: 0, y: 50 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.2 }}
            transition={{ duration: 0.8, ease: 'easeOut' }}
            className="mx-auto max-w-5xl"
          >
            <div className="space-y-4 text-center pt-12">
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
        <div aria-hidden="true" style={{ height: `${MAP_PIN_OFFSET}px` }} />
      </section>

      <section className="bg-[#050714] px-4 py-20 sm:px-6 lg:px-12">
        <motion.div
          initial={{ opacity: 0, y: 40 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.25 }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
          className="mx-auto max-w-4xl space-y-4 text-center"
        >
          <p className="text-xs uppercase tracking-[0.4em] text-sky-200">Help</p>
          <h2 className="text-3xl font-semibold text-white sm:text-4xl">Help & Resources</h2>
          <p className="text-base text-slate-300">
            Jump straight into documentation, watch the latest walkthrough, or explore the open
            source stack powering WEPPcloud.
          </p>
        </motion.div>

        <div className="mx-auto mt-10 grid max-w-5xl gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {HELP_RESOURCES.map((resource, index) => (
            <motion.a
              key={resource.title}
              href={resource.href}
              target="_blank"
              rel="noreferrer"
              className="flex h-full flex-col rounded-2xl border border-white/10 bg-slate-900/60 p-6 text-left shadow-lg shadow-black/30 transition hover:-translate-y-1 hover:border-sky-400/60"
              initial={{ opacity: 0, y: 25 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.2 }}
              transition={{ duration: 0.4, delay: index * 0.1 }}
            >
              <div className="mb-4 flex items-center gap-3 text-slate-100">
                {renderHelpIcon(resource.icon)}
                <span className="text-lg font-semibold">{resource.title}</span>
              </div>
              <p className="flex-grow text-sm text-slate-300">{resource.description}</p>
              <span className="mt-6 text-xs font-semibold uppercase tracking-[0.2em] text-sky-300">
                Visit →
              </span>
            </motion.a>
          ))}
        </div>
      </section>

      <section className="bg-[#030712] px-4 py-20 sm:px-6 lg:px-12">
        <motion.div
          initial={{ opacity: 0, y: 40 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.25 }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
          className="mx-auto max-w-4xl space-y-4 text-center"
        >
          <p className="text-xs uppercase tracking-[0.4em] text-sky-200">Team</p>
          <h2 className="text-3xl font-semibold text-white sm:text-4xl">Points of Contact</h2>
          <p className="text-base text-slate-300">
            Connect with the researchers, engineers, and hydrologists who shape WEPPcloud. Each
            contact can help with specialized workflows, calibration strategies, and emergency
            response planning.
          </p>
        </motion.div>

        <div className="mx-auto mt-12 grid max-w-6xl gap-6 md:grid-cols-2">
          {CONTACTS.map((contact, index) => {
            const accent = CONTACT_ACCENTS[contact.accent]
            const IconComponent = CONTACT_ICON_MAP[contact.icon]
            return (
              <motion.article
                key={contact.email}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, amount: 0.2 }}
                transition={{ duration: 0.5, delay: index * 0.05 }}
                whileHover={{
                  scale: 1.02,
                }}
                onMouseMove={(e) => {
                  const card = e.currentTarget
                  const rect = card.getBoundingClientRect()
                  const x = e.clientX - rect.left
                  const y = e.clientY - rect.top
                  const centerX = rect.width / 2
                  const centerY = rect.height / 2
                  const rotateX = ((y - centerY) / centerY) * -10
                  const rotateY = ((x - centerX) / centerX) * 10
                  
                  // Update card transform
                  card.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) scale(1.02)`
                  
                  // Update highlight position
                  const xPercent = (x / rect.width) * 100
                  const yPercent = (y / rect.height) * 100
                  const highlight = card.querySelector('.card-highlight') as HTMLElement
                  if (highlight) {
                    highlight.style.setProperty('--mouse-x', `${xPercent}%`)
                    highlight.style.setProperty('--mouse-y', `${yPercent}%`)
                    highlight.style.opacity = '1'
                  }
                }}
                onMouseLeave={(e) => {
                  const card = e.currentTarget
                  card.style.transform = ''
                  card.style.transition = 'transform 0.3s ease-out'
                  
                  const highlight = card.querySelector('.card-highlight') as HTMLElement
                  if (highlight) {
                    highlight.style.opacity = '0'
                  }
                }}
                className={cn(
                  'relative flex h-full flex-col overflow-hidden rounded-3xl border bg-slate-950/70 p-6 shadow-2xl shadow-black/40 hover:shadow-black/60',
                  accent.border,
                )}
                style={{ transformStyle: 'preserve-3d', transition: 'transform 0.3s ease-out' }}
              >
                <div
                  className={cn(
                    'pointer-events-none absolute inset-0 bg-gradient-to-br opacity-70 blur-3xl',
                    accent.glow,
                  )}
                  aria-hidden="true"
                />
                <div
                  className="card-highlight pointer-events-none absolute inset-0 opacity-0 transition-opacity duration-200"
                  style={{
                    background: 'radial-gradient(circle at var(--mouse-x, 50%) var(--mouse-y, 50%), rgba(255,255,255,0.08) 0%, transparent 50%)',
                  }}
                  aria-hidden="true"
                />
                <div className="relative z-10 flex flex-col gap-5">
                  <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
                    <div
                      className={cn(
                        'inline-flex h-14 w-14 items-center justify-center rounded-2xl text-lg',
                        accent.icon,
                      )}
                    >
                      <IconComponent className="h-7 w-7" aria-hidden="true" />
                    </div>
                    <div>
                      <p className="text-xs uppercase tracking-[0.4em] text-slate-400">Contact</p>
                      <h3 className="text-xl font-semibold text-white">{contact.name}</h3>
                      <p className="text-sm text-slate-300">{contact.title}</p>
                    </div>
                  </div>
                  <div className="space-y-1 text-sm text-slate-300">
                    <p className="font-medium text-slate-100">{contact.institution}</p>
                    <a
                      className="inline-flex items-center gap-2 text-sky-300 transition hover:text-sky-200"
                      href={`mailto:${contact.email}`}
                    >
                      <span className="text-xs uppercase tracking-[0.3em] text-sky-200">Email</span>
                      <span>{contact.email}</span>
                    </a>
                  </div>
                  <div>
                    <p className="text-xs uppercase tracking-[0.3em] text-slate-400">Expertise</p>
                    <div className="mt-3 flex flex-wrap gap-2">
                      {contact.expertise.map((item) => (
                        <span
                          key={item}
                          className={cn(
                            'rounded-full px-3 py-1 text-xs font-medium',
                            accent.chip,
                          )}
                        >
                          {item}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              </motion.article>
            )
          })}
        </div>
      </section>

      <section className="bg-[#020617] px-4 py-20 sm:px-6 lg:px-12">
        <motion.div
          initial={{ opacity: 0, y: 40 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.25 }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
          className="mx-auto max-w-4xl space-y-4 text-center"
        >
          <p className="text-xs uppercase tracking-[0.4em] text-sky-200">Collaborators</p>
          <h2 className="text-3xl font-semibold text-white sm:text-4xl">
            Affiliations and Collaborators
          </h2>
          <p className="text-base text-slate-300">
            WEPPcloud is made possible through collaborative partnerships across research
            institutions, government agencies, and international funding programs.
          </p>
        </motion.div>

        <div className="mx-auto mt-12 grid max-w-6xl gap-8 sm:grid-cols-2 lg:grid-cols-4">
          {AFFILIATIONS.map((affiliation, index) => (
            <motion.a
              key={affiliation.name}
              href={affiliation.link}
              target="_blank"
              rel="noreferrer"
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.2 }}
              transition={{ duration: 0.5, delay: index * 0.1 }}
              className="group flex flex-col items-center justify-center rounded-2xl border border-white/10 bg-slate-900/40 p-8 transition-all duration-300 hover:-translate-y-1 hover:border-white/30"
            >
              <div className="flex h-20 w-full items-center justify-center">
                <img
                  src={affiliation.logo}
                  alt={affiliation.name}
                  className={cn(
                    "max-h-20 w-auto object-contain grayscale",
                    affiliation.name === "Michigan Technological University"
                      ? "brightness-[2] opacity-90 contrast-125"
                      : "invert opacity-60 contrast-125"
                  )}
                />
              </div>
              <p className="mt-4 text-center text-xs text-slate-400">
                {affiliation.caption}
              </p>
            </motion.a>
          ))}
        </div>
      </section>

      <section className="bg-[#050714] px-4 py-20 sm:px-6 lg:px-12">
        <motion.div
          initial={{ opacity: 0, y: 40 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.25 }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
          className="mx-auto max-w-4xl space-y-4 text-center"
        >
          <p className="text-xs uppercase tracking-[0.4em] text-sky-200">Funding</p>
          <h2 className="text-3xl font-semibold text-white sm:text-4xl">Sponsors</h2>
          <p className="text-base text-slate-300">
            WEPPcloud development is supported by grants from federal agencies, international
            research programs, and scientific funding bodies.
          </p>
        </motion.div>

        <div className="mx-auto mt-12 grid max-w-6xl gap-8 sm:grid-cols-2 lg:grid-cols-4">
          {SPONSORS.map((sponsor, index) => (
            <motion.a
              key={sponsor.name}
              href={sponsor.link}
              target="_blank"
              rel="noreferrer"
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.2 }}
              transition={{ duration: 0.5, delay: index * 0.1 }}
              className="group flex flex-col items-center justify-center rounded-2xl border border-white/10 bg-slate-900/40 p-8 transition-all duration-300 hover:-translate-y-1 hover:border-white/30"
            >
              <div className="flex h-20 w-full items-center justify-center">
                <img
                  src={sponsor.logo}
                  alt={sponsor.name}
                  className="max-h-20 w-auto object-contain grayscale invert opacity-60 contrast-125"
                />
              </div>
              <p className="mt-4 text-center text-xs text-slate-400">{sponsor.caption}</p>
            </motion.a>
          ))}
        </div>
      </section>

      <section className="bg-[#030712] px-4 py-20 sm:px-6 lg:px-12">
        <motion.div
          initial={{ opacity: 0, y: 40 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.25 }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
          className="mx-auto max-w-4xl space-y-4 text-center"
        >
          <p className="text-xs uppercase tracking-[0.4em] text-sky-200">Team</p>
          <h2 className="text-3xl font-semibold text-white sm:text-4xl">Contributors</h2>
          <p className="text-base text-slate-300">
            WEPPcloud is the result of collaborative efforts from researchers, engineers, and
            scientists across multiple institutions.
          </p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.3 }}
          transition={{ duration: 0.6, ease: 'easeOut' }}
          className="mx-auto mt-12 flex max-w-5xl flex-wrap items-center justify-center gap-3"
        >
          {CONTRIBUTORS.map((contributor) => (
            <span
              key={contributor}
              className="rounded-full border border-white/10 bg-slate-800/60 px-4 py-2 text-sm text-slate-200"
            >
              {contributor}
            </span>
          ))}
        </motion.div>
      </section>

      <section className="bg-[#020617] px-4 py-20 sm:px-6 lg:px-12">
        <motion.div
          initial={{ opacity: 0, y: 40 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.25 }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
          className="mx-auto max-w-4xl space-y-4 text-center"
        >
          <p className="text-xs uppercase tracking-[0.4em] text-sky-200">Credits</p>
          <h2 className="text-3xl font-semibold text-white sm:text-4xl">
            Attributions and Data Sources
          </h2>
          <p className="text-base text-slate-300">
            WEPPcloud leverages open data, research-quality datasets, and mapping services from
            partners worldwide.
          </p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.3 }}
          transition={{ duration: 0.6, ease: 'easeOut' }}
          className="mx-auto mt-12 grid max-w-5xl gap-12 sm:grid-cols-2"
        >
          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-white">Map Services</h3>
            <p className="text-sm text-slate-300">
              Map baselayers provided by{' '}
              <a
                href="https://www.google.com/maps"
                target="_blank"
                rel="noreferrer"
                className="text-sky-300 transition hover:text-sky-200"
              >
                Google
              </a>{' '}
              (Terrain, Satellite) and{' '}
              <a
                href="https://www.openstreetmap.org/"
                target="_blank"
                rel="noreferrer"
                className="text-sky-300 transition hover:text-sky-200"
              >
                OpenStreetMap
              </a>{' '}
              contributors.
            </p>
          </div>

          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-white">Regional Data Documentation</h3>
            <div className="space-y-2">
              {[
                { region: 'United States', url: 'https://doc.wepp.cloud/us-data.html' },
                { region: 'Europe', url: 'https://doc.wepp.cloud/eu-data.html' },
                { region: 'Australia', url: 'https://doc.wepp.cloud/au-data.html' },
                { region: 'Earth', url: 'https://doc.wepp.cloud/earth-data.html' },
              ].map((item) => (
                <div key={item.region} className="flex items-center gap-2">
                  <Globe className="h-4 w-4 text-slate-400" aria-hidden="true" />
                  <a
                    href={item.url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-sm text-sky-300 transition hover:text-sky-200"
                  >
                    {item.region}
                  </a>
                </div>
              ))}
            </div>
          </div>
        </motion.div>
      </section>

      <section className="bg-[#030712] px-4 py-16 sm:px-6 lg:px-12">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.3 }}
          transition={{ duration: 0.6, ease: 'easeOut' }}
          className="mx-auto max-w-4xl space-y-4"
        >
          <h2 className="text-center text-2xl font-semibold text-white sm:text-3xl">
            Legal Disclaimer
          </h2>
          <div className="rounded-xl border border-white/10 bg-slate-900/40 p-6 sm:p-8">
            <p className="text-sm leading-relaxed text-slate-300">
              THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY
              EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
              OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT
              SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
              INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED
              TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR
              BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
              CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY
              WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH
              DAMAGE.
            </p>
          </div>
        </motion.div>
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

function renderHelpIcon(icon: HelpResource['icon']) {
  if (icon === 'zap') {
    return <Zap className="h-6 w-6 text-sky-300" aria-hidden="true" />
  }
  if (icon === 'youtube') {
    return (
      <img
        src="/weppcloud/static/images/youtube.png"
        alt="YouTube"
        className="h-6 w-6 rounded-md object-cover"
      />
    )
  }
  return (
    <svg viewBox="0 0 24 24" className="h-6 w-6 text-slate-200" aria-hidden="true">
      <path
        fill="currentColor"
        fillRule="evenodd"
        clipRule="evenodd"
        d="M12 3.2C7.0275 3.2 3 7.2275 3 12.2C3 16.1825 5.57625 19.5463 9.15375 20.7388C9.60375 20.8175 9.7725 20.5475 9.7725 20.3113C9.7725 20.0975 9.76125 19.3888 9.76125 18.635C7.5 19.0513 6.915 18.0838 6.735 17.5775C6.63375 17.3188 6.195 16.52 5.8125 16.3063C5.4975 16.1375 5.0475 15.7213 5.80125 15.71C6.51 15.6988 7.01625 16.3625 7.185 16.6325C7.995 17.9938 9.28875 17.6113 9.80625 17.375C9.885 16.79 10.1213 16.3963 10.38 16.1713C8.3775 15.9463 6.285 15.17 6.285 11.7275C6.285 10.7488 6.63375 9.93875 7.2075 9.30875C7.1175 9.08375 6.8025 8.16125 7.2975 6.92375C7.2975 6.92375 8.05125 6.6875 9.7725 7.84625C10.4925 7.64375 11.2575 7.5425 12.0225 7.5425C12.7875 7.5425 13.5525 7.64375 14.2725 7.84625C15.9938 6.67625 16.7475 6.92375 16.7475 6.92375C17.2425 8.16125 16.9275 9.08375 16.8375 9.30875C17.4113 9.93875 17.76 10.7375 17.76 11.7275C17.76 15.1813 15.6563 15.9463 13.6538 16.1713C13.98 16.4525 14.2613 16.9925 14.2613 17.8363C14.2613 19.04 14.25 20.0075 14.25 20.3113C14.25 20.5475 14.4188 20.8288 14.8688 20.7388C18.4238 19.5463 21 16.1713 21 12.2C21 7.2275 16.9725 3.2 12 3.2Z"
      />
    </svg>
  )
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
