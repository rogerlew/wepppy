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

import { cn } from '@/lib/utils'

const DEFAULT_RUN_DATA_PATH = './run-locations.json'
const RUN_DATA_URL = import.meta.env.VITE_RUN_DATA_URL ?? DEFAULT_RUN_DATA_PATH
const MAP_STYLE = 'https://basemaps.cartocdn.com/gl/positron-nolabels-gl-style/style.json'

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
    border: 'border-violet-600/30',
    glow: 'from-violet-100/40 via-violet-50/20 to-transparent',
    icon: 'bg-violet-100 text-violet-700',
    chip: 'bg-violet-50 text-violet-700 border border-violet-200',
  },
  sky: {
    border: 'border-sky-600/30',
    glow: 'from-sky-100/40 via-sky-50/20 to-transparent',
    icon: 'bg-sky-100 text-sky-700',
    chip: 'bg-sky-50 text-sky-700 border border-sky-200',
  },
  amber: {
    border: 'border-amber-500/30',
    glow: 'from-amber-100/40 via-amber-50/20 to-transparent',
    icon: 'bg-amber-100 text-amber-700',
    chip: 'bg-amber-50 text-amber-700 border border-amber-200',
  },
  emerald: {
    border: 'border-emerald-500/30',
    glow: 'from-emerald-100/40 via-emerald-50/20 to-transparent',
    icon: 'bg-emerald-100 text-emerald-700',
    chip: 'bg-emerald-50 text-emerald-700 border border-emerald-200',
  },
  lime: {
    border: 'border-lime-500/30',
    glow: 'from-lime-100/40 via-lime-50/20 to-transparent',
    icon: 'bg-lime-100 text-lime-700',
    chip: 'bg-lime-50 text-lime-700 border border-lime-200',
  },
  cyan: {
    border: 'border-cyan-500/30',
    glow: 'from-cyan-100/40 via-cyan-50/20 to-transparent',
    icon: 'bg-cyan-100 text-cyan-700',
    chip: 'bg-cyan-50 text-cyan-700 border border-cyan-200',
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
    logo: '/weppcloud/static/images/nasa-grantee-insignia-rgb.png',
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

export function AppLight() {
  const [data, setData] = useState<RunLocation[]>([])
  const [yearFilter, setYearFilter] = useState<string>('all')
  const [isLoading, setIsLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)
  const [panelOpen, setPanelOpen] = useState<boolean>(false)
  const [viewState, setViewState] = useState<MapViewState>(INITIAL_VIEW_STATE)
  const [appState] = useState<AppState>(() => (typeof window !== 'undefined' ? window.__WEPP_STATE__ ?? {} : {}))

  const isAuthenticated = Boolean(appState.user?.is_authenticated)
  const heroHeadline = 'Turning landscape data into watershed intelligence for planning and management'
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
      getFillColor: (d) => (d.has_sbs ? [109, 40, 217, 200] : [2, 132, 199, 200]),
      getLineColor: [255, 255, 255, 220],
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
      getColor: [30, 41, 59, 220],
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
      { label: 'Interfaces', href: '/weppcloud/interfaces/', primary: true },
      { label: 'Docs', href: 'https://doc.wepp.cloud' },
      { label: 'Research', href: 'https://forest.moscowfsl.wsu.edu/library/', external: true },
      {
        label: isAuthenticated ? 'My Runs' : 'Login',
        href: isAuthenticated ? '/weppcloud/runs/' : '/weppcloud/login/',
      },
    ],
    [isAuthenticated],
  )

  return (
    <div className="light-theme min-h-screen bg-white text-slate-800">
      {/* Hero Section - Clean government style */}
      <section id="hero" className="relative bg-white border-b border-gray-200">
        <div className="max-w-6xl mx-auto px-6 py-12 sm:py-16">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, ease: 'easeOut' }}
            className="space-y-6"
          >
            <div>
              <h1 className="text-2xl font-semibold text-slate-800">WEPPcloud</h1>
              <p className="text-sm text-slate-500">Water Erosion Prediction Project</p>
            </div>
            
            <h2 className="text-3xl sm:text-4xl font-semibold text-slate-900 max-w-2xl leading-tight">
              {heroHeadline}
            </h2>
            
            <p className="text-base text-slate-600 max-w-2xl leading-relaxed">
              WEPPcloud is an online interface for running WEPP (Water Erosion Prediction Project) Model. 
              Access tools, explore documentation, or review the latest watershed analytics.
            </p>

            <div className="flex flex-wrap gap-3 pt-2">
              {navItems.map((item) => (
                <a
                  key={item.label}
                  className={
                    item.primary
                      ? "inline-flex items-center px-5 py-2.5 text-sm font-medium border border-blue-600 bg-blue-600 text-white hover:bg-blue-700 hover:border-blue-700 transition-colors shadow-sm"
                      : "inline-flex items-center px-5 py-2.5 text-sm font-medium border border-slate-300 bg-white text-slate-700 hover:bg-slate-50 hover:border-slate-400 transition-colors"
                  }
                  href={item.href}
                  target={item.external ? '_blank' : undefined}
                  rel={item.external ? 'noreferrer' : undefined}
                >
                  {item.label}
                </a>
              ))}
            </div>
          </motion.div>
        </div>
      </section>

      {/* About Section */}
      <section id="about" className="bg-white px-4 py-12 sm:px-6 lg:px-12 border-b border-gray-200">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.2 }}
          transition={{ duration: 0.5, ease: 'easeOut' }}
          className="mx-auto max-w-4xl"
        >
          <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">About</h2>
          <h3 className="text-2xl font-semibold text-slate-900 mb-4">What is WEPPcloud?</h3>
          <p className="text-base leading-relaxed text-slate-600">
            WEPPcloud is an online interface for running WEPP (Water Erosion Prediction Project) Model. WEPP is a
            physically based erosion model built to replace the Universal Soil Loss Equation (USLE) model. The interface
            simplifies the acquisition and preparation of topography, soil, management, and climate inputs for WEPP.
          </p>
        </motion.div>
      </section>

      {/* Map Section */}
      <section id="map" className="bg-white px-4 py-12 sm:px-6 lg:px-12 border-b border-gray-200">
        <div className="mx-auto max-w-6xl space-y-8">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.2 }}
            transition={{ duration: 0.5, ease: 'easeOut' }}
          >
            <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">{mapEyebrow}</h2>
            <h3 className="text-2xl font-semibold text-slate-900 mb-2">{mapTitle}</h3>
            <p className="text-base text-slate-600 max-w-3xl">{mapSubtitle}</p>
            
            {/* Stats grid */}
            <div className="mt-6 grid gap-4 sm:grid-cols-3">
              <MetricCardLight label="Unique runs" value={aggregateStats.totalRuns} />
              <MetricCardLight label="Total hillslopes" value={aggregateStats.totalHillslopes} />
              <MetricCardLight
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
            initial={{ opacity: 0, y: 40 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.3 }}
            transition={{ duration: 0.6, ease: 'easeOut', delay: 0.1 }}
            className="relative border border-gray-300 bg-white shadow-sm"
          >
            <div className="relative h-[65vh] min-h-[520px] overflow-hidden">
              {/* Legend */}
              <div className="light-legend">
                <span className="light-legend-chip">
                  <span className="light-legend-dot bg-sky-600" />
                  Standard runs
                </span>
                <span className="light-legend-chip">
                  <span className="light-legend-dot bg-violet-600" />
                  Runs with SBS
                </span>
                <span className="light-legend-chip">
                  <span className="light-legend-dot bg-emerald-600" />
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
                  <div className="absolute inset-0 flex items-center justify-center bg-gray-100">
                    <p className="text-sm text-slate-500">Preparing map...</p>
                  </div>
                )}
              </div>

              <div className="absolute bottom-4 right-4 border border-gray-300 bg-white px-3 py-2 text-xs text-slate-600">
                Tip: Hold <span className="font-semibold text-slate-800">Ctrl</span> while scrolling to zoom the map.
              </div>

              <button
                type="button"
                className="light-control-toggle"
                aria-expanded={panelOpen}
                onClick={() => setPanelOpen((open) => !open)}
              >
                <span className="light-toggle-icon" aria-hidden="true" />
                <span>{panelOpen ? 'Close' : 'Filters'}</span>
              </button>

              <aside
                className={cn(
                  'absolute right-4 top-16 w-64 border border-gray-300 bg-white p-4 text-sm shadow-lg transition-all',
                  panelOpen ? 'pointer-events-auto opacity-100' : 'pointer-events-none opacity-0',
                )}
              >
                <h4 className="text-sm font-semibold text-slate-800 mb-3">Display options</h4>
                <label className="block text-xs font-medium uppercase tracking-wider text-slate-500 mb-1">
                  Year
                </label>
                <select
                  className="w-full border border-gray-300 bg-white px-3 py-2 text-sm text-slate-700 focus:border-slate-500 focus:outline-none"
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
                <p className="mt-2 text-xs text-slate-500">
                  Zoom to reveal run labels.
                </p>
              </aside>

              {statusMessage && (
                <div className="absolute bottom-4 left-4 border border-gray-300 bg-white px-3 py-2 text-xs text-slate-600">
                  {statusMessage}
                </div>
              )}
            </div>
          </motion.div>
        </div>
      </section>

      {/* Help & Resources */}
      <section className="bg-white px-4 py-12 sm:px-6 lg:px-12 border-b border-gray-200">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.25 }}
          transition={{ duration: 0.5, ease: 'easeOut' }}
          className="mx-auto max-w-4xl mb-8"
        >
          <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">Help</h2>
          <h3 className="text-2xl font-semibold text-slate-900 mb-2">Help & Resources</h3>
          <p className="text-base text-slate-600">
            Documentation, tutorials, and source code for WEPPcloud.
          </p>
        </motion.div>

        <div className="mx-auto max-w-4xl grid gap-4 sm:grid-cols-3">
          {HELP_RESOURCES.map((resource, index) => (
            <motion.a
              key={resource.title}
              href={resource.href}
              target="_blank"
              rel="noreferrer"
              className="flex flex-col p-5 border border-gray-200 bg-gray-50 hover:bg-gray-100 hover:border-gray-300 transition-colors"
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.2 }}
              transition={{ duration: 0.3, delay: index * 0.1 }}
            >
              <div className="mb-3 flex items-center gap-2 text-slate-700">
                {renderHelpIconLight(resource.icon)}
                <span className="font-semibold">{resource.title}</span>
              </div>
              <p className="flex-grow text-sm text-slate-600">{resource.description}</p>
              <span className="mt-4 text-xs font-medium text-slate-500 uppercase tracking-wide">
                Visit →
              </span>
            </motion.a>
          ))}
        </div>
      </section>

      {/* Points of Contact */}
      <section className="bg-white px-4 py-12 sm:px-6 lg:px-12 border-b border-gray-200">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.25 }}
          transition={{ duration: 0.5, ease: 'easeOut' }}
          className="mx-auto max-w-4xl mb-8"
        >
          <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">Team</h2>
          <h3 className="text-2xl font-semibold text-slate-900 mb-2">Points of Contact</h3>
          <p className="text-base text-slate-600">
            Connect with the researchers, engineers, and hydrologists who shape WEPPcloud.
          </p>
        </motion.div>

        <div className="mx-auto max-w-5xl grid gap-4 md:grid-cols-2">
          {CONTACTS.map((contact, index) => {
            const IconComponent = CONTACT_ICON_MAP[contact.icon]
            return (
              <motion.article
                key={contact.email}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, amount: 0.2 }}
                transition={{ duration: 0.4, delay: index * 0.05 }}
                className="flex flex-col p-5 border border-gray-200 bg-white"
              >
                <div className="flex items-start gap-4 mb-4">
                  <div className="flex h-10 w-10 items-center justify-center rounded bg-gray-100 text-slate-600">
                    <IconComponent className="h-5 w-5" aria-hidden="true" />
                  </div>
                  <div className="flex-1">
                    <p className="font-semibold text-slate-900">{contact.name}</p>
                    <p className="text-sm text-slate-600">{contact.title}</p>
                    <p className="text-sm text-slate-500">{contact.institution}</p>
                  </div>
                </div>
                <a
                  className="text-sm text-slate-700 hover:text-slate-900 mb-3"
                  href={`mailto:${contact.email}`}
                >
                  {contact.email}
                </a>
                <div className="flex flex-wrap gap-1.5">
                  {contact.expertise.map((item) => (
                    <span
                      key={item}
                      className="px-2 py-0.5 text-xs bg-gray-50 text-slate-600 border border-gray-200"
                    >
                      {item}
                    </span>
                  ))}
                </div>
              </motion.article>
            )
          })}
        </div>
      </section>

      {/* Affiliations */}
      <section className="bg-white px-4 py-12 sm:px-6 lg:px-12 border-b border-gray-200">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.25 }}
          transition={{ duration: 0.5, ease: 'easeOut' }}
          className="mx-auto max-w-4xl mb-8"
        >
          <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">Collaborators</h2>
          <h3 className="text-2xl font-semibold text-slate-900 mb-2">Affiliations and Collaborators</h3>
          <p className="text-base text-slate-600">
            WEPPcloud is made possible through collaborative partnerships across research institutions, government agencies, and international funding programs.
          </p>
        </motion.div>

        <div className="mx-auto max-w-5xl grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {AFFILIATIONS.map((affiliation, index) => (
            <motion.a
              key={affiliation.name}
              href={affiliation.link}
              target="_blank"
              rel="noreferrer"
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.2 }}
              transition={{ duration: 0.4, delay: index * 0.08 }}
              className="flex flex-col items-center p-6 border border-gray-200 bg-gray-50 hover:bg-gray-100 transition-colors"
            >
              <div className="flex h-16 w-full items-center justify-center mb-3">
                <img
                  src={affiliation.logo}
                  alt={affiliation.name}
                  className="max-h-16 w-auto object-contain"
                />
              </div>
              <p className="text-center text-xs text-slate-500">{affiliation.caption}</p>
            </motion.a>
          ))}
        </div>
      </section>

      {/* Sponsors */}
      <section className="bg-white px-4 py-12 sm:px-6 lg:px-12 border-b border-gray-200">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.25 }}
          transition={{ duration: 0.5, ease: 'easeOut' }}
          className="mx-auto max-w-4xl mb-8"
        >
          <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">Funding</h2>
          <h3 className="text-2xl font-semibold text-slate-900 mb-2">Sponsors</h3>
          <p className="text-base text-slate-600">
            WEPPcloud development is supported by grants from federal agencies, international research programs, and scientific funding bodies.
          </p>
        </motion.div>

        <div className="mx-auto max-w-5xl grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {SPONSORS.map((sponsor, index) => (
            <motion.a
              key={sponsor.name}
              href={sponsor.link}
              target="_blank"
              rel="noreferrer"
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.2 }}
              transition={{ duration: 0.4, delay: index * 0.08 }}
              className="flex flex-col items-center p-6 border border-gray-200 bg-white hover:bg-gray-50 transition-colors"
            >
              <div className="flex h-16 w-full items-center justify-center mb-3">
                <img
                  src={sponsor.logo}
                  alt={sponsor.name}
                  className="max-h-16 w-auto object-contain"
                />
              </div>
              <p className="text-center text-xs text-slate-500">{sponsor.caption}</p>
            </motion.a>
          ))}
        </div>
      </section>

      {/* Contributors */}
      <section className="bg-white px-4 py-12 sm:px-6 lg:px-12 border-b border-gray-200">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.25 }}
          transition={{ duration: 0.5, ease: 'easeOut' }}
          className="mx-auto max-w-4xl mb-8"
        >
          <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">Team</h2>
          <h3 className="text-2xl font-semibold text-slate-900 mb-2">Contributors</h3>
          <p className="text-base text-slate-600">
            WEPPcloud is the result of collaborative efforts from researchers, engineers, and scientists across multiple institutions.
          </p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.3 }}
          transition={{ duration: 0.4, ease: 'easeOut' }}
          className="mx-auto max-w-4xl flex flex-wrap items-center justify-center gap-2"
        >
          {CONTRIBUTORS.map((contributor) => (
            <span
              key={contributor}
              className="px-3 py-1.5 text-sm border border-gray-200 bg-gray-50 text-slate-700"
            >
              {contributor}
            </span>
          ))}
        </motion.div>
      </section>

      {/* Data Sources */}
      <section className="bg-white px-4 py-12 sm:px-6 lg:px-12 border-b border-gray-200">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.25 }}
          transition={{ duration: 0.5, ease: 'easeOut' }}
          className="mx-auto max-w-4xl mb-8"
        >
          <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">Credits</h2>
          <h3 className="text-2xl font-semibold text-slate-900 mb-2">Attributions and Data Sources</h3>
          <p className="text-base text-slate-600">
            WEPPcloud leverages open data, research-quality datasets, and mapping services from partners worldwide.
          </p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.3 }}
          transition={{ duration: 0.4, ease: 'easeOut' }}
          className="mx-auto max-w-4xl grid gap-8 sm:grid-cols-2"
        >
          <div>
            <h4 className="font-semibold text-slate-800 mb-2">Map Services</h4>
            <p className="text-sm text-slate-600">
              Basemap tiles ©{' '}
              <a
                href="https://www.openstreetmap.org/"
                target="_blank"
                rel="noreferrer"
                className="text-sky-700 hover:text-sky-800"
              >
                OpenStreetMap
              </a>{' '}
              contributors, ©{' '}
              <a
                href="https://carto.com/attributions"
                target="_blank"
                rel="noreferrer"
                className="text-sky-700 hover:text-sky-800"
              >
                CARTO
              </a>
              .
            </p>
            <p className="text-sm text-slate-600 mt-2">
              Hydrography flowlines:{' '}
              <a
                href="https://hydro.nationalmap.gov/arcgis/rest/services/nhd/MapServer/4/"
                target="_blank"
                rel="noreferrer"
                className="text-sky-700 hover:text-sky-800"
              >
                U.S. Geological Survey National Hydrography Dataset (NHD), Flowline - Small Scale
              </a>{' '}
              (
              <a
                href="http://nhdgeo.usgs.gov/metadata/nhd_high.htm"
                target="_blank"
                rel="noreferrer"
                className="text-sky-700 hover:text-sky-800"
              >
                metadata
              </a>
              ).
            </p>
          </div>

          <div>
            <h4 className="font-semibold text-slate-800 mb-2">Regional Data Documentation</h4>
            <div className="space-y-1">
              {[
                { region: 'United States', url: 'https://doc.wepp.cloud/us-data.html' },
                { region: 'Europe', url: 'https://doc.wepp.cloud/eu-data.html' },
                { region: 'Australia', url: 'https://doc.wepp.cloud/au-data.html' },
                { region: 'Earth', url: 'https://doc.wepp.cloud/earth-data.html' },
              ].map((item) => (
                <div key={item.region} className="flex items-center gap-2">
                  <Globe className="h-4 w-4 text-slate-400" aria-hidden="true" />
                  <a href={item.url} target="_blank" rel="noreferrer" className="text-sm text-sky-700 hover:text-sky-800">
                    {item.region}
                  </a>
                </div>
              ))}
            </div>
          </div>
        </motion.div>
      </section>

      {/* Legal Disclaimer */}
      <section className="bg-white px-4 py-12 sm:px-6 lg:px-12">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.3 }}
          transition={{ duration: 0.4, ease: 'easeOut' }}
          className="mx-auto max-w-4xl"
        >
          <h2 className="text-lg font-semibold text-slate-800 mb-4">Legal Disclaimer</h2>
          <div className="p-6 border border-gray-200 bg-gray-50">
            <p className="text-sm leading-relaxed text-slate-600">
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

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 px-4 py-6 sm:px-6">
        <div className="mx-auto max-w-4xl text-center text-sm text-slate-600">
          <p>© {new Date().getFullYear()} University of Idaho • USDA Forest Service</p>
        </div>
      </footer>
    </div>
  )
}

