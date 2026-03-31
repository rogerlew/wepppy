# wcag_2.1_aa_compliance

Date: March 31, 2026
Scope reviewed: codebase templates/CSS/JS and provided delineation-page screenshot.
Standard target: WCAG 2.1 Level AA (includes Level A + Level AA criteria).

## Executive Summary
The application is **not WCAG 2.1 AA compliant** based on code-identifiable failures.

Primary failure themes:
1. Keyboard access gaps in custom controls (Level A).
2. Missing semantic role/name/state for custom dialogs and rich-text inputs (Level A).
3. Invalid template/document structure affecting parse reliability (Level A).
4. Focus indicators suppressed or not visually distinguishable (Level AA).
5. Contrast risks in header text styling visible in screenshot and code (Level AA).
6. Layout/content does not scale correctly at 200% zoom (Level AA).

## Confirmed Findings (A + AA)

### 1) Keyboard inoperable custom controls
- WCAG 2.1 A: **2.1.1 Keyboard**
- Evidence:
  - [`ws_deln.html:335`](/workdir/Culvert_web_app/culvert_app/templates/ws_deln.html:335) uses `span` close control with click behavior.
  - [`ws_deln.html:897`](/workdir/Culvert_web_app/culvert_app/templates/ws_deln.html:897) uses `span` close control in project modal.
  - Same pattern repeats in:
    - [`hydro_vuln_analysis.html:434`](/workdir/Culvert_web_app/culvert_app/templates/hydro_vuln_analysis.html:434)
    - [`hydro_vuln_analysis.html:1600`](/workdir/Culvert_web_app/culvert_app/templates/hydro_vuln_analysis.html:1600)
    - [`hydrogeo_vuln.html:404`](/workdir/Culvert_web_app/culvert_app/templates/hydrogeo_vuln.html:404)
    - [`hydrogeo_vuln.html:1721`](/workdir/Culvert_web_app/culvert_app/templates/hydrogeo_vuln.html:1721)
    - [`explore_files.html:379`](/workdir/Culvert_web_app/culvert_app/templates/explore_files.html:379)
    - [`analysis_dashboard.html:273`](/workdir/Culvert_web_app/culvert_app/templates/analysis_dashboard.html:273)
- Impact:
  - Close/exit actions are not guaranteed keyboard focusable/operable.

### 2) Custom dialogs missing robust programmatic semantics
- WCAG 2.1 A: **4.1.2 Name, Role, Value**
- Evidence:
  - Dialog containers are plain `div` elements without `role="dialog"` and `aria-modal="true"` in delineation page:
    - [`ws_deln.html:331`](/workdir/Culvert_web_app/culvert_app/templates/ws_deln.html:331) (`formDataModal`)
    - [`ws_deln.html:880`](/workdir/Culvert_web_app/culvert_app/templates/ws_deln.html:880) (`infoModal`)
    - [`ws_deln.html:893`](/workdir/Culvert_web_app/culvert_app/templates/ws_deln.html:893) (`projectModal`)
    - [`ws_deln.html:963`](/workdir/Culvert_web_app/culvert_app/templates/ws_deln.html:963) (`contactSupportModal`)
    - [`ws_deln.html:1156`](/workdir/Culvert_web_app/culvert_app/templates/ws_deln.html:1156) (`drawBoundaryModal`)
- Impact:
  - AT users may not get reliable modal context/role announcements.

### 3) Rich text input implemented with `contenteditable` without explicit textbox semantics
- WCAG 2.1 A: **4.1.2 Name, Role, Value** and **1.3.1 Info and Relationships**
- Evidence:
  - Support editor is `div contenteditable="true"`:
    - [`ws_deln.html:1053`](/workdir/Culvert_web_app/culvert_app/templates/ws_deln.html:1053)
    - [`hydro_vuln_analysis.html:1758`](/workdir/Culvert_web_app/culvert_app/templates/hydro_vuln_analysis.html:1758)
    - [`hydrogeo_vuln.html:1881`](/workdir/Culvert_web_app/culvert_app/templates/hydrogeo_vuln.html:1881)
    - [`analysis_dashboard.html:353`](/workdir/Culvert_web_app/culvert_app/templates/analysis_dashboard.html:353)
    - [`explore_files.html:563`](/workdir/Culvert_web_app/culvert_app/templates/explore_files.html:563)
