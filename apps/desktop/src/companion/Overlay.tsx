import {
  lazy,
  Suspense,
  useEffect,
  useState,
  type CSSProperties,
  type RefObject,
} from "react";
import { faceLabel, type FaceState } from "../face/faceState";
import { FlatFace, type Quality } from "../face/FlatFace";
import { EXPRESSIONS } from "../face/rig";

const HeadCanvas = lazy(() => import("../face/HeadScene"));

/** Always-on-top work overlay shown while a screen-control tool runs (or previewed from Settings). */
export function Overlay({
  face,
  level,
  quality,
  reduced,
  title,
  startedAt,
  screenAccess,
  preview,
  onStop,
  onRestore,
}: {
  face: FaceState;
  level: RefObject<number>;
  quality: Quality;
  reduced: boolean;
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
    <section
      className={`work-overlay ${face}`}
      aria-label="Work overlay"
      style={{ "--state": EXPRESSIONS[face].hue } as CSSProperties}
    >
      <div className="overlay-face">
        <span className="aura" aria-hidden="true" />
        <Suspense fallback={<FlatFace face={face} compact />}>
          <HeadCanvas
            face={face}
            level={level}
            quality={quality}
            reduced={reduced}
            compact
          />
        </Suspense>
      </div>
      <div className="overlay-body">
        <p className="overlay-title">{title}</p>
        <p className="overlay-stage">
          <i /> {faceLabel[face]}
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
