import { Source } from "../lib/types";

type SourcesCardProps = {
  sources: Source[];
};

export function SourcesCard({ sources }: SourcesCardProps) {
  if (sources.length === 0) {
    return null;
  }

  return (
    <details className="details">
      <summary>Sources</summary>
      <div className="source-list">
        {sources.map((source, index) => (
          <div className="source-card" key={`${source.doi}-${source.chunk_idx}-${index}`}>
            <strong>{source.title || "Untitled paper"}</strong>
            {source.doi ? (
              <a href={`https://doi.org/${source.doi}`} rel="noreferrer" target="_blank">
                {source.doi}
              </a>
            ) : (
              <span className="muted">DOI unavailable</span>
            )}
            <div className="muted">Chunk index: {source.chunk_idx}</div>
          </div>
        ))}
      </div>
    </details>
  );
}
