import type { TokenEvent } from "../types/generation";

type Props = {
  tokens: TokenEvent[];
  revealClasses: boolean;
  selectedPosition: number | null;
  onSelect: (position: number) => void;
  emptyLabel: string;
  /** When true, show a caret after the latest token so streaming is obvious. */
  streaming?: boolean;
  /**
   * Positions where this branch differs from its clean/loaded peer.
   * Highlighted as a token-level diff (the CRN intuition pump).
   */
  diffPositions?: ReadonlySet<number> | null;
  /**
   * Optional prompt prefix rendered with the same typography so the passage
   * reads as one continuous text (prompt → continuation).
   */
  promptPrefix?: string | null;
};

function classForToken(
  token: TokenEvent,
  reveal: boolean,
  isDiff: boolean,
): string {
  const parts = ["tok"];
  if (isDiff) {
    parts.push("tok--diff");
  }
  if (!reveal) {
    return parts.join(" ");
  }
  if (!token.eligible) {
    parts.push("tok--excluded");
  } else if (token.favored) {
    parts.push("tok--favored");
  } else {
    parts.push("tok--nonfavored");
  }
  return parts.join(" ");
}

/**
 * Prefer the first prose paragraph for the continuous-passage view so a later
 * digression or blank-line dump does not break the "one flowing sentence" read.
 * Token ids / detector scores stay full-length on the fixture; this is display-only.
 */
export function tokensForPassage(tokens: TokenEvent[]): TokenEvent[] {
  if (tokens.length === 0) return tokens;
  let acc = "";
  const out: TokenEvent[] = [];
  for (const token of tokens) {
    acc += token.text;
    out.push(token);
    // Stop at a blank line (paragraph break) once we have some prose.
    if (out.length >= 8 && /\n\s*\n/.test(acc)) break;
  }
  return out;
}

/** Collapse internal newlines to spaces for inline passage flow. */
function displayPiece(text: string): string {
  return text.replace(/[\t ]*\n[\t ]*/g, " ");
}

/**
 * Join model pieces as the backend does ("".join). Do not inject spaces —
 * BPE pieces already carry leading spaces / whitespace when needed.
 */
export function TokenText({
  tokens,
  revealClasses,
  selectedPosition,
  onSelect,
  emptyLabel,
  streaming = false,
  diffPositions = null,
  promptPrefix = null,
}: Props) {
  if (!tokens.length && !promptPrefix) {
    return <p className="output-card__empty">{emptyLabel}</p>;
  }

  const shown = streaming ? tokens : tokensForPassage(tokens);
  const prefix = (promptPrefix ?? "").trimEnd();
  // Ensure a single space between prompt and first piece when the piece has no
  // leading whitespace (some tokenizers emit bare first tokens).
  const firstPiece = shown[0]?.text ?? "";
  const needsGap =
    prefix.length > 0 &&
    shown.length > 0 &&
    !/\s$/.test(prefix) &&
    firstPiece.length > 0 &&
    !/^\s/.test(firstPiece);

  return (
    <p className={`token-text${streaming ? " token-text--streaming" : ""}`}>
      {prefix ? (
        <span className="token-text__prompt" data-region="prompt-prefix">
          {prefix}
          {needsGap ? " " : null}
        </span>
      ) : null}
      {shown.map((token) => {
        const selected = selectedPosition === token.position;
        const isDiff = Boolean(diffPositions?.has(token.position));
        const favorLabel = token.eligible
          ? token.favored
            ? "favored"
            : "not favored"
          : token.exclusion_reason === "repeated_ngram"
            ? "excluded: repeated n-gram"
            : token.exclusion_reason === "missing_context"
              ? "excluded: context unavailable"
              : "excluded";
        const label = isDiff ? `${favorLabel}; differs from pair` : favorLabel;
        const cls = `${classForToken(token, revealClasses, isDiff)}${selected ? " tok--selected" : ""}`;
        const piece = displayPiece(token.text);
        if (!piece) return null;
        return (
          <button
            key={`${token.position}-${token.token_id}`}
            type="button"
            className={cls}
            onClick={() => onSelect(token.position)}
            aria-label={`Token ${token.position + 1}: ${piece}, ${label}`}
            aria-pressed={selected}
            title={isDiff || revealClasses ? label : piece}
          >
            {piece}
          </button>
        );
      })}
      {streaming ? (
        <span className="token-caret" aria-hidden="true">
          ▍
        </span>
      ) : null}
    </p>
  );
}
