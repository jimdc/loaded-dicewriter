import {
  DEMO_GALLERY,
  controlZ,
  formatStrength,
  loadedZ,
  type DemoExample,
} from "../data/demoExample";

type Props = {
  selectedId: string;
  onSelect: (id: string) => void;
  disabled?: boolean;
};

function shortPrompt(prompt: string, max = 56): string {
  const t = prompt.trim();
  if (t.length <= max) return t;
  return `${t.slice(0, max - 1)}…`;
}

/**
 * Primary surface: browsable precomputed real-English clean/loaded pairs.
 * This is the whole product experience (no live generation UI).
 */
export function DemoGallery({ selectedId, onSelect, disabled = false }: Props) {
  const examples = DEMO_GALLERY.examples;

  return (
    <section className="demo-gallery" aria-labelledby="gallery-heading">
      <div className="demo-gallery__header">
        <h2 id="gallery-heading" className="demo-gallery__title">
          Worked examples
        </h2>
        <p className="demo-gallery__lede">
          Real English from a language model, frozen offline with coupled sampling — clean and
          watermarked share the same random draws, so only a few tokens differ, yet the detector
          still separates them.
        </p>
      </div>

      <ul className="demo-gallery__list" role="listbox" aria-label="Precomputed examples">
        {examples.map((ex: DemoExample) => {
          const selected = ex.id === selectedId;
          const lz = loadedZ(ex);
          const cz = controlZ(ex);
          const detected = Boolean(ex.loaded.detection?.detected);
          return (
            <li key={ex.id} className="demo-gallery__item">
              <button
                type="button"
                role="option"
                aria-selected={selected}
                className={`demo-gallery__card${selected ? " is-selected" : ""}`}
                onClick={() => onSelect(ex.id)}
                disabled={disabled}
              >
                <span className="demo-gallery__card-top">
                  <span className="demo-gallery__card-label">{ex.label}</span>
                  <span
                    className={`demo-gallery__z${detected ? " demo-gallery__z--hot" : ""}`}
                    title={`Clean z ${cz.toFixed(2)}, watermarked z ${lz.toFixed(2)}`}
                  >
                    z {lz.toFixed(2)}
                  </span>
                </span>
                <span className="demo-gallery__card-prompt">{shortPrompt(ex.prompt)}</span>
                <span className="demo-gallery__card-meta">
                  {formatStrength(ex)}
                  {typeof ex.flip_rate === "number"
                    ? ` · ${(ex.flip_rate * 100).toFixed(0)}% tokens differ`
                    : null}
                  {detected ? " · strong signal" : " · milder signal"}
                </span>
              </button>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