- Impact:
  - Control role/name/value exposure is inconsistent for assistive tech.

### 4) Invalid parsing/DOM structure due nested full documents in templates
- WCAG 2.1 A: **4.1.1 Parsing**
- Evidence:
  - Files use `{% extends "base.html" %}` but still include `<!DOCTYPE html><html><head><body>`:
    - [`ws_deln.html:2`](/workdir/Culvert_web_app/culvert_app/templates/ws_deln.html:2), [`ws_deln.html:4`](/workdir/Culvert_web_app/culvert_app/templates/ws_deln.html:4)
    - [`hydro_vuln_analysis.html:2`](/workdir/Culvert_web_app/culvert_app/templates/hydro_vuln_analysis.html:2), [`hydro_vuln_analysis.html:3`](/workdir/Culvert_web_app/culvert_app/templates/hydro_vuln_analysis.html:3)
    - [`hydrogeo_vuln.html:2`](/workdir/Culvert_web_app/culvert_app/templates/hydrogeo_vuln.html:2)
    - [`project_dashboard.html:2`](/workdir/Culvert_web_app/culvert_app/templates/project_dashboard.html:2)
    - [`analysis_dashboard.html:2`](/workdir/Culvert_web_app/culvert_app/templates/analysis_dashboard.html:2)
    - [`explore_files.html:1`](/workdir/Culvert_web_app/culvert_app/templates/explore_files.html:1)
  - Invalid placement of hidden inputs in `<head>`:
    - [`ws_deln.html:62`](/workdir/Culvert_web_app/culvert_app/templates/ws_deln.html:62)
    - [`project_dashboard.html:31`](/workdir/Culvert_web_app/culvert_app/templates/project_dashboard.html:31)
- Impact:
  - Parsing ambiguity can degrade AT compatibility.

### 5) Delineation controls not fully keyboard focusable (from test + architecture)
- WCAG 2.1 A: **2.1.1 Keyboard**
- Evidence:
  - Your testing confirms keyboard-focus gaps on delineation controls.
  - Map control stack includes mouse-centric Leaflet/Folium plugins:
    - [`subroutine_basemap_generator.py:283`](/workdir/Culvert_web_app/culvert_app/static/visualization/subroutine_basemap_generator.py:283)
    - [`subroutine_basemap_generator.py:291`](/workdir/Culvert_web_app/culvert_app/static/visualization/subroutine_basemap_generator.py:291)
    - [`subroutine_basemap_generator.py:292`](/workdir/Culvert_web_app/culvert_app/static/visualization/subroutine_basemap_generator.py:292)
- Impact:
  - Critical map interactions can remain pointer-dependent.

### 6) Focus indicators removed/suppressed
- WCAG 2.1 AA: **2.4.7 Focus Visible**
- Evidence:
  - Focus outlines explicitly removed in nav/tool menu items:
    - [`base.css:922`](/workdir/Culvert_web_app/culvert_app/static/css/base.css:922)
    - [`base.css:925`](/workdir/Culvert_web_app/culvert_app/static/css/base.css:925)
    - [`base.css:1054`](/workdir/Culvert_web_app/culvert_app/static/css/base.css:1054)
    - [`base.css:1057`](/workdir/Culvert_web_app/culvert_app/static/css/base.css:1057)
  - Additional `outline: none` declarations:
    - [`project_dashboard.html:417`](/workdir/Culvert_web_app/culvert_app/templates/project_dashboard.html:417)
    - [`project_dashboard.html:490`](/workdir/Culvert_web_app/culvert_app/templates/project_dashboard.html:490)
    - [`base.css:1944`](/workdir/Culvert_web_app/culvert_app/static/css/base.css:1944)
    - [`base.css:2101`](/workdir/Culvert_web_app/culvert_app/static/css/base.css:2101)
