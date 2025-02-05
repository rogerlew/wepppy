from wepppy.nodb import Wepp, Climate, Watershed
from csv import DictWriter

run_urls = { "prefire": [
        "https://wepp.cloud/weppcloud/runs/mdobre-gutsy-candelabrum/disturbed9002/",
        "https://wepp.cloud/weppcloud/runs/mdobre-jutting-pun/disturbed9002/",
        "https://dev.wepp.cloud/weppcloud/runs/epizootic-damascene/portland-disturbed/",
        "https://wepp.cloud/weppcloud/runs/mdobre-benevolent-spirochete/reveg/",
        "https://wepp.cloud/weppcloud/runs/mdobre-tufted-journal/disturbed9002/",
        "https://wepp.cloud/weppcloud/runs/mdobre-sixteenth-souk/disturbed9002/",
        "https://wepp.cloud/weppcloud/runs/mdobre-negligent-adoration/disturbed9002/",
        "https://wepp.cloud/weppcloud/runs/mdobre-liberated-gentile/disturbed9002/",
        "https://wepp.cloud/weppcloud/runs/mdobre-forensic-ventricle/disturbed9002/",
        "https://wepp.cloud/weppcloud/runs/mdobre-aboriginal-glow/lt-wepp_bd16b69-snow/",
        "https://wepp.cloud/weppcloud/runs/mdobre-viviparous-bilingual/disturbed9002/",
        "https://wepp.cloud/weppcloud/runs/edible-fluidity/disturbed9002/",
        "https://wepp.cloud/weppcloud/runs/mdobre-lead-free-analyzer/disturbed9002/",
    ],
    "postfire": [
        "https://wepp.cloud/weppcloud/runs/mdobre-antagonistic-veterinarian/disturbed9002/",
        "https://wepp.cloud/weppcloud/runs/mdobre-hourly-vetch/disturbed9002/",
        "https://wepp.cloud/weppcloud/runs/mdobre-cohesive-quadrature/disturbed9002/",
        "https://wepp.cloud/weppcloud/runs/mdobre-suspended-self-discovery/portland-disturbed/",
        "https://wepp.cloud/weppcloud/runs/mdobre-urban-immunologist/reveg/",
        "https://wepp.cloud/weppcloud/runs/mdobre-screaming-tricolor/disturbed9002/",
        "https://wepp.cloud/weppcloud/runs/mdobre-unashamed-department/disturbed9002/",
        "https://wepp.cloud/weppcloud/runs/mdobre-inarguable-ultrasound/disturbed9002/",
        "https://wepp.cloud/weppcloud/runs/mdobre-forensic-ventricle/disturbed9002/",
        "https://wepp.cloud/weppcloud/runs/mdobre-consequential-innovativeness/disturbed9002/",
        "https://wepp.cloud/weppcloud/runs/mdobre-counterbalanced-platinum/disturbed9002/",
        "https://wepp.cloud/weppcloud/runs/mdobre-patented-toy/disturbed9002/",
        "https://wepp.cloud/weppcloud/runs/doctrinaire-firewater/disturbed9002/",
        "https://wepp.cloud/weppcloud/runs/mdobre-supposed-rebus/disturbed9002/",
    ]
}

writer = None

for scenario in run_urls:
    for url in run_urls[scenario]:
        print(url)
        run_id = url.split("/")[-3]
        print(run_id)
        wd = f'/geodata/weppcloud_runs/{run_id}'
        
        wepp = Wepp.getInstance(wd)
        climate = Climate.getInstance(wd)
        watershed = Watershed.getInstance(wd)
        
        climate_mode = str(climate.climate_mode)
        
        parameters = {
            "run_id": run_id,
            "cfg": wepp.config_stem,
            "scenario": scenario,
            "climate_mode": str(climate.climate_mode),
            "watershed_area": watershed.wsarea,
            "number_of_hillslopes": watershed.sub_n,
            "number_of_channels": watershed.chn_n,
            "pmet_kcb": wepp.pmet_kcb,
            "rst": wepp.snow_opts.rst,
            "kslast": wepp.kslast,
            "observed_start_year": climate.observed_start_year,
            "observed_end_year": climate.observed_end_year
        }
        
        if writer is None:
            writer = DictWriter(open('/geodata/share/roger/mdobre_parameters.csv', 'w'), fieldnames=parameters.keys())
            writer.writeheader()
            
        writer.writerow(parameters)
        