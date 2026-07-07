'use client';

import { Hash, GitCommit, Circle, Layers, FlaskConical } from 'lucide-react';
import type { DrawingMeta } from '@/lib/api';

interface Props {
  meta: DrawingMeta;
}

export function MetadataBlock({ meta }: Props) {
  const rows = [
    { label: 'Line Number', value: meta.line_number, icon: Hash },
    { label: 'Drawing No.', value: meta.drawing_no, icon: Hash },
    { label: 'Revision', value: meta.revision, icon: GitCommit },
    { label: 'NPS', value: meta.nps, icon: Circle },
    { label: 'Material Class', value: meta.material_class, icon: Layers },
    { label: 'Service', value: meta.service, icon: FlaskConical },
  ];

  return (
    <div className="grid grid-cols-2 gap-x-4 gap-y-2 sm:grid-cols-3">
      {rows.map((r) => {
        const Icon = r.icon;
        return (
          <div key={r.label} className="flex items-center gap-2">
            <Icon className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
            <div className="min-w-0">
              <div className="text-xs text-muted-foreground">{r.label}</div>
              <div className="text-sm font-medium truncate">
                {r.value || '—'}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
