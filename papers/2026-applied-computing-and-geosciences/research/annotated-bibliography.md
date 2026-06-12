# Annotated Bibliography for the WEPPcloud ACG 2026 Manuscript

Verification note: citation metadata and DOI/stable URLs were checked on 2026-06-12 using DOI landing pages, Crossref records, DOAJ records, and publisher or institutional pages where needed. Entries below are grouped by the nine research-question themes from `deep-research-prompt.md`. "Evidence type" names the kind of support the cited work presents, not the strength of its conclusions.

## 1. Annotated Bibliography

### 1. Production Web-Based Geoscience Modeling Platforms and Science Gateways

- **Lew, R., Dobre, M., Srivastava, A., Brooks, E. S., et al. (2022). "WEPPcloud: An online watershed-scale hydrologic modeling tool. Part I. Model description." Journal of Hydrology, 608, 127603. https://doi.org/10.1016/j.jhydrol.2022.127603**

  This is the direct predecessor for the manuscript. It describes WEPPcloud's watershed-scale hydrologic and erosion modeling workflow, online inputs, and decision-support use cases, especially for forested and post-fire watersheds.

  Relevance: This is the baseline citation for the introduction and for explaining what the proposed ACG paper adds. It supports the domain and model-description foundation, while the new manuscript should differentiate itself as a systems, architecture, and production-behavior successor.

  Evidence type: Model description and applied case use; limited production systems evidence.

- **Wilcox, A., Shayeghmoradi, M., Miller, S., Nesbitt, I., et al. (2026). "The arctic knowledge-based system: Science gateway integration for petascale arctic data processing and geospatial feature prediction." Applied Computing and Geosciences, 29, 100322. https://doi.org/10.1016/j.acags.2026.100322**

  This ACG paper introduces the Science Gateway component of the Arctic Knowledge-Based System for permafrost and Arctic geospatial prediction workflows. It emphasizes Kubernetes, Globus Data Transfer/Compute, Slurm, Parsl, Ray, JupyterHub-authored AI workflows, and deployment across institutional and cloud resources. The paper reports automated authentication and job orchestration between a K8s gateway and remote HPC resources, while researchers can author, modify, and dispatch specialized workflows from JupyterHub.

  Relevance: Strong related-work and venue-positioning citation for architecture-first geoscience platforms. It competes with the "science gateway plus container/HPC orchestration" part of the WEPPcloud story. The distinction should be framed carefully: A-KBS does include workflow and job orchestration, but the paper does not document a comparable fine-grained, domain-specific model task graph with persisted run-state transitions, queue-isolated legacy binaries, status-triggered UI updates, selective reruns, and treatment scenario fan-out.

  Evidence type: Architecture description and integration case study; roadmap and operational integration evidence.

- **Horsburgh, J. S., Morsy, M. M., Castronova, A. M., Goodall, J. L., et al. (2016). "HydroShare: Sharing Diverse Environmental Data Types and Models as Social Objects with Application to the Hydrology Domain." JAWRA Journal of the American Water Resources Association, 52(4), 873-889. https://doi.org/10.1111/1752-1688.12363**

  HydroShare frames hydrologic datasets and models as publishable, shareable "social objects" with metadata, collaboration, discovery, and access services. It focuses on data/model publication and collaboration rather than on direct production execution of long-running model binaries.

  Relevance: Useful for related work on portable research artifacts and model/data sharing. It supports the idea that run state should be treated as a research object, while contrasting with WEPPcloud's file-backed, fork-able, executable run directories.

  Evidence type: Platform design and community data/model-sharing case study.

- **Tarboton, D. G., Ames, D. P., Horsburgh, J. S., Goodall, J. L., et al. (2024). "HydroShare retrospective: Science and technology advances of a comprehensive data and model publication environment for the water science domain." Environmental Modelling & Software, 172, 105902. https://doi.org/10.1016/j.envsoft.2023.105902**

  This retrospective reviews HydroShare's evolution as water-science cyberinfrastructure, including publication workflows, metadata, app integrations, reproducible modeling, and community adoption. It gives a rare long-horizon view of platform sustainability and scientific-use patterns.

  Relevance: Important comparator for production evidence and platform maturity. It supports reviewer expectations that production platforms should report adoption, technology evolution, and reproducibility practices, but it does not replace WEPPcloud's queue-isolated execution and operational emergency-response case.

  Evidence type: Retrospective platform analysis, adoption evidence, and case examples.

- **Swain, N. R., Christensen, S. D., Snow, A. D., Dolder, H., et al. (2016). "A new open source platform for lowering the barrier for environmental web app development." Environmental Modelling & Software, 85, 11-26. https://doi.org/10.1016/j.envsoft.2016.08.003**

  This paper introduces Tethys Platform as a development and hosting environment for environmental web applications. It packages common services for mapping, data management, visualization, and deployment, with several water-resource examples.

  Relevance: A core comparator for the architecture and discussion sections. Tethys supports the argument that environmental web apps need shared infrastructure, while WEPPcloud contrasts as a bespoke production platform optimized around specific legacy-model execution and run-state contracts.

  Evidence type: Framework design and application case studies.

- **Kalyanam, R., Zhao, L., Song, C., Biehl, L., et al. (2019). "MyGeoHub-A sustainable and evolving geospatial science gateway." Future Generation Computer Systems, 94, 820-832. https://doi.org/10.1016/j.future.2018.02.005**

  MyGeoHub is a geospatial science gateway built on HUBzero for data sharing, model hosting, and collaborative research. The paper emphasizes sustainability, reusable geospatial building blocks, and the difficulty of keeping gateways useful as communities evolve.

  Relevance: Useful for production evidence and discussion of sustainability. It supports the need to report platform evolution and community workflows, while WEPPcloud can differentiate with production telemetry and incident-driven architecture choices.

  Evidence type: Platform case study with sustainability and usage discussion.