- Impact:
  - Keyboard users may lose visible location/context while tabbing.

### 7) Contrast minimum risks in header text styling
- WCAG 2.1 AA: **1.4.3 Contrast (Minimum)**
- Evidence from code + screenshot:
  - Username color is bright blue:
    - [`base.css:75`](/workdir/Culvert_web_app/culvert_app/static/css/base.css:75) `#0080ff`
  - Header uses dark gradient background:
    - [`base.css:45`](/workdir/Culvert_web_app/culvert_app/static/css/base.css:45)
  - App title text uses semi-transparent white style:
    - [`base.css:95`](/workdir/Culvert_web_app/culvert_app/static/css/base.css:95) `#ffffff77`
- Quantified check (worst-case side of gradient):
  - `#0080ff` on `#004063` is about **2.89:1** (below 4.5:1 for normal-size text).
  - Semi-transparent title text over dark header area yields low/variable effective contrast.
- Impact:
  - Header text may fail AA contrast in portions of the gradient/screen states.

### 8) Content/layout fails to scale cleanly at 200% zoom
- WCAG 2.1 AA: **1.4.4 Resize Text**
- Evidence from screenshot + code:
  - Your 200% screenshot shows clipping/overlap and reduced usable content area.
  - Fixed viewport-constrained heights used in core layout:
    - [`base.css:1222`](/workdir/Culvert_web_app/culvert_app/static/css/base.css:1222) `.main-container { height: calc(100vh - 6rem); }`
    - [`base.css:1261`](/workdir/Culvert_web_app/culvert_app/static/css/base.css:1261) `.map-container { height/max-height: calc(100vh - 6rem); }`
    - [`base.css:1682`](/workdir/Culvert_web_app/culvert_app/static/css/base.css:1682) `.form-container { height/max-height: calc(100vh - 6rem); }`
  - Rigid two-column form/map split remains at desktop sizes:
    - [`base.css:1675`](/workdir/Culvert_web_app/culvert_app/static/css/base.css:1675) `.form-container { flex: 0 0 30%; }`
    - [`ws_deln.html:279`](/workdir/Culvert_web_app/culvert_app/templates/ws_deln.html:279) `col-md-3 form-container`
    - [`ws_deln.html:847`](/workdir/Culvert_web_app/culvert_app/templates/ws_deln.html:847) `col-md-9 map-container`
  - Header text is forced not to wrap/truncates:
    - [`base.css:77`](/workdir/Culvert_web_app/culvert_app/static/css/base.css:77) `white-space: nowrap`
    - [`base.css:99`](/workdir/Culvert_web_app/culvert_app/static/css/base.css:99) `white-space: nowrap`
    - [`base.css:100`](/workdir/Culvert_web_app/culvert_app/static/css/base.css:100) `overflow: hidden`
    - [`base.css:101`](/workdir/Culvert_web_app/culvert_app/static/css/base.css:101) `text-overflow: ellipsis`
- Impact:
  - At 200% zoom, users can lose text/context and practical access to controls/content without equivalent readability/function.

## Cross-check of Your Original Notes

1. Pages not keyboard navigable: **Supported** (A).
2. Delineation controls not all focusable: **Supported** (A).
3. ARIA labeling missing: **Supported in part** for custom dialogs/editor semantics (A).
4. 11pt font on delineation page: **Not automatically a fail by itself**.
   - At AA, size alone is not a criterion failure; failures depend on resize/reflow/contrast behavior.
5. Does not scale properly to 200%: **Supported** (AA, 1.4.4).

## Compliance Conclusion (Target: WCAG 2.1 AA)
Current state is **not WCAG 2.1 AA compliant**.

Blocking gaps include:
- multiple Level A failures (keyboard + semantics + parsing), and
- Level AA failures (focus visible, contrast minimum, and resize-text behavior at 200% zoom).
