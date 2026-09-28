const RISK = {
  critical: "Safety-critical — verify before acting",
  warn: "Requires review",
};

export const DEMO_CONVOS = [
  {
    id: "c1",
    title: "Ventilation shaft collapse risk assessment",
    alert: true,
    messages: [
      {
        role: "user",
        text: "Assess ventilation adequacy at the Sector 4B shaft face during active blasting — are we within code?",
      },
      {
        role: "assistant",
        text:
          "No — Sector 4B airflow is running roughly **18% below** the NFPA/code minimum during peak blasting cycles, and it correlates with three recent near-miss reports.\n\n**Recommendation:** increase auxiliary duct capacity or stagger blasting with ventilation ramp-up, and re-route ducting so it doesn't obstruct NATM primary support clearances per the design guideline.",
        riskLevel: RISK.critical,
        steps: [
          "Retrieved 12 passages across Ventilation Safety Code, NATM Guideline, and the Sector 4B incident log.",
          "Cross-referenced measured face airflow against NFPA 502 and internal minimum-airflow thresholds.",
          "Flagged discrepancy: airflow ~18% below minimum during peak blasting windows.",
          "Checked ducting layout against NATM support clearance requirements before drafting recommendation.",
        ],
        sources: [
          {
            doc: "Tunnel Ventilation Safety Code 2024.pdf",
            section: "§4.2 Minimum Airflow",
            snippet:
              '"Auxiliary ventilation must maintain a minimum face airflow of 0.5 m³/s per m² cross-section during active blasting operations."',
          },
          {
            doc: "Incident Log - Sector 4B.xlsx",
            section: "Rows 218–224",
            snippet:
              "Three near-miss reports logged 03/12–03/18 citing reduced visibility and elevated CO readings at the shaft face.",
          },
          {
            doc: "NATM Design Guideline Rev. 4.pdf",
            section: "§7.1 Shaft Support",
            snippet: "Ventilation duct routing must not obstruct primary support installation clearances.",
          },
        ],
      },
    ],
  },
  {
    id: "c2",
    title: "NATM support spacing verification",
    alert: false,
    messages: [
      {
        role: "user",
        text: "Verify our steel rib spacing against NATM guidance for weak rock mass (RMR 30-40).",
      },
      {
        role: "assistant",
        text:
          "Current **1.2m rib spacing** is within the allowable range for RMR 30-40, but sits near the upper bound. Guidance recommends tightening to 1.0m if convergence monitoring shows displacement trending above 15mm/week.",
        steps: [
          "Retrieved rock-mass classification tables from the NATM Design Guideline.",
          "Matched current RMR band (30-40) to recommended support spacing ranges.",
          "Checked latest convergence monitoring readings against the trigger threshold.",
        ],
        sources: [
          {
            doc: "NATM Design Guideline Rev. 4.pdf",
            section: "§6.3 Support Spacing",
            snippet: "For RMR 30-40, steel rib spacing of 0.75-1.2m is recommended, tightened as convergence trends increase.",
          },
        ],
      },
    ],
  },
  {
    id: "c3",
    title: "Rockfall probability — Sector 4B",
    alert: true,
    messages: [
      {
        role: "user",
        text: "What is the current rockfall probability rating for Sector 4B and what triggered the last escalation?",
      },
      {
        role: "assistant",
        text:
          'Sector 4B is rated **"elevated"** following last week\'s geotechnical survey, which recorded increased joint spacing and minor spalling near chainage 340+120.',
        riskLevel: RISK.warn,
        steps: [
          "Retrieved latest geotechnical survey for Sector 4B.",
          "Compared joint spacing readings to the prior baseline survey.",
        ],
        sources: [
          {
            doc: "Geotechnical Survey - North Bore.pdf",
            section: "§3 Sector 4B",
            snippet: "Joint spacing increased from 0.4m to 0.25m near chainage 340+120; minor spalling observed on the crown.",
          },
        ],
      },
    ],
  },
  {
    id: "c4",
    title: "Emergency egress compliance check",
    alert: false,
    messages: [
      { role: "user", text: "Are our emergency refuge chamber spacings compliant for the main bore?" },
      {
        role: "assistant",
        text:
          "Yes — refuge chambers are spaced at **300m intervals**, within the 350m maximum required by the Emergency Response Plan.",
        steps: ["Retrieved refuge chamber spacing requirements from the Emergency Response Plan."],
        sources: [
          {
            doc: "Emergency Response Plan.pdf",
            section: "§2.4 Refuge Chambers",
            snippet: "Refuge chambers shall be positioned at intervals not exceeding 350m along the tunnel alignment.",
          },
        ],
      },
    ],
  },
  {
    id: "c5",
    title: "Groundwater ingress mitigation plan",
    alert: false,
    messages: [
      { role: "user", text: "Summarize mitigation options for the groundwater ingress reported at the north portal." },
      {
        role: "assistant",
        text:
          "Recommended approach: **pre-excavation grouting** combined with **staged dewatering**, per the incident response precedent used on the south portal in March.",
        steps: ["Retrieved groundwater mitigation precedent from prior incident reports."],
        sources: [
          {
            doc: "Incident Log - Sector 4B.xlsx",
            section: "Rows 88–94",
            snippet: "South portal ingress resolved via pre-excavation grouting and staged dewatering over 6 days.",
          },
        ],
      },
    ],
  },
  {
    id: "c6",
    title: "Blast vibration monitoring thresholds",
    alert: false,
    messages: [
      { role: "user", text: "What peak particle velocity threshold applies near the adjacent structures?" },
      {
        role: "assistant",
        text: "The applicable PPV limit is **25mm/s** for structures within 50m of the blast zone, per the monitoring records baseline.",
        steps: ["Retrieved PPV thresholds from blast monitoring records."],
        sources: [
          {
            doc: "Blast Monitoring Records Q2.csv",
            section: "Threshold table",
            snippet: "PPV limit: 25mm/s for structures within 50m; 15mm/s beyond that for sensitive structures.",
          },
        ],
      },
    ],
  },
  {
    id: "c7",
    title: "Gas monitoring sensor calibration log",
    alert: false,
    messages: [
      { role: "user", text: "When were CO and methane sensors last calibrated in the main bore?" },
      {
        role: "assistant",
        text:
          "Last full calibration was completed **11 days ago** across all main bore stations; two sensors near chainage 210 are due for recalibration this week.",
        steps: ["Retrieved sensor calibration log for the main bore."],
        sources: [
          {
            doc: "Incident Log - Sector 4B.xlsx",
            section: "Calibration tab",
            snippet: "Stations 12 and 14 (chainage 210) flagged for recalibration within 7 days.",
          },
        ],
      },
    ],
  },
];