- **Krishnan, S., Crosby, C., Nandigam, V., Phan, M., et al. (2011). "OpenTopography: A Services Oriented Architecture for Community Access to LIDAR Topography." Proceedings of COM.Geo 2011. https://doi.org/10.1145/1999320.1999327**

  OpenTopography presents a service-oriented cyberinfrastructure for accessing and processing large lidar topography datasets co-located with compute resources. It is an early but still relevant geoscience example of web-accessible data plus processing services.

  Relevance: Foundational comparator for production geoscience web services. It supports the claim that co-locating data and computation matters, but WEPPcloud's contribution is model-run orchestration and decision-support workflows rather than topographic data delivery alone.

  Evidence type: Architecture case study and service deployment evidence.

- **Gorelick, N., Hancher, M., Dixon, M., Ilyushchenko, S., et al. (2017). "Google Earth Engine: Planetary-scale geospatial analysis for everyone." Remote Sensing of Environment, 202, 18-27. https://doi.org/10.1016/j.rse.2017.06.031**

  Google Earth Engine is the canonical production-scale geospatial analytics platform paper. It emphasizes massive public remote-sensing catalogs, server-side processing, and a browser-based programming model.

  Relevance: High-level platform comparator for the introduction and architecture sections. It competes only at the "web-scale geospatial compute" level; WEPPcloud is narrower but deeper in legacy physics-model execution, watershed run artifacts, and agency decision support.

  Evidence type: Platform architecture and broad adoption evidence.

- **Jalili, V., Afgan, E., Gu, Q., Clements, D., et al. (2020). "The Galaxy platform for accessible, reproducible and collaborative biomedical analyses: 2020 update." Nucleic Acids Research, 48(W1), W395-W402. https://doi.org/10.1093/nar/gkaa434**

  Galaxy is a mature cross-domain example of a browser-based scientific workflow and execution platform with public servers, tool integration, training materials, and remote job execution. Although biomedical, it is one of the strongest examples of how production workflow platforms report community scale and reproducibility.

  Relevance: Useful as a cross-domain contrast in related work or discussion. It supports reviewer expectations for usability, reproducibility, and adoption metrics, while WEPPcloud should avoid being judged as a general workflow platform by focusing on watershed decision support.

  Evidence type: Platform update with adoption, community, and framework-evolution evidence.

### 2. Microservices, Containerization, and Service-Oriented Architectures in Scientific Computing and Geosciences

- **Perret, J., Jessell, M. W., & Bétend, E. (2024). "An open-source, QGIS-based solution for digital geological mapping: GEOL-QMAPS." Applied Computing and Geosciences, 24, 100197. https://doi.org/10.1016/j.acags.2024.100197**

  GEOL-QMAPS presents an open-source QGIS-based workflow for digital geological mapping, including structured field data collection and geological interpretation support. It is not a production web platform, but it is a recent ACG precedent for applied geoscience software papers with concrete workflow value.

  Relevance: Useful for venue positioning and reviewer calibration. It supports the idea that ACG accepts implementation-centered geoscience software contributions when the workflow need and artifact are clear.

  Evidence type: Software description and applied geological mapping case study.

- **Gichamo, T. Z., Sazib, N. S., Tarboton, D. G., & Dash, P. (2020). "HydroDS: Data services in support of physically based, distributed hydrological models." Environmental Modelling & Software, 125, 104623. https://doi.org/10.1016/j.envsoft.2020.104623**

  HydroDS provides web-accessible hydrologic data services for preparing inputs to physically based distributed models. The services automate watershed, terrain, canopy, climate, and soil preprocessing through a Python client library.

  Relevance: Useful historical comparator for service-oriented hydrologic preprocessing. The public Hydro-DS repository's current `master` head is a license commit from 2019-06-03, so use this citation for the architectural precedent rather than as evidence of an actively maintained contemporary platform. WEPPcloud extends the pattern into full run orchestration, state persistence, and interactive analysis surfaces.

  Evidence type: Service architecture, model-setup evaluations, and time-savings evidence.

- **Schramm, M., Pebesma, E., Milenković, M., Foresta, L., et al. (2021). "The openEO API-Harmonising the Use of Earth Observation Cloud Services Using Virtual Data Cube Functionalities." Remote Sensing, 13(6), 1125. https://doi.org/10.3390/rs13061125**

  openEO defines a common API between clients and cloud Earth-observation backends, using virtual raster data cube concepts to hide provider differences. The paper demonstrates comparable workflows across multiple cloud platforms.

  Relevance: Important for the data model and discussion sections because it shows how declarative API contracts can decouple users from backend execution. WEPPcloud's query-engine and MCP routes are analogous in spirit but focused on per-run model archives rather than provider-scale EO processing.

  Evidence type: API design and multi-platform workflow demonstrations.

- **Zhou, N., Georgiou, Y., Pospieszny, M., Zhong, L., et al. (2021). "Container orchestration on HPC systems through Kubernetes." Journal of Cloud Computing, 10, 16. https://doi.org/10.1186/s13677-021-00231-z**

  This paper evaluates Kubernetes-style orchestration on HPC systems and discusses the mismatch between cloud-native, container-managed services and traditional batch-scheduled supercomputing environments. Its abstract and introduction explicitly note that conventional HPC workload managers lack microservice support, integrated container management, and flexible environment provisioning compared with cloud container orchestrators. It is not geoscience-specific, but it is directly relevant to scientific infrastructure.

  Relevance: Useful for architecture discussion around why HPC alone is a poor fit for responsive, on-demand web applications. It supports positioning WEPPcloud as a cloud-native decision-support service that combines containerized services, queue isolation, and interactive status feedback instead of relying on user-facing batch-HPC semantics.

  Evidence type: Systems evaluation and integration analysis.

