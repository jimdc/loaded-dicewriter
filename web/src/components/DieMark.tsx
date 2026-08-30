/** Quiet geometric die mark — local SVG, no external assets. */
export function DieMark({ size = 16 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 16 16"
      aria-hidden="true"
      focusable="false"
    >
      <rect
        x="1.5"
        y="1.5"
        width="13"
        height="13"
        rx="3"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.4"
      />
      <circle cx="5.2" cy="5.2" r="1.1" fill="currentColor" />
      <circle cx="10.8" cy="5.2" r="1.1" fill="currentColor" />
      <circle cx="5.2" cy="10.8" r="1.1" fill="currentColor" />
      <circle cx="10.8" cy="10.8" r="1.1" fill="currentColor" />
      <circle cx="8" cy="8" r="1.1" fill="currentColor" />
    </svg>
  );
}