export const DEMO_DOCS = [
  { name: "Tunnel Ventilation Safety Code 2024.pdf", tag: "SAFETY CODE", meta: "112 pages", color: "critical" },
  { name: "NATM Design Guideline Rev. 4.pdf", tag: "DESIGN SPEC", meta: "89 pages", color: "spec" },
  { name: "Incident Log - Sector 4B.xlsx", tag: "INCIDENT LOG", meta: "340 rows", color: "incident" },
  { name: "Geotechnical Survey - North Bore.pdf", tag: "SURVEY", meta: "64 pages", color: "spec" },
  { name: "Emergency Response Plan.pdf", tag: "SAFETY CODE", meta: "47 pages", color: "critical" },
  { name: "Blast Monitoring Records Q2.csv", tag: "MONITORING", meta: "2,180 rows", color: "incident" },
];

export const MODES = [
  { id: "fast", name: "Fast", desc: "Quick answers for routine questions" },
  { id: "deep", name: "Deep Reasoning", desc: "Multi-step retrieval with full agent trace" },
  { id: "strict", name: "Safety-Strict", desc: "Conservative answers, always cites sources" },
];

export const SUGGESTIONS = [
  "사망 사고가 가장 많이 발생한 사고 유형은?",
  "해체작업 중 사고의 재발방지대책은?",
  "Which accident type caused the most fatalities?",
  "Show accident counts by tunnel type as a chart",
];