- **Bauer, D., Chard, R., Babuji, Y., Chard, K., et al. (2024). "The Globus Compute Dataset: An open function-as-a-service dataset from the edge to the cloud." Future Generation Computer Systems, 153, 558-573. https://doi.org/10.1016/j.future.2023.12.007**

  The paper analyzes a dataset of Globus Compute function-as-a-service executions across edge, campus, cloud, and HPC resources. It provides evidence about distributed scientific function execution patterns.

  Relevance: Good comparator for production evidence and queue/execution telemetry. It supports the manuscript's need to quantify job behavior, queue waits, and workload distributions instead of relying only on architecture diagrams.

  Evidence type: Operational dataset analysis and performance/workload characterization.

- **Stern, C., Abernathey, R., Hamman, J., Wegener, R., et al. (2022). "Pangeo Forge: Crowdsourcing Analysis-Ready, Cloud Optimized Data Production." Frontiers in Climate, 3. https://doi.org/10.3389/fclim.2021.782909**

  Pangeo Forge is a platform for producing analysis-ready, cloud-optimized datasets using community recipes, cloud compute, and catalogs. It targets the operational burden of transforming provider archives into reusable scientific data products.

  Relevance: Relevant to data-interchange and architecture sections, especially the idea that production scientific systems need repeatable data contracts and catalogs. It supports WEPPcloud's Parquet/Arrow sidecar strategy, though for model-output archives rather than external EO feeds.

  Evidence type: Platform design, production workflow examples, and community-process evidence.

### 3. Job Orchestration and Queue-Based Isolation of Long-Running Scientific Model Executions

- **Deelman, E., Vahi, K., Juve, G., Rynge, M., et al. (2015). "Pegasus, a workflow management system for science automation." Future Generation Computer Systems, 46, 17-35. https://doi.org/10.1016/j.future.2014.10.008**

  Pegasus is a mature workflow management system for mapping scientific workflows onto distributed computing resources. It covers planning, execution, provenance, failure handling, and data movement.

  Relevance: Foundational comparison for job orchestration. It contrasts with WEPPcloud because WEPPcloud intentionally uses a simpler queue/dependency architecture tailored to interactive watershed modeling instead of a general DAG workflow manager.

  Evidence type: System architecture with multi-domain science workflow use cases.

- **Babuji, Y., Woodard, A., Li, Z., Katz, D. S., et al. (2019). "Parsl: Pervasive Parallel Programming in Python." Proceedings of HPDC 2019. https://doi.org/10.1145/3307681.3325400**

  Parsl provides a Python parallel scripting model for composing and executing tasks across laptops, clusters, clouds, and supercomputers. It is used for scientific workflows that need portable task graphs and backend abstraction.

  Relevance: Useful for framing the design tradeoff between general workflow engines and application-specific orchestration. WEPPcloud can cite Parsl as a mature alternative while justifying RQ/Redis around interactive user operations, run directories, and legacy binaries.

  Evidence type: Systems paper with benchmarks and application examples.

- **Radosevic, N., Duckham, M., Liu, G.-J., & Tao, Y. (2026). "Hydro KNIME: Scientific workflows for reproducible decision support in identifying suitable hydrological reference station sites." Applied Computing and Geosciences, 30, 100348. https://doi.org/10.1016/j.acags.2026.100348**

  Hydro KNIME uses KNIME workflows, optimization, and geospatial decision criteria to identify candidate hydrological reference station sites. It foregrounds reproducible scientific workflow composition in a hydrologic decision-support context.

  Relevance: Verified ACG precedent for hydrology workflow reproducibility. It supports the manuscript's reproducibility claims but contrasts with WEPPcloud's production queue isolation and per-run state artifacts.

  Evidence type: Workflow case study with decision-support evaluation.

- **Radosevic, N., Duckham, M., Liu, G.-J., & Sun, Q. (2020). "Solar radiation modeling with KNIME and Solar Analyst: Increasing environmental model reproducibility using scientific workflows." Environmental Modelling & Software, 132, 104780. https://doi.org/10.1016/j.envsoft.2020.104780**

  This paper wraps a solar radiation modeling workflow in KNIME to improve reproducibility and transparency. It demonstrates how explicit scientific workflow tools can make environmental model execution more auditable.

  Relevance: Supports the related-work thread on workflow provenance. WEPPcloud can contrast its run directory, job graph, and query catalog as a domain-specific reproducibility contract rather than a generic visual workflow artifact.

  Evidence type: Workflow reproducibility case study.

### 4. Cloud-Native and Columnar Geospatial Data Formats and Embedded Analytical Databases

- **Saeedan, M., & Eldawy, A. (2022). "Spatial parquet: A column file format for geospatial data lakes." Proceedings of ACM SIGSPATIAL 2022. https://doi.org/10.1145/3557915.3561038**

  Spatial Parquet extends Parquet concepts for geospatial data lake workloads and evaluates spatial indexing and query performance. It is a peer-reviewed precursor in the same columnar-geospatial design space as GeoParquet.

  Relevance: Strong support for the data model section. It supports WEPPcloud's choice of Parquet-like columnar interchange and highlights why spatial metadata, indexing, and predicate pushdown matter for model archives.

  Evidence type: Format design and benchmark evaluation.

- **Raasveldt, M., & Mühleisen, H. (2019). "DuckDB: An Embeddable Analytical Database." Proceedings of SIGMOD 2019. https://doi.org/10.1145/3299869.3320212**

  DuckDB is an embedded analytical database designed for in-process OLAP workloads, in contrast to server-oriented analytical databases. Its design emphasizes easy embedding and efficient analytical SQL over local or application-managed data.

  Relevance: Directly informs the query-engine and analytics service sections. It supports a defensible choice of DuckDB for read-only, bounded, per-run model-output analytics without introducing a heavyweight database service.

  Evidence type: Database systems demonstration and performance-oriented design evidence.

- **Lamb, A., Shen, Y., Heres, D., Chakraborty, J., et al. (2024). "Apache Arrow DataFusion: A Fast, Embeddable, Modular Analytic Query Engine." Companion of SIGMOD/PODS 2024. https://doi.org/10.1145/3626246.3653368**

  DataFusion is a modular analytical query engine built around Apache Arrow memory formats. The paper emphasizes embeddability, extensibility, and performance for specialized analytical systems.

  Relevance: Useful technical comparator for the query-engine discussion and Rust/Arrow ecosystem choices. It supports the idea that embedded analytical engines are now a serious substrate for domain-specific data services.

  Evidence type: Systems architecture and benchmark evidence.

