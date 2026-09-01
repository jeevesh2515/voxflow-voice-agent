export default function VoxPreloader() {
  return (
    <div className="vox-preloader" aria-hidden="true">
      <svg
        viewBox="0 0 180 100"
        className="vox-preloader-mark"
        role="presentation"
      >
        <defs>
          <linearGradient id="vox-wire-gradient" x1="0" x2="1" y1="0" y2="0">
            <stop offset="0%" stopColor="#00ffcc" stopOpacity="0.22" />
            <stop offset="42%" stopColor="#00ffcc" />
            <stop offset="100%" stopColor="#a8fff1" />
          </linearGradient>
          <filter id="vox-wire-glow" x="-40%" y="-100%" width="180%" height="300%">
            <feGaussianBlur stdDeviation="2.7" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>
        <path
          className="vox-preloader-wire vox-preloader-wire-base"
          d="M10 52H30L44 30L57 70L72 41L87 58L105 18L122 52H170"
        />
        <path
          className="vox-preloader-wire vox-preloader-wire-echo"
          d="M10 52H36L47 42L59 59L74 47L89 56L108 35L123 52H170"
        />
        <path
          className="vox-preloader-wire vox-preloader-wire-rail"
          d="M12 80H168M12 22H30M150 22H168"
        />
        <g className="vox-preloader-core" filter="url(#vox-wire-glow)">
          <circle cx="105" cy="18" r="4" />
          <circle cx="57" cy="70" r="3" />
          <path d="M83 52H98" />
        </g>
      </svg>
    </div>
  );
}