function MetricCardLight(props: {
  label: string
  value: number | string | null | undefined
  multiline?: boolean
}) {
  return (
    <div className="p-4 border border-gray-200 bg-white">
      <p className="text-xs font-medium uppercase tracking-wider text-slate-500 mb-1">{props.label}</p>
      <p
        className={cn(
          'text-2xl font-semibold text-slate-900 whitespace-pre-line',
          props.multiline && 'leading-tight text-xl',
        )}
      >
        {typeof props.value === 'number' ? props.value.toLocaleString() : props.value ?? '--'}
      </p>
    </div>
  )
}

function renderHelpIconLight(icon: HelpResource['icon']) {
  if (icon === 'zap') {
    return <Zap className="h-5 w-5 text-slate-600" aria-hidden="true" />
  }
  if (icon === 'youtube') {
    return (
      <img
        src="/weppcloud/static/images/youtube.png"
        alt="YouTube"
        className="h-5 w-5 rounded object-cover"
      />
    )
  }
  return (
    <svg viewBox="0 0 24 24" className="h-5 w-5 text-slate-600" aria-hidden="true">
      <path
        fill="currentColor"
        fillRule="evenodd"
        clipRule="evenodd"
        d="M12 3.2C7.0275 3.2 3 7.2275 3 12.2C3 16.1825 5.57625 19.5463 9.15375 20.7388C9.60375 20.8175 9.7725 20.5475 9.7725 20.3113C9.7725 20.0975 9.76125 19.3888 9.76125 18.635C7.5 19.0513 6.915 18.0838 6.735 17.5775C6.63375 17.3188 6.195 16.52 5.8125 16.3063C5.4975 16.1375 5.0475 15.7213 5.80125 15.71C6.51 15.6988 7.01625 16.3625 7.185 16.6325C7.995 17.9938 9.28875 17.6113 9.80625 17.375C9.885 16.79 10.1213 16.3963 10.38 16.1713C8.3775 15.9463 6.285 15.17 6.285 11.7275C6.285 10.7488 6.63375 9.93875 7.2075 9.30875C7.1175 9.08375 6.8025 8.16125 7.2975 6.92375C7.2975 6.92375 8.05125 6.6875 9.7725 7.84625C10.4925 7.64375 11.2575 7.5425 12.0225 7.5425C12.7875 7.5425 13.5525 7.64375 14.2725 7.84625C15.9938 6.67625 16.7475 6.92375 16.7475 6.92375C17.2425 8.16125 16.9275 9.08375 16.8375 9.30875C17.4113 9.93875 17.76 10.7375 17.76 11.7275C17.76 15.1813 15.6563 15.9463 13.6538 16.1713C13.98 16.4525 14.2613 16.9925 14.2613 17.8363C14.2613 19.04 14.25 20.0075 14.25 20.3113C14.25 20.5475 14.4188 20.8288 14.8688 20.7388C18.4238 19.5463 21 16.1713 21 12.2C21 7.2275 16.9725 3.2 12 3.2Z"
      />
    </svg>
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

export default AppLight