- **Mahecha, M. D., Gans, F., Brandt, G., Christiansen, R., et al. (2020). "Earth system data cubes unravel global multivariate dynamics." Earth System Dynamics, 11, 201-234. https://doi.org/10.5194/esd-11-201-2020**

  This paper uses Earth system data cubes to analyze global multivariate dynamics across large spatiotemporal datasets. It demonstrates the scientific value of harmonized, analysis-ready, multidimensional data structures.

  Relevance: Supports the broader argument for self-describing analytical data structures. WEPPcloud should distinguish per-run Parquet sidecars and Arrow metadata from global Earth system cubes, but both rely on stable data contracts.

  Evidence type: Scientific case study using large data-cube analysis.

- **Zarr Developers. (2024). "Zarr Specification." Zenodo. https://doi.org/10.5281/zenodo.11320255**

  Zarr is a cloud-friendly chunked array specification widely used for multidimensional scientific arrays. This is a stable specification DOI rather than a peer-reviewed paper.

  Relevance: Supplemental citation for the data-format discussion, especially when contrasting array-oriented cloud formats with tabular/relational model-output formats. It should be cited sparingly because the WEPPcloud manuscript's primary data contract is Parquet/Arrow, not Zarr.

  Evidence type: Specification, not peer-reviewed evidence.

### 5. Wrapping or Modernizing Legacy Environmental Models for Web or Cloud Execution

- **Hut, R., Drost, N., van de Giesen, N., van Werkhoven, B., et al. (2022). "The eWaterCycle platform for open and FAIR hydrological collaboration." Geoscientific Model Development, 15, 5371-5390. https://doi.org/10.5194/gmd-15-5371-2022**

  eWaterCycle is a FAIR hydrological modeling platform that separates experiment code from model code. It exposes hydrological models through BMI-style Python interfaces, runs models inside software containers, supports multiple models and languages, and uses browser-accessed Jupyter notebooks plus supporting services for data, forcing, model execution, and result export.

  Relevance: Highest-priority addition because it is the closest verified comparator for containerized legacy hydrological models. It directly overlaps with WEPPcloud on model accessibility, containers, notebooks/web access, FAIR data, and model comparison, but differs in being research-notebook and FAIR-experiment oriented rather than an operational decision-support application with queue-isolated production workflows, status-triggered UI behavior, persisted run-state transitions, treatment scenario fan-out, and agency post-fire usage.

  Evidence type: Hydrological platform design, FAIR/reproducibility architecture, and multi-model case studies.

- **Tucker, G. E., Hutton, E. W. H., Piper, M. D., Campforts, B., et al. (2022). "CSDMS: a community platform for numerical modeling of Earth surface processes." Geoscientific Model Development, 15, 1413-1439. https://doi.org/10.5194/gmd-15-1413-2022**

  This paper describes the Community Surface Dynamics Modeling System as an interoperable Earth-surface modeling ecosystem. It covers model repositories and metadata, interface and ontology standards, language-bridging tools, Landlab, data-access components, and a Python-based execution/model-coupling framework.

  Relevance: Important background for the model-interoperability and wrapper discussion. It shows a mature community approach to reusable model components and coupling, while WEPPcloud should be framed as an operational platform for a specific decision-support model family and run-state contract rather than a general community model ecosystem.

  Evidence type: Community cyberinfrastructure and model-interoperability platform paper.

- **Hutton, E. W. H., Piper, M. D., & Tucker, G. E. (2020). "The Basic Model Interface 2.0: A standard interface for coupling numerical models in the geosciences." Journal of Open Source Software, 5(51), 2317. https://doi.org/10.21105/joss.02317**

  BMI 2.0 defines a standard interface for coupling numerical models in geoscience. It is central to CSDMS and underlies tools such as pymt and eWaterCycle that make models callable through common interfaces across languages and execution environments.

  Relevance: Useful when discussing why WEPPcloud does not present itself as a general model-coupling framework. BMI/pymt-style ecosystems support reusable model interoperability; WEPPcloud instead wraps established WEPP-family workflows into an application-specific orchestration, persistence, and decision-support contract.

  Evidence type: Software/interface standard paper.

- **Rajib, M. A., Merwade, V., Kim, I. L., Zhao, L., et al. (2016). "SWATShare - A web platform for collaborative research and education through online sharing, simulation and visualization of SWAT models." Environmental Modelling & Software, 75, 498-512. https://doi.org/10.1016/j.envsoft.2015.10.032**

  SWATShare provides web-based sharing, simulation, calibration, and visualization of SWAT models. It is one of the closest hydrologic-model platform comparators because it combines model instances, online execution, and collaboration.

  Relevance: Important competitor/comparator for architecture, scenario management, and related work. WEPPcloud should differentiate on post-fire decision support, run cloning, queue isolation, and production behavior under burst demand.

  Evidence type: Platform case study with model execution and visualization examples.

- **Bole, N., Bandyopadhyay, A., & Bhadra, A. (2024). "PixelSWAT: A user-friendly ArcGIS tool for preparing inputs to run SWAT in a distributed discretization scheme." Applied Computing and Geosciences, 23, 100175. https://doi.org/10.1016/j.acags.2024.100175**

  PixelSWAT is an ArcGIS Python toolbox for preparing gridded watershed and stream inputs for SWAT. It targets the friction of adapting legacy hydrologic-model inputs to gridded weather and distributed discretization.

  Relevance: Verified ACG precedent for hydrologic-model support software. It supports the manuscript's argument that model-support tools are publishable in ACG, while WEPPcloud's contribution is full production execution architecture rather than input preparation alone.

  Evidence type: Software tool and hydrologic case study.

