export const ACCENT = "var(--accent-color)";

export function TunnelLogo({ size = 26, feet = true, sw = 2.2 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" className="flex-none">
      <path d="M3 18 V11 A9 7 0 0 1 21 11 V18" fill="none" stroke={ACCENT} strokeWidth={sw} strokeLinecap="round" />
      {feet && (
        <>
          <circle cx="7" cy="18" r="1.6" fill={ACCENT} />
          <circle cx="17" cy="18" r="1.6" fill={ACCENT} />
        </>
      )}
    </svg>
  );
}

export const PanelIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
    <rect x="3" y="4" width="18" height="16" rx="3" stroke="currentColor" strokeWidth="1.6" />
    <line x1="9" y1="4" x2="9" y2="20" stroke="currentColor" strokeWidth="1.6" />
  </svg>
);

export const PlusIcon = ({ size = 17, color = "currentColor" }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className="flex-none">
    <path d="M12 5v14M5 12h14" stroke={color} strokeWidth="2" strokeLinecap="round" />
  </svg>
);

export const SearchIcon = ({ size = 17 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className="flex-none">
    <circle cx="11" cy="11" r="6.5" stroke="currentColor" strokeWidth="1.7" />
    <line x1="20" y1="20" x2="15.8" y2="15.8" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
  </svg>
);

export const DocIcon = ({ size = 17, color = "currentColor", sw = 1.7, lines = true }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className="flex-none">
    <rect x="5" y="3" width="14" height="18" rx="1.5" stroke={color} strokeWidth={sw} />
    {lines && (
      <>
        <line x1="8.5" y1="8" x2="15.5" y2="8" stroke={color} strokeWidth="1.4" />
        <line x1="8.5" y1="12" x2="15.5" y2="12" stroke={color} strokeWidth="1.4" />
        <line x1="8.5" y1="16" x2="13" y2="16" stroke={color} strokeWidth="1.4" />
      </>
    )}
  </svg>
);

export const GraphIcon = ({ size = 17, color = "currentColor", sw = 1.7 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className="flex-none">
    <path
      d="M6 8.5 12 5l6 3.5M6 8.5v7L12 19l6-3.5v-7M6 8.5 12 12l6-3.5M12 12v7"
      stroke={color}
      strokeWidth={sw}
      strokeLinejoin="round"
    />
    <circle cx="12" cy="5" r="1.8" fill={color} />
    <circle cx="6" cy="8.5" r="1.8" fill={color} />
    <circle cx="18" cy="8.5" r="1.8" fill={color} />
    <circle cx="12" cy="12" r="1.8" fill={color} />
    <circle cx="6" cy="15.5" r="1.8" fill={color} />
    <circle cx="18" cy="15.5" r="1.8" fill={color} />
    <circle cx="12" cy="19" r="1.8" fill={color} />
  </svg>
);

export const ReportIcon = ({ size = 17, color = "currentColor", sw = 1.7 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className="flex-none">
    <rect x="6" y="4" width="12" height="17" rx="1.5" stroke={color} strokeWidth={sw} />
    <path d="M9 3.5h6a1 1 0 0 1 1 1V6H8V4.5a1 1 0 0 1 1-1Z" stroke={color} strokeWidth={sw} strokeLinejoin="round" />
    <path d="M9 12.5 11 14.5 15 10" stroke={color} strokeWidth={sw} strokeLinecap="round" strokeLinejoin="round" />
    <line x1="8.5" y1="17" x2="14" y2="17" stroke={color} strokeWidth="1.4" />
  </svg>
);

export const SunIcon = ({ size = 17, color = "currentColor", sw = 1.7 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className="flex-none">
    <circle cx="12" cy="12" r="4.2" stroke={color} strokeWidth={sw} />
    <path
      d="M12 2.5v2.3M12 19.2v2.3M4.4 4.4l1.6 1.6M18 18l1.6 1.6M2.5 12h2.3M19.2 12h2.3M4.4 19.6 6 18M18 6l1.6-1.6"
      stroke={color}
      strokeWidth={sw}
      strokeLinecap="round"
    />
  </svg>
);

export const MoonIcon = ({ size = 17, color = "currentColor", sw = 1.7 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className="flex-none">
    <path
      d="M20 14.5A8.5 8.5 0 1 1 9.5 4a6.8 6.8 0 0 0 10.5 10.5Z"
      stroke={color}
      strokeWidth={sw}
      strokeLinejoin="round"
    />
  </svg>
);

export const DotsIcon = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" className="flex-none text-fog-700">
    <circle cx="12" cy="12" r="1.8" fill="currentColor" />
    <circle cx="12" cy="5" r="1.8" fill="currentColor" />
    <circle cx="12" cy="19" r="1.8" fill="currentColor" />
  </svg>
);

export const SparkleIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
    <path
      d="M12 3l2.4 5.8L20 11l-5.6 2.2L12 19l-2.4-5.8L4 11l5.6-2.2L12 3z"
      stroke={ACCENT}
      strokeWidth="1.6"
      strokeLinejoin="round"
    />
  </svg>
);

export const ChevronIcon = ({ open }) => (
  <svg
    width="13"
    height="13"
    viewBox="0 0 24 24"
    fill="none"
    className="transition-transform duration-150"
    style={{ transform: open ? "rotate(180deg)" : "rotate(0deg)" }}
  >
    <path d="M6 9l6 6 6-6" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

export const WarningIcon = () => (
  <svg width="17" height="17" viewBox="0 0 24 24" fill="none" className="flex-none text-risk-icon">
    <path d="M12 3L2 20h20L12 3z" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" />
    <line x1="12" y1="10" x2="12" y2="14" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    <circle cx="12" cy="17" r="1" fill="currentColor" />
  </svg>
);

export const CopyIcon = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
    <rect x="9" y="9" width="11" height="11" rx="2" stroke="currentColor" strokeWidth="1.6" />
    <rect x="4" y="4" width="11" height="11" rx="2" stroke="currentColor" strokeWidth="1.6" />
  </svg>
);

export const CheckIcon = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
    <path d="M4 12.5l5 5L20 7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

export const RegenIcon = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
    <path d="M4 12a8 8 0 0114-5.3M20 12a8 8 0 01-14 5.3" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    <path d="M18 3v4h-4M6 21v-4h4" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

export const ThumbIcon = ({ down }) => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" style={down ? { transform: "scaleY(-1)" } : undefined}>
    <path d="M7 11v9H4v-9h3zm0 0l3-8 2 1-1 5h7l1 2-3 8H9l-2-1" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round" />
  </svg>
);

export const AttachIcon = () => (
  <svg width="17" height="17" viewBox="0 0 24 24" fill="none">
    <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="1.6" />
    <path d="M12 8v8M8 12h8" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
  </svg>
);

export const MicIcon = () => (
  <svg width="17" height="17" viewBox="0 0 24 24" fill="none">
    <rect x="9" y="3" width="6" height="11" rx="3" stroke="currentColor" strokeWidth="1.6" />
    <path d="M5 11a7 7 0 0014 0M12 18v3" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
  </svg>
);

export const SendIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
    <path d="M5 12h14M13 5l7 7-7 7" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

export const StopIcon = () => (
  <svg width="12" height="12" viewBox="0 0 24 24">
    <rect x="5" y="5" width="14" height="14" rx="2.5" fill="currentColor" />
  </svg>
);

export const CloseIcon = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
    <path d="M6 6l12 12M18 6L6 18" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
  </svg>
);

export const TrashIcon = ({ size = 14 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
    <path
      d="M5 7h14M9 7V5a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2m-8 0v12a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1V7m-6 4v6m4-6v6"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
);

export const ChatLineIcon = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" className="flex-none text-fog-700">
    <path d="M8 12h8M8 8h8M8 16h5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
  </svg>
);
