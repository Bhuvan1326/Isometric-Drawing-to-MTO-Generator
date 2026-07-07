'use client';

import { useEffect, useRef, useState } from 'react';
import { FlaskConical, Github, AlertCircle } from 'lucide-react';
import { UploadDropzone } from '@/components/upload-dropzone';
import { ResultsPanel } from '@/components/results-panel';
import { ProcessingState } from '@/components/processing-state';
import { getHealth, getJob, type JobResponse } from '@/lib/api';

type Phase = 'idle' | 'processing' | 'done' | 'error';

export default function Home() {
  const [phase, setPhase] = useState<Phase>('idle');
  const [job, setJob] = useState<JobResponse | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [progress, setProgress] = useState(0);
  const [processingMessage, setProcessingMessage] = useState('');
  const [topError, setTopError] = useState<string | null>(null);
  const [provider, setProvider] = useState<string>('mock');

  // Health check on mount — tells us if the backend is up and which provider.
  useEffect(() => {
    getHealth()
      .then((h) => setProvider(h.provider))
      .catch(() => setProvider('unknown'));
  }, []);

  // Poll the job until it's done or errored.
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  useEffect(() => {
    if (phase !== 'processing' || !job) return;

    let cancelled = false;
    const poll = async () => {
      try {
        const updated = await getJob(job.job_id);
        if (cancelled) return;
        setJob(updated);
        // Advance the fake progress bar — real progress isn't available from
        // the backend, so we ease it forward to show the app is alive.
        setProgress((p) => Math.min(p + 7, 92));
        if (updated.state === 'done') {
          setPhase('done');
          setProgress(100);
          if (pollRef.current) clearInterval(pollRef.current);
        } else if (updated.state === 'error') {
          setPhase('error');
          setProcessingMessage(updated.message || 'Extraction failed.');
          if (pollRef.current) clearInterval(pollRef.current);
        }
      } catch (e) {
        if (cancelled) return;
        setPhase('error');
        setProcessingMessage(
          e instanceof Error ? e.message : 'Failed to reach backend.'
        );
        if (pollRef.current) clearInterval(pollRef.current);
      }
    };

    // Poll immediately, then every 1.2s.
    poll();
    pollRef.current = setInterval(poll, 1200);
    return () => {
      cancelled = true;
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [phase, job?.job_id]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleUploaded = (jobId: string, f: File) => {
    setFile(f);
    setProgress(8);
    setProcessingMessage('');
    setTopError(null);
    // Seed a job object so the poller has a job_id to start with.
    setJob({
      job_id: jobId,
      state: 'processing',
      message: null,
      filename: f.name,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      mto: null,
    });
    setPhase('processing');
  };

  const handleReset = () => {
    setPhase('idle');
    setJob(null);
    setFile(null);
    setProgress(0);
    setProcessingMessage('');
    setTopError(null);
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 sticky top-0 z-10">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 h-14 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <FlaskConical className="h-5 w-5 text-primary" />
            <span className="font-semibold">IsoMTO</span>
            <span className="text-sm text-muted-foreground hidden sm:inline">
              — Isometric Drawing to MTO Generator
            </span>
          </div>
          <div className="flex items-center gap-3 text-sm">
            <span className="text-muted-foreground hidden sm:inline">
              Backend:
            </span>
            <span
              className={
                provider === 'mock'
                  ? 'text-amber-600 font-medium'
                  : provider === 'unknown'
                  ? 'text-rose-600 font-medium'
                  : 'text-emerald-600 font-medium'
              }
            >
              {provider === 'unknown'
                ? 'unreachable'
                : provider === 'mock'
                ? 'mock mode'
                : `${provider} (live)`}
            </span>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-8">
        {phase === 'idle' && (
          <div className="mx-auto max-w-2xl space-y-6">
            <div className="text-center space-y-2">
              <h1 className="text-3xl font-bold tracking-tight">
                Upload a piping isometric
              </h1>
              <p className="text-muted-foreground">
                We&apos;ll extract every pipe, fitting, flange, valve, gasket,
                and bolt set into a structured Material Take-Off.
              </p>
            </div>

            {provider === 'unknown' && (
              <div className="flex items-start gap-2 rounded-md border border-rose-300 bg-rose-50 p-3 text-sm text-rose-800">
                <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
                <span>
                  Backend unreachable at the configured URL. Start the FastAPI
                  server (see README) or set <code>NEXT_PUBLIC_API_URL</code>.
                </span>
              </div>
            )}

            <UploadDropzone
              onUploaded={handleUploaded}
              onError={(msg) => setTopError(msg)}
            />

            {topError && (
              <div className="flex items-start gap-2 rounded-md border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
                <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
                <span>{topError}</span>
              </div>
            )}

            <div className="rounded-lg border bg-muted/30 p-4 text-sm text-muted-foreground">
              <p className="font-medium text-foreground mb-1">
                How it works
              </p>
              <ol className="list-decimal list-inside space-y-1">
                <li>Upload a PNG, JPG, or PDF isometric drawing.</li>
                <li>
                  The backend pre-processes the image (renders PDF pages,
                  normalizes) and sends it to a vision LLM with a strict JSON
                  schema.
                </li>
                <li>
                  A validation layer normalizes units and re-derives gaskets
                  and bolt sets from flange counts.
                </li>
                <li>
                  Review the MTO table, summary cards, and metadata, then
                  export to CSV.
                </li>
              </ol>
            </div>
          </div>
        )}

        {phase === 'processing' && job && (
          <div className="mx-auto max-w-2xl">
            <ProcessingState
              filename={job.filename}
              progress={progress}
              message={processingMessage}
            />
          </div>
        )}

        {(phase === 'done' || phase === 'error') && job && (
          <ResultsPanel job={job} file={file} onReset={handleReset} />
        )}
      </main>

      <footer className="border-t mt-12">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-4 text-sm text-muted-foreground flex items-center justify-between">
          <span>IsoMTO — take-home assessment</span>
          <a
            href="https://aistudio.google.com/"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 hover:text-foreground"
          >
            <Github className="h-3.5 w-3.5" />
            Powered by Gemini
          </a>
        </div>
      </footer>
    </div>
  );
}
