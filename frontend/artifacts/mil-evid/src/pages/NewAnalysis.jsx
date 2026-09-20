import { useEffect, useRef, useState } from "react";

import {
  Check,
  Shield,
  Scale,
  History,
  TriangleAlert,
  Zap,
  Radio,
  LoaderCircle,
} from "lucide-react";

import { useNavigate } from "react-router-dom";

import PageHeader from "../components/PageHeader";
import Panel from "../components/Panel";
import Pill from "../components/Pill";
import Button from "../components/Button";

import { apiClient } from "../services/apiClient";


const cn = (...items) =>
  items.filter(Boolean).join(" ");


/* ============================================================
   FIXED ANALYTICAL PERSPECTIVES
   ============================================================ */

const perspectives = [
  {
    name: "Military",
    description:
      "Force posture, operations, capabilities, movements, and strategic military indicators.",
    icon: Shield,
    label: "force & posture",
  },
  {
    name: "Legal",
    description:
      "Applicable law, obligations, legal frameworks, and documented legal positions.",
    icon: Scale,
    label: "law & obligations",
  },
  {
    name: "Historical",
    description:
      "Historical context, precedent, timelines, and comparable events.",
    icon: History,
    label: "context & precedent",
  },
];


/* ============================================================
   REAL BACKEND PIPELINE STAGES
   ============================================================ */

const stages = [
  {
    code: "q",
    label: "Query Processing",
  },
  {
    code: "r",
    label: "Perspective Retrieval",
  },
  {
    code: "e",
    label: "Evidence Retrieval",
  },
  {
    code: "rr",
    label: "Reranking",
  },
  {
    code: "mp",
    label: "Multi-Perspective Analysis",
  },
  {
    code: "cv",
    label: "Claim Verification",
  },
  {
    code: "cd",
    label: "Contradiction Detection",
  },
  {
    code: "cs",
    label: "Confidence Scoring",
  },
  {
    code: "rg",
    label: "Response Generation",
  },
];


/* ============================================================
   STATUS ORDER
   ============================================================ */

const statusOrder = {
  q: 0,
  r: 1,
  e: 2,
  rr: 3,
  mp: 4,
  cv: 5,
  cd: 6,
  cs: 7,
  rg: 8,
  completed: 9,
};


/* ============================================================
   POLLING INTERVAL
   ============================================================ */

const POLL_INTERVAL = 1000;


/* ============================================================
   STATUS HELPERS
   ============================================================ */

const getStatusIndex = (status) => {
  if (status === "completed") {
    return stages.length;
  }

  const index = stages.findIndex(
    (stage) => stage.code === status
  );

  return index;
};


const isStageComplete = (
  stageIndex,
  currentStatus
) => {
  if (currentStatus === "completed") {
    return true;
  }

  const currentIndex =
    getStatusIndex(currentStatus);

  if (currentIndex < 0) {
    return false;
  }

  /*
   * During "cv", Claim Verification and
   * Contradiction Detection are both running.
   *
   * Claim Verification is therefore NOT marked
   * complete until "cd" is reached.
   */
  return stageIndex < currentIndex;
};


const isStageWorking = (
  stageIndex,
  currentStatus
) => {
  if (
    currentStatus === "completed" ||
    currentStatus === "failed"
  ) {
    return false;
  }

  const currentIndex =
    getStatusIndex(currentStatus);

  return (
    currentIndex >= 0 &&
    stageIndex === currentIndex
  );
};