- **Dile, Y. T., Daggupati, P., George, C., Srinivasan, R., et al. (2016). "Introducing a new open source GIS user interface for the SWAT model." Environmental Modelling & Software, 85, 129-138. https://doi.org/10.1016/j.envsoft.2016.08.004**

  QSWAT provides an open-source GIS interface for SWAT model setup, replacing dependence on proprietary desktop GIS tools. It focuses on usability and model preparation rather than production web execution.

  Relevance: Useful for the legacy-model modernization section. It supports the recurring pattern that environmental models require substantial wrapper and input tooling, which WEPPcloud extends into web-native execution and analysis.

  Evidence type: Software description and case demonstration.

- **Lin, Q., & Zhang, D. (2021). "A scalable distributed parallel simulation tool for the SWAT model." Environmental Modelling & Software, 144, 105133. https://doi.org/10.1016/j.envsoft.2021.105133**

  This paper presents a distributed parallel simulation tool for SWAT to improve execution scalability. It addresses compute scaling for repeated model runs and large simulation workloads.

  Relevance: Directly relevant to performance substrate and scenario fan-out. It competes on scalable model execution, but WEPPcloud can differentiate by emphasizing interactive production queues, scenario cloning, and agency workflows rather than parallelizing one model family.

  Evidence type: Benchmark-oriented systems evaluation.

- **Elliot, W. J. (2004). "WEPP Internet Interfaces for Forest Erosion Prediction." JAWRA Journal of the American Water Resources Association, 40(2), 299-309. https://doi.org/10.1111/j.1752-1688.2004.tb01030.x**

  This foundational paper describes early web interfaces that made WEPP forest erosion prediction accessible through Internet tools. It establishes a long history of wrapping WEPP for practitioners.

  Relevance: Important historical citation for introduction and related work. It supports the claim that WEPP web tooling is mature and user-facing, while the ACG paper's novelty lies in production-scale watershed architecture after decades of interface evolution.

  Evidence type: Tool description and applied interface examples.

- **Hernandez, M., Nearing, M. A., Al-Hamdan, O. Z., Pierson, F. B., et al. (2017). "The Rangeland Hydrology and Erosion Model: A Dynamic Approach for Predicting Soil Loss on Rangelands." Water Resources Research, 53(11), 9368-9391. https://doi.org/10.1002/2017WR020651**

  RHEM is a process-based model for predicting runoff and erosion on rangelands, and it underlies a web decision-support tool used by land managers. The model paper emphasizes rangeland-specific parameterization and dynamic erosion prediction.

  Relevance: Useful for post-fire and legacy-model context, especially where rangeland decision-support tooling is discussed. It contrasts with WEPPcloud's watershed-scale, forest/post-fire focus.

  Evidence type: Model development and validation evidence.

### 6. Large-Scale Interactive Web Geovisualization of Model Output

- **Gardner Oldemeyer, T. A., & Russell, G. P. (2022). "Interactive web mapping tools and custom subsurface cross-sections for interdisciplinary geologic investigation." Applied Computing and Geosciences, 13, 100077. https://doi.org/10.1016/j.acags.2021.100077**

  This ACG paper describes Python geospatial analytics, web mapping, and custom subsurface cross-section generation for geologic investigation. It demonstrates a web platform that turns complex subsurface data into stakeholder-facing visual products.

  Relevance: Verified ACG visualization precedent. It supports a GL-Dashboard/visual analytics section by showing that interactive geoscience web visualization is squarely in ACG scope, while WEPPcloud can differentiate on watershed model-output scale and scenario comparison.

  Evidence type: Software case study and stakeholder visualization workflow.

- **Zhang, J., Que, X., Madhikarmi, B., Hazen, R. M., et al. (2024). "Using a 3D heat map to explore the diverse correlations among elements and mineral species." Applied Computing and Geosciences, 21, 100154. https://doi.org/10.1016/j.acags.2024.100154**

  This paper presents a 3D heat-map visualization approach for exploring correlations between elements and mineral species. It is an ACG example of interactive visualization as a scientific-analysis contribution.

  Relevance: Useful for visualization related work and ACG precedent. It supports the manuscript's claim that visual analytics surfaces can be part of the scientific contribution, provided they are grounded in domain tasks.

  Evidence type: Visualization method and exploratory data-analysis examples.

- **Wang, Y. (2019). "Deck.gl: Large-scale Web-based Visual Analytics Made Easy." arXiv preprint. https://doi.org/10.48550/arXiv.1910.08865**

  This preprint describes deck.gl, a GPU/WebGL framework for large web-based visual analytics. It discusses design goals and real-world applications for rendering large spatial datasets interactively.

  Relevance: Supplemental citation for GL-Dashboard implementation choices. It should be labeled as a preprint if cited, but it directly supports the need for WebGL/deck.gl-style rendering once Leaflet-style interfaces become insufficient.

  Evidence type: Preprint with design discussion and application examples; not peer-reviewed.

- **Koylu, C., Tian, G., & Windsor, M. (2023). "Flowmapper.org: a web-based framework for designing origin-destination flow maps." Journal of Maps, 19(1). https://doi.org/10.1080/17445647.2021.1996479**

  Flowmapper.org is a web framework for interactive origin-destination flow mapping. It focuses on cartographic design and web interaction for movement data.

  Relevance: Useful as a web geovisualization comparator, especially for map interaction and stakeholder-facing spatial analytics. It supports WEPPcloud's need for web-native visualization but is not a model-output platform.

  Evidence type: Tool description and mapping examples.

- **Nygren, O., Calle, M., Gonzales-Inca, C., Kasvi, E., et al. (2024). "Automated geovisualization of flood disaster impacts in the global South cities with open geospatial data sets and ICEYE SAR flood data." International Journal of Disaster Risk Reduction, 103, 104319. https://doi.org/10.1016/j.ijdrr.2024.104319**

  This paper automates geospatial data processing and visualization of flood impacts using open geospatial data and SAR flood data. It shows how geovisualization workflows can support disaster risk communication.

  Relevance: Useful for the post-fire emergency-response framing and visualization sections. It supports the value of automated, decision-oriented geovisualization for hazards, while WEPPcloud's contribution is erosion/hydrology modeling rather than flood extent mapping.

  Evidence type: Disaster case study and automated geovisualization workflow.

