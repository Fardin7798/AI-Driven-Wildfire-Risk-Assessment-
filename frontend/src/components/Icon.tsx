// Icons from designs/wildfire/assets/icons (24x24 grid, stroke 1.75, round caps).
const PATHS = {
  search: "M18 11 A7 7 0 1 1 4 11 A7 7 0 1 1 18 11 Z M20.5 20.5 L16 16",
  "arrow-down": "M12 5 L12 19 M6 13 L12 19 L18 13",
  wind: "M3 8 L13 8 A3 3 0 1 0 10 5 M3 12 L18 12 A3 3 0 1 1 15 15 M3 16 L10 16",
  flame:
    "M12 3 C12 3 18 8 18 14 A6 6 0 0 1 6 14 C6 10.5 8.5 8.5 9 6.5 C10.5 8 11 9.5 11 11 C13 9.5 12.5 6 12 3 Z M12 20 A2.5 2.5 0 0 1 9.5 17.5 C9.5 15.5 12 14 12 14 C12 14 14.5 15.5 14.5 17.5 A2.5 2.5 0 0 1 12 20 Z",
  "shield-house":
    "M12 3 L19 6 L19 11.5 C19 16 16 19.5 12 21 C8 19.5 5 16 5 11.5 L5 6 Z M8.5 12.5 L12 9.5 L15.5 12.5 M9.75 11.5 L9.75 15.5 L14.25 15.5 L14.25 11.5",
} as const;

export type IconName = keyof typeof PATHS;

export function Icon({ name, size = 24, color = "#FFFFFF", strokeWidth, className, style }: {
  name: IconName; size?: number; color?: string; strokeWidth?: number; className?: string; style?: React.CSSProperties;
}) {
  // FigCraft scaled the path, keeping stroke ≈ 1.75 * scale (min 1.5); in a viewBox we divide back.
  const s = size / 24;
  const sw = (strokeWidth ?? Math.max(1.5, 1.75 * s)) / s;
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={sw}
      strokeLinecap="round" strokeLinejoin="round" className={className} style={style} aria-hidden>
      <path d={PATHS[name]} />
    </svg>
  );
}
