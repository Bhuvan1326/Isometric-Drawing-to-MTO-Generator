'use client';

import { Ruler, GitBranch, Disc, ToggleLeft, CircleDot, Wrench } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import type { Summary } from '@/lib/api';
import { cn } from '@/lib/utils';

interface Props {
  summary: Summary;
}

interface CardDef {
  label: string;
  value: number;
  unit: string;
  icon: React.ComponentType<{ className?: string }>;
  accent: string;
}

export function SummaryCards({ summary }: Props) {
  const cards: CardDef[] = [
    {
      label: 'Total Pipe',
      value: summary.total_pipe_length_m,
      unit: 'm',
      icon: Ruler,
      accent: 'text-blue-600',
    },
    {
      label: 'Fittings',
      value: summary.fittings,
      unit: 'EA',
      icon: GitBranch,
      accent: 'text-emerald-600',
    },
    {
      label: 'Flanges',
      value: summary.flanges,
      unit: 'EA',
      icon: Disc,
      accent: 'text-amber-600',
    },
    {
      label: 'Valves',
      value: summary.valves,
      unit: 'EA',
      icon: ToggleLeft,
      accent: 'text-rose-600',
    },
    {
      label: 'Gaskets',
      value: summary.gaskets,
      unit: 'EA',
      icon: CircleDot,
      accent: 'text-cyan-600',
    },
    {
      label: 'Bolt Sets',
      value: summary.bolt_sets,
      unit: 'SET',
      icon: Wrench,
      accent: 'text-violet-600',
    },
  ];

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
      {cards.map((c) => (
        <Card key={c.label} className="overflow-hidden">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                {c.label}
              </span>
              <c.icon className={cn('h-4 w-4', c.accent)} />
            </div>
            <div className="mt-2 flex items-baseline gap-1">
              <span className="text-2xl font-semibold tabular-nums">
                {c.value}
              </span>
              <span className="text-xs text-muted-foreground">{c.unit}</span>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