### 7. Scenario Management and Ensemble Run Management

- **Stroud Water Research Center. (2017). "Model My Watershed." WikiWatershed software. https://wikiwatershed.org/model/**

  Model My Watershed is a public-facing watershed-modeling web application for analyzing land use and soil data, modeling stormwater runoff and water-quality impacts, and comparing conservation or development scenarios. The official citation guidance cites it as software rather than as a peer-reviewed systems paper; peer-reviewed publications around the tool primarily emphasize education and watershed learning outcomes.

  Relevance: Useful audience and scenario-management comparator because it overlaps with WEPPcloud on watershed web modeling and conservation/development scenario comparison. WEPPcloud should differentiate on physics-based erosion/hydrology execution, file-backed run artifacts, queue-isolated long-running jobs, treatment scenario fan-out, and operational post-fire decision support.

  Evidence type: Verified software/tool documentation, not peer-reviewed platform architecture evidence.

- **Alyaev, S., Ivanova, S., Holsaeter, A., Bratvold, R. B., & Bendiksen, M. (2021). "An interactive sequential-decision benchmark from geosteering." Applied Computing and Geosciences, 12, 100072. https://doi.org/10.1016/j.acags.2021.100072**

  This ACG paper presents a web-based decision-support benchmark for geosteering decisions under uncertainty. Users make sequential decisions, simulated measurements update ensembles, and the system compares human and algorithmic decisions.

  Relevance: Verified ACG precedent for interactive model-based decision benchmarks. It supports the scenario/decision-support section and shows that ACG accepts systems tied to measurable user decision tasks.

  Evidence type: Interactive experiment, participant comparison, and benchmark case.

- **Cheraghi, Y., Alyaev, S., Bratvold, R. B., Hong, A., et al. (2025). "Analyzing expert decision-making in geosteering: Statistical insights from a large-scale controlled experiment." Applied Computing and Geosciences, 26, 100237. https://doi.org/10.1016/j.acags.2025.100237**

  This follow-on ACG paper analyzes expert geosteering decisions from a large controlled experiment and associated dataset. It reports statistical insights into decision-making behavior under uncertainty.

  Relevance: Useful for reviewer calibration around production/user evidence. It supports using measured interaction data to strengthen a platform paper, and it suggests WEPPcloud should report real usage and scenario-run behavior where available.

  Evidence type: Controlled experiment and statistical analysis of user decisions.

- **Hadka, D., Herman, J., Reed, P., & Keller, K. (2015). "An open source framework for many-objective robust decision making." Environmental Modelling & Software, 74, 114-129. https://doi.org/10.1016/j.envsoft.2015.07.014**

  This paper introduces Rhodium, a Python framework for robust decision making under uncertainty using many-objective optimization and exploratory analysis. It is not a web platform, but it formalizes scenario exploration and policy robustness workflows.

  Relevance: Useful for scenario-management related work. It supports the general need for ensembles and scenario exploration, while WEPPcloud's scenario contribution is operational cloning, selective reruns, and comparison for land-management treatments.

  Evidence type: Framework description with computational examples.

- **Kwakkel, J. H. (2017). "The Exploratory Modeling Workbench: An open source toolkit for exploratory modeling, scenario discovery, and (multi-objective) robust decision making." Environmental Modelling & Software, 96, 239-250. https://doi.org/10.1016/j.envsoft.2017.06.054**

  The Exploratory Modeling Workbench supports running many computational experiments, identifying uncertainty combinations, and evaluating policies under deep uncertainty. It integrates with existing models rather than replacing them.

  Relevance: Useful for distinguishing "scenario analytics" from "scenario operations." WEPPcloud's Omni scenarios should be positioned as production run management and treatment-comparison infrastructure, not as a general robust-decision framework.

  Evidence type: Software framework and exploratory modeling demonstrations.

- **Barnhart, K. R., Hutton, E. W. H., Tucker, G. E., Gasparini, N. M., et al. (2020). "Short communication: Landlab v2.0: a software package for Earth surface dynamics." Earth Surface Dynamics, 8, 379-397. https://doi.org/10.5194/esurf-8-379-2020**

  Landlab is a Python toolkit for assembling Earth-surface process models from reusable components. It supports experimentation with model structures and coupled processes.

  Relevance: Useful as a contrast to WEPPcloud's approach to legacy physics binaries. Landlab supports modular modeling, while WEPPcloud focuses on operationalizing established models and workflows for decision users.

  Evidence type: Software package description and example model components.

### 8. LLM and Agent Interfaces to Scientific Data Services

- **Zhang, J., Clairmont, C., Que, X., Li, W., et al. (2025). "Streamlining geoscience data analysis with an LLM-driven workflow." Applied Computing and Geosciences, 25, 100218. https://doi.org/10.1016/j.acags.2024.100218**

  This verified ACG paper builds an LLM-driven workflow around the Mindat API, mineral co-occurrence analysis, and heat-map visualization. It uses prompt-engineered supervisor/action agents to translate natural language into geoscience data-analysis tasks.

  Relevance: Strong precedent for WEPPcloud's secondary MCP/agent-access theme. It supports the idea that agent interfaces can be publishable in ACG, but WEPPcloud should keep LLM routes secondary to production architecture unless the agent workflow is evaluated.

  Evidence type: Workflow implementation and use-case demonstrations.

- **Ma, X., Ralph, J., Zhang, J., Que, X., et al. (2024). "OpenMindat: Open and FAIR mineralogy data from the Mindat database." Geoscience Data Journal, 11(1), 94-105. https://doi.org/10.1002/gdj3.204**

  OpenMindat describes FAIR access to mineralogy data from Mindat, including data publication and API-oriented reuse. It provides the data-service substrate for later Mindat LLM workflows.

  Relevance: Useful for data-service and agent-access framing. It supports the claim that machine-readable, FAIR APIs are prerequisites for reliable scientific agents.

  Evidence type: Data-service description and FAIR data publication evidence.

