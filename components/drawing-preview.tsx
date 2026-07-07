'use client';

import { useEffect, useState } from 'react';
import { FileText, AlertCircle } from 'lucide-react';
import { cn } from '@/lib/utils';

interface Props {
  file: File | null;
}

export function DrawingPreview({ file }: Props) {
  const [url, setUrl] = useState<string | null>(null);
  const [isPdf, setIsPdf] = useState(false);

  useEffect(() => {
    if (!file) {
      setUrl(null);
      return;
    }
    const objUrl = URL.createObjectURL(file);
    setUrl(objUrl);
    setIsPdf(file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf'));
    return () => URL.revokeObjectURL(objUrl);
  }, [file]);

  if (!file) {
    return (
      <div className="flex h-full min-h-[300px] flex-col items-center justify-center gap-2 rounded-lg border border-dashed text-muted-foreground">
        <FileText className="h-8 w-8" />
        <p className="text-sm">No drawing uploaded</p>
      </div>
    );
  }

  if (isPdf) {
    return (
      <div className="h-full min-h-[300px]">
        <object
          data={url || ''}
          type="application/pdf"
          className="h-full min-h-[300px] w-full rounded-lg border"
        >
          <div className="flex h-full min-h-[300px] flex-col items-center justify-center gap-2 p-6 text-center">
            <AlertCircle className="h-8 w-8 text-amber-500" />
            <p className="text-sm">
              PDF preview unavailable in this browser.
              <br />
              The file was still sent to the pipeline.
            </p>
          </div>
        </object>
      </div>
    );
  }

  return (
    <div className={cn('h-full min-h-[300px]')}>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={url || ''}
        alt={file.name}
        className="h-full max-h-[70vh] w-full rounded-lg border object-contain bg-muted/30"
      />
    </div>
  );
}
