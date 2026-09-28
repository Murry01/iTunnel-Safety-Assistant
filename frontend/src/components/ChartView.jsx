import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

// Categorical data colors — fixed in both themes, they distinguish data
// series rather than acting as UI chrome.
const PALETTE = ["#e8823a", "#7f77dd", "#1d9e75", "#378add", "#d4537e", "#e0a458", "#9aa0a6"];

// Chrome (grid/axis/tooltip) does need to flip — recharts renders to inline
// SVG with these as literal style/attribute values, outside the CSS
// cascade, so they can't pick up the --ink-*/--fog-* variables for free.
const CHROME = {
  dark: { grid: "#3a352c", tick: "#9aa0a6", tooltipBg: "#232019", tooltipBorder: "#3a352c" },
  light: { grid: "#ddd8cf", tick: "#6b655a", tooltipBg: "#ffffff", tooltipBorder: "#d8d2c5" },
};

export default function ChartView({ spec, theme = "dark" }) {
  const c = CHROME[theme] ?? CHROME.dark;
  const data = spec.labels.map((label, i) => ({ label: String(label), value: spec.values[i] }));
  const tooltipStyle = { background: c.tooltipBg, border: `1px solid ${c.tooltipBorder}`, fontSize: 12 };

  return (
    <div className="rounded-xl border border-ink-600 bg-ink-850 p-3.5">
      {spec.title && <p className="mb-2 text-[12.5px] font-medium text-fog-200">{spec.title}</p>}
      <ResponsiveContainer width="100%" height={260}>
        {spec.chart_type === "pie" ? (
          <PieChart>
            <Tooltip contentStyle={tooltipStyle} />
            <Legend wrapperStyle={{ fontSize: 11 }} />
            <Pie data={data} dataKey="value" nameKey="label" outerRadius={90} label>
              {data.map((_, i) => (
                <Cell key={i} fill={PALETTE[i % PALETTE.length]} />
              ))}
            </Pie>
          </PieChart>
        ) : spec.chart_type === "line" ? (
          <LineChart data={data}>
            <CartesianGrid stroke={c.grid} strokeDasharray="3 3" />
            <XAxis dataKey="label" tick={{ fontSize: 10, fill: c.tick }} />
            <YAxis tick={{ fontSize: 10, fill: c.tick }} />
            <Tooltip contentStyle={tooltipStyle} />
            <Line type="monotone" dataKey="value" stroke={PALETTE[0]} strokeWidth={2} />
          </LineChart>
        ) : (
          <BarChart data={data}>
            <CartesianGrid stroke={c.grid} strokeDasharray="3 3" />
            <XAxis dataKey="label" tick={{ fontSize: 10, fill: c.tick }} angle={-35} textAnchor="end" height={60} />
            <YAxis tick={{ fontSize: 10, fill: c.tick }} />
            <Tooltip contentStyle={tooltipStyle} />
            <Bar dataKey="value" fill={PALETTE[0]} radius={[4, 4, 0, 0]} />
          </BarChart>
        )}
      </ResponsiveContainer>
    </div>
  );
}