- **Zhang, Y., Wang, Z., He, Z., Li, J., et al. (2024). "BB-GeoGPT: A framework for learning a large language model for geographic information science." Information Processing & Management, 61(5), 103808. https://doi.org/10.1016/j.ipm.2024.103808**

  BB-GeoGPT presents a GIScience-oriented large language model framework. It addresses domain adaptation and performance for geographic information tasks.

  Relevance: Useful as background, not as a direct platform comparator. It supports a discussion of geoscience/GIS LLM capability, while WEPPcloud's agent route should emphasize bounded tools and authoritative model archives rather than model training.

  Evidence type: Model/framework evaluation.

- **Hadid, A., Chakraborty, T., & Busby, D. (2024). "When geoscience meets generative AI and large language models: Foundations, trends, and future challenges." Expert Systems. https://doi.org/10.1111/exsy.13654**

  This review surveys generative AI and LLM trends for geoscience applications, including opportunities and risks. It provides high-level context for responsible LLM use in geoscience workflows.

  Relevance: Useful for discussion risks around MCP/LLM access. It supports caution about reliability, hallucination, and domain grounding, which reinforces WEPPcloud's bounded JSON-query and tool-facing design.

  Evidence type: Review article.

### 9. Post-Fire Erosion/Hydrology Decision-Support Tooling

- **Robichaud, P. R., Elliot, W. J., Pierson, F. B., Hall, D. E., & Moffet, C. A. (2007). "Predicting postfire erosion and mitigation effectiveness with a web-based probabilistic erosion model." CATENA, 71(2), 229-241. https://doi.org/10.1016/j.catena.2007.03.003**

  This ERMiT paper presents a web-based probabilistic post-fire erosion model built on WEPP technology. It estimates erosion and mitigation effectiveness under variability in rainfall, soil burn severity, and soil properties.

  Relevance: Foundational post-fire decision-support citation. It supports WEPPcloud's BAER/post-fire lineage and provides a contrast between hillslope probabilistic tools and watershed-scale, scenario-rich cloud workflows.

  Evidence type: Tool description, probabilistic modeling, and post-fire decision-support case.

- **Robichaud, P. R., & Ashmun, L. E. (2013). "Tools to aid post-wildfire assessment and erosion-mitigation treatment decisions." International Journal of Wildland Fire, 22(1), 95-105. https://doi.org/10.1071/WF11162**

  This paper reviews tools developed for post-wildfire assessment and erosion-mitigation treatment decisions, including prediction models, research syntheses, field methods, databases, and cost-benefit spreadsheets. It explicitly frames internet delivery as a way to disseminate and update science-based decision tools.

  Relevance: Key related-work citation for BAER workflows and the applied decision-support gap. It supports the manuscript's argument that production-ready tools matter to post-fire management.

  Evidence type: Review/synthesis of decision-support tools and operational use.

- **Staley, D. M., Negri, J. A., Kean, J. W., Laber, J. L., et al. (2017). "Prediction of spatially explicit rainfall intensity-duration thresholds for post-fire debris-flow generation in the western United States." Geomorphology, 278, 149-162. https://doi.org/10.1016/j.geomorph.2016.10.019**

  This paper develops spatially explicit rainfall intensity-duration thresholds for post-fire debris-flow generation. The methods underpin emergency hazard assessments for recently burned watersheds.

  Relevance: Important adjacent post-fire hazard-decision literature. It contrasts with WEPPcloud because debris-flow threshold assessment is not the same as erosion/hydrology scenario modeling, but the operational emergency-response audience overlaps.

  Evidence type: Statistical model development and validation against post-fire debris-flow observations.

- **Oakley, N. S., Liu, T., McGuire, L. A., Simpson, M., et al. (2023). "Toward Probabilistic Post-Fire Debris-Flow Hazard Decision Support." Bulletin of the American Meteorological Society, 104(9), E1587-E1605. https://doi.org/10.1175/BAMS-D-22-0188.1**

  This paper proposes probabilistic post-fire debris-flow decision-support tools that couple high-resolution ensemble precipitation forecasts with debris-flow likelihood and volume models. It focuses on uncertainty communication and impact-based decision support.

  Relevance: High-value recent post-fire decision-support citation. It supports the manuscript's framing around emergency-response demand and probabilistic hazard workflows, while WEPPcloud should distinguish its erosion-treatment and watershed scenario focus.

  Evidence type: Prototype decision-support workflow and ensemble case analysis.

- **Foltz, R. B., Robichaud, P. R., & Rhee, H. (2009). "A synthesis of post-fire road treatments for BAER teams: methods, treatment effectiveness, and decision making tools for rehabilitation." USDA Forest Service General Technical Report RMRS-GTR-228. https://doi.org/10.2737/RMRS-GTR-228**

  This synthesis compiles road rehabilitation methods, treatment effectiveness, and decision tools for BAER teams. It is a stable government technical report rather than a journal article, but it is central to the applied post-fire decision ecosystem.

  Relevance: Useful background for roads and BAER operational context if the WEPPcloud manuscript discusses road outputs or treatment workflows. Cite as supporting operational context, not as a peer-reviewed systems comparator.

  Evidence type: Technical synthesis and practitioner guidance.

## 2. Synthesis

### Most Cite-Worthy Entries