export default function NewAnalysis() {
  const navigate = useNavigate();

  const pollRef = useRef(null);
  const mountedRef = useRef(true);

  const [form, setForm] = useState({
    query: "",
    retrievalTopK: 50,
    rerankTopK: 8,

    dynamicEvidence: false,
    acledCountry: "",
    acledStartDate: "",
    acledEndDate: "",
  });

  const [error, setError] = useState("");

  const [running, setRunning] = useState(false);

  const [analysisId, setAnalysisId] =
    useState(null);

  const [backendStatus, setBackendStatus] =
    useState("q");


  /* ==========================================================
     BUILD BACKEND PAYLOAD
     ========================================================== */

  const buildAnalysisPayload = () => {
    const payload = {
      query: form.query.trim(),

      retrieval_top_k: Number(
        form.retrievalTopK
      ),

      rerank_top_k: Number(
        form.rerankTopK
      ),
    };

    if (form.dynamicEvidence) {
      if (
        form.acledCountry.trim()
      ) {
        payload.acled_country =
          form.acledCountry.trim();
      }

      if (form.acledStartDate) {
        payload.acled_start_date =
          form.acledStartDate;
      }

      if (form.acledEndDate) {
        payload.acled_end_date =
          form.acledEndDate;
      }
    }

    return payload;
  };


  /* ==========================================================
     STOP POLLING
     ========================================================== */

  const stopPolling = () => {
    if (pollRef.current) {
      clearInterval(
        pollRef.current
      );

      pollRef.current = null;
    }
  };


  /* ==========================================================
     CHECK REAL BACKEND STATUS
     ========================================================== */

  const checkAnalysisStatus = async (
    id
  ) => {
    try {
      const analysis =
        await apiClient.getAnalysis(id);

      if (!mountedRef.current) {
        return;
      }

      const status =
        analysis?.status;

      if (!status) {
        throw new Error(
          "The server returned no analysis status."
        );
      }

      setBackendStatus(status);

      /* -----------------------------------------------
         ANALYSIS COMPLETED
         ----------------------------------------------- */

      if (status === "completed") {
        stopPolling();

        setRunning(false);

        /*
         * Give React a moment to render the final
         * completed state before navigating.
         */
        window.setTimeout(() => {
          if (!mountedRef.current) {
            return;
          }

          navigate(
            `/analysis/${id}`,
            {
              replace: true,
            }
          );
        }, 350);

        return;
      }


      /* -----------------------------------------------
         ANALYSIS FAILED
         ----------------------------------------------- */

      if (status === "failed") {
        stopPolling();

        setRunning(false);

        setError(
          "The analysis failed while processing. Please try again."
        );

        return;
      }

    } catch (err) {
      console.error(
        "Failed to fetch analysis status:",
        err
      );

      /*
       * Do not immediately kill the analysis for a
       * temporary polling/network failure.
       *
       * The backend may still be running.
       */
    }
  };


  /* ==========================================================
     START BACKEND POLLING
     ========================================================== */

  const startPolling = (
    id
  ) => {
    stopPolling();

    /*
     * Check immediately instead of waiting
     * one full second.
     */
    checkAnalysisStatus(id);

    pollRef.current =
      window.setInterval(() => {
        checkAnalysisStatus(id);
      }, POLL_INTERVAL);
  };


  /* ==========================================================
     SUBMIT ANALYSIS
     ========================================================== */

  const submit = async (
    event
  ) => {
    event.preventDefault();

    setError("");

    /* -----------------------------------------------
       QUERY VALIDATION
       ----------------------------------------------- */

    if (
      form.query.trim().length < 20
    ) {
      setError(
        "Give the question enough detail to support a meaningful evidence retrieval and analysis pass."
      );

      return;
    }


    /* -----------------------------------------------
       RETRIEVAL VALIDATION
       ----------------------------------------------- */

    if (
      Number(form.retrievalTopK) < 1 ||
      Number(form.rerankTopK) < 1
    ) {
      setError(
        "Retrieval and reranking values must be greater than zero."
      );

      return;
    }


    /* -----------------------------------------------
       START
       ----------------------------------------------- */

    setRunning(true);

    setBackendStatus("q");

    setAnalysisId(null);


    try {
      const payload =
        buildAnalysisPayload();


      /*
       * POST now returns immediately with an
       * analysis_id and initial backend status.
       */
      const result =
        await apiClient.runAnalysis(
          payload
        );


      const id =
        result?.analysis_id ||
        result?.id ||
        result?.analysis?.id;


      if (!id) {
        throw new Error(
          "The server did not return an analysis ID."
        );
      }


      setAnalysisId(id);


      /*
       * Start reading the REAL backend status.
       */
      startPolling(id);

    } catch (err) {
      console.error(
        "Analysis request failed:",
        err
      );

      stopPolling();

      setRunning(false);

      setError(
        err?.message ||
          "Unable to start the analysis. Please try again."
      );
    }
  };


  /* ==========================================================
     CLEANUP
     ========================================================== */

  useEffect(() => {
    mountedRef.current = true;

    return () => {
      mountedRef.current = false;

      stopPolling();
    };
  }, []);


  /* ==========================================================
     LIVE PROCESSING SCREEN
     ========================================================== */

  if (running) {
    const currentStageIndex =
      getStatusIndex(
        backendStatus
      );

    const progress =
      backendStatus === "completed"
        ? 100
        : currentStageIndex < 0
          ? 0
          : Math.round(
              ((currentStageIndex + 1) /
                stages.length) *
                100
            );


    return (
      <div className="mx-auto max-w-3xl py-12">

        <PageHeader
          eyebrow="Analysis run / live processing"
          title="Building the evidence room."
          description="MIL-EVID is processing your question through the evidence-grounded analysis pipeline. The status below reflects the backend execution state."
        />


        {/* =====================================================
            LIVE BACKEND INDICATOR
        ===================================================== */}

        <div className="mt-8 flex items-center justify-between border border-border bg-card px-4 py-3">

          <div className="flex items-center gap-3">

            <span className="relative flex h-2.5 w-2.5">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-accent opacity-60" />

              <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-accent" />
            </span>

            <span className="font-mono-ui text-[10px] uppercase tracking-[.12em] text-muted-foreground">
              Backend processing
            </span>

          </div>


          {analysisId && (
            <span className="font-mono-ui text-[9px] text-muted-foreground">
              {String(analysisId).slice(0, 8)}…
            </span>
          )}

        </div>


        {/* =====================================================
            REAL STATUS LIST
        ===================================================== */}

        <div className="mt-4 border border-border bg-card p-6">

          {stages.map(
            (
              stage,
              index
            ) => {

              const complete =
                isStageComplete(
                  index,
                  backendStatus
                );

              const working =
                isStageWorking(
                  index,
                  backendStatus
                );


              return (
                <div
                  className={cn(
                    "flex items-center gap-4 border-b border-border py-4 last:border-0",
                    !complete &&
                      !working &&
                      "opacity-35"
                  )}
                  key={stage.code}
                >

                  {/* -----------------------------------------
                      STATUS ICON
                     ----------------------------------------- */}

                  <span
                    className={cn(
                      "grid h-7 w-7 shrink-0 place-items-center border font-mono-ui text-[10px]",

                      complete &&
                        "border-primary bg-primary text-primary-foreground",

                      working &&
                        "border-accent text-accent",

                      !complete &&
                        !working &&
                        "border-border"
                    )}
                  >

                    {complete ? (
                      <Check size={14} />
                    ) : working ? (
                      <LoaderCircle
                        size={14}
                        className="animate-spin"
                      />
                    ) : (
                      `0${index + 1}`
                    )}

                  </span>


                  {/* -----------------------------------------
                      STAGE NAME
                     ----------------------------------------- */}

                  <span
                    className={cn(
                      "text-sm",
                      complete &&
                        "text-foreground",
                      working &&
                        "text-accent"
                    )}
                  >
                    {stage.label}
                  </span>


                  {/* -----------------------------------------
                      STATUS LABEL
                     ----------------------------------------- */}

                  {complete && (
                    <span className="ml-auto font-mono-ui text-[9px] uppercase text-primary">
                      complete
                    </span>
                  )}

                  {working && (
                    <span className="ml-auto font-mono-ui text-[9px] uppercase text-accent">
                      working
                    </span>
                  )}

                </div>
              );
            }
          )}

        </div>


        {/* =====================================================
            PROGRESS INDICATOR
            This is derived from backend status.
            It is NOT a timer.
        ===================================================== */}

        <div className="mt-6">

          <div className="mb-2 flex items-center justify-between">

            <span className="font-mono-ui text-[9px] uppercase tracking-[.12em] text-muted-foreground">
              Backend pipeline progress
            </span>

            <span className="font-mono-ui text-[10px] text-accent">
              {progress}%
            </span>

          </div>

          <div className="h-1 bg-muted">

            <div
              className="h-full bg-accent transition-all duration-300"
              style={{
                width: `${progress}%`,
              }}
            />

          </div>

        </div>


        {/* =====================================================
            FAILED STATE
        ===================================================== */}

        {backendStatus ===
          "failed" && (
          <div className="mt-6 flex gap-2 border border-destructive/30 bg-destructive/10 px-3 py-3 text-sm text-destructive">

            <TriangleAlert
              size={16}
              className="mt-0.5 shrink-0"
            />

            <span>
              The backend analysis failed.
            </span>

          </div>
        )}

      </div>
    );
  }


  /* ==========================================================
     NEW ANALYSIS FORM
     ========================================================== */

  return (
    <>
      <PageHeader
        eyebrow="Analysis workspace / New"
        title="Frame an analysis."
        description="Ask a question and let MIL-EVID test it through military, legal, and historical perspectives using evidence-grounded retrieval."
        action={
          <Pill tone="green">
            <span className="h-1.5 w-1.5 rounded-full bg-primary" />
            Evidence engine ready
          </Pill>
        }
      />


      <form
        onSubmit={submit}
        className="grid gap-5 xl:grid-cols-[1.15fr_.85fr]"
      >

        {/* =====================================================
            RESEARCH QUESTION
        ===================================================== */}

        <Panel
          title="Research question"
          meta="Required"
        >

          <label className="block">

            <span className="mb-2 block text-xs font-medium">
              What do you need to understand?
            </span>

            <textarea
              value={form.query}
              onChange={(event) =>
                setForm(
                  (current) => ({
                    ...current,
                    query:
                      event.target.value,
                  })
                )
              }
              className="min-h-48 w-full resize-y border border-input bg-background p-4 text-sm leading-6 outline-none focus:border-accent"
              placeholder="Example: What are the documented military, legal, and historical factors surrounding the security situation in the Suwałki corridor?"
              data-testid="input-analysis-query"
            />

          </label>


          <div className="mt-4 flex items-center justify-between border-t border-border pt-4">

            <span className="font-mono-ui text-[9px] uppercase tracking-[.12em] text-muted-foreground">
              Minimum detail recommended
            </span>

            <span
              className={cn(
                "font-mono-ui text-[10px]",

                form.query.trim().length >=
                  20
                  ? "text-primary"
                  : "text-muted-foreground"
              )}
            >
              {form.query.trim().length} characters
            </span>

          </div>

        </Panel>


        {/* =====================================================
            PERSPECTIVES
        ===================================================== */}

        <Panel
          title="Analytical perspectives"
          meta="Three perspectives / fixed"
        >

          <div className="space-y-3">

            {perspectives.map(
              ({
                name,
                description,
                icon: Icon,
                label,
              }) => (
                <div
                  key={name}
                  className="border border-border bg-background p-4"
                >

                  <div className="flex items-start gap-3">

                    <div className="flex h-9 w-9 shrink-0 items-center justify-center border border-accent/40 bg-accent/5 text-accent">
                      <Icon size={17} />
                    </div>

                    <div className="min-w-0 flex-1">

                      <div className="flex items-center justify-between gap-3">

                        <span className="text-sm font-medium">
                          {name}
                        </span>

                        <span className="font-mono-ui text-[9px] uppercase text-muted-foreground">
                          {label}
                        </span>

                      </div>

                      <p className="mt-2 text-xs leading-5 text-muted-foreground">
                        {description}
                      </p>

                    </div>

                    <Check
                      size={15}
                      className="mt-1 shrink-0 text-primary"
                    />

                  </div>

                </div>
              )
            )}

          </div>


          <div className="mt-4 border-t border-border pt-4">

            <div className="flex items-start gap-2 text-[11px] leading-5 text-muted-foreground">

              <Shield
                size={14}
                className="mt-0.5 shrink-0 text-accent"
              />

              <span>
                Every analysis uses all three perspectives.
                They are selected by the backend to maintain
                consistent analytical coverage.
              </span>

            </div>

          </div>

        </Panel>


        {/* =====================================================
            RETRIEVAL CONFIGURATION
        ===================================================== */}

        <Panel
          title="Retrieval configuration"
          meta="Evidence pipeline"
        >

          <div className="grid gap-4 sm:grid-cols-2">

            <label>

              <span className="mb-2 block text-xs font-medium">
                Retrieval top-K
              </span>

              <input
                type="number"
                min="1"
                max="500"
                value={form.retrievalTopK}
                onChange={(event) =>
                  setForm(
                    (current) => ({
                      ...current,
                      retrievalTopK:
                        event.target.value,
                    })
                  )
                }
                className="h-11 w-full border border-input bg-background px-3 text-sm outline-none focus:border-accent"
              />

              <span className="mt-1 block text-[10px] text-muted-foreground">
                Candidate evidence retrieved before reranking.
              </span>

            </label>


            <label>

              <span className="mb-2 block text-xs font-medium">
                Rerank top-K
              </span>

              <input
                type="number"
                min="1"
                max="100"
                value={form.rerankTopK}
                onChange={(event) =>
                  setForm(
                    (current) => ({
                      ...current,
                      rerankTopK:
                        event.target.value,
                    })
                  )
                }
                className="h-11 w-full border border-input bg-background px-3 text-sm outline-none focus:border-accent"
              />

              <span className="mt-1 block text-[10px] text-muted-foreground">
                Evidence retained after cross-encoder reranking.
              </span>

            </label>

          </div>


          <div className="mt-5 border-t border-border pt-5">

            <div className="flex items-start justify-between gap-4">

              <div className="flex items-start gap-3">

                <div className="flex h-9 w-9 shrink-0 items-center justify-center border border-border bg-muted">

                  <Radio
                    size={16}
                    className="text-accent"
                  />

                </div>

                <div>

                  <div className="text-xs font-medium">
                    Dynamic conflict evidence
                  </div>

                  <div className="mt-1 text-[11px] leading-5 text-muted-foreground">
                    Include ACLED evidence when the backend
                    configuration and query support it.
                  </div>

                </div>

              </div>


              <input
                type="checkbox"
                checked={
                  form.dynamicEvidence
                }
                onChange={(event) =>
                  setForm(
                    (current) => ({
                      ...current,
                      dynamicEvidence:
                        event.target.checked,
                    })
                  )
                }
                data-testid="input-dynamic-evidence"
              />

            </div>


            {form.dynamicEvidence && (
              <div className="mt-5 grid gap-4 border-t border-border pt-5 sm:grid-cols-3">

                <label>

                  <span className="mb-2 block text-xs font-medium">
                    Country
                  </span>

                  <input
                    value={
                      form.acledCountry
                    }
                    onChange={(event) =>
                      setForm(
                        (current) => ({
                          ...current,
                          acledCountry:
                            event.target.value,
                        })
                      )
                    }
                    className="h-10 w-full border border-input bg-background px-3 text-xs outline-none focus:border-accent"
                    placeholder="e.g. Ukraine"
                  />

                </label>


                <label>

                  <span className="mb-2 block text-xs font-medium">
                    Start date
                  </span>

                  <input
                    type="date"
                    value={
                      form.acledStartDate
                    }
                    onChange={(event) =>
                      setForm(
                        (current) => ({
                          ...current,
                          acledStartDate:
                            event.target.value,
                        })
                      )
                    }
                    className="h-10 w-full border border-input bg-background px-3 text-xs outline-none focus:border-accent"
                  />

                </label>


                <label>

                  <span className="mb-2 block text-xs font-medium">
                    End date
                  </span>

                  <input
                    type="date"
                    value={
                      form.acledEndDate
                    }
                    onChange={(event) =>
                      setForm(
                        (current) => ({
                          ...current,
                          acledEndDate:
                            event.target.value,
                        })
                      )
                    }
                    className="h-10 w-full border border-input bg-background px-3 text-xs outline-none focus:border-accent"
                  />

                </label>

              </div>
            )}

          </div>

        </Panel>


        {/* =====================================================
            ANALYSIS SUMMARY
        ===================================================== */}

        <Panel
          title="Analysis configuration"
          meta="Execution summary"
        >

          <div className="space-y-4">

            <div className="flex items-center justify-between border-b border-border pb-3">

              <span className="text-xs text-muted-foreground">
                Perspectives
              </span>

              <span className="font-mono-ui text-xs text-accent">
                3
              </span>

            </div>


            <div className="flex items-center justify-between border-b border-border pb-3">

              <span className="text-xs text-muted-foreground">
                Retrieval candidates
              </span>

              <span className="font-mono-ui text-xs">
                {form.retrievalTopK}
              </span>

            </div>


            <div className="flex items-center justify-between border-b border-border pb-3">

              <span className="text-xs text-muted-foreground">
                Reranked evidence
              </span>

              <span className="font-mono-ui text-xs">
                {form.rerankTopK}
              </span>

            </div>


            <div className="flex items-center justify-between">

              <span className="text-xs text-muted-foreground">
                Dynamic evidence
              </span>

              <Pill
                tone={
                  form.dynamicEvidence
                    ? "green"
                    : "copper"
                }
              >
                {form.dynamicEvidence
                  ? "Enabled"
                  : "Disabled"}
              </Pill>

            </div>

          </div>


          {error && (
            <div
              className="mt-5 flex gap-2 border border-destructive/30 bg-destructive/10 px-3 py-3 text-sm text-destructive"
              data-testid="status-analysis-error"
            >

              <TriangleAlert
                size={16}
                className="mt-0.5 shrink-0"
              />

              <span>
                {error}
              </span>

            </div>
          )}


          <Button
            type="submit"
            className="mt-6 w-full"
            data-testid="button-run-analysis"
          >

            <Zap size={16} />

            Run evidence-grounded analysis

          </Button>


          <p className="mt-3 text-center font-mono-ui text-[9px] uppercase tracking-[.12em] text-muted-foreground">
            Military · Legal · Historical
          </p>

        </Panel>

      </form>
    </>
  );
}