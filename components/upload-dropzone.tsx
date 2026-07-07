'use client';

import { useCallback, useRef, useState } from 'react';
import { UploadCloud, FileText, X, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import {
  ACCEPTED_EXTENSIONS,
  ACCEPTED_TYPES,
  MAX_FILE_SIZE_BYTES,
  MAX_FILE_SIZE_MB,
  uploadFile,
  ApiError as ApiErrorClass,
} from '@/lib/api';
import { cn } from '@/lib/utils';

interface Props {
  onUploaded: (jobId: string, file: File) => void;
  onError: (message: string) => void;
}

export function UploadDropzone({ onUploaded, onError }: Props) {
  const [dragOver, setDragOver] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [progress, setProgress] = useState(0);
  const [uploading, setUploading] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const validate = (f: File): string | null => {
    const ext = '.' + (f.name.split('.').pop() || '').toLowerCase();
    if (!ACCEPTED_EXTENSIONS.includes(ext)) {
      return `Unsupported file type "${ext}". Allowed: ${ACCEPTED_EXTENSIONS.join(', ')}`;
    }
    // Some browsers may not set type for unusual extensions; check both.
    if (f.type && !ACCEPTED_TYPES.includes(f.type)) {
      // Allow through if the extension is valid — content-type can be missing
      // or odd for PDFs in some browsers. The server re-validates anyway.
    }
    if (f.size > MAX_FILE_SIZE_BYTES) {
      return `File is too large (${(f.size / 1024 / 1024).toFixed(1)}MB). Max ${MAX_FILE_SIZE_MB}MB.`;
    }
    if (f.size === 0) {
      return 'File is empty.';
    }
    return null;
  };

  const handleFile = useCallback(
    (f: File) => {
      setLocalError(null);
      const err = validate(f);
      if (err) {
        setLocalError(err);
        return;
      }
      setFile(f);
      setProgress(0);
    },
    []
  );

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const f = e.dataTransfer.files?.[0];
      if (f) handleFile(f);
    },
    [handleFile]
  );

  const onUpload = async () => {
    if (!file) return;
    setUploading(true);
    setProgress(0);
    try {
      const { job_id } = await uploadFile(file, (pct) => setProgress(pct));
      onUploaded(job_id, file);
    } catch (e) {
      const msg =
        e instanceof ApiErrorClass ? e.message : 'Upload failed unexpectedly.';
      setLocalError(msg);
      onError(msg);
    } finally {
      setUploading(false);
    }
  };

  const reset = () => {
    setFile(null);
    setProgress(0);
    setLocalError(null);
    if (inputRef.current) inputRef.current.value = '';
  };

  return (
    <div className="w-full">
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED_EXTENSIONS.join(',')}
        className="hidden"
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) handleFile(f);
        }}
      />

      {!file && (
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={onDrop}
          onClick={() => inputRef.current?.click()}
          className={cn(
            'flex flex-col items-center justify-center gap-3 rounded-lg border-2 border-dashed p-10 cursor-pointer transition-colors',
            dragOver
              ? 'border-primary bg-primary/5'
              : 'border-border hover:border-primary/50 hover:bg-muted/50'
          )}
        >
          <UploadCloud className="h-10 w-10 text-muted-foreground" />
          <div className="text-center">
            <p className="font-medium">
              Drop a piping isometric here, or click to browse
            </p>
            <p className="text-sm text-muted-foreground mt-1">
              PNG, JPG, or PDF — max {MAX_FILE_SIZE_MB}MB
            </p>
          </div>
        </div>
      )}

      {file && (
        <div className="rounded-lg border p-4 space-y-3">
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-start gap-3 min-w-0">
              <FileText className="h-8 w-8 text-primary shrink-0 mt-0.5" />
              <div className="min-w-0">
                <p className="font-medium truncate">{file.name}</p>
                <p className="text-sm text-muted-foreground">
                  {(file.size / 1024 / 1024).toFixed(2)} MB
                </p>
              </div>
            </div>
            {!uploading && (
              <Button
                variant="ghost"
                size="icon"
                onClick={reset}
                aria-label="Remove file"
              >
                <X className="h-4 w-4" />
              </Button>
            )}
          </div>

          {uploading && (
            <div className="space-y-1">
              <Progress value={progress} />
              <p className="text-sm text-muted-foreground">
                Uploading… {progress}%
              </p>
            </div>
          )}

          {!uploading && (
            <div className="flex gap-2">
              <Button onClick={onUpload}>Generate MTO</Button>
              <Button variant="outline" onClick={reset}>
                Choose different file
              </Button>
            </div>
          )}
        </div>
      )}

      {localError && (
        <div className="mt-3 flex items-start gap-2 rounded-md border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
          <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
          <span>{localError}</span>
        </div>
      )}
    </div>
  );
}