| Rank | Entry | Why it matters for the WEPPcloud manuscript |
| --- | --- | --- |
| 1 | Lew et al. 2022, WEPPcloud Part I | Direct predecessor; anchors the domain and defines what the new paper succeeds. |
| 2 | Hut et al. 2022, eWaterCycle | Closest verified comparator for FAIR, containerized, multi-model hydrological execution. |
| 3 | Wilcox et al. 2026, A-KBS | Closest ACG architecture precedent for science gateways, containers, HPC, and geospatial prediction. |
| 4 | Tarboton et al. 2024, HydroShare retrospective | Best long-horizon platform sustainability and adoption comparator in water science. |
| 5 | Swain et al. 2016, Tethys Platform | Core environmental web-app platform comparator; helps justify bespoke vs. framework paths. |
| 6 | Rajib et al. 2016, SWATShare | Closest hydrologic web execution/collaboration competitor. |
| 7 | Tucker et al. 2022, CSDMS | Mature community model-interoperability and coupling ecosystem comparator. |
| 8 | Robichaud et al. 2007, ERMiT | Foundational post-fire WEPP web decision-support citation. |
| 9 | Robichaud & Ashmun 2013, post-wildfire tools | Connects BAER decision workflows to internet-delivered science tools. |
| 10 | Gorelick et al. 2017, Google Earth Engine | Canonical production-scale geospatial analytics platform. |
| 11 | Stern et al. 2022, Pangeo Forge | Strong cloud-optimized data-production comparator for cataloged data contracts. |
| 12 | Raasveldt & Mühleisen 2019, DuckDB | Supports embedded analytics for per-run archives. |
| 13 | Saeedan & Eldawy 2022, Spatial Parquet | Peer-reviewed support for columnar geospatial file design. |
| 14 | Alyaev et al. 2021, geosteering benchmark | ACG precedent for interactive decision-support systems with measurable user behavior. |
| 15 | Oakley et al. 2023, probabilistic PFDF support | Recent post-fire hazard decision-support comparator with uncertainty communication. |

### Gaps the Manuscript Can Claim

The literature has many prototypes, data portals, model interfaces, and general science-gateway frameworks, but comparatively few papers document the production behavior of a long-lived geoscience modeling platform serving deadline-driven operational users. eWaterCycle is the strongest comparator for FAIR, containerized hydrological models, and A-KBS reports modern gateway/HPC workflow orchestration. The remaining gap is narrower but defensible: none of the verified comparators combine fine-grained application-level environmental-model task orchestration, queue isolation from interactive request paths, portable file-backed run artifacts, treatment scenario fan-out, status-triggered web UI behavior, and post-fire emergency-response usage in one production architecture.

There is also a gap around model-output contracts. Pangeo Forge, Earth system data cubes, Spatial Parquet, DuckDB, and DataFusion show strong movement toward cloud-optimized, columnar, and embedded analytical substrates, but they generally address provider archives, data lakes, or general query engines. A WEPPcloud paper can claim a narrower but useful contribution: per-run model outputs exposed through self-describing Parquet/Arrow metadata and bounded, declarative analytics over run-scoped archives.

Scenario work is well represented in robust decision-making frameworks, geosteering decision benchmarks, Model My Watershed, and SWAT-related platforms, but those comparators rarely discuss operational cloning, selective rerun, and storage/compute reuse for treatment scenarios initiated from one user action. The Omni scenario workflow can therefore be positioned as production scenario management rather than generic ensemble analysis or educational conservation-scenario comparison.

Finally, LLM/agent papers are emerging in geoscience, but the verified literature is thin on LLM agents operating against scientific modeling platforms through constrained tool contracts. The Zhang et al. Mindat workflow supports the ACG genre, but WEPPcloud should present MCP routes as a bounded access layer over authoritative run catalogs, not as an open-ended chatbot contribution.

### Positioning Risks

The largest direct risks are eWaterCycle and A-KBS. eWaterCycle already makes a strong FAIR hydrology claim around containerized multi-model execution, BMI interfaces, notebooks, model comparison, and reproducible experiments. A-KBS already makes an ACG architecture claim around a science gateway, containers, Kubernetes, HPC, Globus, and AI-assisted geospatial workflows. WEPPcloud should not claim novelty merely for using microservices, containers, or remote job execution. The differentiator should be the application-level orchestration contract: production hydrologic/erosion decision support, fine-grained model task sequencing, queue-isolated legacy binaries, file-backed run-state artifacts, scenario fan-out, and measured post-fire workload behavior.

HydroShare, SWATShare, and Model My Watershed are also close enough that reviewers may ask why WEPPcloud is not simply another hydrologic web platform. The answer should be concrete: HydroShare is primarily publication/collaboration infrastructure; SWATShare is SWAT-focused sharing and execution; Model My Watershed is public-facing stormwater/water-quality scenario software; WEPPcloud is a production watershed modeling service with a run-state contract, queue-isolated long-running erosion/hydrology jobs, scenario fan-out, and interactive analytics over model-output archives.

Google Earth Engine and Pangeo Forge may dwarf WEPPcloud in scale. They should be used as conceptual comparators for cloud data/analytics patterns, not as direct competitors. WEPPcloud's claim is not planetary-scale raster analytics; it is the architecture required to operate legacy physics models interactively for watershed decision users.

## 3. Unverified Leads

- **Core "Pangeo ecosystem" platform paper.** A peer-reviewed, DOI-bearing paper for the overall Pangeo platform was not identified in this pass. Use Stern et al. 2022 on Pangeo Forge as the verified, citable Pangeo-family entry.
- **Kepler.gl platform paper.** Kepler.gl is widely used and relevant to geospatial visualization, but a peer-reviewed platform paper with DOI was not found. Use deck.gl as a clearly labeled preprint only if an implementation citation is needed.
- **GeoParquet formal peer-reviewed paper.** GeoParquet has stable project/specification URLs, but a peer-reviewed GeoParquet paper was not identified. Use Saeedan & Eldawy 2022 on Spatial Parquet for peer-reviewed geospatial-Parquet support and cite the GeoParquet specification separately only if required.
- **Model My Watershed technical architecture paper.** The official software citation and public documentation are verified, and education-focused papers exist, but a DOI-bearing systems architecture paper for Model My Watershed was not identified in this pass.
- **MCP-specific scientific modeling papers.** No peer-reviewed paper on Model Context Protocol interfaces to environmental modeling platforms was identified. Treat MCP as an implementation detail and cite broader LLM/agent and FAIR API literature instead.
