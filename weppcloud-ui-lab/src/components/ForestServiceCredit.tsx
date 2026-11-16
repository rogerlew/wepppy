export function ForestServiceCredit() {
  return (
    <div className="mt-4 space-y-2 text-sm" data-forest-service-credit>
      <p>
        Optional Forest Service Basemap for project maps: {' '}
        <a className="underline" href="https://www.arcgis.com/home/item.html?id=2e1593463c30495e9c802098527e3d1b" rel="noreferrer">
          USDA, U.S. Forest Service
        </a>{' '}— Forest Service - Geospatial Office. Google Terrain remains the default.
      </p>
      <details>
        <summary className="cursor-pointer underline">Forest Service map use limitations</summary>
        <p className="mt-2">
          This map cannot establish ownership, legal boundaries, jurisdiction, or access rights.
          Obtain permission before entering private land and check public-land restrictions.
          For motor-vehicle access, consult official Motor Vehicle Use Maps or the Forest Service.
          Hazards may be absent. This map is unsuitable for navigation.
        </p>
      </details>
    </div>
  )
}
