// Example implementation for Affiliations section
// This shows how to structure the logos with grayscale filters

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
    logo: '/weppcloud/static/images/ui-main-horizontal.jpg',
    link: 'https://www.uidaho.edu/',
  },
  {
    name: 'European Union Horizon 2020',
    caption: "WEPPcloud EU has received funding from the European Union's Horizon 2020 research and innovation programme under grant agreement No 101003890.",
    logo: '/weppcloud/static/images/eu-horizon-2020-logo.png', // TODO: Add this logo
    link: 'https://cordis.europa.eu/project/id/101003890',
  },
  {
    name: 'Swansea University',
    caption: 'Gweddw Crefft Heb Ei Dawn - Technical Skill is Bereft Without Culture. Swansea University',
    logo: '/weppcloud/static/images/Swansea_University_logo.png',
    link: 'https://www.swansea.ac.uk/',
  },
  {
    name: 'USDA Forest Service',
    caption: 'Caring for the land and serving people. Rocky Mountain Research Station',
    logo: '/weppcloud/static/images/usfslogo.png',
    link: 'https://www.fs.usda.gov/rmrs/',
  },
  {
    name: 'UI Research Computing & Data Services',
    caption: 'WEPPcloud is proudly hosted by the University of Idaho Research Computing + Data Services.',
    logo: '/weppcloud/static/images/RCDS_Logo-horizontal.svg',
    link: 'https://www.uidaho.edu/research/computing',
  },
]

export function AffiliationsSection() {
  return (
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

      <div className="mx-auto mt-12 grid max-w-6xl gap-8 sm:grid-cols-2 lg:grid-cols-3">
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
                className="max-h-20 w-auto object-contain grayscale brightness-0 invert opacity-70 transition-all duration-300 group-hover:grayscale-0 group-hover:brightness-100 group-hover:invert-0 group-hover:opacity-100"
              />
            </div>
            <p className="mt-4 text-center text-xs text-slate-400 transition-colors group-hover:text-slate-300">
              {affiliation.caption}
            </p>
          </motion.a>
        ))}
      </div>
    </section>
  )
}

/* 
TAILWIND FILTER CLASSES EXPLAINED:
- grayscale: Makes the image grayscale (desaturated)
- brightness-0: Makes the image black
- invert: Inverts colors (black becomes white for dark theme)
- opacity-70: Reduces opacity to 70% for subtlety

On hover:
- grayscale-0: Removes grayscale (shows original colors)
- brightness-100: Restores normal brightness
- invert-0: Removes inversion (shows original colors)
- opacity-100: Full opacity

This creates a nice effect where logos appear muted/monochrome 
and "light up" with color on hover, fitting the dark theme.
*/
