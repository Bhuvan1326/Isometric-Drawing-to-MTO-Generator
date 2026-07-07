'use client';

import { Download, RotateCcw, AlertTriangle, Info } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { DrawingPreview } from '@/components/drawing-preview';
import { MetadataBlock } from '@/components/metadata-block';
import { MTOTable } from '@/components/mto-table';
import { SummaryCards } from '@/components/summary-cards';
import { getCsvUrl, type JobResponse } from '@/lib/api';

interface Props {
  job: JobResponse;
  file: File | null;
  onReset: () => void;
}

export function ResultsPanel({ job, file, onReset }: Props) {
  const mto = job.mto;
  const isMock = mto?.source === 'mock';

  return (
    <div className="space-y-6">
      {/* Mock-mode banner — the spec requires the mock to be clearly labelled. */}
      {isMock && (
        <div className="flex items-start gap-3 rounded-lg border border-amber-300 bg-amber-50 p-4 text-amber-900">
          <Info className="h-5 w-5 shrink-0 mt-0.5" />
          <div className="text-sm">
            <p className="font-semibold">Mock mode — no API key configured.</p>
            <p className="mt-1">
              The backend returned a clearly-labelled sample MTO so the app
              runs end-to-end. Set <code className="font-mono">GEMINI_API_KEY</code> in{' '}
              <code className="font-mono">backend/.env</code> to run the real
              vision pipeline on your drawing.
            </p>
          </div>
        </div>
      )}

      {/* Error state */}
      {job.state === 'error' && (
        <div className="flex items-start gap-3 rounded-lg border border-destructive/30 bg-destructive/10 p-4 text-destructive">
          <AlertTriangle className="h-5 w-5 shrink-0 mt-0.5" />
          <div className="text-sm">
            <p className="font-semibold">Extraction failed.</p>
            <p className="mt-1">{job.message || 'Unknown error.'}</p>
          </div>
        </div>
      )}

      {mto && (
        <>
          {/* Summary cards */}
          <SummaryCards summary={mto.summary} />

          {/* Metadata + actions */}
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between gap-3 flex-wrap">
                <CardTitle className="text-lg">Drawing Metadata</CardTitle>
                <div className="flex items-center gap-2">
                  <Badge variant={isMock ? 'secondary' : 'default'}>
                    {isMock ? 'Mock sample' : `Source: ${mto.source}`}
                  </Badge>
                  <Button variant="outline" size="sm" onClick={onReset}>
                    <RotateCcw className="h-4 w-4 mr-1" />
                    New drawing
                  </Button>
                  <a href={getCsvUrl(job.job_id)} download>
                    <Button size="sm">
                      <Download className="h-4 w-4 mr-1" />
                      Export CSV
                    </Button>
                  </a>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <MetadataBlock meta={mto.drawing_meta} />
            </CardContent>
          </Card>

          {/* Side-by-side: drawing + table */}
          <div className="grid gap-6 lg:grid-cols-2">
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-lg">Drawing</CardTitle>
              </CardHeader>
              <CardContent>
                <DrawingPreview file={file} />
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-lg">
                  Material Take-Off
                  <span className="ml-2 text-sm font-normal text-muted-foreground">
                    {mto.items.length} items
                  </span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <MTOTable items={mto.items} />
              </CardContent>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
