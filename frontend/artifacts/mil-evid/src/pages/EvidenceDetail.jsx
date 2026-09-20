import { useEffect, useState } from "react";

import {
  ArrowRight,
  Globe2,
} from "lucide-react";

import {
  Link,
  useParams,
} from "react-router-dom";

import PageHeader from "../components/PageHeader";
import Panel from "../components/Panel";
import Pill from "../components/Pill";
import EmptyState from "../components/EmptyState";

import { apiClient } from "../services/apiClient";

const formatDate = (date) => {
  if (!date) {
    return "Unknown date";
  }

  const parsedDate = new Date(date);

  if (Number.isNaN(parsedDate.getTime())) {
    return "Unknown date";
  }

  return new Intl.DateTimeFormat(
    "en-GB",
    {
      day: "2-digit",
      month: "short",
      year: "numeric",
    }
  ).format(parsedDate);
};

const formatDateTime = (date) => {
  if (!date) {
    return "Unknown";
  }

  const parsedDate = new Date(date);

  if (Number.isNaN(parsedDate.getTime())) {
    return "Unknown";
  }

  return new Intl.DateTimeFormat(
    "en-GB",
    {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }
  ).format(parsedDate);
};

export default function EvidenceDetail() {
  const { id } = useParams();

  const [record, setRecord] =
    useState(null);

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState("");

  useEffect(() => {
    let cancelled = false;

    async function loadEvidence() {
      try {
        setLoading(true);
        setError("");

        const response =
          await apiClient.getEvidence(id);

        if (cancelled) return;

        setRecord(response);
      } catch (loadError) {
        if (cancelled) return;

        console.error(
          "Unable to load evidence:",
          loadError
        );

        if (
          loadError?.status === 404
        ) {
          setError(
            "Evidence record not found."
          );
        } else {
          setError(
            loadError?.message ||
              "Unable to load evidence record."
          );
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    if (id) {
      loadEvidence();
    }

    return () => {
      cancelled = true;
    };
  }, [id]);

  if (loading) {
    return (
      <EmptyState
        title="Loading evidence record..."
        text="Retrieving the evidence record from the backend."
      />
    );
  }

  if (error || !record) {
    return (
      <EmptyState
        title={
          error ||
          "Evidence record not found."
        }
        text="This evidence record is not available in the workspace."
      />
    );
  }

  return (
    <>
      <PageHeader
        eyebrow={`Evidence record / ${record.id}`}
        title={
          record.title ||
          "Untitled evidence"
        }
        description={`${record.source} · ${
          record.source_type
        } · captured ${formatDate(
          record.date
        )}`}
        action={
          <Link
            to="/evidence"
            className="inline-flex h-10 items-center gap-2 border border-border bg-card px-3 text-xs hover:bg-muted"
            data-testid="link-back-evidence"
          >
            <ArrowRight
              size={15}
              className="rotate-180"
            />
            Back to explorer
          </Link>
        }
      />

      <div className="grid gap-5 lg:grid-cols-[1.25fr_.75fr]">
        <Panel
          title="Record text"
          meta="Evidence content"
        >
          <div className="border-l-2 border-accent pl-5 text-sm leading-8 text-foreground/85 whitespace-pre-wrap">
            {record.text ||
              "No evidence text is available for this record."}
          </div>

          {record.url && (
            <a
              href={record.url}
              target="_blank"
              rel="noreferrer"
              className="mt-7 inline-flex items-center gap-2 text-xs text-accent hover:underline"
              data-testid="link-open-source"
            >
              <Globe2 size={14} />
              Open source reference
              <ArrowRight
                size={13}
              />
            </a>
          )}
        </Panel>

        <Panel
          title="Provenance"
          meta="Source attributes"
        >
          <div className="space-y-4 text-xs">
            <div>
              <div className="font-mono-ui text-[9px] uppercase text-muted-foreground">
                Source
              </div>

              <div className="mt-1">
                {record.source ||
                  "Unknown source"}
              </div>
            </div>

            <div>
              <div className="font-mono-ui text-[9px] uppercase text-muted-foreground">
                Source type
              </div>

              <div className="mt-1">
                <Pill tone="copper">
                  {record.source_type ||
                    "Unknown"}
                </Pill>
              </div>
            </div>

            <div>
              <div className="font-mono-ui text-[9px] uppercase text-muted-foreground">
                Perspective
              </div>

              <div className="mt-1">
                <Pill tone="copper">
                  {record.perspective ||
                    "Unassigned"}
                </Pill>
              </div>
            </div>

            <div>
              <div className="font-mono-ui text-[9px] uppercase text-muted-foreground">
                Record date
              </div>

              <div className="mt-1">
                {formatDate(
                  record.date
                )}
              </div>
            </div>

            <div>
              <div className="font-mono-ui text-[9px] uppercase text-muted-foreground">
                Document ID
              </div>

              <div className="mt-1 break-all font-mono-ui text-[10px]">
                {record.document_id ||
                  "Not available"}
              </div>
            </div>

            <div>
              <div className="font-mono-ui text-[9px] uppercase text-muted-foreground">
                Chunk index
              </div>

              <div className="mt-1 font-mono-ui">
                {record.chunk_index ??
                  "Not available"}
              </div>
            </div>

            <div>
              <div className="font-mono-ui text-[9px] uppercase text-muted-foreground">
                Indexed
              </div>

              <div className="mt-1">
                {formatDateTime(
                  record.created_at
                )}
              </div>
            </div>
          </div>
        </Panel>
      </div>

      <div className="mt-5">
        <Panel
          title="Relationships"
          meta="Claim relationships"
        >
          <EmptyState
            title="No claim relationships available."
            text="Claim-to-evidence relationships are stored against completed analyses and are not currently returned by the standalone evidence endpoint."
          />
        </Panel>
      </div>
    </>
  );
}