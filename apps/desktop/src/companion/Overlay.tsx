import { useEffect, useState } from "react";
import { faceLabel, type FaceState } from "../face/faceState";
import { FlatFace } from "../face/HeadScene";

export function Overlay({
  face,
  title,
  startedAt,
  screenAccess,
  preview,
  onStop,
  onRestore,
}: {
  face: FaceState;
  title: string;
  startedAt?: string;
  screenAccess: boolean;
  preview: boolean;
  onStop: () => void;
  onRestore: () => void;
}) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);
  const elapsed = startedAt
    ? Math.max(0, Math.round((now - Date.parse(startedAt)) / 1000))
    : 0;
  return (
    <section className="work-overlay" aria-label="Work overlay">
      <FlatFace face={face} compact />
      <div className="overlay-body">
        <p className="overlay-title">{title}</p>
        <p className="overlay-stage">
          {faceLabel[face]}
          {startedAt &&
            ` · ${Math.floor(elapsed / 60)}:${String(elapsed % 60).padStart(2, "0")}`}
        </p>
        <p className={`screen-access ${screenAccess ? "live" : ""}`}>
          {screenAccess
            ? "● Screen control active"
            : preview
              ? "Preview · no screen access"
              : "No screen access"}
        </p>
        <div className="row">
          <button
            type="button"
            disabled
            title="Pause is not supported by Hermes yet"
          >
            Pause
          </button>
          <button type="button" className="danger" onClick={onStop}>
            Stop
          </button>
          <button type="button" onClick={onRestore}>
            Restore
          </button>
        </div>
      </div>
    </section>
  );
}
