'use client';

import { Loader2 } from 'lucide-react';
import { Progress } from '@/components/ui/progress';

interface Props {
  filename: string;
  progress: number;
  message: string;
}

// The pipeline stages shown to the user. We map a 0-100 progress value to
// these labels so the user sees what's happening, not just a spinner.
const STAGES = [
  { at: 0, label: 'Uploading drawing' },
  { at: 15, label: 'Pre-processing image' },
  { at: 30, label: 'Sending to vision model' },
  { at: 70, label: 'Validating & deriving gaskets/bolts' },
  { at: 90, label: 'Computing summary totals' },
];

function stageFor(pct: number): string {
  let current = STAGES[0].label;
  for (const s of STAGES) {
    if (pct >= s.at) current = s.label;
  }
  return current;
}

export function ProcessingState({ filename, progress, message }: Props) {
  return (
    <div className="flex flex-col items-center justify-center gap-4 rounded-lg border border-dashed p-10 text-center">
      <Loader2 className="h-8 w-8 animate-spin text-primary" />
      <div className="space-y-1">
        <p className="font-medium">{stageFor(progress)}</p>
        <p className="text-sm text-muted-foreground truncate max-w-md">
          {filename}
        </p>
        {message && (
          <p className="text-xs text-muted-foreground">{message}</p>
        )}
      </div>
      <div className="w-full max-w-md">
        <Progress value={progress} />
      </div>
    </div>
  );
}
