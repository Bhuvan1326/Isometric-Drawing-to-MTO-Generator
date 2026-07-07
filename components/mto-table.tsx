'use client';

import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import type { Category, MTOItem } from '@/lib/api';
import { cn } from '@/lib/utils';

interface Props {
  items: MTOItem[];
}

const CATEGORY_COLORS: Record<Category, string> = {
  PIPE: 'bg-blue-100 text-blue-800 border-blue-200',
  FITTING: 'bg-emerald-100 text-emerald-800 border-emerald-200',
  FLANGE: 'bg-amber-100 text-amber-800 border-amber-200',
  VALVE: 'bg-rose-100 text-rose-800 border-rose-200',
  GASKET: 'bg-cyan-100 text-cyan-800 border-cyan-200',
  BOLT: 'bg-violet-100 text-violet-800 border-violet-200',
  SUPPORT: 'bg-slate-100 text-slate-800 border-slate-200',
};

function confidenceClass(c: number | null): string {
  if (c === null) return 'text-muted-foreground';
  if (c >= 0.8) return 'text-emerald-600';
  if (c >= 0.5) return 'text-amber-600';
  return 'text-rose-600';
}

function formatQty(item: MTOItem): string {
  // Pipe shows total length; everything else shows integer count.
  if (item.category === 'PIPE') {
    return `${item.quantity.toFixed(2)} ${item.unit}`;
  }
  const q = Number.isInteger(item.quantity)
    ? item.quantity.toString()
    : item.quantity.toFixed(2);
  return `${q} ${item.unit}`;
}

export function MTOTable({ items }: Props) {
  if (items.length === 0) {
    return (
      <div className="flex h-40 items-center justify-center rounded-lg border border-dashed text-sm text-muted-foreground">
        No items extracted.
      </div>
    );
  }

  return (
    <div className="rounded-lg border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-12">#</TableHead>
            <TableHead className="w-24">Category</TableHead>
            <TableHead>Description</TableHead>
            <TableHead className="w-20">Size</TableHead>
            <TableHead className="w-24">Rating</TableHead>
            <TableHead className="w-28">Material</TableHead>
            <TableHead className="w-16">End</TableHead>
            <TableHead className="w-24 text-right">Qty</TableHead>
            <TableHead className="w-16 text-right">Conf.</TableHead>
            <TableHead>Remarks</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {items.map((item) => (
            <TableRow key={item.item_no}>
              <TableCell className="font-mono text-xs text-muted-foreground">
                {item.item_no}
              </TableCell>
              <TableCell>
                <Badge
                  variant="outline"
                  className={cn('font-medium', CATEGORY_COLORS[item.category])}
                >
                  {item.category}
                </Badge>
              </TableCell>
              <TableCell className="font-medium">
                {item.description}
              </TableCell>
              <TableCell className="text-sm">
                {item.size_nps || '—'}
              </TableCell>
              <TableCell className="text-sm">
                {item.schedule_rating || '—'}
              </TableCell>
              <TableCell className="text-sm text-muted-foreground">
                {item.material_spec || '—'}
              </TableCell>
              <TableCell className="text-sm">
                {item.end_type || '—'}
              </TableCell>
              <TableCell className="text-right font-medium tabular-nums">
                {formatQty(item)}
              </TableCell>
              <TableCell
                className={cn(
                  'text-right tabular-nums text-sm font-medium',
                  confidenceClass(item.confidence)
                )}
              >
                {item.confidence !== null
                  ? item.confidence.toFixed(2)
                  : '—'}
              </TableCell>
              <TableCell className="text-xs text-muted-foreground max-w-[200px]">
                {item.remarks || ''}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
